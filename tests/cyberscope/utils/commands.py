"""Safe argument-array subprocess execution."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    error: str = ""


class CommandRunner:
    def __init__(self, default_timeout: float = 10.0, max_output_bytes: int = 65_536) -> None:
        self.default_timeout = default_timeout
        self.max_output_bytes = max_output_bytes

    def run(self, argv: Sequence[str], timeout: float | None = None) -> CommandResult:
        if isinstance(argv, (str, bytes)):
            raise TypeError("command must be an argument sequence, not a string")
        command = tuple(argv)
        if not command or any(not isinstance(item, str) or not item for item in command):
            raise ValueError("command must contain non-empty string arguments")
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.default_timeout if timeout is None else timeout,
                check=False,
            )
            return CommandResult(
                command,
                completed.returncode,
                self._bounded(completed.stdout),
                self._bounded(completed.stderr),
                time.monotonic() - started,
            )
        except FileNotFoundError:
            return CommandResult(command, None, "", "", time.monotonic() - started, error=f"command not found: {command[0]}")
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                command,
                None,
                self._bounded(_as_text(exc.stdout)),
                self._bounded(_as_text(exc.stderr)),
                time.monotonic() - started,
                timed_out=True,
                error=f"command timed out after {timeout or self.default_timeout:g} seconds",
            )

    def _bounded(self, value: str) -> str:
        encoded = value.encode("utf-8", errors="replace")[: self.max_output_bytes]
        return encoded.decode("utf-8", errors="replace")


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
