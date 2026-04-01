"""
src/jarvis/project package.

Exports the public surface of the project management layer.
"""
from .model import Project, ProjectPolicy, AutonomyMode
from .manager import ProjectManager
from .context import get_active_project, set_active_project

__all__ = [
    "Project",
    "ProjectPolicy",
    "AutonomyMode",
    "ProjectManager",
    "get_active_project",
    "set_active_project",
]
