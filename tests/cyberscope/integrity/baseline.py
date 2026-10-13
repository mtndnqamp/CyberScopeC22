"""Validated, atomic baseline persistence."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cyberscope.integrity.comparison import diff_values
from cyberscope.integrity.providers import IntegrityProvider
from cyberscope.models import CollectedState, Difference
from cyberscope.utils.files import atomic_write_json, confined_path


BASELINE_NAME = re.compile(r"^baseline_\d{4}-\d{2}-\d{2}_\d{6}_[0-9a-f]{8}\.json$")


class BaselineValidationError(ValueError):
    """Raised when persisted baseline evidence is unsafe or inconsistent."""


@dataclass(frozen=True)
class BaselineRecord:
    path: Path
    created_at: str
    provider_id: str
    monitored_state: dict[str, Any]
    diagnostic_state: dict[str, Any]
    digest: str
    environment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "created_at": self.created_at,
            "provider_id": self.provider_id,
            "environment": self.environment,
            "monitored_state": self.monitored_state,
            "diagnostic_state": self.diagnostic_state,
            "digest": self.digest,
        }


class BaselineRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create(
        self,
        state: CollectedState,
        integrity: IntegrityProvider,
        environment: dict[str, Any] | None = None,
    ) -> BaselineRecord:
        now = datetime.now().astimezone()
        filename = f"baseline_{now:%Y-%m-%d_%H%M%S}_{secrets.token_hex(4)}.json"
        path = self.root / filename
        record = BaselineRecord(
            path=path,
            created_at=now.isoformat(timespec="seconds"),
            provider_id=integrity.provider_id,
            monitored_state=state.monitored,
            diagnostic_state=state.diagnostic,
            digest=integrity.digest(state.monitored),
            environment=environment or {},
        )
        atomic_write_json(path, record.to_dict())
        atomic_write_json(self.root / "latest.json", record.to_dict())
        return record

    def load(self, name: str = "latest.json", integrity: IntegrityProvider | None = None) -> BaselineRecord:
        if name != "latest.json" and not BASELINE_NAME.fullmatch(name):
            raise BaselineValidationError("invalid baseline filename")
        try:
            path = confined_path(self.root, self.root / name)
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise BaselineValidationError(f"cannot load baseline: {exc}") from exc
        required = {"schema_version", "created_at", "provider_id", "monitored_state", "diagnostic_state", "digest", "environment"}
        if not isinstance(raw, dict) or not required.issubset(raw) or raw["schema_version"] != 1:
            raise BaselineValidationError("invalid or unsupported baseline schema")
        if not isinstance(raw["monitored_state"], dict) or not isinstance(raw["diagnostic_state"], dict):
            raise BaselineValidationError("baseline states must be mappings")
        if integrity is not None:
            if raw["provider_id"] != integrity.provider_id:
                raise BaselineValidationError("integrity provider does not match baseline")
            if integrity.digest(raw["monitored_state"]) != raw["digest"]:
                raise BaselineValidationError("stored baseline digest does not match monitored state")
        return BaselineRecord(
            path=path,
            created_at=str(raw["created_at"]),
            provider_id=str(raw["provider_id"]),
            monitored_state=raw["monitored_state"],
            diagnostic_state=raw["diagnostic_state"],
            digest=str(raw["digest"]),
            environment=raw["environment"] if isinstance(raw["environment"], dict) else {},
        )

    def list(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted((item for item in self.root.iterdir() if BASELINE_NAME.fullmatch(item.name)), reverse=True)

    def compare(self, baseline: BaselineRecord, state: CollectedState, integrity: IntegrityProvider) -> tuple[str, list[Difference]]:
        return integrity.digest(state.monitored), diff_values(baseline.monitored_state, state.monitored)
