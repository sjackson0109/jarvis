"""
Provider registry – manages all configured LLM providers.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Dict, Optional

from ..debug import debug_log
from .base import LLMProvider, ProviderStatus

if TYPE_CHECKING:
    from .policy import ProviderSelectionPolicy, SelectionResult, TaskType


class ProviderRegistry:
    """
    Thread-safe registry of configured LLM providers.

    Providers are registered by ID and can be queried, selected, or
    refreshed at runtime. The registry is the single source of truth
    for available providers.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, LLMProvider] = {}
        self._lock = threading.RLock()

    def register(self, provider_id: str, provider: LLMProvider) -> None:
        """Register a provider under the given ID."""
        with self._lock:
            self._providers[provider_id] = provider
            debug_log(f"provider registered: {provider_id}", "provider")

    def unregister(self, provider_id: str) -> None:
        """Remove a provider from the registry."""
        with self._lock:
            if provider_id in self._providers:
                del self._providers[provider_id]
                debug_log(f"provider unregistered: {provider_id}", "provider")

    def get(self, provider_id: str) -> Optional[LLMProvider]:
        """Return a provider by ID, or None if not found."""
        with self._lock:
            return self._providers.get(provider_id)

    def all_providers(self) -> Dict[str, LLMProvider]:
        """Return a snapshot of all registered providers."""
        with self._lock:
            return dict(self._providers)

    def select(
        self,
        policy: "ProviderSelectionPolicy",
        task_type: Optional["TaskType"] = None,
        hardware_profile: Optional[object] = None,
    ) -> Optional["SelectionResult"]:
        """
        Use the given policy to select the best available provider.

        Returns a SelectionResult or None if no suitable provider exists.
        """
        from .policy import TaskType as TT
        with self._lock:
            providers_snapshot = dict(self._providers)
        return policy.select(
            providers=providers_snapshot,
            task_type=task_type or TT.CHAT,
            hardware_profile=hardware_profile,
        )

    def describe_all(self) -> str:
        """Return a multi-line human-readable description of all registered providers."""
        with self._lock:
            if not self._providers:
                return "No providers registered."
            lines = []
            for pid, p in self._providers.items():
                lines.append(f"  [{pid}] {p.describe()}")
            return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: Optional[ProviderRegistry] = None
_registry_lock = threading.Lock()


def get_provider_registry() -> ProviderRegistry:
    """Return the global provider registry singleton (created on first call)."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ProviderRegistry()
        return _registry


def initialise_providers_from_config(cfg: object) -> ProviderRegistry:
    """
    Populate the global provider registry from a Settings config object.

    Registers:
    - OllamaProvider (always, as local default)
    - AnthropicProvider (if anthropic_api_key is configured)

    Args:
        cfg: A Settings instance from src/jarvis/config.py

    Returns:
        The populated ProviderRegistry
    """
    registry = get_provider_registry()

    # Always register Ollama as local provider
    from .ollama import OllamaProvider
    ollama = OllamaProvider(
        base_url=getattr(cfg, "ollama_base_url", "http://127.0.0.1:11434"),
        model_id=getattr(cfg, "ollama_chat_model", "llama3.2:3b"),
        embed_model=getattr(cfg, "ollama_embed_model", "nomic-embed-text"),
    )
    registry.register("ollama", ollama)

    # Register Anthropic if configured
    anthropic_key = getattr(cfg, "anthropic_api_key", None)
    if anthropic_key:
        from .anthropic import AnthropicProvider
        anthropic_model = getattr(cfg, "anthropic_model", "claude-3-5-haiku-20241022")
        anthropic = AnthropicProvider(api_key=anthropic_key, model_id=anthropic_model)
        registry.register("anthropic", anthropic)
        debug_log("anthropic provider registered", "provider")

    debug_log(
        f"providers initialised: {list(registry.all_providers().keys())}", "provider"
    )
    return registry
