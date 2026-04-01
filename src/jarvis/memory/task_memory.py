"""
Task-centric memory storage.
Copyright 2026 sjackson0109

Stores rich operational context for tasks rather than accumulating
raw conversational transcripts. Each task record tracks requirement,
scope, plan, decisions, steps, outputs, blockers, and completion state.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..debug import debug_log


class TaskMemoryStatus(Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class TaskDecision:
    """A decision made during task execution (autonomous or user-directed)."""
    description: str
    chosen_option: str
    alternatives_considered: List[str] = field(default_factory=list)
    was_autonomous: bool = False  # True if the system decided; False if user decided
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskMemoryRecord:
    """
    Persistent record of a task and its execution context.

    This is richer than TaskState (which is session-scoped and in-memory).
    TaskMemoryRecord persists across sessions and captures strategic context.
    """
    task_id: str
    project_id: Optional[str]
    requirement: str
    scope: str = ""
    plan: str = ""
    decisions: List[TaskDecision] = field(default_factory=list)
    executed_steps: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    status: TaskMemoryStatus = TaskMemoryStatus.IN_PROGRESS
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    # References to artefacts produced (file paths, URLs, etc.)
    artefact_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "requirement": self.requirement,
            "scope": self.scope,
            "plan": self.plan,
            "decisions": [
                {
                    "description": d.description,
                    "chosen_option": d.chosen_option,
                    "alternatives_considered": d.alternatives_considered,
                    "was_autonomous": d.was_autonomous,
                    "timestamp": d.timestamp,
                }
                for d in self.decisions
            ],
            "executed_steps": self.executed_steps,
            "outputs": self.outputs,
            "blockers": self.blockers,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "artefact_refs": self.artefact_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskMemoryRecord":
        decisions = [
            TaskDecision(
                description=d["description"],
                chosen_option=d["chosen_option"],
                alternatives_considered=d.get("alternatives_considered", []),
                was_autonomous=d.get("was_autonomous", False),
                timestamp=d.get("timestamp", 0.0),
            )
            for d in data.get("decisions", [])
        ]
        return cls(
            task_id=data["task_id"],
            project_id=data.get("project_id"),
            requirement=data["requirement"],
            scope=data.get("scope", ""),
            plan=data.get("plan", ""),
            decisions=decisions,
            executed_steps=data.get("executed_steps", []),
            outputs=data.get("outputs", []),
            blockers=data.get("blockers", []),
            status=TaskMemoryStatus(data.get("status", "in_progress")),
            started_at=data.get("started_at", time.time()),
            completed_at=data.get("completed_at"),
            artefact_refs=data.get("artefact_refs", []),
        )


class TaskMemoryStore:
    """
    Persistent store for task memory records.

    Records are stored as individual JSON files in a configurable directory.
    Supports retrieval by task_id, project_id, and status.
    """

    def __init__(self, store_dir: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._store_dir = Path(store_dir) if store_dir else self._default_store_dir()
        self._store_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_store_dir() -> Path:
        import os
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        return base / "jarvis" / "task_memory"

    def _record_path(self, task_id: str) -> Path:
        return self._store_dir / f"{task_id}.json"

    def save(self, record: TaskMemoryRecord) -> None:
        """Persist a task memory record."""
        with self._lock:
            path = self._record_path(record.task_id)
            try:
                with path.open("w", encoding="utf-8") as f:
                    json.dump(record.to_dict(), f, indent=2)
                debug_log(f"task memory saved: {record.task_id}", "memory")
            except Exception as e:
                debug_log(f"task memory save failed: {e}", "memory")

    def load(self, task_id: str) -> Optional[TaskMemoryRecord]:
        """Load a task memory record by ID."""
        with self._lock:
            path = self._record_path(task_id)
            if not path.exists():
                return None
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return TaskMemoryRecord.from_dict(data)
            except Exception as e:
                debug_log(f"task memory load failed {task_id}: {e}", "memory")
                return None

    def list_by_project(self, project_id: str) -> List[TaskMemoryRecord]:
        """Return all task records for a given project, sorted by start time."""
        with self._lock:
            records = []
            for path in self._store_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("project_id") == project_id:
                        records.append(TaskMemoryRecord.from_dict(data))
                except Exception:
                    continue
            return sorted(records, key=lambda r: r.started_at)

    def list_recent(self, limit: int = 20) -> List[TaskMemoryRecord]:
        """Return the most recent task records across all projects."""
        with self._lock:
            records = []
            for path in self._store_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    records.append(TaskMemoryRecord.from_dict(data))
                except Exception:
                    continue
            records.sort(key=lambda r: r.started_at, reverse=True)
            return records[:limit]
