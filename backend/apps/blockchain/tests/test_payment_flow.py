from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.test import TransactionTestCase

from django.contrib.auth import get_user_model

User = get_user_model()
from apps.wallet.models import Wallet, WalletType
from apps.merchants.models import Merchant, MerchantQRCode, MerchantStatus, QRCodeStatus
from apps.transactions.models import PaymentTransaction, PaymentStatus
from apps.blockchain.tasks import poll_pending_transactions
from apps.transactions.services import PaymentService

class TestPaymentFlow(TransactionTestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="password", first_name="User", last_name="Test")
        Wallet.objects.create(user=self.user, type=WalletType.USER)
        
        internal_wallet = Wallet.objects.create(type=WalletType.MERCHANT)
        self.merchant = Merchant.objects.create(
            user=self.user,
            name="Test Merchant",
            wallet_address="0x1234567890123456789012345678901234567890",
            internal_wallet=internal_wallet,
            status=MerchantStatus.ACTIVE
        )
        
        self.qr_code = MerchantQRCode.objects.create(
            merchant=self.merchant,
            merchant_wallet_address=self.merchant.wallet_address,
            amount_usdc=Decimal("10.00"),
            nonce="testnonce123",
            expires_at=timezone.now() + timedelta(minutes=5),
            status=QRCodeStatus.ACTIVE
        )
    
    def test_initiate_qr_payment_success(self):
        """Test payment creation sets status to CREATED"""
        payment = PaymentService.initiate_qr_payment(self.user, self.qr_code.nonce)
        self.assertEqual(payment.status, PaymentStatus.CREATED)
        self.assertEqual(payment.amount_inr, Decimal("0.00"))

    def test_initiate_expired_qr_fails(self):
        """Test scanning expired QR fails"""
        self.qr_code.expires_at = timezone.now() - timedelta(minutes=1)
        self.qr_code.save()
        with self.assertRaisesMessage(ValueError, "QR code is expired"):
            PaymentService.initiate_qr_payment(self.user, self.qr_code.nonce)

    def test_initiate_consumed_qr_fails(self):
        """Test scanning consumed QR fails (Replay attack prevention)"""
        self.qr_code.is_consumed = True
        self.qr_code.save()
        with self.assertRaisesMessage(ValueError, "QR code has already been consumed"):
            PaymentService.initiate_qr_payment(self.user, self.qr_code.nonce)

    def test_submit_blockchain_signature(self):
        """Test signature submission links tx_hash and sets status to SUBMITTED"""
        payment = PaymentService.initiate_qr_payment(self.user, self.qr_code.nonce)
        tx_hash = "0xtest123"
        
        updated_payment = PaymentService.submit_blockchain_signature(
            payment_id=payment.id, 
            user=self.user, 
            tx_hash=tx_hash, 
            wallet_address="0xUserWalletAddress"
        )
        
        self.assertEqual(updated_payment.status, PaymentStatus.SUBMITTED)
        self.assertEqual(updated_payment.blockchain_tx_hash, tx_hash)

    def test_submit_duplicate_tx_hash_fails(self):
        """Test submitting the same tx_hash twice fails (Duplicate transaction prevention)"""
        payment1 = PaymentService.initiate_qr_payment(self.user, self.qr_code.nonce)
        tx_hash = "0xtestduplicate"
        PaymentService.submit_blockchain_signature(payment1.id, self.user, tx_hash, "0xW")
        
        # Create a second QR and payment
        qr_code2 = MerchantQRCode.objects.create(
            merchant=self.merchant,
            merchant_wallet_address=self.merchant.wallet_address,
            amount_usdc=Decimal("10.00"),
            nonce="testnonce456",
            expires_at=timezone.now() + timedelta(minutes=5),
            status=QRCodeStatus.ACTIVE
        )
        payment2 = PaymentService.initiate_qr_payment(self.user, qr_code2.nonce)
        
        with self.assertRaisesMessage(ValueError, "Transaction hash already submitted for another payment"):
            PaymentService.submit_blockchain_signature(payment2.id, self.user, tx_hash, "0xW")

    @patch('apps.blockchain.indexer.BlockchainIndexer.check_transaction')
    @patch('apps.blockchain.indexer.BlockchainIndexer.verify_payment_transfer')
    def test_indexer_worker_settles_confirmed_payment(self, mock_verify, mock_check):
        """Test that the celery worker correctly settles a SUBMITTED payment after 3 confirmations"""
        payment = PaymentService.initiate_qr_payment(self.user, self.qr_code.nonce)
        PaymentService.submit_blockchain_signature(payment.id, self.user, "0xconfirmedtx", "0xW")
        
        # Mock indexer responses for 3 confirmations and exact match
        mock_check.return_value = {
            "status": "CONFIRMED",
            "confirmations": 3,
            "receipt": {}
        }
        mock_verify.return_value = {
            "valid": True,
            "transfer": {}
        }
        
        poll_pending_transactions()
        
        payment = PaymentTransaction.objects.get(id=payment.id)
        self.qr_code.refresh_from_db()
        
        self.assertEqual(payment.status, PaymentStatus.CONFIRMED)
        self.assertTrue(self.qr_code.is_consumed)
        self.assertEqual(self.qr_code.status, "COMPLETED")
        
        # Verify ledger entry was created
        merchant_wallet = self.qr_code.merchant.internal_wallet
        merchant_wallet.refresh_from_db()
        self.assertGreater(merchant_wallet.get_balance("USDC"), Decimal("0"))
