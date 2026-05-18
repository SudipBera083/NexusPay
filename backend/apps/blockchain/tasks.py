"""
Blockchain Celery Tasks
=======================
Background workers for:
- Polling pending transaction confirmations
- Expiring stale QR codes
- Provider health checking
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from decimal import Decimal

logger = logging.getLogger("nexuspay.blockchain")

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def poll_pending_transactions(self):
    """
    Every 15s: Iterate SUBMITTED payments.
    Use select_for_update(skip_locked=True) to prevent duplicate processing.
    Check status via indexer.
    On CONFIRMED (>= 3 confs): verify ERC20 transfer exactly and update ledger idempotently.
    On timeout (e.g., 1 hour): mark FAILED.
    """
    from apps.transactions.models import PaymentTransaction, PaymentStatus
    from apps.blockchain.indexer import get_indexer
    from apps.wallet.services import WalletService
    from apps.wallet.models import Wallet
    from core.events import EventDispatcher, DomainEventType

    # Timeout threshold for stuck transactions (1 hour)
    timeout_threshold = timezone.now() - timezone.timedelta(hours=1)

    with transaction.atomic():
        # Fetch up to 50 SUBMITTED transactions, locking them for this worker
        pending_payments = PaymentTransaction.objects.select_for_update(skip_locked=True).filter(
            status=PaymentStatus.SUBMITTED
        )[:50]

        if not pending_payments:
            return {"checked": 0, "message": "No pending transactions"}

        indexer = get_indexer()
        results = {"checked": 0, "confirmed": 0, "failed": 0, "pending": 0}

        for payment in pending_payments:
            try:
                # 1. Check for timeout
                if payment.updated_at < timeout_threshold:
                    logger.warning(f"Payment {payment.id} timed out waiting for confirmations.")
                    payment.transition_to(PaymentStatus.FAILED)
                    results["failed"] += 1
                    continue

                if not payment.blockchain_tx_hash:
                    logger.error(f"Payment {payment.id} is SUBMITTED but has no tx_hash")
                    payment.transition_to(PaymentStatus.FAILED)
                    results["failed"] += 1
                    continue

                # 2. Check blockchain status
                check = indexer.check_transaction(payment.blockchain_tx_hash)
                status = check["status"]
                
                # We require strictly 3 confirmations
                if status == "FAILED":
                    payment.transition_to(PaymentStatus.FAILED)
                    results["failed"] += 1
                    continue
                    
                if status in ["MEMPOOL_PENDING", "CONFIRMING"]:
                    results["pending"] += 1
                    continue
                    
                if status == "CONFIRMED":
                    # 3. Finality reached, verify ERC20 Transfer
                    qr_code = payment.qr_code
                    receipt = check.get("receipt")
                    
                    verification = indexer.verify_payment_transfer(
                        receipt=receipt,
                        expected_to=qr_code.merchant_wallet_address,
                        expected_amount=qr_code.amount_usdc,
                        tolerance_pct=Decimal("0.00") # Exact matching enforced
                    )
                    
                    if not verification["valid"]:
                        logger.error(f"Verification failed for {payment.id}: {verification['reason']}")
                        payment.transition_to(PaymentStatus.FAILED)
                        results["failed"] += 1
                        continue
                        
                    # 4. Idempotent Ledger Update
                    # Prevent duplicate settlement by checking if a WalletTransaction already exists for this payment
                    from apps.wallet.models import WalletTransaction
                    existing_tx = WalletTransaction.objects.filter(metadata__payment_id=str(payment.id)).exists()
                    
                    if not existing_tx:
                        # Create the ledger entries
                        # Calculate exact fee
                        fee_pct = qr_code.merchant.get_fee_pct() / Decimal("100")
                        fee_amount = (qr_code.amount_usdc * fee_pct).quantize(Decimal("0.000001"))
                        net_amount = qr_code.amount_usdc - fee_amount
                        
                        # Double entry: Credit Merchant's internal wallet from the Settlement Treasury
                        settlement_treasury, _ = Wallet.objects.get_or_create(
                            type="TREASURY_EXTERNAL", 
                            defaults={"user": None}
                        )
                        
                        WalletService.transfer(
                            from_wallet=settlement_treasury,
                            to_wallet=qr_code.merchant.internal_wallet,
                            currency="USDC",
                            amount=net_amount,
                            category="PAYMENT",
                            description=f"Web3 Payment from {payment.user.email}",
                            reference_id=f"SETTLE-{payment.id}",
                            idempotency_key=f"SETTLE-{payment.id}",
                            metadata={"payment_id": str(payment.id), "tx_hash": payment.blockchain_tx_hash}
                        )
                        
                        # Note: In a fully modeled treasury, the fee would be routed to a TREASURY_FEES wallet here.
                    
                    # 5. Consume QR and finalize
                    qr_code.is_consumed = True
                    qr_code.status = "COMPLETED"
                    qr_code.save(update_fields=["is_consumed", "status"])
                    
                    payment.transition_to(PaymentStatus.CONFIRMED)
                    results["confirmed"] += 1
                    
                    logger.info(f"[SETTLEMENT] Completed payment {payment.id} for {qr_code.amount_usdc} USDC")

            except Exception as e:
                logger.error(f"Error processing payment {payment.id}: {e}")

        logger.info(f"[INDEXER] Poll complete: {results}")
        return results

@shared_task
def expire_stale_qr_codes():
    """
    Every 5 minutes: Expire QR codes past their expiry timestamp.
    Prevents replay attacks with stale QR codes.
    """
    from apps.merchants.models import MerchantQRCode

    expired = MerchantQRCode.objects.filter(
        status="ACTIVE",
        expires_at__lt=timezone.now(),
    )
    count = expired.update(status="EXPIRED")
    if count:
        logger.info(f"[QR] Expired {count} stale QR codes")
    return {"expired": count}


@shared_task
def blockchain_provider_health_check():
    """Every 5 minutes: Check health of all configured providers and log results"""
    from core.blockchain.provider import get_provider
    provider = get_provider()
    health = provider.health_check()
    logger.info(f"[PROVIDER HEALTH] {health}")
    return health
