"""
Active project context – singleton for the currently active project.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import threading
from typing import Optional

from ..debug import debug_log
from .model import Project


_active_project: Optional[Project] = None
_context_lock = threading.Lock()


def get_active_project() -> Optional[Project]:
    """Return the currently active project, or None if no project is active."""
    with _context_lock:
        return _active_project


def set_active_project(project: Optional[Project]) -> None:
    """Set the active project context. Pass None to clear."""
    global _active_project
    with _context_lock:
        _active_project = project
        if project:
            debug_log(f"active project: {project.name} ({project.id})", "project")
        else:
            debug_log("active project cleared", "project")
