"""
Unit tests for src/jarvis/memory/task_memory.py.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import time

import pytest

from src.jarvis.memory.task_memory import (
    TaskDecision,
    TaskMemoryRecord,
    TaskMemoryStatus,
    TaskMemoryStore,
)


# ---------------------------------------------------------------------------
# TaskMemoryStatus enum
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_task_memory_status_values():
    assert TaskMemoryStatus.IN_PROGRESS.value == "in_progress"
    assert TaskMemoryStatus.COMPLETED.value == "completed"
    assert TaskMemoryStatus.FAILED.value == "failed"
    assert TaskMemoryStatus.BLOCKED.value == "blocked"


# ---------------------------------------------------------------------------
# TaskDecision fields
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_task_decision_fields():
    decision = TaskDecision(
        description="Choose between REST and gRPC",
        chosen_option="REST",
        alternatives_considered=["gRPC", "GraphQL"],
        was_autonomous=True,
    )
    assert decision.description == "Choose between REST and gRPC"
    assert decision.chosen_option == "REST"
    assert "gRPC" in decision.alternatives_considered
    assert decision.was_autonomous is True
    assert decision.timestamp > 0


# ---------------------------------------------------------------------------
# TaskMemoryRecord.to_dict() / from_dict() round-trip
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_task_memory_record_roundtrip():
    decision = TaskDecision(
        description="Use PostgreSQL",
        chosen_option="PostgreSQL",
        alternatives_considered=["MySQL", "SQLite"],
        was_autonomous=False,
        timestamp=1234567890.0,
    )
    now = time.time()
    record = TaskMemoryRecord(
        task_id="task-abc-123",
        project_id="proj-xyz",
        requirement="Build a database schema",
        scope="Database layer only",
        plan="Create tables, add indices",
        decisions=[decision],
        executed_steps=["Create users table"],
        outputs=["schema.sql created"],
        blockers=["Migration tool not installed"],
        status=TaskMemoryStatus.COMPLETED,
        started_at=now,
        completed_at=now + 60,
        artefact_refs=["/path/to/schema.sql"],
    )
    data = record.to_dict()
    restored = TaskMemoryRecord.from_dict(data)

    assert restored.task_id == record.task_id
    assert restored.project_id == record.project_id
    assert restored.requirement == record.requirement
    assert restored.scope == record.scope
    assert restored.plan == record.plan
    assert restored.status == TaskMemoryStatus.COMPLETED
    assert restored.completed_at == record.completed_at
    assert restored.artefact_refs == ["/path/to/schema.sql"]
    assert len(restored.decisions) == 1
    assert restored.decisions[0].chosen_option == "PostgreSQL"
    assert restored.decisions[0].alternatives_considered == ["MySQL", "SQLite"]


# ---------------------------------------------------------------------------
# TaskMemoryStore save / load round-trip
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_task_memory_store_save_and_load(tmp_path):
    store = TaskMemoryStore(store_dir=str(tmp_path))
    record = TaskMemoryRecord(
        task_id="store-test-001",
        project_id="proj-123",
        requirement="Test the store",
    )
    store.save(record)
    loaded = store.load("store-test-001")
    assert loaded is not None
    assert loaded.task_id == "store-test-001"
    assert loaded.requirement == "Test the store"


@pytest.mark.unit
def test_task_memory_store_load_missing_returns_none(tmp_path):
    store = TaskMemoryStore(store_dir=str(tmp_path))
    result = store.load("nonexistent-id")
    assert result is None


@pytest.mark.unit
def test_task_memory_store_list_by_project(tmp_path):
    store = TaskMemoryStore(store_dir=str(tmp_path))
    for i in range(3):
        store.save(TaskMemoryRecord(
            task_id=f"task-{i}",
            project_id="shared-project",
            requirement=f"Task {i}",
        ))
    store.save(TaskMemoryRecord(
        task_id="other-task",
        project_id="other-project",
        requirement="Other",
    ))
    records = store.list_by_project("shared-project")
    assert len(records) == 3
    assert all(r.project_id == "shared-project" for r in records)


@pytest.mark.unit
def test_task_memory_store_list_recent(tmp_path):
    store = TaskMemoryStore(store_dir=str(tmp_path))
    for i in range(5):
        store.save(TaskMemoryRecord(
            task_id=f"recent-{i}",
            project_id="proj",
            requirement=f"Task {i}",
            started_at=float(i),
        ))
    recent = store.list_recent(limit=3)
    assert len(recent) == 3
    # Most recent first
    assert recent[0].started_at >= recent[1].started_at
