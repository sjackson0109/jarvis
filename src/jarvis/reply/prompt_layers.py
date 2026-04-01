"""
Layered prompt architecture.
Copyright 2026 sjackson0109

Implements a deterministic layered prompt composition with clear precedence:

  1. global_baseline   – system-wide foundational instructions
  2. provider          – provider or connection-specific guidance
  3. project           – project-specific instructions
  4. agent_template    – specialist agent type instructions
  5. session           – session or conversation precursor
  6. task              – task-specific execution augmentations

Higher layers (lower index) set context; lower layers (higher index)
refine or specialise. Layers are concatenated with a double newline
separator. Empty layers are skipped.

Inspection: `compose_prompt()` returns both the final text and a
layer-by-layer breakdown for UI display.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from ..debug import debug_log


LAYER_NAMES = [
    "global_baseline",
    "provider",
    "project",
    "agent_template",
    "session",
    "task",
]


@dataclass
class PromptLayers:
    """
    A complete set of prompt layers for a single LLM invocation.

    Layers are composed top-to-bottom; empty strings are skipped.
    """
    global_baseline: str = ""
    provider: str = ""
    project: str = ""
    agent_template: str = ""
    session: str = ""
    task: str = ""


@dataclass
class PromptComposition:
    """Result of composing prompt layers."""
    final_prompt: str
    # Layer-by-layer breakdown for inspection (name, content)
    layers_used: List[Tuple[str, str]] = field(default_factory=list)


def compose_prompt(layers: PromptLayers) -> PromptComposition:
    """
    Compose the final system prompt from layered inputs.

    Returns both the composed text and a breakdown suitable for
    display in the operational console.

    Args:
        layers: PromptLayers instance with content per layer

    Returns:
        PromptComposition with the final prompt and layer breakdown
    """
    layer_values = [
        ("global_baseline", layers.global_baseline),
        ("provider", layers.provider),
        ("project", layers.project),
        ("agent_template", layers.agent_template),
        ("session", layers.session),
        ("task", layers.task),
    ]

    parts = []
    layers_used = []
    for name, content in layer_values:
        stripped = content.strip()
        if stripped:
            parts.append(stripped)
            layers_used.append((name, stripped))

    final_prompt = "\n\n".join(parts)
    active_count = len(layers_used)
    debug_log(f"prompt composed: {active_count} active layers", "prompt")

    return PromptComposition(final_prompt=final_prompt, layers_used=layers_used)


def describe_composition(composition: PromptComposition) -> str:
    """
    Return a human-readable description of which layers are active.

    Useful for debugging and UI display.
    """
    if not composition.layers_used:
        return "No prompt layers active."
    lines = ["Active prompt layers:"]
    for name, content in composition.layers_used:
        preview = content[:60].replace("\n", " ")
        if len(content) > 60:
            preview += "…"
        lines.append(f"  [{name}]: {preview}")
    return "\n".join(lines)
