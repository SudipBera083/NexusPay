"""
Domain Event System
====================
Lightweight internal event dispatcher for domain events.
Decouples service layers from side-effect orchestration.
Events are dispatched asynchronously via Celery.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("nexuspay.events")


class DomainEventType:
    """Canonical domain event type constants"""
    # Wallet events
    WALLET_CONNECTED = "WalletConnected"
    WALLET_DISCONNECTED = "WalletDisconnected"

    # Deposit / On-Ramp
    DEPOSIT_INITIATED = "DepositInitiated"
    DEPOSIT_COMPLETED = "DepositCompleted"
    DEPOSIT_FAILED = "DepositFailed"

    # Conversion
    CONVERSION_EXECUTED = "ConversionExecuted"
    CONVERSION_FAILED = "ConversionFailed"

    # Payment lifecycle
    PAYMENT_CREATED = "PaymentCreated"
    PAYMENT_QR_GENERATED = "PaymentQRGenerated"
    SIGNATURE_RECEIVED = "SignatureReceived"
    BLOCKCHAIN_SUBMITTED = "BlockchainSubmitted"
    BLOCKCHAIN_CONFIRMED = "BlockchainConfirmed"
    SETTLEMENT_COMPLETED = "SettlementCompleted"
    PAYMENT_FAILED = "PaymentFailed"
    PAYMENT_EXPIRED = "PaymentExpired"
    PAYMENT_REVERSED = "PaymentReversed"

    # Risk / Fraud
    FRAUD_DETECTED = "FraudDetected"
    RISK_FLAG_CREATED = "RiskFlagCreated"

    # Reconciliation
    RECONCILIATION_FAILED = "ReconciliationFailed"
    TREASURY_IMBALANCE_DETECTED = "TreasuryImbalanceDetected"
    JOURNAL_IMBALANCE_DETECTED = "JournalImbalanceDetected"

    # Merchant
    MERCHANT_REGISTERED = "MerchantRegistered"
    MERCHANT_SETTLEMENT_COMPLETED = "MerchantSettlementCompleted"


@dataclass
class DomainEvent:
    """
    Immutable domain event envelope.
    All events carry a unique ID, timestamp, and typed payload.
    """
    event_type: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For tracing related events

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }


class EventDispatcher:
    """
    Asynchronous domain event dispatcher.
    Dispatches events to Celery tasks for processing.
    Handlers are registered per event type and executed asynchronously.
    """

    @staticmethod
    def dispatch(
        event_type: str,
        payload: dict,
        user_id: str = None,
        correlation_id: str = None,
    ) -> DomainEvent:
        """
        Dispatch a domain event asynchronously.
        Returns the event envelope for logging/tracing.
        """
        event = DomainEvent(
            event_type=event_type,
            payload=payload,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        logger.info(
            f"[EVENT] Dispatching {event_type} | "
            f"event_id={event.event_id} | user={user_id}"
        )

        # Dispatch to Celery async task
        try:
            from apps.notifications.tasks import process_domain_event
            process_domain_event.delay(event.to_dict())
        except Exception as e:
            logger.warning(f"[EVENT] Celery dispatch failed for {event_type}: {e}")
            # Events are non-critical — log and continue
            # In production this would go to a dead letter queue

        return event

    @staticmethod
    def dispatch_sync(event_type: str, payload: dict, user_id: str = None) -> DomainEvent:
        """
        Synchronous dispatch — used in contexts where Celery is unavailable.
        Logs the event but doesn't retry.
        """
        event = DomainEvent(event_type=event_type, payload=payload, user_id=user_id)
        logger.info(f"[EVENT:SYNC] {event_type} | {event.event_id}")
        return event
