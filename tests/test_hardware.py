"""
Unit tests for src/jarvis/hardware.py.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest

from src.jarvis.hardware import (
    ExecutionMode,
    HardwareProfile,
    detect_hardware,
    get_hardware_profile,
)


@pytest.mark.unit
def test_detect_hardware_returns_profile():
    profile = detect_hardware()
    assert isinstance(profile, HardwareProfile)


@pytest.mark.unit
def test_profile_total_ram_non_negative():
    profile = detect_hardware()
    assert profile.total_ram_gb >= 0


@pytest.mark.unit
def test_profile_cpu_logical_cores_at_least_one():
    profile = detect_hardware()
    assert profile.cpu_logical_cores >= 1


@pytest.mark.unit
def test_profile_recommended_mode_is_valid():
    profile = detect_hardware()
    assert profile.recommended_mode in list(ExecutionMode)


@pytest.mark.unit
def test_profile_recommended_model_tier_is_valid():
    profile = detect_hardware()
    assert profile.recommended_model_tier in ("tiny", "small", "medium", "large")


@pytest.mark.unit
def test_get_hardware_profile_returns_same_object():
    p1 = get_hardware_profile(force_refresh=True)
    p2 = get_hardware_profile()
    assert p1 is p2
