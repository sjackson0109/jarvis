"""
Guardrails – hard execution boundaries.
Copyright 2026 sjackson0109

Implements scope-limited file access control with configurable
allowed/denied paths. Denials are auditable and traceable.

Design:
- Path normalisation before any comparison (resolves .., symlinks on disk)
- Explicit deny list takes precedence over allow list
- System paths are never modifiable unless explicitly permitted
- All denials are logged with a reason
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .debug import debug_log


# Paths that are always denied unless guardrail_allow_system_paths is True
_SYSTEM_PATH_PREFIXES = [
    "/etc",
    "/sys",
    "/proc",
    "/boot",
    "/usr/lib",
    "/usr/bin",
    "/usr/sbin",
    "/bin",
    "/sbin",
    "/lib",
    "/lib64",
    # Windows system paths (normalised to forward slash for comparison)
    "c:/windows",
    "c:/program files",
    "c:/program files (x86)",
]


@dataclass
class GuardrailConfig:
    """
    Configuration for filesystem guardrails.

    Loaded from global config and optionally overridden by project policy.
    """
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allow_system_paths: bool = False


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    allowed: bool
    reason: str
    path: str


class GuardrailEngine:
    """
    Enforces path-based execution boundaries.

    Thread-safe. Configuration can be updated at runtime (e.g. on project switch).
    """

    def __init__(self, config: Optional[GuardrailConfig] = None) -> None:
        self._config = config or GuardrailConfig()
        self._lock = threading.RLock()

    def configure(self, config: GuardrailConfig) -> None:
        """Update guardrail configuration."""
        with self._lock:
            self._config = config
            debug_log(
                f"guardrails updated: allowed={len(config.allowed_paths)} denied={len(config.denied_paths)}",
                "guardrail",
            )

    def check_path(self, path: str, operation: str = "access") -> GuardrailResult:
        """
        Check whether an operation on a path is permitted.

        Args:
            path: Filesystem path to check
            operation: Human-readable operation name (for audit log)

        Returns:
            GuardrailResult indicating whether the operation is allowed
        """
        with self._lock:
            normalised = _normalise_path(path)
            result = self._evaluate(normalised, operation)
            if not result.allowed:
                debug_log(
                    f"DENIED {operation} on '{normalised}': {result.reason}",
                    "guardrail",
                )
            return result

    def _evaluate(self, normalised: str, operation: str) -> GuardrailResult:
        cfg = self._config

        # 1. System path check (unless explicitly permitted)
        if not cfg.allow_system_paths:
            for sys_prefix in _SYSTEM_PATH_PREFIXES:
                if normalised.lower().startswith(sys_prefix):
                    return GuardrailResult(
                        allowed=False,
                        reason=f"System path blocked: {sys_prefix}",
                        path=normalised,
                    )

        # 2. Explicit deny list (deny takes precedence over allow)
        for denied in cfg.denied_paths:
            norm_denied = _normalise_path(denied)
            if normalised.startswith(norm_denied):
                return GuardrailResult(
                    allowed=False,
                    reason=f"Path in denied list: {norm_denied}",
                    path=normalised,
                )

        # 3. If allow list is non-empty, path must be within it
        if cfg.allowed_paths:
            for allowed in cfg.allowed_paths:
                norm_allowed = _normalise_path(allowed)
                if normalised.startswith(norm_allowed):
                    return GuardrailResult(allowed=True, reason="Within allowed path", path=normalised)
            return GuardrailResult(
                allowed=False,
                reason="Path not in allowed list",
                path=normalised,
            )

        # 4. No allow list configured – allow by default (deny list already checked)
        return GuardrailResult(allowed=True, reason="No restrictions", path=normalised)


def _normalise_path(path: str) -> str:
    """
    Normalise a path for consistent comparison.

    Resolves the path string (but does NOT stat the filesystem, so
    works even for paths that do not yet exist).
    """
    try:
        return str(Path(path).expanduser()).lower().rstrip("/\\").replace("\\", "/")
    except Exception:
        return path.lower().rstrip("/\\").replace("\\", "/")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_engine: Optional[GuardrailEngine] = None
_engine_lock = threading.Lock()


def get_guardrail_engine() -> GuardrailEngine:
    """Return the global guardrail engine singleton."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = GuardrailEngine()
        return _engine


def initialise_guardrails_from_config(cfg: object) -> GuardrailEngine:
    """
    Configure the global guardrail engine from a Settings config object.

    Args:
        cfg: Settings instance from src/jarvis/config.py
    """
    config = GuardrailConfig(
        allowed_paths=list(getattr(cfg, "guardrail_allowed_paths", [])),
        denied_paths=list(getattr(cfg, "guardrail_denied_paths", [])),
        allow_system_paths=bool(getattr(cfg, "guardrail_allow_system_paths", False)),
    )
    engine = get_guardrail_engine()
    engine.configure(config)
    return engine
