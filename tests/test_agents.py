"""
Unit tests for src/jarvis/agents/ package.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest

from src.jarvis.agents.template import AgentTemplate, BUILTIN_TEMPLATES
from src.jarvis.agents.registry import AgentTemplateLibrary
from src.jarvis.agents.lifecycle import (
    AgentLifecycleState,
    SubAgentOrchestrator,
)


# ---------------------------------------------------------------------------
# BUILTIN_TEMPLATES
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_builtin_templates_count():
    assert len(BUILTIN_TEMPLATES) == 7


@pytest.mark.unit
def test_builtin_templates_all_have_is_builtin():
    for tmpl in BUILTIN_TEMPLATES:
        assert tmpl.is_builtin is True, f"Template '{tmpl.template_id}' is not marked as builtin"


@pytest.mark.unit
def test_builtin_template_ids_unique():
    ids = [t.template_id for t in BUILTIN_TEMPLATES]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# AgentTemplate.to_dict() / from_dict() round-trip
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_agent_template_roundtrip():
    original = AgentTemplate(
        template_id="test_agent",
        name="Test Agent",
        purpose="Testing round-trip serialisation.",
        agent_prompt="You are a test agent.",
        allowed_tools=["localFiles", "webSearch"],
        approval_posture="strict",
        store_memory=False,
        reporting_style="Bullet points.",
        fallback_behaviour="retry",
        is_builtin=False,
        metadata={"version": 1},
    )
    data = original.to_dict()
    restored = AgentTemplate.from_dict(data)

    assert restored.template_id == original.template_id
    assert restored.name == original.name
    assert restored.purpose == original.purpose
    assert restored.agent_prompt == original.agent_prompt
    assert restored.allowed_tools == original.allowed_tools
    assert restored.approval_posture == original.approval_posture
    assert restored.store_memory == original.store_memory
    assert restored.reporting_style == original.reporting_style
    assert restored.fallback_behaviour == original.fallback_behaviour
    assert restored.is_builtin == original.is_builtin
    assert restored.metadata == original.metadata


# ---------------------------------------------------------------------------
# AgentTemplateLibrary
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_library_get_builtin_template(tmp_path):
    lib = AgentTemplateLibrary(templates_dir=str(tmp_path))
    tmpl = lib.get("solutions_architect")
    assert tmpl is not None
    assert tmpl.template_id == "solutions_architect"


@pytest.mark.unit
def test_library_delete_builtin_returns_false(tmp_path):
    lib = AgentTemplateLibrary(templates_dir=str(tmp_path))
    result = lib.delete("solutions_architect")
    assert result is False


@pytest.mark.unit
def test_library_save_and_delete_user_template(tmp_path):
    lib = AgentTemplateLibrary(templates_dir=str(tmp_path))
    tmpl = AgentTemplate(
        template_id="user_custom",
        name="User Custom",
        purpose="A user-defined template.",
    )
    lib.save_user_template(tmpl)
    assert lib.get("user_custom") is not None
    assert lib.delete("user_custom") is True
    assert lib.get("user_custom") is None


@pytest.mark.unit
def test_library_clone_creates_non_builtin(tmp_path):
    lib = AgentTemplateLibrary(templates_dir=str(tmp_path))
    clone = lib.clone("research_agent", "my_research", "My Research Agent")
    assert clone is not None
    assert clone.template_id == "my_research"
    assert clone.is_builtin is False


# ---------------------------------------------------------------------------
# SubAgentOrchestrator lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_orchestrator_spawn_creates_context():
    orch = SubAgentOrchestrator()
    tmpl = BUILTIN_TEMPLATES[0]
    ctx = orch.spawn(tmpl, "Write a test report")
    assert ctx.state == AgentLifecycleState.CREATED
    assert ctx.template_id == tmpl.template_id
    assert ctx.delegated_task == "Write a test report"


@pytest.mark.unit
def test_orchestrator_complete_transitions_state():
    orch = SubAgentOrchestrator()
    tmpl = BUILTIN_TEMPLATES[0]
    ctx = orch.spawn(tmpl, "Task A")
    orch.start(ctx.agent_id)
    orch.complete(ctx.agent_id, output="Done!")
    updated = orch.get(ctx.agent_id)
    assert updated.state == AgentLifecycleState.COMPLETED
    assert updated.output == "Done!"


@pytest.mark.unit
def test_orchestrator_fail_transitions_state():
    orch = SubAgentOrchestrator()
    tmpl = BUILTIN_TEMPLATES[1]
    ctx = orch.spawn(tmpl, "Task B")
    orch.start(ctx.agent_id)
    orch.fail(ctx.agent_id, error="Something went wrong")
    updated = orch.get(ctx.agent_id)
    assert updated.state == AgentLifecycleState.FAILED
    assert updated.error == "Something went wrong"


@pytest.mark.unit
def test_orchestrator_cleanup_removes_terminal_agents():
    orch = SubAgentOrchestrator()
    tmpl = BUILTIN_TEMPLATES[0]

    ctx1 = orch.spawn(tmpl, "Task 1")
    orch.start(ctx1.agent_id)
    orch.complete(ctx1.agent_id)

    ctx2 = orch.spawn(tmpl, "Task 2")
    orch.start(ctx2.agent_id)

    removed = orch.cleanup_completed()
    assert removed == 1
    assert orch.get(ctx1.agent_id) is None
    assert orch.get(ctx2.agent_id) is not None


@pytest.mark.unit
def test_orchestrator_list_active():
    orch = SubAgentOrchestrator()
    tmpl = BUILTIN_TEMPLATES[0]

    ctx = orch.spawn(tmpl, "Active task")
    assert len(orch.list_active()) == 0

    orch.start(ctx.agent_id)
    active = orch.list_active()
    assert len(active) == 1
    assert active[0].agent_id == ctx.agent_id
