"""
Unit tests for src/jarvis/guardrails.py.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

import pytest

from src.jarvis.guardrails import (
    GuardrailConfig,
    GuardrailEngine,
    GuardrailResult,
    _normalise_path,
)


@pytest.mark.unit
def test_system_path_etc_passwd_denied():
    engine = GuardrailEngine(GuardrailConfig())
    result = engine.check_path("/etc/passwd")
    assert result.allowed is False
    assert "System path blocked" in result.reason


@pytest.mark.unit
def test_windows_system_path_denied():
    engine = GuardrailEngine(GuardrailConfig())
    result = engine.check_path("c:/windows/system32")
    assert result.allowed is False


@pytest.mark.unit
def test_path_in_denied_list_is_denied():
    cfg = GuardrailConfig(denied_paths=["/home/user/secrets"])
    engine = GuardrailEngine(cfg)
    result = engine.check_path("/home/user/secrets/api_key.txt")
    assert result.allowed is False
    assert "denied list" in result.reason


@pytest.mark.unit
def test_path_in_allowed_list_is_allowed():
    cfg = GuardrailConfig(allowed_paths=["/home/user/projects"])
    engine = GuardrailEngine(cfg)
    result = engine.check_path("/home/user/projects/myapp/main.py")
    assert result.allowed is True


@pytest.mark.unit
def test_path_not_in_allowed_list_is_denied():
    cfg = GuardrailConfig(allowed_paths=["/home/user/projects"])
    engine = GuardrailEngine(cfg)
    result = engine.check_path("/home/user/documents/resume.pdf")
    assert result.allowed is False
    assert "not in allowed list" in result.reason


@pytest.mark.unit
def test_path_allowed_when_no_restrictions():
    engine = GuardrailEngine(GuardrailConfig())
    result = engine.check_path("/home/user/safe_file.txt")
    assert result.allowed is True
    assert result.reason == "No restrictions"


@pytest.mark.unit
def test_allow_system_paths_permits_etc():
    cfg = GuardrailConfig(allow_system_paths=True)
    engine = GuardrailEngine(cfg)
    result = engine.check_path("/etc/hosts")
    assert result.allowed is True


@pytest.mark.unit
def test_guardrail_result_fields():
    result = GuardrailResult(allowed=True, reason="test reason", path="/foo/bar")
    assert result.allowed is True
    assert result.reason == "test reason"
    assert result.path == "/foo/bar"


@pytest.mark.unit
def test_denied_takes_precedence_over_allowed():
    cfg = GuardrailConfig(
        allowed_paths=["/home/user"],
        denied_paths=["/home/user/secrets"],
    )
    engine = GuardrailEngine(cfg)
    result = engine.check_path("/home/user/secrets/token.txt")
    assert result.allowed is False
