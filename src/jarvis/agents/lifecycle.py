"""
Sub-agent lifecycle management.
Copyright 2026 sjackson0109

Manages creation, execution, and teardown of ephemeral sub-agents.
Sub-agents are scoped to a single delegated task and shut down when done.
They inherit project guardrails and cannot escape top-level scope controls.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..debug import debug_log
from .template import AgentTemplate


class AgentLifecycleState(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class SubAgentContext:
    """
    Runtime context for an ephemeral sub-agent.

    Created when an agent is spawned and released when it terminates.
    """
    agent_id: str
    template_id: str
    delegated_task: str
    project_id: Optional[str]
    state: AgentLifecycleState = AgentLifecycleState.CREATED
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    output: Optional[str] = None
    error: Optional[str] = None
    # Artefacts produced during this agent's execution
    artefacts: List[str] = field(default_factory=list)


class SubAgentOrchestrator:
    """
    Manages ephemeral sub-agent lifecycle.

    Agents are created, run synchronously (future: async), and cleaned up.
    The orchestrator maintains visibility of active agents and their outputs.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, SubAgentContext] = {}
        self._lock = threading.RLock()

    def spawn(
        self,
        template: AgentTemplate,
        delegated_task: str,
        project_id: Optional[str] = None,
    ) -> SubAgentContext:
        """
        Create and register an ephemeral sub-agent context.

        The caller is responsible for executing the agent's work and
        calling complete() or fail() when done.

        Args:
            template: The agent template to instantiate
            delegated_task: Description of the task being delegated
            project_id: Optional project scope

        Returns:
            SubAgentContext for tracking and executing the agent
        """
        with self._lock:
            agent_id = str(uuid.uuid4())
            ctx = SubAgentContext(
                agent_id=agent_id,
                template_id=template.template_id,
                delegated_task=delegated_task,
                project_id=project_id,
                state=AgentLifecycleState.CREATED,
            )
            self._agents[agent_id] = ctx
            debug_log(
                f"sub-agent spawned: {template.name} id={agent_id} task={delegated_task[:60]}",
                "agent",
            )
            return ctx

    def start(self, agent_id: str) -> None:
        """Mark an agent as running."""
        with self._lock:
            ctx = self._agents.get(agent_id)
            if ctx:
                ctx.state = AgentLifecycleState.RUNNING
                ctx.started_at = time.time()

    def complete(self, agent_id: str, output: Optional[str] = None) -> None:
        """Mark an agent as successfully completed and release its context."""
        with self._lock:
            ctx = self._agents.get(agent_id)
            if ctx:
                ctx.state = AgentLifecycleState.COMPLETED
                ctx.completed_at = time.time()
                ctx.output = output
                debug_log(f"sub-agent completed: {agent_id}", "agent")

    def fail(self, agent_id: str, error: Optional[str] = None) -> None:
        """Mark an agent as failed."""
        with self._lock:
            ctx = self._agents.get(agent_id)
            if ctx:
                ctx.state = AgentLifecycleState.FAILED
                ctx.completed_at = time.time()
                ctx.error = error
                debug_log(f"sub-agent failed: {agent_id} error={error}", "agent")

    def terminate(self, agent_id: str) -> None:
        """Forcefully terminate a running agent."""
        with self._lock:
            ctx = self._agents.get(agent_id)
            if ctx:
                ctx.state = AgentLifecycleState.TERMINATED
                ctx.completed_at = time.time()
                debug_log(f"sub-agent terminated: {agent_id}", "agent")

    def get(self, agent_id: str) -> Optional[SubAgentContext]:
        with self._lock:
            return self._agents.get(agent_id)

    def list_active(self) -> List[SubAgentContext]:
        """Return all currently running agents."""
        with self._lock:
            return [
                ctx for ctx in self._agents.values()
                if ctx.state == AgentLifecycleState.RUNNING
            ]

    def cleanup_completed(self) -> int:
        """Remove completed/failed/terminated agents. Returns count removed."""
        with self._lock:
            terminal_states = {
                AgentLifecycleState.COMPLETED,
                AgentLifecycleState.FAILED,
                AgentLifecycleState.TERMINATED,
            }
            to_remove = [
                aid for aid, ctx in self._agents.items()
                if ctx.state in terminal_states
            ]
            for aid in to_remove:
                del self._agents[aid]
            return len(to_remove)
