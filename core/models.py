
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Attempt:
    """Record of a single diagnose → fix → test cycle."""

    attempt_number: int
    diagnosis: str
    patched_code: str
    test_passed: bool
    test_output: str          # stdout/stderr from execution
    error_message: str | None


@dataclass
class SessionState:
    """Full state for one debugging session."""

    original_code: str
    user_provided_error: str | None
    attempts: list[Attempt] = field(default_factory=list)
    final_code: str | None = None
    resolved: bool = False
    max_attempts: int = 4
