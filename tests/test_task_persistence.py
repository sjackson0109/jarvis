"""
Unit tests for persistence helpers in src/jarvis/task_state.py.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest

from src.jarvis.task_state import (
    StepStatus,
    TaskStatus,
    begin_task,
    clear_saved_task,
    load_saved_task,
    reset_task,
    save_active_task,
)


@pytest.mark.unit
def test_save_active_task_returns_true(tmp_path):
    begin_task("Test persistence task")
    result = save_active_task(task_dir=str(tmp_path))
    assert result is True
    assert (tmp_path / "active_task.json").exists()


@pytest.mark.unit
def test_load_saved_task_restores_intent(tmp_path):
    begin_task("Restore this intent")
    save_active_task(task_dir=str(tmp_path))

    # Reset and verify it's gone
    reset_task()

    loaded = load_saved_task(task_dir=str(tmp_path))
    assert loaded is True

    from src.jarvis.task_state import get_active_task
    task = get_active_task()
    assert task.intent == "Restore this intent"


@pytest.mark.unit
def test_load_saved_task_restores_status(tmp_path):
    begin_task("Status restore test")
    from src.jarvis.task_state import get_active_task
    task = get_active_task()
    task.set_executing()
    save_active_task(task_dir=str(tmp_path))

    reset_task()
    load_saved_task(task_dir=str(tmp_path))

    restored = get_active_task()
    assert restored.status == TaskStatus.EXECUTING


@pytest.mark.unit
def test_load_saved_task_restores_steps(tmp_path):
    begin_task("Steps restore test")
    from src.jarvis.task_state import get_active_task
    task = get_active_task()
    step = task.add_step("Do something", tool_name="localFiles")
    step.start()
    save_active_task(task_dir=str(tmp_path))

    reset_task()
    load_saved_task(task_dir=str(tmp_path))

    restored = get_active_task()
    assert len(restored.steps) == 1
    assert restored.steps[0].description == "Do something"
    assert restored.steps[0].tool_name == "localFiles"
    assert restored.steps[0].status == StepStatus.RUNNING


@pytest.mark.unit
def test_load_saved_task_returns_false_when_no_file(tmp_path):
    result = load_saved_task(task_dir=str(tmp_path))
    assert result is False


@pytest.mark.unit
def test_clear_saved_task_removes_file(tmp_path):
    begin_task("Clear test")
    save_active_task(task_dir=str(tmp_path))
    assert (tmp_path / "active_task.json").exists()

    clear_saved_task(task_dir=str(tmp_path))
    assert not (tmp_path / "active_task.json").exists()


@pytest.mark.unit
def test_clear_saved_task_no_error_when_no_file(tmp_path):
    # Should not raise even if there is nothing to clear
    clear_saved_task(task_dir=str(tmp_path))
