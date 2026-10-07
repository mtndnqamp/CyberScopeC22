"""Interfaces and the built-in integrity provider."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from cyberscope.integrity.hashing import sha256_digest
from cyberscope.models import CollectedState


@runtime_checkable
class DeviceStateProvider(Protocol):
    def collect(self) -> CollectedState:
        """Collect current monitored and diagnostic state."""


@runtime_checkable
class IntegrityProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Return an identifier stored with each baseline."""

    def digest(self, monitored_state: Mapping[str, object]) -> str:
        """Calculate an integrity digest."""


class CanonicalIntegrityProvider:
    @property
    def provider_id(self) -> str:
        return "cyberscope-canonical-sha256-v1"

    def digest(self, monitored_state: Mapping[str, object]) -> str:
        return sha256_digest(monitored_state)
