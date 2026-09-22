"""Machine-readable and capstone-friendly report generation."""

from __future__ import annotations

import re
import secrets
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from cyberscope.utils.files import atomic_write_json, atomic_write_text


REPORT_QUERY = re.compile(r"^(?:[A-Z]+-\d{3}|STABILITY)(?:_[A-Za-z0-9_.-]+)?(?:\.json|\.txt)?$")


class ReportWriter:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, result: Mapping[str, Any]) -> tuple[Path, Path]:
        test_id = str(result.get("test_id", ""))
        if not re.fullmatch(r"[A-Z]+-\d{3}|STABILITY", test_id):
            raise ValueError("result contains invalid test ID")
        now = datetime.now().astimezone()
        stem = f"{test_id}_{now:%Y-%m-%d_%H%M%S}_{secrets.token_hex(4)}"
        json_path = self.root / f"{stem}.json"
        text_path = self.root / f"{stem}.txt"
        atomic_write_json(json_path, dict(result))
        atomic_write_text(text_path, self._render_text(result))
        return json_path, text_path

    def list(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(self.root.glob("*.json"), reverse=True)

    def find(self, query: str) -> list[Path]:
        if not REPORT_QUERY.fullmatch(query):
            raise ValueError("invalid report query")
        if not self.root.exists():
            return []
        exact = self.root / query
        if exact.is_file():
            return [exact]
        return sorted(self.root.glob(f"{query}*.json"), reverse=True)

    def _render_text(self, result: Mapping[str, Any]) -> str:
        changes = result.get("changed_parameters", [])
        change_lines = []
        if isinstance(changes, list):
            for item in changes:
                if isinstance(item, Mapping):
                    change_lines.extend([
                        f"  {item.get('path', 'unknown')}",
                        f"    before: {item.get('before')!r}",
                        f"    after:  {item.get('after')!r}",
                    ])
        if not change_lines:
            change_lines.append("  None")
        evidence = "\n".join(f"  - {item}" for item in result.get("evidence", [])) or "  None"
        errors = "\n".join(f"  - {item}" for item in result.get("errors", [])) or "  None"
        notes = "\n".join(f"  - {item}" for item in result.get("notes", [])) or "  None"
        return "\n".join([
            "CyberScope Security Test Report",
            "================================",
            f"Test ID: {result.get('test_id', '')}",
            f"Test Name: {result.get('test_name', '')}",
            f"Category: {result.get('category', '')}",
            f"Date: {result.get('timestamp', '')}",
            f"Device: {result.get('device', '')}",
            f"Operating System: {result.get('operating_system', '')}",
            f"Environment: {result.get('environment', '')}",
            f"Environment Mode: {result.get('environment_mode', '')}",
            "",
            f"Threat Scenario: {result.get('threat', '')}",
            f"Expected Result: {result.get('expected_result', '')}",
            f"Baseline Hash: {result.get('baseline_hash', '')}",
            f"Runtime Hash: {result.get('runtime_hash', '')}",
            f"Integrity Match: {'YES' if result.get('integrity_match') else 'NO'}",
            "Changed Parameters:",
            *change_lines,
            f"Detection Result: {result.get('detection_result', '')}",
            f"Result: {result.get('status', '')}",
            f"Restoration: {result.get('restoration_status', '')}",
            "Evidence:",
            evidence,
            "Errors:",
            errors,
            "Notes:",
            notes,
            "",
        ])
