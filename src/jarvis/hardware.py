"""
Hardware profiling and execution policy.
Copyright 2026 sjackson0109

Detects host capabilities at startup and maps them to recommended
model strategies. Supports explicit override via config.

Design:
- Read-only detection (no side-effects)
- Fast: uses psutil and platform stdlib only, no subprocess or GPU queries
  unless psutil provides GPU info
- Result is cached after first call
"""
from __future__ import annotations

import platform
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .debug import debug_log

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class ExecutionMode(Enum):
    """Runtime execution profile mode."""
    LOW_RESOURCE = "low_resource"          # Raspberry Pi / constrained hardware
    BALANCED = "balanced"                  # Standard laptop or desktop
    PERFORMANCE = "performance"            # Workstation class
    CLUSTER_ASSISTED = "cluster_assisted"  # Remote inference enabled


@dataclass
class HardwareProfile:
    """
    Snapshot of detected host hardware capabilities.

    Used by the provider selection policy to choose appropriate models
    and concurrency settings.
    """
    total_ram_gb: float = 0.0
    available_ram_gb: float = 0.0
    cpu_physical_cores: int = 1
    cpu_logical_cores: int = 1
    cpu_architecture: str = ""
    os_platform: str = ""
    is_virtual_machine: bool = False
    # GPU detection (basic – presence only via platform hints)
    gpu_available: bool = False
    gpu_name: str = ""
    # Recommended mode derived from hardware
    recommended_mode: ExecutionMode = ExecutionMode.BALANCED
    # Recommended local model tier for this hardware
    recommended_model_tier: str = "medium"   # "tiny", "small", "medium", "large"
    # Recommended max concurrency (agentic turns, sub-agents)
    recommended_max_concurrency: int = 2
    # Any detection notes or warnings
    notes: list = field(default_factory=list)


def detect_hardware() -> HardwareProfile:
    """
    Detect host hardware capabilities and return a HardwareProfile.

    This function is safe to call at startup; it never modifies system state.
    CPU topology, RAM, OS, and basic virtualisation hints are detected.
    """
    profile = HardwareProfile()
    profile.os_platform = platform.system()
    profile.cpu_architecture = platform.machine()

    if _PSUTIL_AVAILABLE:
        try:
            vmem = psutil.virtual_memory()
            profile.total_ram_gb = round(vmem.total / (1024 ** 3), 1)
            profile.available_ram_gb = round(vmem.available / (1024 ** 3), 1)
        except Exception:
            profile.notes.append("Could not read RAM info")

        try:
            profile.cpu_physical_cores = psutil.cpu_count(logical=False) or 1
            profile.cpu_logical_cores = psutil.cpu_count(logical=True) or 1
        except Exception:
            profile.notes.append("Could not read CPU info")
    else:
        import os
        profile.cpu_logical_cores = os.cpu_count() or 1
        profile.cpu_physical_cores = profile.cpu_logical_cores
        profile.notes.append("psutil not available – limited hardware detection")

    # Basic VM detection
    profile.is_virtual_machine = _detect_virtualisation()

    # Derive recommended mode and tier
    profile.recommended_mode = _derive_mode(profile)
    profile.recommended_model_tier = _derive_model_tier(profile)
    profile.recommended_max_concurrency = _derive_concurrency(profile)

    debug_log(
        f"hardware profile: RAM={profile.total_ram_gb}GB "
        f"cores={profile.cpu_physical_cores}p/{profile.cpu_logical_cores}l "
        f"mode={profile.recommended_mode.value} "
        f"tier={profile.recommended_model_tier}",
        "hardware",
    )
    return profile


def _detect_virtualisation() -> bool:
    """Best-effort VM detection via platform hints (no subprocess)."""
    version = platform.version().lower()
    vm_hints = ("hyperv", "vmware", "virtualbox", "kvm", "xen", "qemu", "lxc")
    return any(h in version for h in vm_hints)


def _derive_mode(p: HardwareProfile) -> ExecutionMode:
    """Derive execution mode from hardware profile."""
    ram = p.total_ram_gb
    cores = p.cpu_physical_cores

    if ram < 4 or cores <= 2:
        return ExecutionMode.LOW_RESOURCE
    if ram >= 32 and cores >= 8:
        return ExecutionMode.PERFORMANCE
    return ExecutionMode.BALANCED


def _derive_model_tier(p: HardwareProfile) -> str:
    """Map RAM to recommended local model tier."""
    ram = p.total_ram_gb
    if ram < 4:
        return "tiny"    # 1b–3b models only
    if ram < 8:
        return "small"   # 3b–7b models
    if ram < 16:
        return "medium"  # 7b–13b models
    return "large"       # 13b+ models


def _derive_concurrency(p: HardwareProfile) -> int:
    """Recommend max concurrency for agentic tasks."""
    if p.recommended_mode == ExecutionMode.LOW_RESOURCE:
        return 1
    if p.recommended_mode == ExecutionMode.PERFORMANCE:
        return 4
    return 2


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_cached_profile: Optional[HardwareProfile] = None
_profile_lock = threading.Lock()


def get_hardware_profile(force_refresh: bool = False) -> HardwareProfile:
    """
    Return the cached hardware profile, detecting it on first call.

    Args:
        force_refresh: If True, re-detect even if cached.
    """
    global _cached_profile
    with _profile_lock:
        if _cached_profile is None or force_refresh:
            _cached_profile = detect_hardware()
        return _cached_profile
