"""
LLM Provider abstraction – base interface.
Copyright 2026 sjackson0109

All LLM providers must implement this interface so that the reply engine,
sub-agent framework, and policy engine can work with any backend uniformly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ProviderKind(Enum):
    LOCAL = "local"    # Runs entirely on the host machine
    REMOTE = "remote"  # Remote inference endpoint / cluster
    PUBLIC = "public"  # Third-party public API (e.g. Anthropic, OpenAI)


class ProviderStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class ProviderCapabilities:
    """What a provider supports."""
    supports_streaming: bool = True
    supports_tool_calling: bool = False
    supports_vision: bool = False
    max_context_tokens: int = 4096
    cost_per_1k_input_tokens: Optional[float] = None   # None = free / local
    cost_per_1k_output_tokens: Optional[float] = None


@dataclass
class ProviderInfo:
    """Human-readable metadata about a provider instance."""
    provider_id: str
    kind: ProviderKind
    display_name: str
    model_id: str
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    status: ProviderStatus = ProviderStatus.UNKNOWN
    # Why this provider was selected (for transparency)
    selection_reason: str = ""
    # Provider-specific connection metadata (URL, tenant, region, etc.)
    connection_metadata: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """
    Abstract base for all LLM provider backends.

    Subclasses implement the actual transport layer (HTTP, SDK, etc.).
    The reply engine and orchestrator should interact exclusively through
    this interface to remain provider-agnostic.
    """

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return human-readable metadata about this provider instance."""
        ...

    @abstractmethod
    def check_availability(self) -> ProviderStatus:
        """Probe the provider and return current availability status."""
        ...

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_sec: float = 30.0,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Send a messages array and return the raw response dict.

        Returns None on timeout or error. Caller interprets content.
        """
        ...

    def chat_streaming(
        self,
        messages: List[Dict[str, Any]],
        on_token: Optional[Callable[[str], None]] = None,
        timeout_sec: float = 60.0,
    ) -> Optional[str]:
        """
        Streaming chat – default falls back to non-streaming.

        Providers that support streaming should override this.
        """
        result = self.chat(messages, timeout_sec=timeout_sec)
        if result is None:
            return None
        return _extract_text(result)

    def describe(self) -> str:
        """One-line human-readable description for UI and logs."""
        info = self.info
        return (
            f"{info.display_name} [{info.kind.value}] "
            f"model={info.model_id} status={info.status.value}"
        )


def _extract_text(data: Dict[str, Any]) -> Optional[str]:
    """Extract text from a provider response (normalises across formats)."""
    # Ollama chat non-stream
    if "message" in data and isinstance(data["message"], dict):
        content = data["message"].get("content")
        if isinstance(content, str):
            return content
    # OpenAI-compatible
    if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
        choice = data["choices"][0]
        if isinstance(choice, dict):
            msg = choice.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    return content
            text = choice.get("text")
            if isinstance(text, str):
                return text
    # Direct content field
    if "content" in data and isinstance(data["content"], str):
        return data["content"]
    return None
