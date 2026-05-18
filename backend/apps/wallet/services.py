"""Wallet service layer — atomic double-entry transfer, audit logging, and WS notifications"""
import logging
import uuid
from decimal import Decimal
from django.db import transaction

from core.exceptions import (
    InsufficientBalanceError,
    WalletNotFoundError,
    WalletLockedError,
)
from .models import Wallet, WalletType, WalletTransaction, JournalEntry, AuditLog, CurrencyChoice, TransactionType, TransactionStatus

logger = logging.getLogger("nexuspay")


class WalletService:

    @staticmethod
    def get_treasury_wallet(wallet_type: str) -> Wallet:
        """Get or create a specialized treasury/merchant wallet"""
        wallet, _ = Wallet.objects.get_or_create(type=wallet_type)
        return wallet

    @staticmethod
    def create_wallet(user) -> Wallet:
        """Create wallet on signup"""
        wallet, created = Wallet.objects.get_or_create(user=user, type=WalletType.USER)
        if created:
            logger.info(f"[WALLET] Created wallet for {user.email}")
            AuditLog.log(
                actor=user,
                action="WALLET_CREATED",
                resource_type="Wallet",
                resource_id=str(wallet.id),
                after={"user": str(user.id), "inr_balance": "0.00", "usdt_balance": "0.00000000"},
            )
        return wallet

    @staticmethod
    def get_wallet(user) -> Wallet:
        """Get user wallet"""
        try:
            return Wallet.objects.get(user=user, is_active=True, type=WalletType.USER)
        except Wallet.DoesNotExist:
            raise WalletNotFoundError()

    @staticmethod
    @transaction.atomic
    def transfer(
        from_wallet: Wallet,
        to_wallet: Wallet,
        currency: str,
        amount: Decimal,
        category: str,
        description: str = "",
        reference_id: str = "",
        idempotency_key: str = None,
        metadata: dict = None,
        actor=None,
    ) -> JournalEntry:
        """
        Atomic Double-Entry Transfer
        Debits from_wallet and Credits to_wallet within a single JournalEntry.
        """
        if from_wallet.is_locked:
            raise WalletLockedError(f"Source Wallet locked: {from_wallet.lock_reason}")
        if to_wallet.is_locked:
            raise WalletLockedError(f"Destination Wallet locked: {to_wallet.lock_reason}")

        # Idempotency check
        if idempotency_key:
            existing = WalletTransaction.objects.filter(idempotency_key=f"{idempotency_key}-DR").first()
            if existing:
                logger.info(f"[IDEMPOTENCY] Replaying transaction for key {idempotency_key}")
                return existing.journal_entry

        # Lock both wallets in deterministic order by PK to prevent deadlocks
        wallets = list(Wallet.objects.select_for_update().filter(pk__in=[from_wallet.pk, to_wallet.pk]).order_by('pk'))
        
        # Ensure we don't try to transfer to the exact same wallet
        if from_wallet.pk == to_wallet.pk:
            raise ValueError("Cannot transfer to the same wallet")

        locked_from = next(w for w in wallets if w.pk == from_wallet.pk)
        locked_to = next(w for w in wallets if w.pk == to_wallet.pk)

        # Balance check
        if locked_from.type != WalletType.TREASURY_EXTERNAL:
            if locked_from.get_balance(currency) < amount:
                raise InsufficientBalanceError(
                    f"Insufficient {currency} balance in {locked_from.type}. Available: {locked_from.get_balance(currency)}, Required: {amount}"
                )

        journal = JournalEntry.objects.create(description=description)
        ref = reference_id or str(uuid.uuid4())

        # 1. Debit
        balance_before_from = locked_from.get_balance(currency)
        balance_after_from = balance_before_from - amount
        locked_from.set_balance(currency, balance_after_from)
        locked_from.save(update_fields=[locked_from.balance_field(currency), "updated_at"])

        tx_debit = WalletTransaction.objects.create(
            journal_entry=journal,
            wallet=locked_from,
            transaction_type=TransactionType.DEBIT,
            currency=currency,
            category=category,
            amount=amount,
            balance_before=balance_before_from,
            balance_after=balance_after_from,
            description=description,
            reference_id=ref,
            idempotency_key=f"{idempotency_key}-DR" if idempotency_key else None,
            status=TransactionStatus.COMPLETED,
            metadata=metadata or {},
        )

        # 2. Credit
        balance_before_to = locked_to.get_balance(currency)
        balance_after_to = balance_before_to + amount
        locked_to.set_balance(currency, balance_after_to)
        locked_to.save(update_fields=[locked_to.balance_field(currency), "updated_at"])

        tx_credit = WalletTransaction.objects.create(
            journal_entry=journal,
            wallet=locked_to,
            transaction_type=TransactionType.CREDIT,
            currency=currency,
            category=category,
            amount=amount,
            balance_before=balance_before_to,
            balance_after=balance_after_to,
            description=description,
            reference_id=ref,
            idempotency_key=f"{idempotency_key}-CR" if idempotency_key else None,
            status=TransactionStatus.COMPLETED,
            metadata=metadata or {},
        )

        # Audit Log
        AuditLog.log(
            actor=actor,
            action=f"DOUBLE_ENTRY_TRANSFER_{currency}",
            resource_type="JournalEntry",
            resource_id=str(journal.id),
            before={"from_bal": str(balance_before_from), "to_bal": str(balance_before_to)},
            after={"from_bal": str(balance_after_from), "to_bal": str(balance_after_to), "amount": str(amount)},
        )

        logger.info(f"[TRANSFER] {currency} {amount} | {locked_from.type}({locked_from.id}) → {locked_to.type}({locked_to.id}) | J-ID: {journal.id}")

        # WebSockets
        if locked_from.type == WalletType.USER:
            transaction.on_commit(lambda: _fire_wallet_update(locked_from))
        if locked_to.type == WalletType.USER:
            transaction.on_commit(lambda: _fire_wallet_update(locked_to))

        return journal

    @staticmethod
    @transaction.atomic
    def reverse_journal(journal_id: str, actor=None) -> JournalEntry:
        """Reverse an entire double-entry journal"""
        try:
            original_journal = JournalEntry.objects.get(id=journal_id)
        except JournalEntry.DoesNotExist:
            raise ValueError("Journal not found")

        txs = original_journal.transactions.all()
        if not txs or any(t.status == TransactionStatus.REVERSED for t in txs):
            raise ValueError("Journal already reversed or invalid")

        original_debit = next(t for t in txs if t.transaction_type == TransactionType.DEBIT)
        original_credit = next(t for t in txs if t.transaction_type == TransactionType.CREDIT)

        # To reverse, we transfer back from the credited wallet to the debited wallet
        reversal_journal = WalletService.transfer(
            from_wallet=original_credit.wallet,
            to_wallet=original_debit.wallet,
            currency=original_debit.currency,
            amount=original_debit.amount,
            category="REVERSAL",
            description=f"Reversal of Journal {original_journal.id}",
            reference_id=f"REV-{original_debit.reference_id}",
            actor=actor,
        )

        for tx in txs:
            tx.status = TransactionStatus.REVERSED
            tx.save(update_fields=["status"])

        return reversal_journal

    @staticmethod
    def simulate_deposit(wallet: Wallet, currency: str, amount: Decimal, actor=None) -> JournalEntry:
        """Simulate fiat/crypto deposit by routing from EXTERNAL TREASURY"""
        treasury = WalletService.get_treasury_wallet(WalletType.TREASURY_EXTERNAL)
        return WalletService.transfer(
            from_wallet=treasury,
            to_wallet=wallet,
            currency=currency,
            amount=amount,
            category="DEPOSIT",
            description=f"Simulated {currency} deposit",
            metadata={"source": "simulation"},
            actor=actor,
        )

    @staticmethod
    def withdraw_to_web3(wallet: Wallet, amount: Decimal, actor=None) -> JournalEntry:
        """Process an external Web3 USDT withdrawal via Double-Entry routing"""
        if not wallet.web3_address:
            raise ValueError("Wallet does not have a linked Web3 address")
        
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero")

        treasury = WalletService.get_treasury_wallet(WalletType.TREASURY_EXTERNAL)
        
        return WalletService.transfer(
            from_wallet=wallet,
            to_wallet=treasury,
            currency=CurrencyChoice.USDT,
            amount=amount,
            category="WITHDRAWAL",
            description=f"External withdrawal to {wallet.web3_address}",
            metadata={"destination_address": wallet.web3_address},
            actor=actor,
        )


def _fire_wallet_update(wallet: Wallet):
    """Fire Celery task to push updated balance via WebSocket (called after commit)"""
    if wallet.type != WalletType.USER or not wallet.user_id:
        return
    try:
        from apps.notifications.tasks import notify_wallet_update
        wallet.refresh_from_db()
        notify_wallet_update.delay(
            user_id=str(wallet.user_id),
            inr_balance=str(wallet.inr_balance),
            usdt_balance=str(wallet.usdt_balance),
        )
    except Exception as e:
        logger.warning(f"[WS NOTIFY] Could not fire wallet update: {e}")
