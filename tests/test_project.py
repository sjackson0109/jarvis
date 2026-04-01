"""
Unit tests for src/jarvis/project/ package.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest

from src.jarvis.project.model import (
    AutonomyMode,
    Project,
    ProjectPolicy,
)
from src.jarvis.project.manager import ProjectManager
from src.jarvis.project.context import get_active_project, set_active_project


# ---------------------------------------------------------------------------
# ProjectPolicy defaults
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_project_policy_defaults():
    policy = ProjectPolicy()
    assert policy.provider_force_id is None
    assert policy.provider_force_model is None
    assert policy.provider_privacy_level is None
    assert policy.autonomy_mode == AutonomyMode.SEMI_AUTONOMOUS
    assert policy.checkpoint_strategy == "milestones"
    assert policy.memory_retention_days == 30
    assert policy.store_informational_queries is False
    assert policy.allowed_paths == []
    assert policy.denied_paths == []
    assert policy.allowed_tools == []
    assert policy.project_prompt == ""


# ---------------------------------------------------------------------------
# Project.to_dict() / from_dict() round-trip
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_project_roundtrip():
    policy = ProjectPolicy(
        provider_force_id="ollama",
        autonomy_mode=AutonomyMode.HIGHLY_AUTONOMOUS,
        allowed_paths=["/home/user/projects"],
    )
    original = Project(
        id="test-id-123",
        name="Test Project",
        description="A test project",
        policy=policy,
        is_voice_default=True,
        metadata={"key": "value"},
    )
    data = original.to_dict()
    restored = Project.from_dict(data)

    assert restored.id == original.id
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.is_voice_default == original.is_voice_default
    assert restored.metadata == original.metadata
    assert restored.policy.provider_force_id == "ollama"
    assert restored.policy.autonomy_mode == AutonomyMode.HIGHLY_AUTONOMOUS
    assert restored.policy.allowed_paths == ["/home/user/projects"]


# ---------------------------------------------------------------------------
# ProjectManager.create()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_project_manager_create(tmp_path):
    manager = ProjectManager(projects_dir=str(tmp_path))
    project = manager.create(name="My Project", description="desc")
    assert project.id in [p.id for p in manager.list_all()]
    assert project.name == "My Project"


@pytest.mark.unit
def test_project_manager_create_persists_to_disk(tmp_path):
    manager = ProjectManager(projects_dir=str(tmp_path))
    project = manager.create(name="Persisted")
    json_file = tmp_path / f"{project.id}.json"
    assert json_file.exists()


@pytest.mark.unit
def test_project_manager_delete(tmp_path):
    manager = ProjectManager(projects_dir=str(tmp_path))
    project = manager.create(name="To Delete")
    assert manager.delete(project.id) is True
    assert manager.get(project.id) is None


# ---------------------------------------------------------------------------
# ProjectManager.set_voice_default() – only one default at a time
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_set_voice_default_only_one(tmp_path):
    manager = ProjectManager(projects_dir=str(tmp_path))
    p1 = manager.create(name="Project A")
    p2 = manager.create(name="Project B")

    manager.set_voice_default(p1.id)
    assert manager.get(p1.id).is_voice_default is True
    assert manager.get(p2.id).is_voice_default is False

    manager.set_voice_default(p2.id)
    assert manager.get(p1.id).is_voice_default is False
    assert manager.get(p2.id).is_voice_default is True


@pytest.mark.unit
def test_get_voice_default_returns_none_when_none_set(tmp_path):
    manager = ProjectManager(projects_dir=str(tmp_path))
    manager.create(name="No Default")
    assert manager.get_voice_default() is None


# ---------------------------------------------------------------------------
# Active project context
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_set_and_get_active_project():
    project = Project(id="ctx-test", name="Context Project")
    set_active_project(project)
    try:
        retrieved = get_active_project()
        assert retrieved is not None
        assert retrieved.id == "ctx-test"
    finally:
        set_active_project(None)


@pytest.mark.unit
def test_clear_active_project():
    project = Project(id="clear-test", name="Clear Test")
    set_active_project(project)
    set_active_project(None)
    assert get_active_project() is None
