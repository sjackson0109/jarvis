"""
Anthropic LLM provider implementation.
Copyright 2026 sjackson0109

Wraps the Anthropic Messages API and exposes it through the LLMProvider
interface. Uses *requests* directly (no anthropic SDK dependency) so the
provider can be imported even when the SDK is not installed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from ..debug import debug_log
from .base import (
    LLMProvider,
    ProviderCapabilities,
    ProviderInfo,
    ProviderKind,
    ProviderStatus,
)

_ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    """
    LLM provider backed by the Anthropic Messages API.

    The API key is stored in memory and is never written to logs.
    """

    def __init__(
        self,
        api_key: str,
        model_id: str = "claude-3-5-haiku-20241022",
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._cached_status: ProviderStatus = ProviderStatus.UNKNOWN

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    @property
    def info(self) -> ProviderInfo:
        # Haiku pricing at time of writing; override via extra_options if needed
        cost_in = 0.25 if "haiku" in self._model_id else 3.0
        cost_out = 1.25 if "haiku" in self._model_id else 15.0
        return ProviderInfo(
            provider_id="anthropic",
            kind=ProviderKind.PUBLIC,
            display_name="Anthropic (cloud)",
            model_id=self._model_id,
            capabilities=ProviderCapabilities(
                supports_streaming=False,
                supports_tool_calling=True,
                supports_vision=True,
                max_context_tokens=200000,
                cost_per_1k_input_tokens=cost_in,
                cost_per_1k_output_tokens=cost_out,
            ),
            status=self._cached_status,
        )

    def check_availability(self) -> ProviderStatus:
        """Probe GET /v1/models with a 3-second timeout."""
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }
        try:
            resp = requests.get(
                f"{_ANTHROPIC_API_BASE}/models",
                headers=headers,
                timeout=3.0,
            )
            if resp.status_code == 200:
                self._cached_status = ProviderStatus.AVAILABLE
                debug_log("anthropic available", "provider")
            else:
                self._cached_status = ProviderStatus.UNAVAILABLE
                debug_log(f"anthropic unavailable – HTTP {resp.status_code}", "provider")
        except requests.exceptions.ConnectionError:
            self._cached_status = ProviderStatus.UNAVAILABLE
            debug_log("anthropic connection error", "provider")
        except Exception as exc:
            self._cached_status = ProviderStatus.UNAVAILABLE
            debug_log(f"anthropic check failed: {exc}", "provider")
        return self._cached_status

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_sec: float = 30.0,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Send messages to the Anthropic Messages API.

        Converts OpenAI-format messages (system / user / assistant) to
        Anthropic format, then wraps the response in a dict compatible with
        ``_extract_text`` so callers need no Anthropic-specific logic.
        """
        system_prompt: Optional[str] = None
        anthropic_messages: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role in ("user", "assistant"):
                anthropic_messages.append({"role": role, "content": content})

        max_tokens: int = 4096
        if extra_options and isinstance(extra_options, dict):
            max_tokens = int(extra_options.get("max_tokens", max_tokens))

        payload: Dict[str, Any] = {
            "model": self._model_id,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        debug_log(
            f"anthropic chat: model={self._model_id} messages={len(anthropic_messages)}",
            "provider",
        )

        try:
            resp = requests.post(
                f"{_ANTHROPIC_API_BASE}/messages",
                json=payload,
                headers=headers,
                timeout=timeout_sec,
            )
            resp.raise_for_status()
            data = resp.json()

            # Normalise response to the Ollama-compatible shape expected by _extract_text
            content_blocks = data.get("content", [])
            text_content = ""
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")

            return {"message": {"role": "assistant", "content": text_content}}

        except requests.exceptions.Timeout:
            print("  ⏱️ Anthropic request timed out", flush=True)
        except requests.exceptions.ConnectionError as exc:
            print(f"  ❌ Anthropic connection error: {exc}", flush=True)
        except requests.exceptions.HTTPError as exc:
            print(f"  ❌ Anthropic API error: {exc}", flush=True)
        except Exception as exc:
            print(f"  ❌ Anthropic error: {exc}", flush=True)

        return None

    # ------------------------------------------------------------------
    # Anthropic-specific helpers
    # ------------------------------------------------------------------

    def get_account_context(self) -> Dict[str, Any]:
        """Return available account / quota context for this provider."""
        return {"provider": "anthropic", "model": self._model_id}
