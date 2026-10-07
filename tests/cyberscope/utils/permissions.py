"""Explicit guards for potentially disruptive host tests."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


def require_real_test(enabled: bool, supported: bool, detail: str) -> PermissionDecision:
    if not enabled:
        return PermissionDecision(False, "real host mutation requires --real-test")
    if not supported:
        return PermissionDecision(False, detail)
    return PermissionDecision(True, "explicit real-test mode enabled")
