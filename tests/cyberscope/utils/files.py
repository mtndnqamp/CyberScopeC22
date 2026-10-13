"""Atomic writing and safe file measurements."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "mode": None, "uid": None, "gid": None, "size": None}
    stat_result = path.stat()
    return {
        "exists": True,
        "sha256": sha256_file(path) if path.is_file() else None,
        "mode": f"{stat_result.st_mode & 0o7777:04o}",
        "uid": stat_result.st_uid,
        "gid": stat_result.st_gid,
        "size": stat_result.st_size,
    }


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def atomic_write_json(path: Path, data: object) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def confined_path(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"path is outside controlled root: {candidate}")
    return resolved
