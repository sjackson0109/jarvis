# Memory Policy & Task Memory Spec

This document specifies the memory retention policy and task-centric storage system that persists rich operational context across sessions.

## Modules

| Module | Path |
|--------|------|
| Retention policy | `src/jarvis/memory/policy.py` |
| Task memory store | `src/jarvis/memory/task_memory.py` |

---

## 1. Purpose

Jarvis's memory system is intentionally layered. This spec covers the two new modules introduced to support long-running autonomous workflows:

| Module | Scope | Lifecycle | Storage |
|--------|-------|-----------|---------|
| `policy.py` | Cross-cutting | Rules, no state | In-memory |
| `task_memory.py` | Per-task records | Cross-session | JSON files |

### Contrast with Existing Memory

| Module | Purpose | Scope |
|--------|---------|-------|
| `memory/conversation.py` | Short-term dialogue context (last 5 minutes) | Session |
| `memory/db.py` | Conversation summaries via vector search | Long-term |
| `memory/policy.py` | **(New)** Controls what gets stored | Policy |
| `memory/task_memory.py` | **(New)** Rich task execution records | Long-term |

---

## 2. `MemoryDomain` Enum

Distinct domains with different retention semantics.

| Value | Description |
|-------|-------------|
| `CONVERSATION` | Short-term dialogue context |
| `ACTIVE_TASK` | Current task execution state (session-scoped) |
| `PROJECT` | Project-scoped persistent memory |
| `TASK_HISTORY` | Completed task records (cross-session) |
| `PROVIDER_CONTEXT` | Provider and account metadata |
| `AGENT_TEMPLATES` | Sub-agent template library metadata |

---

## 3. `RetentionPolicy` Dataclass

Controls what is stored and for how long. Can be overridden at project level.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `store_informational` | `bool` | `False` | Persist informational (Q&A) queries |
| `store_operational` | `bool` | `True` | Persist operational task records |
| `store_task_outputs` | `bool` | `True` | Store full output payloads (vs metadata only) |
| `retention_days` | `int` | `30` | Retention in days (0 = keep forever) |
| `max_conversation_summaries` | `int` | `90` | Max conversation summary history entries |

---

## 4. `should_store()` Decision Function

```python
from jarvis.memory.policy import should_store, RetentionPolicy

store = should_store(is_operational=True, policy=policy)
```

| `is_operational` | Policy Field Checked | Default Result |
|-----------------|---------------------|---------------|
| `True` | `store_operational` | `True` |
| `False` | `store_informational` | `False` |

- A `None` policy argument uses `RetentionPolicy()` defaults.
- The decision is emitted via `debug_log` at category `"memory"`.

**Rationale**: Informational queries (e.g. "what is the capital of France?") generate high-frequency noise. Only operational interactions (those that cause side-effects or multi-step execution) default to being stored.

---

## 5. `TaskDecision` Dataclass

Records a single decision made during task execution.

| Field | Type | Description |
|-------|------|-------------|
| `description` | `str` | What the decision was about |
| `chosen_option` | `str` | The option that was selected |
| `alternatives_considered` | `List[str]` | Other options that were evaluated |
| `was_autonomous` | `bool` | `True` if the system decided; `False` if the user decided |
| `timestamp` | `float` | Unix timestamp of the decision |

---

## 6. `TaskMemoryRecord` Dataclass

Persistent record of a task and its full execution context. Richer than `TaskState` (which is session-scoped and in-memory).

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | UUID4 for this task |
| `project_id` | `Optional[str]` | Owning project ID |
| `requirement` | `str` | Original user requirement |
| `scope` | `str` | Boundaries of what this task covers |
| `plan` | `str` | Execution plan description |
| `decisions` | `List[TaskDecision]` | All decisions made during execution |
| `executed_steps` | `List[str]` | Steps that were actually run |
| `outputs` | `List[str]` | Produced outputs |
| `blockers` | `List[str]` | Issues that blocked progress |
| `status` | `TaskMemoryStatus` | `IN_PROGRESS`, `COMPLETED`, `FAILED`, `BLOCKED` |
| `started_at` | `float` | Unix timestamp of task start |
| `completed_at` | `Optional[float]` | Unix timestamp of completion |
| `artefact_refs` | `List[str]` | References to produced artefacts (file paths, URLs) |

Serialisation: `to_dict()` / `from_dict()` for JSON persistence.

---

## 7. `TaskMemoryStore`

Persistent store backed by individual JSON files.

```python
from jarvis.memory.task_memory import TaskMemoryStore

store = TaskMemoryStore()
store.save(record)
record = store.load(task_id)
recent = store.list_recent(limit=20)
by_project = store.list_by_project(project_id)
```

| Method | Description |
|--------|-------------|
| `save(record)` | Write (or overwrite) a record to disk |
| `load(task_id)` | Load a record by ID; returns `None` if not found |
| `list_by_project(project_id)` | All records for a project, sorted by `started_at` |
| `list_recent(limit=20)` | Most recent records across all projects |

---

## 8. Persistence

Records are stored in `~/.local/share/jarvis/task_memory/<task_id>.json`.

Override via:
- `store_dir` argument to `TaskMemoryStore()`
- `XDG_DATA_HOME` environment variable

---

## 9. Testing Notes

- `TaskMemoryStore` accepts a `store_dir` argument; use a temporary directory in tests.
- Test `should_store()` with both `is_operational=True` and `False`, with explicit and default policy.
- Test `from_dict(to_dict(record))` round-trip, including nested `TaskDecision` objects.
- Test `list_recent()` returns results sorted by `started_at` descending.
- Test that `list_by_project()` excludes records from other projects.
