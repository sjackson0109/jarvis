"""Tests for src/jarvis/providers package and src/jarvis/hardware module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.jarvis.providers.base import (
    LLMProvider,
    ProviderCapabilities,
    ProviderInfo,
    ProviderKind,
    ProviderStatus,
    _extract_text,
)
from src.jarvis.providers.ollama import OllamaProvider
from src.jarvis.providers.anthropic import AnthropicProvider
from src.jarvis.providers.policy import (
    PolicyConstraints,
    PrivacyLevel,
    ProviderSelectionPolicy,
    SelectionResult,
    TaskType,
)
from src.jarvis.providers.registry import ProviderRegistry, get_provider_registry
from src.jarvis.hardware import (
    ExecutionMode,
    HardwareProfile,
    detect_hardware,
    get_hardware_profile,
    _derive_mode,
    _derive_model_tier,
    _derive_concurrency,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubProvider(LLMProvider):
    """Minimal concrete provider for testing."""

    def __init__(self, pid: str, kind: ProviderKind, available: bool = True) -> None:
        self._pid = pid
        self._kind = kind
        self._available = available

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id=self._pid,
            kind=self._kind,
            display_name=f"Stub({self._pid})",
            model_id="stub-model",
            capabilities=ProviderCapabilities(cost_per_1k_input_tokens=None),
        )

    def check_availability(self) -> ProviderStatus:
        return ProviderStatus.AVAILABLE if self._available else ProviderStatus.UNAVAILABLE

    def chat(self, messages, tools=None, timeout_sec=30.0, extra_options=None):
        return {"message": {"role": "assistant", "content": "stub"}}


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_ollama_format(self):
        assert _extract_text({"message": {"content": "hello"}}) == "hello"

    def test_openai_message_format(self):
        data = {"choices": [{"message": {"content": "world"}}]}
        assert _extract_text(data) == "world"

    def test_openai_text_format(self):
        data = {"choices": [{"text": "plain"}]}
        assert _extract_text(data) == "plain"

    def test_direct_content(self):
        assert _extract_text({"content": "direct"}) == "direct"

    def test_unrecognised_returns_none(self):
        assert _extract_text({"unknown": "field"}) is None


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    def _make(self, model="llama3.2:3b") -> OllamaProvider:
        return OllamaProvider(base_url="http://localhost:11434", model_id=model)

    def test_info_is_local(self):
        p = self._make()
        assert p.info.kind == ProviderKind.LOCAL
        assert p.info.model_id == "llama3.2:3b"

    def test_describe(self):
        p = self._make()
        desc = p.describe()
        assert "local" in desc
        assert "llama3.2:3b" in desc

    def test_check_availability_returns_available(self):
        p = self._make()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": []}
        with patch("requests.get", return_value=mock_resp):
            status = p.check_availability()
        assert status == ProviderStatus.AVAILABLE

    def test_check_availability_returns_unavailable_on_error(self):
        p = self._make()
        with patch("requests.get", side_effect=ConnectionError("refused")):
            status = p.check_availability()
        assert status == ProviderStatus.UNAVAILABLE

    def test_chat_returns_dict(self):
        p = self._make()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Hi!"}}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp):
            result = p.chat([{"role": "user", "content": "Hello"}])
        assert isinstance(result, dict)
        assert result["message"]["content"] == "Hi!"

    def test_chat_returns_none_on_timeout(self):
        import requests as req
        p = self._make()
        with patch("requests.post", side_effect=req.exceptions.Timeout):
            result = p.chat([])
        assert result is None

    def test_chat_disables_think_for_qwen3(self):
        p = self._make(model="qwen3:8b")
        captured = {}
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "ok"}}
        mock_resp.raise_for_status = MagicMock()

        def _post(url, json=None, **kwargs):
            captured.update(json or {})
            return mock_resp

        with patch("requests.post", side_effect=_post):
            p.chat([{"role": "user", "content": "hi"}])
        assert captured.get("think") is False

    def test_list_local_models(self):
        p = self._make()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "llama3.2:3b"}, {"name": "nomic-embed-text"}]}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            models = p.list_local_models()
        assert "llama3.2:3b" in models
        assert "nomic-embed-text" in models

    def test_chat_streaming_returns_text(self):
        import json
        p = self._make()
        lines = [
            json.dumps({"message": {"content": "hel"}}).encode(),
            json.dumps({"message": {"content": "lo"}}).encode(),
        ]
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_lines.return_value = lines
        with patch("requests.post", return_value=mock_resp):
            result = p.chat_streaming([{"role": "user", "content": "hi"}])
        assert result == "hello"


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    def _make(self, model="claude-3-5-haiku-20241022") -> AnthropicProvider:
        return AnthropicProvider(api_key="sk-test-key", model_id=model)

    def test_info_is_public(self):
        p = self._make()
        assert p.info.kind == ProviderKind.PUBLIC
        assert p.info.capabilities.cost_per_1k_input_tokens == 0.25

    def test_info_non_haiku_cost(self):
        p = self._make(model="claude-3-opus-20240229")
        assert p.info.capabilities.cost_per_1k_input_tokens == 3.0

    def test_check_availability_available(self):
        p = self._make()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.get", return_value=mock_resp):
            status = p.check_availability()
        assert status == ProviderStatus.AVAILABLE

    def test_check_availability_connection_error(self):
        import requests as req
        p = self._make()
        with patch("requests.get", side_effect=req.exceptions.ConnectionError):
            status = p.check_availability()
        assert status == ProviderStatus.UNAVAILABLE

    def test_chat_normalises_response(self):
        p = self._make()
        api_resp = {
            "content": [{"type": "text", "text": "Hello from Anthropic"}],
            "role": "assistant",
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_resp
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp):
            result = p.chat([{"role": "user", "content": "Hi"}])
        assert result is not None
        assert result["message"]["content"] == "Hello from Anthropic"

    def test_chat_system_message_separated(self):
        """System messages must be sent as the 'system' param, not in messages list."""
        p = self._make()
        captured = {}
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"content": [{"type": "text", "text": "ok"}]}
        mock_resp.raise_for_status = MagicMock()

        def _post(url, json=None, headers=None, **kwargs):
            captured.update(json or {})
            return mock_resp

        with patch("requests.post", side_effect=_post):
            p.chat([
                {"role": "system", "content": "You are a test bot"},
                {"role": "user", "content": "hello"},
            ])

        assert captured.get("system") == "You are a test bot"
        assert all(m["role"] != "system" for m in captured.get("messages", []))

    def test_chat_returns_none_on_error(self):
        import requests as req
        p = self._make()
        with patch("requests.post", side_effect=req.exceptions.Timeout):
            result = p.chat([{"role": "user", "content": "hi"}])
        assert result is None

    def test_get_account_context(self):
        p = self._make()
        ctx = p.get_account_context()
        assert ctx["provider"] == "anthropic"
        assert ctx["model"] == p.info.model_id

    def test_api_key_not_in_describe(self):
        p = self._make()
        desc = p.describe()
        assert "sk-test-key" not in desc


# ---------------------------------------------------------------------------
# PolicyConstraints / ProviderSelectionPolicy
# ---------------------------------------------------------------------------

class TestProviderSelectionPolicy:
    def _providers(self, local_available=True, public_available=True):
        return {
            "ollama": _StubProvider("ollama", ProviderKind.LOCAL, available=local_available),
            "anthropic": _StubProvider("anthropic", ProviderKind.PUBLIC, available=public_available),
        }

    def test_prefers_local_with_prefer_local(self):
        policy = ProviderSelectionPolicy(
            PolicyConstraints(privacy_level=PrivacyLevel.PREFER_LOCAL)
        )
        result = policy.select(self._providers())
        assert result is not None
        assert result.provider_id == "ollama"

    def test_local_only_excludes_public(self):
        policy = ProviderSelectionPolicy(
            PolicyConstraints(privacy_level=PrivacyLevel.LOCAL_ONLY)
        )
        providers = {"anthropic": _StubProvider("anthropic", ProviderKind.PUBLIC, available=True)}
        result = policy.select(providers)
        assert result is None

    def test_allow_public_picks_first_available(self):
        policy = ProviderSelectionPolicy(
            PolicyConstraints(privacy_level=PrivacyLevel.ALLOW_PUBLIC)
        )
        providers = {"anthropic": _StubProvider("anthropic", ProviderKind.PUBLIC, available=True)}
        result = policy.select(providers)
        assert result is not None
        assert result.provider_id == "anthropic"

    def test_force_provider_id_overrides_all(self):
        policy = ProviderSelectionPolicy(
            PolicyConstraints(
                privacy_level=PrivacyLevel.LOCAL_ONLY,
                force_provider_id="anthropic",
                force_model_id="claude-3-opus",
            )
        )
        result = policy.select(self._providers())
        assert result is not None
        assert result.provider_id == "anthropic"
        assert result.model_id == "claude-3-opus"

    def test_returns_none_when_all_unavailable(self):
        policy = ProviderSelectionPolicy()
        providers = {
            "a": _StubProvider("a", ProviderKind.LOCAL, available=False),
            "b": _StubProvider("b", ProviderKind.PUBLIC, available=False),
        }
        result = policy.select(providers)
        assert result is None

    def test_cost_filter_excludes_expensive(self):
        class _PricedProvider(_StubProvider):
            @property
            def info(self):
                info = super().info
                info.capabilities.cost_per_1k_input_tokens = 10.0
                return info

        policy = ProviderSelectionPolicy(
            PolicyConstraints(
                privacy_level=PrivacyLevel.ALLOW_PUBLIC,
                max_cost_per_1k_tokens=1.0,
            )
        )
        providers = {
            "cheap": _StubProvider("cheap", ProviderKind.LOCAL, available=True),
            "pricey": _PricedProvider("pricey", ProviderKind.PUBLIC, available=True),
        }
        result = policy.select(providers)
        assert result is not None
        assert result.provider_id == "cheap"

    def test_fallback_to_public_when_local_unavailable(self):
        policy = ProviderSelectionPolicy(
            PolicyConstraints(privacy_level=PrivacyLevel.PREFER_LOCAL)
        )
        result = policy.select(self._providers(local_available=False, public_available=True))
        assert result is not None
        assert result.provider_id == "anthropic"


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_register_and_get(self):
        reg = ProviderRegistry()
        stub = _StubProvider("x", ProviderKind.LOCAL)
        reg.register("x", stub)
        assert reg.get("x") is stub

    def test_unregister(self):
        reg = ProviderRegistry()
        stub = _StubProvider("y", ProviderKind.LOCAL)
        reg.register("y", stub)
        reg.unregister("y")
        assert reg.get("y") is None

    def test_all_providers_is_snapshot(self):
        reg = ProviderRegistry()
        stub = _StubProvider("z", ProviderKind.LOCAL)
        reg.register("z", stub)
        snapshot = reg.all_providers()
        reg.unregister("z")
        assert "z" in snapshot        # snapshot is unaffected
        assert reg.get("z") is None   # registry is updated

    def test_describe_all_empty(self):
        reg = ProviderRegistry()
        assert reg.describe_all() == "No providers registered."

    def test_describe_all_lists_providers(self):
        reg = ProviderRegistry()
        reg.register("local1", _StubProvider("local1", ProviderKind.LOCAL))
        desc = reg.describe_all()
        assert "local1" in desc

    def test_select_delegates_to_policy(self):
        reg = ProviderRegistry()
        reg.register("ollama", _StubProvider("ollama", ProviderKind.LOCAL, available=True))
        policy = ProviderSelectionPolicy(PolicyConstraints(privacy_level=PrivacyLevel.LOCAL_ONLY))
        result = reg.select(policy)
        assert result is not None
        assert result.provider_id == "ollama"

    def test_get_provider_registry_is_singleton(self):
        reg1 = get_provider_registry()
        reg2 = get_provider_registry()
        assert reg1 is reg2


# ---------------------------------------------------------------------------
# HardwareProfile / detect_hardware
# ---------------------------------------------------------------------------

class TestHardwareProfile:
    def test_detect_returns_profile(self):
        profile = detect_hardware()
        assert isinstance(profile, HardwareProfile)
        assert profile.cpu_logical_cores >= 1
        assert profile.recommended_mode in list(ExecutionMode)
        assert profile.recommended_model_tier in ("tiny", "small", "medium", "large")

    def test_low_resource_mode(self):
        p = HardwareProfile(total_ram_gb=2.0, cpu_physical_cores=1)
        assert _derive_mode(p) == ExecutionMode.LOW_RESOURCE

    def test_balanced_mode(self):
        p = HardwareProfile(total_ram_gb=8.0, cpu_physical_cores=4)
        assert _derive_mode(p) == ExecutionMode.BALANCED

    def test_performance_mode(self):
        p = HardwareProfile(total_ram_gb=64.0, cpu_physical_cores=16)
        assert _derive_mode(p) == ExecutionMode.PERFORMANCE

    def test_model_tier_tiny(self):
        p = HardwareProfile(total_ram_gb=2.0, cpu_physical_cores=2)
        assert _derive_model_tier(p) == "tiny"

    def test_model_tier_small(self):
        p = HardwareProfile(total_ram_gb=6.0, cpu_physical_cores=2)
        assert _derive_model_tier(p) == "small"

    def test_model_tier_medium(self):
        p = HardwareProfile(total_ram_gb=12.0, cpu_physical_cores=4)
        assert _derive_model_tier(p) == "medium"

    def test_model_tier_large(self):
        p = HardwareProfile(total_ram_gb=32.0, cpu_physical_cores=8)
        assert _derive_model_tier(p) == "large"

    def test_concurrency_low_resource(self):
        p = HardwareProfile(total_ram_gb=2.0, cpu_physical_cores=1)
        p.recommended_mode = ExecutionMode.LOW_RESOURCE
        assert _derive_concurrency(p) == 1

    def test_concurrency_performance(self):
        p = HardwareProfile(total_ram_gb=64.0, cpu_physical_cores=16)
        p.recommended_mode = ExecutionMode.PERFORMANCE
        assert _derive_concurrency(p) == 4

    def test_concurrency_balanced(self):
        p = HardwareProfile(total_ram_gb=16.0, cpu_physical_cores=8)
        p.recommended_mode = ExecutionMode.BALANCED
        assert _derive_concurrency(p) == 2

    def test_get_hardware_profile_cached(self):
        p1 = get_hardware_profile(force_refresh=True)
        p2 = get_hardware_profile()
        assert p1 is p2


# ---------------------------------------------------------------------------
# Config integration – new Settings fields
# ---------------------------------------------------------------------------

class TestConfigNewFields:
    def test_load_settings_has_provider_fields(self):
        from src.jarvis.config import load_settings
        s = load_settings()
        assert hasattr(s, "anthropic_api_key")
        assert hasattr(s, "anthropic_model")
        assert hasattr(s, "provider_privacy_level")
        assert hasattr(s, "provider_force_id")
        assert hasattr(s, "provider_force_model")
        assert hasattr(s, "hardware_execution_mode")
        assert hasattr(s, "active_project_id")
        assert hasattr(s, "projects_dir")
        assert hasattr(s, "guardrail_allowed_paths")
        assert hasattr(s, "guardrail_denied_paths")
        assert hasattr(s, "guardrail_allow_system_paths")

    def test_default_privacy_level(self):
        from src.jarvis.config import load_settings
        s = load_settings()
        assert s.provider_privacy_level == "prefer_local"

    def test_default_anthropic_model(self):
        from src.jarvis.config import load_settings
        s = load_settings()
        assert s.anthropic_model == "claude-3-5-haiku-20241022"

    def test_default_guardrail_paths_are_lists(self):
        from src.jarvis.config import load_settings
        s = load_settings()
        assert isinstance(s.guardrail_allowed_paths, list)
        assert isinstance(s.guardrail_denied_paths, list)

    def test_get_default_config_has_new_keys(self):
        from src.jarvis.config import get_default_config
        cfg = get_default_config()
        assert "anthropic_api_key" in cfg
        assert "provider_privacy_level" in cfg
        assert "guardrail_allowed_paths" in cfg
        assert "_config_version" in cfg
