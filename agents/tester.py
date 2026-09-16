"""
Tester Agent — executes patched code in the sandbox and reports results.

This is mostly deterministic: it writes the Fixer's code to the sandbox,
runs it, and returns pass/fail + output. Not a pure LLM call.
"""

from __future__ import annotations

from sandbox.runner import run_code, RunResult


def run(patched_code: str, timeout: int = 5) -> tuple[bool, str, str | None]:
    """
    Execute patched code in the sandbox and report results.

    Args:
        patched_code: The corrected Python code to test.
        timeout: Max seconds for execution.

    Returns:
        A tuple of (test_passed, test_output, error_message).
        - test_passed: True if exit code is 0 and no errors.
        - test_output: Combined stdout + stderr for display.
        - error_message: The stderr content if the test failed, else None.
    """
    result: RunResult = run_code(patched_code, timeout=timeout)

    # Build a combined output string for display
    output_parts = []
    if result.stdout:
        output_parts.append(f"[stdout]\n{result.stdout}")
    if result.stderr:
        output_parts.append(f"[stderr]\n{result.stderr}")

    test_output = "\n".join(output_parts) if output_parts else "(no output)"

    if result.success:
        return True, test_output, None
    else:
        error_msg = result.stderr if result.stderr else f"Process exited with code {result.exit_code}"
        return False, test_output, error_msg
