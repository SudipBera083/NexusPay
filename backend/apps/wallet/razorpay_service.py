"""
NexusPay Razorpay Service
==========================
Handles UPI/card payment collection via Razorpay.
On payment confirmation → auto-converts INR → USDC → sends on-chain to MetaMask.
"""
import hmac
import hashlib
import logging
import uuid
from decimal import Decimal

import razorpay
from django.conf import settings
from django.db import transaction

from .models import Wallet, WalletType
from .services import WalletService

logger = logging.getLogger("nexuspay")


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


class RazorpayDepositService:

    @staticmethod
    def create_payment_link(wallet: Wallet, amount_inr: Decimal, description: str = "") -> dict:
        """
        Creates a Razorpay Payment Link that Person A can open in GPay/PhonePe.
        Returns the short URL that can be shared or shown as QR.
        """
        client = get_razorpay_client()

        # Razorpay amounts are in paise (1 INR = 100 paise)
        amount_paise = int(amount_inr * 100)

        order_id = f"NEXUS-{uuid.uuid4().hex[:12].upper()}"

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": description or f"NexusPay deposit — {wallet.user.email}",
            "reference_id": order_id,
            "notify": {
                "sms": False,
                "email": False,
            },
            "reminder_enable": False,
            "notes": {
                "wallet_id": str(wallet.id),
                "user_email": wallet.user.email,
                "nexuspay_order_id": order_id,
            },
            "callback_url": f"{settings.FRONTEND_URL}/wallet?deposit=success",
            "callback_method": "get",
        }

        link = client.payment_link.create(payload)

        logger.info(
            f"[RAZORPAY] Payment link created: {link['id']} "
            f"| ₹{amount_inr} | User: {wallet.user.email}"
        )

        return {
            "payment_link_id": link["id"],
            "short_url": link["short_url"],
            "amount_inr": str(amount_inr),
            "reference_id": order_id,
            "status": link["status"],
        }

    @staticmethod
    def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
        """
        Verifies Razorpay webhook HMAC-SHA256 signature.
        MUST be called before processing any webhook event.
        """
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    @transaction.atomic
    def process_payment_captured(event_data: dict) -> bool:
        """
        Called when Razorpay fires payment.captured webhook.
        1. Credits INR to user's NexusPay wallet
        2. Immediately auto-converts INR → USDC at live rate
        3. Triggers on-chain USDC transfer to user's MetaMask
        """
        payment = event_data.get("payload", {}).get("payment", {}).get("entity", {})
        if not payment:
            logger.error("[RAZORPAY WEBHOOK] Missing payment entity in event")
            return False

        payment_id = payment.get("id")
        amount_paise = payment.get("amount", 0)
        notes = payment.get("notes", {})
        wallet_id = notes.get("wallet_id")
        reference_id = notes.get("nexuspay_order_id")

        if not wallet_id:
            logger.error(f"[RAZORPAY WEBHOOK] No wallet_id in notes for payment {payment_id}")
            return False

        # Idempotency: skip if already processed
        from .models import WalletTransaction
        if WalletTransaction.objects.filter(reference_id=f"RZP-{payment_id}").exists():
            logger.warning(f"[RAZORPAY WEBHOOK] Payment {payment_id} already processed. Skipping.")
            return True

        try:
            wallet = Wallet.objects.select_for_update().get(id=wallet_id)
        except Wallet.DoesNotExist:
            logger.error(f"[RAZORPAY WEBHOOK] Wallet {wallet_id} not found")
            return False

        amount_inr = Decimal(amount_paise) / 100

        # Step 1: Credit INR from external treasury (represents Razorpay settlement)
        treasury_inr = WalletService.get_treasury_wallet(WalletType.TREASURY_RESERVE_INR)
        WalletService.transfer(
            from_wallet=treasury_inr,
            to_wallet=wallet,
            currency="INR",
            amount=amount_inr,
            category="DEPOSIT",
            description=f"UPI deposit via Razorpay (Payment ID: {payment_id})",
            reference_id=f"RZP-{payment_id}",
            idempotency_key=f"RZP-DEPOSIT-{payment_id}",
            actor=wallet.user,
            metadata={
                "razorpay_payment_id": payment_id,
                "razorpay_reference": reference_id,
                "source": "UPI",
            },
        )

        logger.info(
            f"[RAZORPAY] ₹{amount_inr} credited to {wallet.user.email} "
            f"(Razorpay: {payment_id})"
        )

        # Step 2: Auto-convert INR → USDC and send on-chain to MetaMask
        if wallet.web3_address:
            RazorpayDepositService._auto_convert_and_send_onchain(
                wallet=wallet,
                amount_inr=amount_inr,
                razorpay_payment_id=payment_id,
            )

        return True

    @staticmethod
    def _auto_convert_and_send_onchain(wallet: Wallet, amount_inr: Decimal, razorpay_payment_id: str):
        """
        Converts INR → USDC internally and queues an on-chain transfer to user's MetaMask.
        """
        try:
            from apps.transactions.services import ConversionService
            conversion = ConversionService.convert(
                user=wallet.user,
                from_currency="INR",
                to_currency="USDC",
                amount=amount_inr,
                idempotency_key=f"RZP-CONV-{razorpay_payment_id}",
            )

            usdc_amount = conversion.to_amount
            logger.info(
                f"[RAZORPAY] Auto-converted ₹{amount_inr} → {usdc_amount} USDC "
                f"for {wallet.user.email}"
            )

            # Queue on-chain transfer task (async via Celery)
            from .tasks import send_usdc_to_metamask
            send_usdc_to_metamask.delay(
                wallet_id=str(wallet.id),
                usdc_amount=str(usdc_amount),
                to_address=wallet.web3_address,
                reference_id=f"RZP-ONCHAIN-{razorpay_payment_id}",
            )

        except Exception as e:
            logger.error(
                f"[RAZORPAY] Auto-conversion failed for {wallet.user.email}: {e}. "
                f"INR balance remains credited — user can manually convert."
            )
