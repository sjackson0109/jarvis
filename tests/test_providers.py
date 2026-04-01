"""
Unit tests for src/jarvis/providers package.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.jarvis.providers.base import (
    LLMProvider,
    ProviderCapabilities,
    ProviderInfo,
    ProviderKind,
    ProviderStatus,
    _extract_text,
)
from src.jarvis.providers.policy import (
    PolicyConstraints,
    PrivacyLevel,
    ProviderSelectionPolicy,
    TaskType,
)
from src.jarvis.providers.registry import ProviderRegistry, get_provider_registry


# ---------------------------------------------------------------------------
# Stub provider for testing
# ---------------------------------------------------------------------------

class _MockProvider(LLMProvider):
    """Minimal concrete provider for testing – always available."""

    def __init__(self, pid: str, kind: ProviderKind = ProviderKind.LOCAL) -> None:
        self._pid = pid
        self._kind = kind

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id=self._pid,
            kind=self._kind,
            display_name=f"Mock({self._pid})",
            model_id="mock-model",
            capabilities=ProviderCapabilities(),
        )

    def check_availability(self) -> ProviderStatus:
        return ProviderStatus.AVAILABLE

    def chat(self, messages, tools=None, timeout_sec=30.0, extra_options=None):
        return {"message": {"role": "assistant", "content": "mock"}}


# ---------------------------------------------------------------------------
# ProviderKind enum
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_provider_kind_values():
    assert ProviderKind.LOCAL.value == "local"
    assert ProviderKind.REMOTE.value == "remote"
    assert ProviderKind.PUBLIC.value == "public"


# ---------------------------------------------------------------------------
# ProviderCapabilities defaults
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_provider_capabilities_defaults():
    caps = ProviderCapabilities()
    assert caps.supports_streaming is True
    assert caps.supports_tool_calling is False
    assert caps.supports_vision is False
    assert caps.max_context_tokens == 4096
    assert caps.cost_per_1k_input_tokens is None
    assert caps.cost_per_1k_output_tokens is None


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_extract_text_ollama_format():
    assert _extract_text({"message": {"content": "hello"}}) == "hello"


@pytest.mark.unit
def test_extract_text_openai_format():
    data = {"choices": [{"message": {"content": "world"}}]}
    assert _extract_text(data) == "world"


@pytest.mark.unit
def test_extract_text_direct_content():
    assert _extract_text({"content": "direct"}) == "direct"


@pytest.mark.unit
def test_extract_text_none_on_unknown():
    assert _extract_text({"unknown": "field"}) is None


# ---------------------------------------------------------------------------
# ProviderSelectionPolicy.select() with force override
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_selection_policy_force_override():
    policy = ProviderSelectionPolicy(
        PolicyConstraints(
            privacy_level=PrivacyLevel.LOCAL_ONLY,
            force_provider_id="anthropic",
            force_model_id="claude-opus",
        )
    )
    providers = {
        "local": _MockProvider("local", ProviderKind.LOCAL),
        "anthropic": _MockProvider("anthropic", ProviderKind.PUBLIC),
    }
    result = policy.select(providers)
    assert result is not None
    assert result.provider_id == "anthropic"
    assert result.model_id == "claude-opus"


# ---------------------------------------------------------------------------
# ProviderSelectionPolicy.select() with LOCAL_ONLY privacy level
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_selection_policy_local_only_excludes_public():
    policy = ProviderSelectionPolicy(
        PolicyConstraints(privacy_level=PrivacyLevel.LOCAL_ONLY)
    )
    providers = {"anthropic": _MockProvider("anthropic", ProviderKind.PUBLIC)}
    result = policy.select(providers)
    assert result is None


@pytest.mark.unit
def test_selection_policy_local_only_allows_local():
    policy = ProviderSelectionPolicy(
        PolicyConstraints(privacy_level=PrivacyLevel.LOCAL_ONLY)
    )
    providers = {"ollama": _MockProvider("ollama", ProviderKind.LOCAL)}
    result = policy.select(providers)
    assert result is not None
    assert result.provider_id == "ollama"


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_registry_register_and_get():
    reg = ProviderRegistry()
    stub = _MockProvider("r1", ProviderKind.LOCAL)
    reg.register("r1", stub)
    assert reg.get("r1") is stub


@pytest.mark.unit
def test_registry_all_providers_returns_snapshot():
    reg = ProviderRegistry()
    stub = _MockProvider("r2", ProviderKind.LOCAL)
    reg.register("r2", stub)
    snapshot = reg.all_providers()
    assert "r2" in snapshot


@pytest.mark.unit
def test_registry_describe_all_empty():
    reg = ProviderRegistry()
    assert reg.describe_all() == "No providers registered."


@pytest.mark.unit
def test_registry_describe_all_lists_provider():
    reg = ProviderRegistry()
    reg.register("mylocal", _MockProvider("mylocal", ProviderKind.LOCAL))
    desc = reg.describe_all()
    assert "mylocal" in desc


@pytest.mark.unit
def test_registry_select_uses_policy():
    reg = ProviderRegistry()
    reg.register("local", _MockProvider("local", ProviderKind.LOCAL))
    policy = ProviderSelectionPolicy(PolicyConstraints(privacy_level=PrivacyLevel.LOCAL_ONLY))
    result = reg.select(policy)
    assert result is not None
    assert result.provider_id == "local"
