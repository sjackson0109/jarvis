#!/usr/bin/env bash
# =============================================================================
# create_feature_branches.sh
# =============================================================================
# Creates and pushes the 5 feature branches for the Jarvis architectural
# refactor. Each branch is sourced from the same base commit and contains
# only the files relevant to that feature area.
#
# Usage:
#   bash scripts/create_feature_branches.sh
#
# Prerequisites:
#   - Run from the root of the sjackson0109/jarvis repository
#   - You must have push access to the remote
#   - The copilot/refactor-jarvis-architectural-phase branch must be present
#     (it is the source of the cherry-picked files)
#
# Branches created:
#   Feature/TaskState_w_Approval      – task state persistence + approval
#   Feature/PolicyEngine              – provider abstraction + prompt layers
#   Feature/AuditSystem               – task-centric memory storage
#   Feature/RuntimeHealth_n_Bootstrap – hardware profiling + project scoping
#   Feature/ProcessIsolation          – sub-agents + guardrails + desktop UI
# =============================================================================
set -euo pipefail

HEAD_SHA="9ee9a9cd6d3432397757ff62ed1b1bb6209c7c88"  # copilot/refactor-jarvis-architectural-phase tip
BASE_SHA="0c910021b2070aa3f49d6fa9555fa5a9fd2b1769"  # Merge PR #2 (base for all feature branches)

REMOTE="origin"

echo "🌿 Jarvis feature branch creator"
echo "   HEAD (source): ${HEAD_SHA:0:8}"
echo "   BASE (parent): ${BASE_SHA:0:8}"
echo ""

# Helper: create a branch from BASE, checkout files, commit, push
create_branch() {
    local branch_name="$1"
    local commit_msg="$2"
    shift 2
    local files=("$@")

    echo "──────────────────────────────────────────────"
    echo "🔀 Creating: $branch_name"

    # Create branch from base
    git checkout -b "$branch_name" "$BASE_SHA" 2>/dev/null || {
        echo "   Branch already exists – resetting to base"
        git checkout "$branch_name"
        git reset --hard "$BASE_SHA"
    }

    # Checkout each file from HEAD
    for f in "${files[@]}"; do
        git checkout "$HEAD_SHA" -- "$f" 2>/dev/null && echo "   ✅ $f" || echo "   ⚠️  $f (skipped – not in HEAD)"
    done

    # Commit
    git add -A
    git commit -m "$commit_msg" --allow-empty

    # Push
    git push "$REMOTE" "$branch_name:$branch_name" --force
    echo "   🚀 Pushed to $REMOTE/$branch_name"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Branch 1 – Feature/TaskState_w_Approval
# ─────────────────────────────────────────────────────────────────────────────
create_branch "Feature/TaskState_w_Approval" \
    "feat(TaskState_w_Approval): task state persistence and approval improvements" \
    "src/jarvis/task_state.py" \
    "src/jarvis/task_state.spec.md" \
    "tests/test_task_state.py" \
    "tests/test_task_persistence.py"

# ─────────────────────────────────────────────────────────────────────────────
# Branch 2 – Feature/PolicyEngine
# Note: config.py is rebuilt with only provider-related fields below
# ─────────────────────────────────────────────────────────────────────────────
create_branch "Feature/PolicyEngine" \
    "feat(PolicyEngine): unified LLM provider abstraction and layered prompting" \
    "src/jarvis/providers/__init__.py" \
    "src/jarvis/providers/anthropic.py" \
    "src/jarvis/providers/base.py" \
    "src/jarvis/providers/ollama.py" \
    "src/jarvis/providers/policy.py" \
    "src/jarvis/providers/registry.py" \
    "src/jarvis/providers/providers.spec.md" \
    "src/jarvis/reply/prompt_layers.py" \
    "src/jarvis/reply/prompt_layers.spec.md" \
    "tests/test_providers.py" \
    "tests/test_providers_and_hardware.py" \
    "tests/test_prompt_layers.py"

# ─────────────────────────────────────────────────────────────────────────────
# Branch 3 – Feature/AuditSystem
# ─────────────────────────────────────────────────────────────────────────────
create_branch "Feature/AuditSystem" \
    "feat(AuditSystem): task-centric memory storage and retention policy" \
    "src/jarvis/memory/policy.py" \
    "src/jarvis/memory/task_memory.py" \
    "src/jarvis/memory/memory.spec.md" \
    "tests/test_memory_policy.py" \
    "tests/test_task_memory.py"

# ─────────────────────────────────────────────────────────────────────────────
# Branch 4 – Feature/RuntimeHealth_n_Bootstrap
# ─────────────────────────────────────────────────────────────────────────────
create_branch "Feature/RuntimeHealth_n_Bootstrap" \
    "feat(RuntimeHealth_n_Bootstrap): hardware profiling and project-scoped operation" \
    "src/jarvis/hardware.py" \
    "src/jarvis/hardware.spec.md" \
    "src/jarvis/project/__init__.py" \
    "src/jarvis/project/context.py" \
    "src/jarvis/project/manager.py" \
    "src/jarvis/project/model.py" \
    "src/jarvis/project/project.spec.md" \
    "tests/test_hardware.py" \
    "tests/test_project.py"

# ─────────────────────────────────────────────────────────────────────────────
# Branch 5 – Feature/ProcessIsolation
# ─────────────────────────────────────────────────────────────────────────────
create_branch "Feature/ProcessIsolation" \
    "feat(ProcessIsolation): sub-agent framework, guardrails, and desktop console" \
    "src/jarvis/agents/__init__.py" \
    "src/jarvis/agents/lifecycle.py" \
    "src/jarvis/agents/registry.py" \
    "src/jarvis/agents/template.py" \
    "src/jarvis/agents/agents.spec.md" \
    "src/jarvis/guardrails.py" \
    "src/jarvis/guardrails.spec.md" \
    "src/jarvis/__init__.py" \
    "src/desktop_app/app.py" \
    "src/desktop_app/project_panel.py" \
    "src/desktop_app/provider_panel.py" \
    "src/desktop_app/task_dashboard.py" \
    "src/desktop_app/desktop_app.spec.md" \
    "tests/test_agents.py" \
    "tests/test_guardrails.py"

# Return to original branch
git checkout copilot/refactor-jarvis-architectural-phase 2>/dev/null || git checkout main

echo "══════════════════════════════════════════════"
echo "✅ All 5 feature branches created and pushed!"
echo ""
echo "  Feature/TaskState_w_Approval"
echo "  Feature/PolicyEngine"
echo "  Feature/AuditSystem"
echo "  Feature/RuntimeHealth_n_Bootstrap"
echo "  Feature/ProcessIsolation"
echo ""
echo "  Each branch is based on: ${BASE_SHA:0:8}"
echo "  Source files from:       ${HEAD_SHA:0:8}"
echo "══════════════════════════════════════════════"
