"""Deterministic canonical JSON and SHA-256 generation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


def _validate_json_value(value: Any, path: str = "root") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite float at {path}")
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"non-string key at {path}")
            _validate_json_value(nested, f"{path}.{key}" if path != "root" else key)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_json_value(nested, f"{path}[{index}]")
        return
    raise TypeError(f"non-JSON value at {path}: {type(value).__name__}")


def canonical_json(data: Mapping[str, object]) -> str:
    """Return stable compact JSON suitable for integrity hashing."""

    _validate_json_value(data)
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_digest(data: Mapping[str, object]) -> str:
    """Return the lowercase SHA-256 digest of canonical JSON."""

    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
