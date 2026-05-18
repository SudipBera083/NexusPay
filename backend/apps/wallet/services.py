"""Wallet service layer — atomic credit/debit with ledger recording"""
import logging
import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import F

from core.exceptions import (
    InsufficientBalanceError,
    WalletNotFoundError,
    WalletLockedError,
)
from .models import Wallet, WalletTransaction, AuditLog, CurrencyChoice, TransactionType, TransactionStatus

logger = logging.getLogger("nexuspay")


class WalletService:

    @staticmethod
    def create_wallet(user) -> Wallet:
        """Create wallet on signup"""
        wallet, created = Wallet.objects.get_or_create(user=user)
        if created:
            logger.info(f"[WALLET] Created wallet for {user.email}")
            AuditLog.log(
                actor=user,
                action="WALLET_CREATED",
                resource_type="Wallet",
                resource_id=str(wallet.id),
                after={"user": str(user.id)},
            )
        return wallet

    @staticmethod
    def get_wallet(user) -> Wallet:
        try:
            return Wallet.objects.select_for_update().get(user=user, is_active=True)
        except Wallet.DoesNotExist:
            raise WalletNotFoundError()

    @staticmethod
    @transaction.atomic
    def credit(
        wallet: Wallet,
        currency: str,
        amount: Decimal,
        category: str,
        description: str = "",
        reference_id: str = "",
        metadata: dict = None,
        actor=None,
    ) -> WalletTransaction:
        """Credit funds to wallet — atomic, ledger-based"""
        if wallet.is_locked:
            raise WalletLockedError(f"Wallet locked: {wallet.lock_reason}")

        # Lock row
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        balance_before = wallet.get_balance(currency)
        balance_after = balance_before + amount

        # Update balance
        if currency == CurrencyChoice.INR:
            wallet.inr_balance = balance_after
        else:
            wallet.usdt_balance = balance_after
        wallet.save(update_fields=["inr_balance" if currency == CurrencyChoice.INR else "usdt_balance", "updated_at"])

        # Write ledger record
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=TransactionType.CREDIT,
            currency=currency,
            category=category,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id or str(uuid.uuid4()),
            status=TransactionStatus.COMPLETED,
            metadata=metadata or {},
        )

        logger.info(f"[CREDIT] {currency} {amount} → wallet {wallet.id} | bal: {balance_before}→{balance_after}")
        return tx

    @staticmethod
    @transaction.atomic
    def debit(
        wallet: Wallet,
        currency: str,
        amount: Decimal,
        category: str,
        description: str = "",
        reference_id: str = "",
        metadata: dict = None,
        actor=None,
    ) -> WalletTransaction:
        """Debit funds from wallet — atomic with balance check"""
        if wallet.is_locked:
            raise WalletLockedError(f"Wallet locked: {wallet.lock_reason}")

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        balance_before = wallet.get_balance(currency)
        if balance_before < amount:
            raise InsufficientBalanceError(
                f"Insufficient {currency} balance. Available: {balance_before}, Required: {amount}"
            )

        balance_after = balance_before - amount

        if currency == CurrencyChoice.INR:
            wallet.inr_balance = balance_after
        else:
            wallet.usdt_balance = balance_after
        wallet.save(update_fields=["inr_balance" if currency == CurrencyChoice.INR else "usdt_balance", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=TransactionType.DEBIT,
            currency=currency,
            category=category,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id or str(uuid.uuid4()),
            status=TransactionStatus.COMPLETED,
            metadata=metadata or {},
        )

        logger.info(f"[DEBIT] {currency} {amount} ← wallet {wallet.id} | bal: {balance_before}→{balance_after}")
        return tx

    @staticmethod
    @transaction.atomic
    def reverse_transaction(tx_id: str, actor=None) -> WalletTransaction:
        """Reverse a completed transaction"""
        try:
            original_tx = WalletTransaction.objects.select_for_update().get(
                id=tx_id, status=TransactionStatus.COMPLETED
            )
        except WalletTransaction.DoesNotExist:
            raise ValueError("Transaction not found or already reversed")

        wallet = Wallet.objects.select_for_update().get(pk=original_tx.wallet_id)

        # Reverse: if original was debit, credit back; if credit, debit back
        if original_tx.transaction_type == TransactionType.DEBIT:
            reversal_type = TransactionType.CREDIT
            if original_tx.currency == CurrencyChoice.INR:
                wallet.inr_balance += original_tx.amount
                new_balance = wallet.inr_balance
                wallet.save(update_fields=["inr_balance", "updated_at"])
            else:
                wallet.usdt_balance += original_tx.amount
                new_balance = wallet.usdt_balance
                wallet.save(update_fields=["usdt_balance", "updated_at"])
        else:
            reversal_type = TransactionType.DEBIT
            if original_tx.currency == CurrencyChoice.INR:
                wallet.inr_balance -= original_tx.amount
                new_balance = wallet.inr_balance
                wallet.save(update_fields=["inr_balance", "updated_at"])
            else:
                wallet.usdt_balance -= original_tx.amount
                new_balance = wallet.usdt_balance
                wallet.save(update_fields=["usdt_balance", "updated_at"])

        reversal_tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=reversal_type,
            currency=original_tx.currency,
            category="REVERSAL",
            amount=original_tx.amount,
            balance_before=original_tx.balance_after,
            balance_after=new_balance,
            description=f"Reversal of transaction {original_tx.id}",
            reference_id=f"REV-{original_tx.reference_id}",
            status=TransactionStatus.COMPLETED,
            related_transaction=original_tx,
        )

        original_tx.status = TransactionStatus.REVERSED
        original_tx.save(update_fields=["status"])

        logger.info(f"[REVERSAL] Transaction {tx_id} reversed → new tx {reversal_tx.id}")
        return reversal_tx

    @staticmethod
    def simulate_deposit(wallet: Wallet, currency: str, amount: Decimal, actor=None) -> WalletTransaction:
        """Simulate fiat/crypto deposit — for demo purposes"""
        return WalletService.credit(
            wallet=wallet,
            currency=currency,
            amount=amount,
            category="DEPOSIT",
            description=f"Simulated {currency} deposit",
            metadata={"source": "simulation"},
            actor=actor,
        )
