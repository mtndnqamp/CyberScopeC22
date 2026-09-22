"""Atomic evidence artifacts for one security-test execution."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cyberscope.utils.files import atomic_write_json, atomic_write_text


TEST_ID = re.compile(r"^[A-Z]+-\d{3}$|^STABILITY$")
ALLOWED_JSON_ARTIFACTS = {"baseline.json", "runtime.json", "diff.json", "result.json"}


@dataclass(frozen=True)
class EvidenceSession:
    root: Path

    @classmethod
    def create(cls, evidence_root: Path, test_id: str) -> "EvidenceSession":
        if not TEST_ID.fullmatch(test_id):
            raise ValueError(f"invalid test ID: {test_id}")
        now = datetime.now().astimezone()
        root = evidence_root / f"{test_id}_{now:%Y%m%d_%H%M%S}_{secrets.token_hex(4)}"
        root.mkdir(parents=True, exist_ok=False)
        atomic_write_text(root / "commands.log", "")
        atomic_write_text(root / "run.log", f"[{now.isoformat(timespec='seconds')}] Starting {test_id}\n")
        return cls(root)

    def write_json(self, name: str, value: object) -> Path:
        if name not in ALLOWED_JSON_ARTIFACTS:
            raise ValueError(f"unsupported evidence artifact: {name}")
        path = self.root / name
        atomic_write_json(path, value)
        return path

    def append_command(self, record: dict[str, Any]) -> Path:
        path = self.root / "commands.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        return path

    def append_run(self, message: str) -> Path:
        safe_message = message.replace("\r", " ").replace("\n", " ")
        path = self.root / "run.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {safe_message}\n")
        return path
