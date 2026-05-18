"""
Blockchain Configuration Module
================================
Centralised blockchain config loaded from environment variables.
All values are read via django-decouple — NEVER hardcoded.
Provider abstraction means swapping Alchemy → Infura is a single env var change.
"""
from decouple import config


def load_blockchain_config() -> dict:
    """
    Load all blockchain configuration from environment variables.
    Returns a typed config dict used throughout the application.
    Any new provider only requires adding its env vars — zero code changes.
    """
    return {
        # ─── Provider Selection ───────────────────────────────────
        "PROVIDER_PRIMARY": config("BLOCKCHAIN_PROVIDER_PRIMARY", default="public"),

        # ─── Alchemy ──────────────────────────────────────────────
        "ALCHEMY_API_KEY": config("ALCHEMY_API_KEY", default=""),
        "ALCHEMY_BASE_URL": config(
            "ALCHEMY_POLYGON_AMOY_URL",
            default="https://polygon-amoy.g.alchemy.com/v2/"
        ),

        # ─── Infura ───────────────────────────────────────────────
        "INFURA_PROJECT_ID": config("INFURA_PROJECT_ID", default=""),
        "INFURA_BASE_URL": config(
            "INFURA_POLYGON_AMOY_URL",
            default="https://polygon-amoy.infura.io/v3/"
        ),

        # ─── QuickNode ────────────────────────────────────────────
        "QUICKNODE_URL": config("QUICKNODE_POLYGON_AMOY_URL", default=""),

        # ─── Ankr ─────────────────────────────────────────────────
        "ANKR_URL": config(
            "ANKR_POLYGON_AMOY_URL",
            default="https://rpc.ankr.com/polygon_amoy"
        ),

        # ─── Public RPC Fallbacks ─────────────────────────────────
        "PUBLIC_RPC_URLS": [
            config("POLYGON_AMOY_RPC_PRIMARY", default="https://rpc-amoy.polygon.technology"),
            config("POLYGON_AMOY_RPC_FALLBACK_1", default="https://polygon-amoy.public.blastapi.io"),
            config("POLYGON_AMOY_RPC_FALLBACK_2", default="https://rpc.ankr.com/polygon_amoy"),
        ],

        # ─── Network ──────────────────────────────────────────────
        "NETWORK": config("BLOCKCHAIN_NETWORK", default="polygon_amoy"),
        "CHAIN_ID": config("BLOCKCHAIN_CHAIN_ID", default=80002, cast=int),
        "REQUIRED_CONFIRMATIONS": config(
            "BLOCKCHAIN_REQUIRED_CONFIRMATIONS", default=3, cast=int
        ),

        # ─── Token: USDC ──────────────────────────────────────────
        "USDC_CONTRACT_ADDRESS": config(
            "USDC_CONTRACT_ADDRESS",
            default="0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582"  # Polygon Amoy testnet
        ),
        "USDC_TOKEN_DECIMALS": config("USDC_TOKEN_DECIMALS", default=6, cast=int),
        "USDC_TOKEN_SYMBOL": config("USDC_TOKEN_SYMBOL", default="USDC"),

        # ERC20 Transfer event topic (keccak256 of Transfer(address,address,uint256))
        "ERC20_TRANSFER_TOPIC": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",

        # ─── Indexer ──────────────────────────────────────────────
        "INDEXER_POLL_INTERVAL": config("INDEXER_POLL_INTERVAL_SECONDS", default=15, cast=int),
        "INDEXER_MAX_BLOCK_RANGE": config("INDEXER_MAX_BLOCK_RANGE", default=500, cast=int),
        "MAX_RETRIES": config("INDEXER_MAX_RETRIES", default=5, cast=int),

        # ─── QR Payments ──────────────────────────────────────────
        "QR_HMAC_SECRET": config("QR_HMAC_SECRET", default="insecure-dev-secret-change-this"),
        "QR_DEFAULT_EXPIRY_SECONDS": config("QR_DEFAULT_EXPIRY_SECONDS", default=300, cast=int),

        # ─── Risk / Fraud ─────────────────────────────────────────
        "FRAUD_RAPID_PAYMENT_WINDOW": config("FRAUD_RAPID_PAYMENT_WINDOW_SECONDS", default=60, cast=int),
        "FRAUD_RAPID_PAYMENT_THRESHOLD": config("FRAUD_RAPID_PAYMENT_THRESHOLD", default=5, cast=int),
        "FRAUD_LARGE_TX_THRESHOLD_USDC": config("FRAUD_LARGE_TX_THRESHOLD_USDC", default=10000, cast=float),
        "FRAUD_VELOCITY_MULTIPLIER": config("FRAUD_VELOCITY_MULTIPLIER", default=3.0, cast=float),
    }
