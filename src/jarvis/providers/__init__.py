"""
src/jarvis/providers package.

Exports the public surface of the provider abstraction layer.
"""
from .base import LLMProvider, ProviderCapabilities, ProviderInfo, ProviderKind, ProviderStatus
from .policy import ProviderSelectionPolicy, PolicyConstraints, PrivacyLevel, TaskType
from .registry import ProviderRegistry, get_provider_registry, initialise_providers_from_config

__all__ = [
    # Base abstractions
    "LLMProvider",
    "ProviderCapabilities",
    "ProviderInfo",
    "ProviderKind",
    "ProviderStatus",
    # Policy
    "ProviderSelectionPolicy",
    "PolicyConstraints",
    "PrivacyLevel",
    "TaskType",
    # Registry
    "ProviderRegistry",
    "get_provider_registry",
    "initialise_providers_from_config",
]
