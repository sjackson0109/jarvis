"""
Ollama LLM provider implementation.
Copyright 2026 sjackson0109

Wraps the Ollama HTTP API and exposes it through the LLMProvider interface.
Ollama is always registered as the primary local provider.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

import requests

from ..debug import debug_log
from .base import (
    LLMProvider,
    ProviderCapabilities,
    ProviderInfo,
    ProviderKind,
    ProviderStatus,
    _extract_text,
)


class OllamaProvider(LLMProvider):
    """
    LLM provider backed by a local Ollama instance.

    Communicates with the Ollama HTTP API at *base_url*.
    """

    def __init__(
        self,
        base_url: str,
        model_id: str,
        embed_model: str = "nomic-embed-text",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._embed_model = embed_model
        self._cached_status: ProviderStatus = ProviderStatus.UNKNOWN

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id="ollama",
            kind=ProviderKind.LOCAL,
            display_name="Ollama (local)",
            model_id=self._model_id,
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_tool_calling=True,
                supports_vision=False,
                max_context_tokens=4096,
                cost_per_1k_input_tokens=None,
                cost_per_1k_output_tokens=None,
            ),
            status=self._cached_status,
            connection_metadata={"base_url": self._base_url, "embed_model": self._embed_model},
        )

    def check_availability(self) -> ProviderStatus:
        """Probe GET /api/tags with a 3-second timeout."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                self._cached_status = ProviderStatus.AVAILABLE
                debug_log(f"ollama available at {self._base_url}", "provider")
            else:
                self._cached_status = ProviderStatus.UNAVAILABLE
                debug_log(
                    f"ollama unavailable – HTTP {resp.status_code}", "provider"
                )
        except Exception as exc:
            self._cached_status = ProviderStatus.UNAVAILABLE
            debug_log(f"ollama check failed: {exc}", "provider")
        return self._cached_status

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_sec: float = 30.0,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send a messages array to Ollama and return the raw response dict."""
        payload: Dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": 4096},
        }

        if extra_options and isinstance(extra_options, dict):
            payload["options"].update(extra_options)

        if tools and isinstance(tools, list) and len(tools) > 0:
            payload["tools"] = tools

        # Disable thinking mode for qwen3 models (causes very slow responses)
        # See: https://docs.ollama.com/capabilities/thinking
        if self._model_id.startswith("qwen3"):
            payload["think"] = False

        debug_log(f"ollama chat: model={self._model_id} messages={len(messages)}", "provider")

        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=timeout_sec,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
        except requests.exceptions.Timeout:
            print("  ⏱️ Ollama request timed out", flush=True)
        except requests.exceptions.ConnectionError as exc:
            print(f"  ❌ Ollama connection error: {exc}", flush=True)
        except Exception as exc:
            print(f"  ❌ Ollama error: {exc}", flush=True)

        return None

    def chat_streaming(
        self,
        messages: List[Dict[str, Any]],
        on_token: Optional[Callable[[str], None]] = None,
        timeout_sec: float = 60.0,
    ) -> Optional[str]:
        """Stream tokens from Ollama, invoking *on_token* for each chunk."""
        payload: Dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "stream": True,
            "options": {"num_ctx": 4096},
        }

        if self._model_id.startswith("qwen3"):
            payload["think"] = False

        debug_log(
            f"ollama streaming: model={self._model_id} messages={len(messages)}",
            "provider",
        )

        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=timeout_sec,
                stream=True,
            )
            resp.raise_for_status()

            chunks: List[str] = []
            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and isinstance(data["message"], dict):
                            content = data["message"].get("content", "")
                            if content:
                                chunks.append(content)
                                if on_token:
                                    on_token(content)
                    except json.JSONDecodeError:
                        continue

            result = "".join(chunks)
            return result if result.strip() else None

        except requests.exceptions.Timeout:
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Ollama-specific helpers
    # ------------------------------------------------------------------

    def list_local_models(self) -> List[str]:
        """Return a list of model name strings available in the local Ollama instance."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return [m["name"] for m in models if isinstance(m, dict) and "name" in m]
        except Exception as exc:
            debug_log(f"ollama list_local_models failed: {exc}", "provider")
            return []

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def embed_model(self) -> str:
        return self._embed_model
