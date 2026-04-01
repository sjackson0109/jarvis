"""
Memory retention policy.
Copyright 2026 sjackson0109

Controls what gets stored in long-term memory based on request type
and project policy. Separates task-centric storage from informational
query noise.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..debug import debug_log


class MemoryDomain(Enum):
    """Distinct memory domains with different retention semantics."""
    CONVERSATION = "conversation"       # Short-term dialogue context
    ACTIVE_TASK = "active_task"         # Current task execution state
    PROJECT = "project"                 # Project-scoped persistent memory
    TASK_HISTORY = "task_history"       # Completed task records
    PROVIDER_CONTEXT = "provider_context"  # Provider/account metadata
    AGENT_TEMPLATES = "agent_templates"    # Sub-agent template library metadata


@dataclass
class RetentionPolicy:
    """
    Controls what gets stored and for how long.

    Global defaults can be overridden per project.
    """
    # Whether to persist informational (Q&A) queries to long-term memory
    store_informational: bool = False
    # Whether to persist operational task records
    store_operational: bool = True
    # Whether to store full task output payloads (vs just metadata)
    store_task_outputs: bool = True
    # Retention duration in days (0 = keep forever)
    retention_days: int = 30
    # Max conversation summary history entries to retain
    max_conversation_summaries: int = 90


def should_store(
    is_operational: bool,
    policy: Optional[RetentionPolicy] = None,
) -> bool:
    """
    Determine whether an interaction should be persisted to long-term memory.

    Args:
        is_operational: True if the request was classified as operational
        policy: Retention policy to apply (defaults to global defaults)

    Returns:
        True if the interaction should be stored
    """
    p = policy or RetentionPolicy()
    if is_operational:
        result = p.store_operational
        debug_log(f"memory store decision: operational={is_operational} → {result}", "memory")
        return result
    result = p.store_informational
    debug_log(f"memory store decision: informational → {result}", "memory")
    return result
