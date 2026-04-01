"""
Project model – first-class project construct.
Copyright 2026 sjackson0109

Each project provides a scoped control plane overriding global policy for:
- Provider/model selection
- Autonomy mode
- Prompt layers
- Memory policy
- Guardrail paths
- Allowed tools
- Sub-agent template defaults
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AutonomyMode(Enum):
    MANUAL = "manual"                    # Every step confirmed
    SEMI_AUTONOMOUS = "semi_autonomous"  # Checkpoints for strategic decisions
    HIGHLY_AUTONOMOUS = "highly_autonomous"  # Minimal interruption within policy


@dataclass
class ProjectPolicy:
    """
    Per-project policy overrides.

    Fields set to None inherit from global config.
    """
    # Provider policy (None = inherit global)
    provider_force_id: Optional[str] = None
    provider_force_model: Optional[str] = None
    provider_privacy_level: Optional[str] = None   # "local_only", "prefer_local", "allow_public"

    # Autonomy
    autonomy_mode: AutonomyMode = AutonomyMode.SEMI_AUTONOMOUS
    checkpoint_strategy: str = "milestones"  # "every_step", "milestones", "phase_transitions"

    # Memory
    memory_retention_days: int = 30
    store_informational_queries: bool = False  # Whether to persist informational Q&A

    # Guardrails
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)

    # Tools
    allowed_tools: List[str] = field(default_factory=list)  # Empty = all allowed

    # Prompt layer overrides
    project_prompt: str = ""  # Project-specific system prompt layer


@dataclass
class Project:
    """
    A first-class project construct.

    Projects scope all Jarvis behaviour: prompts, memory, autonomy,
    providers, and guardrails. Only one project is the voice-default
    at any given time, but multiple may run in background.
    """
    id: str
    name: str
    description: str = ""
    policy: ProjectPolicy = field(default_factory=ProjectPolicy)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # Whether this is the current voice-default project
    is_voice_default: bool = False
    # Arbitrary metadata for extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise project to a plain dict for JSON storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_voice_default": self.is_voice_default,
            "metadata": self.metadata,
            "policy": {
                "provider_force_id": self.policy.provider_force_id,
                "provider_force_model": self.policy.provider_force_model,
                "provider_privacy_level": self.policy.provider_privacy_level,
                "autonomy_mode": self.policy.autonomy_mode.value,
                "checkpoint_strategy": self.policy.checkpoint_strategy,
                "memory_retention_days": self.policy.memory_retention_days,
                "store_informational_queries": self.policy.store_informational_queries,
                "allowed_paths": self.policy.allowed_paths,
                "denied_paths": self.policy.denied_paths,
                "allowed_tools": self.policy.allowed_tools,
                "project_prompt": self.policy.project_prompt,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Deserialise project from a plain dict."""
        policy_data = data.get("policy", {})
        policy = ProjectPolicy(
            provider_force_id=policy_data.get("provider_force_id"),
            provider_force_model=policy_data.get("provider_force_model"),
            provider_privacy_level=policy_data.get("provider_privacy_level"),
            autonomy_mode=AutonomyMode(policy_data.get("autonomy_mode", "semi_autonomous")),
            checkpoint_strategy=policy_data.get("checkpoint_strategy", "milestones"),
            memory_retention_days=policy_data.get("memory_retention_days", 30),
            store_informational_queries=policy_data.get("store_informational_queries", False),
            allowed_paths=policy_data.get("allowed_paths", []),
            denied_paths=policy_data.get("denied_paths", []),
            allowed_tools=policy_data.get("allowed_tools", []),
            project_prompt=policy_data.get("project_prompt", ""),
        )
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            policy=policy,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            is_voice_default=data.get("is_voice_default", False),
            metadata=data.get("metadata", {}),
        )
