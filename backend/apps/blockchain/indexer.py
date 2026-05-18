"""
Blockchain Indexer
==================
Polls the blockchain via the provider abstraction layer to:
- Monitor pending transactions until confirmation
- Decode ERC20 Transfer logs
- Verify amount and recipient match the payment intent
- Detect dropped/reorged transactions
"""
import logging
from decimal import Decimal
from django.utils import timezone
from django.conf import settings

from core.blockchain.provider import get_provider

logger = logging.getLogger("nexuspay.blockchain")


class ERC20Decoder:
    """Decodes raw ERC20 Transfer event logs into structured data"""

    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    @staticmethod
    def decode_transfer_log(log: dict) -> dict | None:
        """
        Decode ERC20 Transfer(address indexed from, address indexed to, uint256 value) log.
        Returns structured transfer data or None if not an ERC20 Transfer.
        """
        topics = log.get("topics", [])
        if not topics or topics[0].lower() != ERC20Decoder.TRANSFER_TOPIC:
            return None

        if len(topics) < 3:
            return None

        try:
            # Topics[1] = from address (padded to 32 bytes)
            from_address = "0x" + topics[1][-40:]
            # Topics[2] = to address (padded to 32 bytes)
            to_address = "0x" + topics[2][-40:]
            # Data = uint256 value (hex)
            raw_value = int(log.get("data", "0x0"), 16)

            decimals = settings.BLOCKCHAIN_CONFIG["USDC_TOKEN_DECIMALS"]
            amount_human = Decimal(raw_value) / Decimal(10 ** decimals)

            return {
                "from_address": from_address.lower(),
                "to_address": to_address.lower(),
                "amount_raw": str(raw_value),
                "amount_human": str(amount_human),
                "token_contract": log.get("address", "").lower(),
                "block_number": int(log.get("blockNumber", "0x0"), 16),
                "tx_hash": log.get("transactionHash", "").lower(),
                "log_index": int(log.get("logIndex", "0x0"), 16),
            }
        except (ValueError, KeyError, IndexError) as e:
            logger.warning(f"[INDEXER] Failed to decode ERC20 log: {e}")
            return None


class BlockchainIndexer:
    """
    Core blockchain indexer — monitors on-chain activity and drives
    the payment settlement pipeline.
    Provider-agnostic: delegates all RPC calls to get_provider().
    """

    def __init__(self):
        self.provider = get_provider()
        self.bc_config = settings.BLOCKCHAIN_CONFIG
        self.required_confirmations = self.bc_config["REQUIRED_CONFIRMATIONS"]
        self.usdc_contract = self.bc_config["USDC_CONTRACT_ADDRESS"].lower()

    def get_current_block(self) -> int | None:
        """Fetch latest block number"""
        response = self.provider.get_block_number()
        if response.success and response.data:
            try:
                return int(response.data, 16)
            except (ValueError, TypeError):
                pass
        return None

    def get_receipt(self, tx_hash: str) -> dict | None:
        """Fetch transaction receipt from the network"""
        response = self.provider.get_transaction_receipt(tx_hash)
        if response.success:
            return response.data
        return None

    def check_transaction(self, tx_hash: str) -> dict:
        """
        Check a pending transaction's current state.
        Returns status report dict.
        """
        receipt = self.get_receipt(tx_hash)
        current_block = self.get_current_block()

        if receipt is None:
            # Transaction not yet mined (or dropped)
            return {
                "status": "MEMPOOL_PENDING",
                "confirmations": 0,
                "block_number": None,
                "receipt": None,
            }

        if current_block is None:
            return {"status": "CONFIRMING", "confirmations": 0}

        tx_block = int(receipt.get("blockNumber", "0x0"), 16)
        confirmations = max(0, current_block - tx_block + 1)

        # EVM: status 0x1 = success, 0x0 = reverted
        tx_success = receipt.get("status") == "0x1"

        if not tx_success:
            return {
                "status": "FAILED",
                "confirmations": confirmations,
                "block_number": tx_block,
                "receipt": receipt,
            }

        if confirmations >= self.required_confirmations:
            return {
                "status": "CONFIRMED",
                "confirmations": confirmations,
                "block_number": tx_block,
                "receipt": receipt,
            }

        return {
            "status": "CONFIRMING",
            "confirmations": confirmations,
            "block_number": tx_block,
            "receipt": receipt,
        }

    def extract_usdc_transfer(self, receipt: dict) -> dict | None:
        """
        Extract and decode the USDC Transfer log from a transaction receipt.
        Returns decoded transfer data or None.
        """
        logs = receipt.get("logs", [])
        for log in logs:
            contract = log.get("address", "").lower()
            if contract != self.usdc_contract:
                continue
            decoded = ERC20Decoder.decode_transfer_log(log)
            if decoded:
                return decoded
        return None

    def verify_payment_transfer(
        self,
        receipt: dict,
        expected_to: str,
        expected_amount: Decimal,
        tolerance_pct: Decimal = Decimal("0.001"),  # 0.1% tolerance
    ) -> dict:
        """
        Verify that a confirmed transaction contains a valid USDC transfer
        matching the expected recipient and amount.
        """
        transfer = self.extract_usdc_transfer(receipt)
        if not transfer:
            return {"valid": False, "reason": "No USDC Transfer log found in receipt"}

        actual_to = transfer["to_address"].lower()
        actual_amount = Decimal(transfer["amount_human"])

        if actual_to != expected_to.lower():
            return {
                "valid": False,
                "reason": f"Recipient mismatch: expected {expected_to}, got {actual_to}",
                "transfer": transfer,
            }

        # Enforce exact matching up to 6 decimal precision for USDC
        actual_quantized = actual_amount.quantize(Decimal("0.000001"))
        expected_quantized = expected_amount.quantize(Decimal("0.000001"))
        
        if actual_quantized != expected_quantized:
            return {
                "valid": False,
                "reason": f"Amount mismatch: expected {expected_quantized}, got {actual_quantized}",
                "transfer": transfer,
            }

        return {"valid": True, "transfer": transfer}

    def scan_merchant_transfers(self, merchant_address: str, from_block: int) -> list[dict]:
        """
        Scan for incoming USDC transfers to a merchant address.
        Used by the background indexer to detect inbound payments.
        """
        config = self.bc_config
        filter_params = {
            "fromBlock": hex(from_block),
            "toBlock": "latest",
            "address": config["USDC_CONTRACT_ADDRESS"],
            "topics": [
                ERC20Decoder.TRANSFER_TOPIC,
                None,  # any sender
                "0x" + "0" * 24 + merchant_address[2:].lower(),  # padded recipient
            ],
        }

        response = self.provider.get_logs(filter_params)
        if not response.success:
            logger.warning(f"[INDEXER] get_logs failed for merchant {merchant_address}: {response.error}")
            return []

        transfers = []
        for log in (response.data or []):
            decoded = ERC20Decoder.decode_transfer_log(log)
            if decoded:
                transfers.append(decoded)

        return transfers


def get_indexer() -> BlockchainIndexer:
    """Get a BlockchainIndexer instance"""
    return BlockchainIndexer()
