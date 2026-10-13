"""Path-aware deterministic state comparison."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cyberscope.models import Difference


_MISSING = object()


def diff_values(before: Any, after: Any, path: str = "") -> list[Difference]:
    """Return stable dotted-path differences between JSON-compatible values."""

    if isinstance(before, Mapping) and isinstance(after, Mapping):
        differences: list[Difference] = []
        for key in sorted(set(before) | set(after)):
            nested_path = f"{path}.{key}" if path else str(key)
            left = before.get(key, _MISSING)
            right = after.get(key, _MISSING)
            if left is _MISSING:
                differences.append(Difference(nested_path, "added", None, right))
            elif right is _MISSING:
                differences.append(Difference(nested_path, "removed", left, None))
            else:
                differences.extend(diff_values(left, right, nested_path))
        return differences
    if before != after:
        return [Difference(path or "root", "changed", before, after)]
    return []
