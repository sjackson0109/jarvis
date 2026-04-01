"""
Unit tests for src/jarvis/memory/policy.py.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest

from src.jarvis.memory.policy import RetentionPolicy, should_store


@pytest.mark.unit
def test_should_store_operational_default():
    assert should_store(is_operational=True) is True


@pytest.mark.unit
def test_should_store_informational_default():
    assert should_store(is_operational=False) is False


@pytest.mark.unit
def test_should_store_informational_when_policy_enables_it():
    policy = RetentionPolicy(store_informational=True)
    assert should_store(is_operational=False, policy=policy) is True


@pytest.mark.unit
def test_should_store_operational_can_be_disabled():
    policy = RetentionPolicy(store_operational=False)
    assert should_store(is_operational=True, policy=policy) is False


@pytest.mark.unit
def test_retention_policy_defaults():
    policy = RetentionPolicy()
    assert policy.store_informational is False
    assert policy.store_operational is True
    assert policy.store_task_outputs is True
    assert policy.retention_days == 30
    assert policy.max_conversation_summaries == 90
