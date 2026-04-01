# Guardrails Spec

This document specifies the hard execution boundary system that enforces least-privilege filesystem access for all tool operations.

## Module

| Module | Path |
|--------|------|
| Guardrails | `src/jarvis/guardrails.py` |

---

## 1. Purpose

Provides auditable, path-based access control enforced **before** any tool execution that touches the filesystem. The guardrail engine:
- Maintains an explicit allow list and deny list per configuration.
- Always blocks a hard-coded set of system paths.
- Logs every denial via `debug_log` for audit purposes.
- Can be reconfigured at runtime (e.g. on project switch) without restarting the daemon.

---

## 2. `GuardrailConfig` Dataclass

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allowed_paths` | `List[str]` | `[]` | Paths that are explicitly permitted |
| `denied_paths` | `List[str]` | `[]` | Paths that are explicitly denied |
| `allow_system_paths` | `bool` | `False` | If `True`, bypasses the always-denied system prefixes |

---

## 3. `GuardrailResult` Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `allowed` | `bool` | Whether the operation is permitted |
| `reason` | `str` | Human-readable explanation |
| `path` | `str` | Normalised path that was evaluated |

---

## 4. `GuardrailEngine`

Thread-safe engine that evaluates path access requests.

```python
from jarvis.guardrails import get_guardrail_engine

engine = get_guardrail_engine()
result = engine.check_path("/home/user/project/src", operation="write")
if not result.allowed:
    raise PermissionError(result.reason)
```

| Method | Description |
|--------|-------------|
| `configure(config)` | Update configuration; takes effect immediately |
| `check_path(path, operation)` | Evaluate and return `GuardrailResult` |

`operation` is a human-readable string used only in audit logs (e.g. `"read"`, `"write"`, `"delete"`).

---

## 5. Evaluation Order

Each `check_path()` call follows this deterministic order:

| Step | Rule | Effect on Denied |
|------|------|-----------------|
| 1 | System paths (unless `allow_system_paths=True`) | Deny with `"System path blocked: <prefix>"` |
| 2 | Explicit deny list | Deny with `"Path in denied list: <prefix>"` |
| 3 | Explicit allow list (if non-empty) | Deny with `"Path not in allowed list"` if not matched |
| 4 | Default | Allow with `"No restrictions"` |

The deny list always takes precedence over the allow list.

---

## 6. Always-Denied System Path Prefixes

The following prefixes are blocked regardless of `allowed_paths` unless `allow_system_paths=True`:

**Linux / macOS**
- `/etc`, `/sys`, `/proc`, `/boot`
- `/usr/lib`, `/usr/bin`, `/usr/sbin`
- `/bin`, `/sbin`, `/lib`, `/lib64`

**Windows** (normalised to forward slashes)
- `c:/windows`
- `c:/program files`
- `c:/program files (x86)`

---

## 7. `_normalise_path()` Semantics

All paths are normalised before comparison to ensure consistent matching across operating systems:

1. `Path(path).expanduser()` – resolves `~` to the home directory.
2. `.lower()` – case-insensitive comparison.
3. `.rstrip("/\\")` – removes trailing slashes.
4. `.replace("\\", "/")` – converts Windows separators to forward slashes.

> **Note**: `_normalise_path()` does **not** call `Path.resolve()` or `stat()`, so it works on paths that do not yet exist on disk.

---

## 8. Startup Initialisation

`initialise_guardrails_from_config(cfg)` configures the global engine from a `Settings` instance:

```python
from jarvis.guardrails import initialise_guardrails_from_config

engine = initialise_guardrails_from_config(cfg)
```

Config fields read:

| Config Field | Type | Default |
|-------------|------|---------|
| `guardrail_allowed_paths` | `list[str]` | `[]` |
| `guardrail_denied_paths` | `list[str]` | `[]` |
| `guardrail_allow_system_paths` | `bool` | `False` |

---

## 9. Module-Level Singleton

```python
from jarvis.guardrails import get_guardrail_engine

engine = get_guardrail_engine()  # Created on first call; thread-safe
```

The singleton is created with an empty `GuardrailConfig` (no allow/deny restrictions, system paths blocked) until `initialise_guardrails_from_config()` is called.

---

## 10. Integration Point

The guardrail engine is called **at the tool layer**, before execution, not inside tool implementations. The `localFiles` tool and any other filesystem-touching tools should call `check_path()` with the target path and operation before proceeding.

Project switches should call `engine.configure()` with the new project's `allowed_paths` / `denied_paths` to update boundaries without restarting.

---

## 11. Auditable Denials

Every denied access is emitted via `debug_log` at category `"guardrail"`:

```
DENIED <operation> on '<normalised_path>': <reason>
```

This provides a complete audit trail of all blocked operations without exposing sensitive path contents to the user.

---

## 12. Testing Notes

- Test each evaluation step in isolation (system path, deny list, allow list, default).
- Test `_normalise_path()` with `~`, trailing slashes, backslashes, and mixed case.
- Test that `configure()` takes effect on subsequent `check_path()` calls.
- Test that `allow_system_paths=True` bypasses the system prefix block.
- Test that the deny list blocks paths that would otherwise match the allow list.
