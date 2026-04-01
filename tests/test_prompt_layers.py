"""
Unit tests for src/jarvis/reply/prompt_layers.py.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Load the module directly from its file to avoid triggering reply/__init__.py,
# which transitively imports the optional 'mcp' package.
_spec = importlib.util.spec_from_file_location(
    "jarvis.reply.prompt_layers",
    Path(__file__).parent.parent / "src" / "jarvis" / "reply" / "prompt_layers.py",
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
import sys as _sys
_sys.modules["jarvis.reply.prompt_layers"] = _mod
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

PromptComposition = _mod.PromptComposition
PromptLayers = _mod.PromptLayers
compose_prompt = _mod.compose_prompt
describe_composition = _mod.describe_composition


@pytest.mark.unit
def test_compose_all_layers():
    layers = PromptLayers(
        global_baseline="Global baseline.",
        provider="Provider guidance.",
        project="Project instructions.",
        agent_template="Agent type prompt.",
        session="Session context.",
        task="Task specifics.",
    )
    result = compose_prompt(layers)
    assert "Global baseline." in result.final_prompt
    assert "Provider guidance." in result.final_prompt
    assert "Project instructions." in result.final_prompt
    assert "Agent type prompt." in result.final_prompt
    assert "Session context." in result.final_prompt
    assert "Task specifics." in result.final_prompt
    assert len(result.layers_used) == 6


@pytest.mark.unit
def test_empty_layers_are_skipped():
    layers = PromptLayers(
        global_baseline="Only this layer.",
        provider="",
        project="  ",  # whitespace only – should be skipped
    )
    result = compose_prompt(layers)
    assert len(result.layers_used) == 1
    assert result.layers_used[0][0] == "global_baseline"


@pytest.mark.unit
def test_layers_separated_by_double_newline():
    layers = PromptLayers(
        global_baseline="First.",
        task="Second.",
    )
    result = compose_prompt(layers)
    assert result.final_prompt == "First.\n\nSecond."


@pytest.mark.unit
def test_layers_used_only_contains_non_empty():
    layers = PromptLayers(
        global_baseline="Non-empty.",
        provider="",
        task="Also non-empty.",
    )
    result = compose_prompt(layers)
    names = [name for name, _ in result.layers_used]
    assert "provider" not in names
    assert "global_baseline" in names
    assert "task" in names


@pytest.mark.unit
def test_describe_composition_no_layers():
    comp = PromptComposition(final_prompt="", layers_used=[])
    desc = describe_composition(comp)
    assert desc == "No prompt layers active."


@pytest.mark.unit
def test_describe_composition_human_readable():
    layers = PromptLayers(global_baseline="Be helpful.", task="Solve the problem.")
    comp = compose_prompt(layers)
    desc = describe_composition(comp)
    assert "Active prompt layers:" in desc
    assert "[global_baseline]" in desc
    assert "[task]" in desc


@pytest.mark.unit
def test_compose_all_empty_returns_empty_string():
    layers = PromptLayers()
    result = compose_prompt(layers)
    assert result.final_prompt == ""
    assert result.layers_used == []
