"""
Project manager – CRUD and lifecycle for projects.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from ..debug import debug_log
from .model import Project, ProjectPolicy


class ProjectManager:
    """
    Manages project persistence and lifecycle.

    Projects are stored as individual JSON files in the projects directory.
    One project at a time is the voice-default; others may run in background.
    """

    def __init__(self, projects_dir: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._projects: Dict[str, Project] = {}
        self._projects_dir = Path(projects_dir) if projects_dir else self._default_projects_dir()
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()

    @staticmethod
    def _default_projects_dir() -> Path:
        import os
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        return base / "jarvis" / "projects"

    def _project_path(self, project_id: str) -> Path:
        return self._projects_dir / f"{project_id}.json"

    def _load_all(self) -> None:
        """Load all project files from disk."""
        with self._lock:
            for path in self._projects_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    project = Project.from_dict(data)
                    self._projects[project.id] = project
                except Exception as e:
                    debug_log(f"failed to load project {path.name}: {e}", "project")

    def _save(self, project: Project) -> None:
        """Persist a project to disk."""
        path = self._project_path(project.id)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(project.to_dict(), f, indent=2)
        except Exception as e:
            debug_log(f"failed to save project {project.id}: {e}", "project")

    def create(
        self,
        name: str,
        description: str = "",
        policy: Optional[ProjectPolicy] = None,
        make_voice_default: bool = False,
    ) -> Project:
        """Create and persist a new project."""
        with self._lock:
            project_id = str(uuid.uuid4())
            project = Project(
                id=project_id,
                name=name,
                description=description,
                policy=policy or ProjectPolicy(),
                is_voice_default=False,
            )
            if make_voice_default:
                self._clear_voice_default()
                project.is_voice_default = True
            self._projects[project_id] = project
            self._save(project)
            debug_log(f"project created: {name} id={project_id}", "project")
            return project

    def get(self, project_id: str) -> Optional[Project]:
        with self._lock:
            return self._projects.get(project_id)

    def list_all(self) -> List[Project]:
        with self._lock:
            return sorted(self._projects.values(), key=lambda p: p.created_at)

    def update(self, project: Project) -> None:
        """Update an existing project and persist it."""
        with self._lock:
            project.updated_at = time.time()
            self._projects[project.id] = project
            self._save(project)
            debug_log(f"project updated: {project.id}", "project")

    def delete(self, project_id: str) -> bool:
        """Delete a project. Returns True if it existed."""
        with self._lock:
            if project_id not in self._projects:
                return False
            del self._projects[project_id]
            path = self._project_path(project_id)
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            debug_log(f"project deleted: {project_id}", "project")
            return True

    def set_voice_default(self, project_id: str) -> bool:
        """Mark a project as the voice-default. Returns True on success."""
        with self._lock:
            if project_id not in self._projects:
                return False
            self._clear_voice_default()
            self._projects[project_id].is_voice_default = True
            self._save(self._projects[project_id])
            debug_log(f"voice-default project: {project_id}", "project")
            return True

    def get_voice_default(self) -> Optional[Project]:
        """Return the current voice-default project, or None."""
        with self._lock:
            for p in self._projects.values():
                if p.is_voice_default:
                    return p
            return None

    def _clear_voice_default(self) -> None:
        """Remove voice-default flag from all projects (call while locked)."""
        for p in self._projects.values():
            if p.is_voice_default:
                p.is_voice_default = False
                self._save(p)
