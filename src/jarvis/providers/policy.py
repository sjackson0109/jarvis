"""
Provider selection policy engine.
Copyright 2026 sjackson0109

Determines which LLM provider/model to use for a given request based on:
- Hardware capabilities
- User/project override
- Task type
- Provider availability
- Cost or quota constraints
- Privacy restrictions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from ..debug import debug_log

if TYPE_CHECKING:
    from .base import LLMProvider


class TaskType(Enum):
    CHAT = "chat"
    TOOL_USE = "tool_use"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    LONG_RUNNING = "long_running"


class PrivacyLevel(Enum):
    """How strictly to enforce local-only operation."""
    LOCAL_ONLY = "local_only"      # Never send data to public APIs
    PREFER_LOCAL = "prefer_local"  # Use public only if local unavailable
    ALLOW_PUBLIC = "allow_public"  # Public providers are permitted


@dataclass
class PolicyConstraints:
    """
    A complete set of constraints that govern provider selection.

    These can be set at global level, project level, or task level.
    More specific levels override more general ones.
    """
    privacy_level: PrivacyLevel = PrivacyLevel.PREFER_LOCAL
    # Explicit provider override (bypasses policy; use with care)
    force_provider_id: Optional[str] = None
    # Explicit model override
    force_model_id: Optional[str] = None
    # Max allowed cost per 1k tokens (None = no limit)
    max_cost_per_1k_tokens: Optional[float] = None
    # Allowed provider kinds (empty = all allowed)
    allowed_kinds: List[str] = field(default_factory=list)


@dataclass
class SelectionResult:
    """The result of a provider selection decision."""
    provider_id: str
    model_id: str
    reason: str
    is_fallback: bool = False


class ProviderSelectionPolicy:
    """
    Selects the appropriate provider for a request.

    Priority order (highest to lowest):
    1. force_provider_id / force_model_id (explicit override)
    2. Privacy level restriction (LOCAL_ONLY blocks public)
    3. Provider availability check
    4. Cost constraint filter
    5. Task-type preference
    6. Hardware capability hints (from HardwareProfile if provided)
    """

    def __init__(self, constraints: Optional[PolicyConstraints] = None) -> None:
        self._constraints = constraints or PolicyConstraints()

    @property
    def constraints(self) -> PolicyConstraints:
        return self._constraints

    def select(
        self,
        providers: Dict[str, "LLMProvider"],
        task_type: TaskType = TaskType.CHAT,
        hardware_profile: Optional[object] = None,
    ) -> Optional[SelectionResult]:
        """
        Select the best provider from the registered providers.

        Args:
            providers: Dict of provider_id -> LLMProvider
            task_type: The type of task being performed
            hardware_profile: Optional HardwareProfile for hardware-aware selection

        Returns:
            SelectionResult or None if no suitable provider found
        """
        c = self._constraints

        # 1. Explicit force override
        if c.force_provider_id and c.force_provider_id in providers:
            provider = providers[c.force_provider_id]
            model = c.force_model_id or provider.info.model_id
            debug_log(f"provider forced: {c.force_provider_id} model={model}", "provider")
            return SelectionResult(
                provider_id=c.force_provider_id,
                model_id=model,
                reason=f"Explicit override: provider={c.force_provider_id}, model={model}",
            )

        candidates = list(providers.items())

        # 2. Privacy filter
        if c.privacy_level == PrivacyLevel.LOCAL_ONLY:
            from .base import ProviderKind
            candidates = [
                (pid, p) for pid, p in candidates
                if p.info.kind == ProviderKind.LOCAL
            ]
            debug_log(
                f"privacy=LOCAL_ONLY: {len(candidates)} candidates remain", "provider"
            )

        # 3. Allowed kinds filter
        if c.allowed_kinds:
            candidates = [
                (pid, p) for pid, p in candidates
                if p.info.kind.value in c.allowed_kinds
            ]

        # 4. Availability check
        from .base import ProviderStatus
        available: List[tuple] = []
        for pid, p in candidates:
            status = p.check_availability()
            if status == ProviderStatus.AVAILABLE:
                available.append((pid, p))
            else:
                debug_log(f"provider unavailable: {pid}", "provider")

        if not available:
            debug_log("no available providers found", "provider")
            return None

        # 5. Cost filter
        if c.max_cost_per_1k_tokens is not None:
            cost_ok = [
                (pid, p) for pid, p in available
                if (
                    p.info.capabilities.cost_per_1k_input_tokens is None
                    or p.info.capabilities.cost_per_1k_input_tokens
                    <= c.max_cost_per_1k_tokens
                )
            ]
            if cost_ok:
                available = cost_ok

        # 6. Prefer local for privacy, pick first otherwise
        from .base import ProviderKind
        local_candidates = [
            (pid, p) for pid, p in available
            if p.info.kind == ProviderKind.LOCAL
        ]
        if local_candidates and c.privacy_level != PrivacyLevel.ALLOW_PUBLIC:
            chosen_id, chosen = local_candidates[0]
            reason = f"Local provider preferred (privacy={c.privacy_level.value})"
        else:
            chosen_id, chosen = available[0]
            reason = f"First available provider (task={task_type.value})"

        model = c.force_model_id or chosen.info.model_id
        debug_log(
            f"selected provider: {chosen_id} model={model} reason={reason}", "provider"
        )
        return SelectionResult(provider_id=chosen_id, model_id=model, reason=reason)
