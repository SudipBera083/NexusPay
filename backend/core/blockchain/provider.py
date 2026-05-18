"""
Blockchain Provider Abstraction Layer
=====================================
Supports: Alchemy, Infura, QuickNode, Ankr, Public RPC
- Provider failover with retry logic
- Health checking
- Provider-agnostic interface
- All credentials loaded from environment (never hardcoded)
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional, Any
from django.conf import settings

logger = logging.getLogger("nexuspay.blockchain")


@dataclass
class ProviderConfig:
    """Immutable provider configuration loaded from environment"""
    name: str
    url: str
    chain_id: int
    priority: int  # Lower = higher priority


@dataclass
class RPCResponse:
    success: bool
    data: Optional[Any]
    provider_used: str
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class BlockchainProviderRegistry:
    """
    Registry of available RPC providers ordered by priority.
    Loaded entirely from Django settings (which load from env vars).
    No provider credentials are ever stored in code.
    """

    def __init__(self):
        self._providers: list[ProviderConfig] = []
        self._health_cache: dict[str, float] = {}  # url → last_failure_timestamp
        self._load_providers()

    def _load_providers(self):
        """Load providers from settings in priority order"""
        bc = settings.BLOCKCHAIN_CONFIG
        primary_name = bc.get("PROVIDER_PRIMARY", "public")

        # Build provider list based on what's configured
        candidates = []

        # Alchemy
        if bc.get("ALCHEMY_API_KEY") and primary_name == "alchemy":
            candidates.append(ProviderConfig(
                name="alchemy",
                url=f"{bc['ALCHEMY_BASE_URL']}{bc['ALCHEMY_API_KEY']}",
                chain_id=bc["CHAIN_ID"],
                priority=0,
            ))

        # Infura
        if bc.get("INFURA_PROJECT_ID") and primary_name == "infura":
            candidates.append(ProviderConfig(
                name="infura",
                url=f"{bc['INFURA_BASE_URL']}{bc['INFURA_PROJECT_ID']}",
                chain_id=bc["CHAIN_ID"],
                priority=1,
            ))

        # QuickNode
        if bc.get("QUICKNODE_URL") and primary_name == "quicknode":
            candidates.append(ProviderConfig(
                name="quicknode",
                url=bc["QUICKNODE_URL"],
                chain_id=bc["CHAIN_ID"],
                priority=1,
            ))

        # Ankr
        if bc.get("ANKR_URL"):
            candidates.append(ProviderConfig(
                name="ankr",
                url=bc["ANKR_URL"],
                chain_id=bc["CHAIN_ID"],
                priority=2,
            ))

        # Public RPC endpoints (always available as fallbacks)
        for i, url in enumerate(bc.get("PUBLIC_RPC_URLS", [])):
            candidates.append(ProviderConfig(
                name=f"public_{i}",
                url=url,
                chain_id=bc["CHAIN_ID"],
                priority=10 + i,
            ))

        self._providers = sorted(candidates, key=lambda p: p.priority)
        logger.info(
            f"[BLOCKCHAIN] Loaded {len(self._providers)} providers: "
            f"{[p.name for p in self._providers]}"
        )

    def get_healthy_providers(self) -> list[ProviderConfig]:
        """Return providers that haven't recently failed, in priority order"""
        now = time.time()
        cooldown = 60  # 60s cooldown after failure
        return [
            p for p in self._providers
            if now - self._health_cache.get(p.url, 0) > cooldown
        ]

    def mark_failed(self, provider: ProviderConfig):
        """Mark a provider as unhealthy"""
        self._health_cache[provider.url] = time.time()
        logger.warning(f"[BLOCKCHAIN] Provider '{provider.name}' marked as unhealthy")

    def mark_healthy(self, provider: ProviderConfig):
        """Clear failure mark"""
        self._health_cache.pop(provider.url, None)


class BlockchainProvider:
    """
    Provider-agnostic blockchain interface.
    Executes JSON-RPC calls with automatic failover across registered providers.
    Business logic NEVER knows which provider is serving the request.
    """

    def __init__(self):
        self.registry = BlockchainProviderRegistry()
        self._max_retries = settings.BLOCKCHAIN_CONFIG.get("MAX_RETRIES", 3)

    def _rpc_call(self, method: str, params: list, provider: ProviderConfig) -> Any:
        """Execute a single JSON-RPC call to a provider"""
        import httpx
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(provider.url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise ValueError(f"RPC error: {data['error']}")
            return data.get("result")

    def call(self, method: str, params: list = None) -> RPCResponse:
        """
        Execute an RPC call with automatic provider failover.
        Tries providers in priority order. Falls back to next on failure.
        """
        params = params or []
        providers = self.registry.get_healthy_providers()

        if not providers:
            logger.error("[BLOCKCHAIN] No healthy providers available")
            return RPCResponse(success=False, data=None, provider_used="none",
                               error="No healthy providers available")

        for provider in providers:
            for attempt in range(self._max_retries):
                start = time.monotonic()
                try:
                    result = self._rpc_call(method, params, provider)
                    latency = (time.monotonic() - start) * 1000
                    self.registry.mark_healthy(provider)
                    return RPCResponse(
                        success=True,
                        data=result,
                        provider_used=provider.name,
                        latency_ms=round(latency, 2),
                    )
                except Exception as e:
                    logger.warning(
                        f"[BLOCKCHAIN] Provider '{provider.name}' attempt {attempt + 1} "
                        f"failed for {method}: {e}"
                    )
                    if attempt == self._max_retries - 1:
                        self.registry.mark_failed(provider)

        return RPCResponse(success=False, data=None, provider_used="none",
                           error=f"All providers failed for method: {method}")

    # ─── Convenience Methods ──────────────────────────────────

    def get_transaction_receipt(self, tx_hash: str) -> RPCResponse:
        return self.call("eth_getTransactionReceipt", [tx_hash])

    def get_transaction(self, tx_hash: str) -> RPCResponse:
        return self.call("eth_getTransaction", [tx_hash])

    def get_block_number(self) -> RPCResponse:
        return self.call("eth_blockNumber", [])

    def get_logs(self, filter_params: dict) -> RPCResponse:
        return self.call("eth_getLogs", [filter_params])

    def get_chain_id(self) -> RPCResponse:
        return self.call("eth_chainId", [])

    def call_contract(self, to: str, data: str, block: str = "latest") -> RPCResponse:
        return self.call("eth_call", [{"to": to, "data": data}, block])

    def health_check(self) -> dict:
        """Check health of all configured providers"""
        results = {}
        for provider in self.registry._providers:
            try:
                start = time.monotonic()
                self._rpc_call("eth_blockNumber", [], provider)
                latency = (time.monotonic() - start) * 1000
                results[provider.name] = {"healthy": True, "latency_ms": round(latency, 2)}
            except Exception as e:
                results[provider.name] = {"healthy": False, "error": str(e)}
        return results


# Singleton instance — initialized once, reused across requests
_provider_instance: Optional[BlockchainProvider] = None


def get_provider() -> BlockchainProvider:
    """Get the global blockchain provider singleton"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = BlockchainProvider()
    return _provider_instance
