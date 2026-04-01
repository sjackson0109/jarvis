"""
src/jarvis/agents package.

Exports the public surface of the sub-agent framework.
"""
from .template import AgentTemplate, BUILTIN_TEMPLATES
from .registry import AgentTemplateLibrary, get_template_library
from .lifecycle import SubAgentOrchestrator, SubAgentContext, AgentLifecycleState

__all__ = [
    "AgentTemplate",
    "BUILTIN_TEMPLATES",
    "AgentTemplateLibrary",
    "get_template_library",
    "SubAgentOrchestrator",
    "SubAgentContext",
    "AgentLifecycleState",
]
