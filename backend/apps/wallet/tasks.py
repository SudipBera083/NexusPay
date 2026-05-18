"""
Wallet Celery Tasks
====================
- send_usdc_to_metamask: Transfers USDC on-chain to user's MetaMask (Polygon)
"""
import logging
from decimal import Decimal
from celery import shared_task
from django.conf import settings

logger = logging.getLogger("nexuspay")


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    name="wallet.send_usdc_to_metamask",
)
def send_usdc_to_metamask(self, wallet_id: str, usdc_amount: str, to_address: str, reference_id: str):
    """
    Sends real USDC on-chain from the NexusPay treasury to a user's MetaMask address on Polygon.

    Requirements for production:
    - TREASURY_PRIVATE_KEY env var (treasury EVM wallet that holds USDC)
    - Sufficient MATIC for gas
    - Sufficient USDC in treasury

    On testnet (Polygon Amoy): uses USDC contract 0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582
    On mainnet (Polygon): uses USDC contract 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
    """
    from apps.wallet.models import Wallet
    from core.blockchain.provider import get_web3_provider

    try:
        wallet = Wallet.objects.get(id=wallet_id)
        user = wallet.user
        amount = Decimal(usdc_amount)

        logger.info(f"[ON-CHAIN] Sending {amount} USDC to {to_address} for {user.email}")

        # ── Get Web3 provider ──────────────────────────────────────────────────
        w3 = get_web3_provider()
        if not w3 or not w3.is_connected():
            raise Exception("Web3 provider unavailable")

        # ── Treasury private key ───────────────────────────────────────────────
        treasury_private_key = settings.TREASURY_PRIVATE_KEY
        if not treasury_private_key:
            raise Exception("TREASURY_PRIVATE_KEY not configured. Cannot send on-chain.")

        treasury_account = w3.eth.account.from_key(treasury_private_key)
        treasury_address = treasury_account.address

        # ── USDC ERC20 ABI (minimal Transfer) ─────────────────────────────────
        ERC20_ABI = [
            {
                "name": "transfer",
                "type": "function",
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"},
                ],
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
            },
            {
                "name": "balanceOf",
                "type": "function",
                "inputs": [{"name": "_owner", "type": "address"}],
                "outputs": [{"name": "balance", "type": "uint256"}],
                "stateMutability": "view",
            },
            {
                "name": "decimals",
                "type": "function",
                "inputs": [],
                "outputs": [{"name": "", "type": "uint8"}],
                "stateMutability": "view",
            },
        ]

        usdc_contract_address = settings.BLOCKCHAIN_CONFIG.get("usdc_contract_address")
        contract = w3.eth.contract(
            address=w3.to_checksum_address(usdc_contract_address),
            abi=ERC20_ABI,
        )

        # ── Get USDC decimals (6 for USDC, not 18) ────────────────────────────
        decimals = contract.functions.decimals().call()
        raw_amount = int(amount * (10 ** decimals))

        # ── Check treasury balance ─────────────────────────────────────────────
        treasury_balance = contract.functions.balanceOf(treasury_address).call()
        if treasury_balance < raw_amount:
            raise Exception(
                f"Treasury USDC balance insufficient. "
                f"Have: {treasury_balance / 10**decimals}, Need: {amount}"
            )

        # ── Build and send transaction ─────────────────────────────────────────
        nonce = w3.eth.get_transaction_count(treasury_address)
        gas_price = w3.eth.gas_price

        txn = contract.functions.transfer(
            w3.to_checksum_address(to_address),
            raw_amount,
        ).build_transaction({
            "chainId": settings.BLOCKCHAIN_CONFIG.get("chain_id", 80002),
            "gas": 100000,
            "gasPrice": gas_price,
            "nonce": nonce,
        })

        signed_txn = w3.eth.account.sign_transaction(txn, private_key=treasury_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_hash_hex = tx_hash.hex()

        logger.info(
            f"[ON-CHAIN] USDC transfer submitted: {tx_hash_hex} "
            f"| {amount} USDC → {to_address}"
        )

        # ── Wait for confirmation ──────────────────────────────────────────────
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] == 1:
            logger.info(f"[ON-CHAIN] ✅ Transfer confirmed: {tx_hash_hex}")

            # Record on-chain transfer in ledger
            _record_onchain_transfer(
                wallet=wallet,
                usdc_amount=amount,
                tx_hash=tx_hash_hex,
                to_address=to_address,
                reference_id=reference_id,
            )
        else:
            raise Exception(f"Transaction reverted on-chain: {tx_hash_hex}")

    except Exception as exc:
        logger.error(f"[ON-CHAIN] Transfer failed for {wallet_id}: {exc}")
        raise self.retry(exc=exc)


def _record_onchain_transfer(wallet, usdc_amount: Decimal, tx_hash: str, to_address: str, reference_id: str):
    """Records the on-chain USDC transfer as a wallet debit (it left the internal balance)."""
    from apps.wallet.models import WalletType
    from apps.wallet.services import WalletService

    try:
        treasury_usdc = WalletService.get_treasury_wallet(WalletType.TREASURY_USDC_RESERVE)
        WalletService.transfer(
            from_wallet=wallet,
            to_wallet=treasury_usdc,
            currency="USDC",
            amount=usdc_amount,
            category="WITHDRAWAL",
            description=f"On-chain USDC sent to MetaMask ({to_address[:10]}...)",
            reference_id=reference_id,
            idempotency_key=f"ONCHAIN-{tx_hash}",
            actor=wallet.user,
            metadata={"tx_hash": tx_hash, "to_address": to_address, "on_chain": True},
        )
        logger.info(f"[ON-CHAIN] Ledger debit recorded for {tx_hash}")
    except Exception as e:
        logger.error(f"[ON-CHAIN] Failed to record ledger debit: {e}")
