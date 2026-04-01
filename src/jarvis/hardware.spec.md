# Hardware Profiling Spec

This document specifies the hardware detection and execution mode system used to adapt Jarvis's model and concurrency recommendations to the host device.

## Module

| Module | Path |
|--------|------|
| Hardware profiling | `src/jarvis/hardware.py` |

---

## 1. Purpose

Detects host hardware capabilities at startup and maps them to a recommended execution profile. This profile informs provider selection (model tier) and the agentic loop (concurrency limits) without requiring manual configuration on typical hardware.

Design principles:
- **Read-only**: never modifies system state.
- **Fast**: uses `psutil` and stdlib only; no subprocess calls or GPU driver queries.
- **Graceful degradation**: falls back to minimal detection if `psutil` is unavailable.
- **Cached**: detection runs once per session; result is reused.

---

## 2. `HardwareProfile` Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `total_ram_gb` | `float` | Total physical RAM in gigabytes |
| `available_ram_gb` | `float` | Currently available RAM |
| `cpu_physical_cores` | `int` | Physical (non-hyperthreaded) CPU cores |
| `cpu_logical_cores` | `int` | Logical CPU threads |
| `cpu_architecture` | `str` | Architecture string (e.g. `"x86_64"`, `"aarch64"`) |
| `os_platform` | `str` | Operating system name (e.g. `"Linux"`, `"Windows"`) |
| `is_virtual_machine` | `bool` | Best-effort VM detection via platform version hints |
| `gpu_available` | `bool` | Whether a GPU is considered present |
| `gpu_name` | `str` | GPU name string if detected |
| `recommended_mode` | `ExecutionMode` | Derived execution mode |
| `recommended_model_tier` | `str` | `"tiny"`, `"small"`, `"medium"`, or `"large"` |
| `recommended_max_concurrency` | `int` | Max parallel agentic tasks |
| `notes` | `list` | Detection warnings (e.g. `"psutil not available"`) |

---

## 3. `ExecutionMode` Enum

| Value | Hardware Profile | Use Case |
|-------|-----------------|----------|
| `LOW_RESOURCE` | < 4 GB RAM or ≤ 2 cores | Raspberry Pi, embedded, constrained devices |
| `BALANCED` | 4–31 GB RAM, 3–7 cores | Typical laptop or desktop |
| `PERFORMANCE` | ≥ 32 GB RAM and ≥ 8 cores | Workstation or developer machine |
| `CLUSTER_ASSISTED` | Remote inference enabled | Delegated to a remote node or cluster |

---

## 4. Hardware → Mode / Tier Mapping

### Execution Mode

```
total_ram_gb < 4  OR  cpu_physical_cores <= 2  →  LOW_RESOURCE
total_ram_gb >= 32 AND cpu_physical_cores >= 8  →  PERFORMANCE
otherwise                                        →  BALANCED
```

### Model Tier

| RAM | Tier | Suitable Models |
|-----|------|----------------|
| < 4 GB | `"tiny"` | 1b–3b parameter models |
| 4–7 GB | `"small"` | 3b–7b parameter models |
| 8–15 GB | `"medium"` | 7b–13b parameter models |
| ≥ 16 GB | `"large"` | 13b+ parameter models |

### Max Concurrency

| Mode | `recommended_max_concurrency` |
|------|-------------------------------|
| `LOW_RESOURCE` | 1 |
| `BALANCED` | 2 |
| `PERFORMANCE` | 4 |

---

## 5. `get_hardware_profile()` Cached Singleton

```python
from jarvis.hardware import get_hardware_profile

profile = get_hardware_profile()             # Cached after first call
profile = get_hardware_profile(force_refresh=True)  # Re-detect
```

- Thread-safe via `threading.Lock`.
- `detect_hardware()` is the underlying (non-cached) function.
- VM detection uses `platform.version()` string heuristics (looks for `"hyperv"`, `"vmware"`, `"virtualbox"`, `"kvm"`, `"xen"`, `"qemu"`, `"lxc"`).

---

## 6. Config Override

The `hardware_execution_mode` setting in `Settings` allows the user to override the detected mode:

| Config Value | Override |
|-------------|----------|
| `"low_resource"` | Force `LOW_RESOURCE` |
| `"balanced"` | Force `BALANCED` |
| `"performance"` | Force `PERFORMANCE` |
| `"cluster_assisted"` | Force `CLUSTER_ASSISTED` |
| `None` (default) | Use detected mode |

When overridden, `recommended_model_tier` and `recommended_max_concurrency` are **not** automatically updated; callers should check the config-overridden mode and adjust accordingly.

---

## 7. Low-End Device Considerations

On `LOW_RESOURCE` hardware (e.g. Raspberry Pi 4 with 4 GB RAM):
- Only `"tiny"` tier models (1b–3b) are recommended.
- `recommended_max_concurrency = 1` prevents parallel tool execution from exhausting memory.
- The `psutil` library may not be installed; the module falls back to `os.cpu_count()` and sets `total_ram_gb = 0.0` with a warning in `notes`.
- Sub-agent spawning should respect `recommended_max_concurrency` to avoid OOM.

---

## 8. Debug Logging

Hardware detection emits a single `debug_log` line at category `"hardware"`:

```
hardware profile: RAM=<X>GB cores=<P>p/<L>l mode=<mode> tier=<tier>
```

---

## 9. Testing Notes

- Mock `psutil` via `unittest.mock.patch` to test fallback paths.
- Test each `_derive_mode` boundary: `< 4 GB`, `4 GB`, `>= 32 GB`.
- Test `get_hardware_profile(force_refresh=True)` clears the cache and calls `detect_hardware` again.
- VM detection tests should patch `platform.version()` to return strings containing VM hints.
