"""
Agent template library registry.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from ..debug import debug_log
from .template import AgentTemplate, BUILTIN_TEMPLATES


class AgentTemplateLibrary:
    """
    Registry of agent templates (built-in and user-defined).

    Built-in templates are loaded at startup and cannot be deleted.
    User-defined templates can be created, edited, cloned, and deleted.
    """

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._templates: Dict[str, AgentTemplate] = {}
        self._templates_dir = Path(templates_dir) if templates_dir else self._default_dir()
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._load_builtins()
        self._load_user_templates()

    @staticmethod
    def _default_dir() -> Path:
        import os
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        return base / "jarvis" / "agent_templates"

    def _load_builtins(self) -> None:
        with self._lock:
            for tmpl in BUILTIN_TEMPLATES:
                self._templates[tmpl.template_id] = tmpl

    def _load_user_templates(self) -> None:
        with self._lock:
            for path in self._templates_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    tmpl = AgentTemplate.from_dict(data)
                    if tmpl.template_id not in self._templates:
                        self._templates[tmpl.template_id] = tmpl
                except Exception as e:
                    debug_log(f"failed to load template {path.name}: {e}", "agent")

    def get(self, template_id: str) -> Optional[AgentTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_all(self) -> List[AgentTemplate]:
        with self._lock:
            return list(self._templates.values())

    def save_user_template(self, template: AgentTemplate) -> None:
        """Save a user-defined template to disk."""
        with self._lock:
            template.is_builtin = False
            self._templates[template.template_id] = template
            path = self._templates_dir / f"{template.template_id}.json"
            try:
                with path.open("w", encoding="utf-8") as f:
                    json.dump(template.to_dict(), f, indent=2)
                debug_log(f"template saved: {template.template_id}", "agent")
            except Exception as e:
                debug_log(f"template save failed: {e}", "agent")

    def clone(self, template_id: str, new_id: str, new_name: str) -> Optional[AgentTemplate]:
        """Clone a template under a new ID."""
        with self._lock:
            original = self._templates.get(template_id)
            if original is None:
                return None
            data = original.to_dict()
            data["template_id"] = new_id
            data["name"] = new_name
            data["is_builtin"] = False
            clone = AgentTemplate.from_dict(data)
            self.save_user_template(clone)
            return clone

    def delete(self, template_id: str) -> bool:
        """Delete a user-defined template. Returns False for builtins."""
        with self._lock:
            tmpl = self._templates.get(template_id)
            if tmpl is None:
                return False
            if tmpl.is_builtin:
                debug_log(f"cannot delete builtin template: {template_id}", "agent")
                return False
            del self._templates[template_id]
            path = self._templates_dir / f"{template_id}.json"
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            debug_log(f"template deleted: {template_id}", "agent")
            return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_library: Optional[AgentTemplateLibrary] = None
_library_lock = threading.Lock()


def get_template_library(templates_dir: Optional[str] = None) -> AgentTemplateLibrary:
    """Return the global agent template library singleton."""
    global _library
    with _library_lock:
        if _library is None:
            _library = AgentTemplateLibrary(templates_dir=templates_dir)
        return _library
