"""
Orchestrator — runs the Diagnose → Fix → Test loop.

Exposes a generator function `run_debug_session()` that yields each
Attempt as it completes, enabling the Streamlit UI to render progress
live (attempt-by-attempt) rather than waiting for the entire loop.
"""

from __future__ import annotations

from typing import Generator

from core.models import Attempt, SessionState
from agents import diagnoser, fixer, tester

# Default Ollama model — change if you have a different one pulled.
DEFAULT_MODEL = "codellama"


def run_debug_session(
    original_code: str,
    user_error: str | None = None,
    max_attempts: int = 4,
    model_name: str = DEFAULT_MODEL,
) -> Generator[tuple[Attempt, SessionState], None, None]:
    """
    Run the full diagnose → fix → test loop as a generator.

    Yields:
        A tuple of (current_attempt, current_session_state) after each
        attempt, so the caller (e.g. Streamlit) can render progress live.

    The final yielded SessionState will have `resolved=True` if a fix
    was found, or `resolved=False` if max_attempts was exhausted.
    """
    state = SessionState(
        original_code=original_code,
        user_provided_error=user_error,
        max_attempts=max_attempts,
    )

    for i in range(1, max_attempts + 1):
        # --- Diagnose ---
        diagnosis = diagnoser.diagnose(state, model_name=model_name)

        # --- Fix ---
        patched_code = fixer.fix(state, diagnosis, model_name=model_name)

        # --- Test ---
        test_passed, test_output, error_msg = tester.run(patched_code)

        # --- Record attempt ---
        attempt = Attempt(
            attempt_number=i,
            diagnosis=diagnosis,
            patched_code=patched_code,
            test_passed=test_passed,
            test_output=test_output,
            error_message=error_msg,
        )
        state.attempts.append(attempt)

        if test_passed:
            state.resolved = True
            state.final_code = patched_code
            yield attempt, state
            return  # Stop the loop — bug is fixed

        # On the final failed attempt, set final_code before yielding
        # so the consumer (UI) sees it in the yielded state.
        if i == max_attempts and not state.resolved:
            state.final_code = patched_code

        yield attempt, state


# ---------------------------------------------------------------------------
# CLI test entrypoint: python -m core.orchestrator
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    # Read sample bug for testing
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_path = os.path.join(project_root, "sample_bugs", "bug1_index_error.py")

    with open(sample_path, "r") as f:
        buggy_code = f.read()

    print("=" * 60)
    print("CLI Test — Orchestrator with bug1_index_error.py")
    print("=" * 60)

    for attempt, session in run_debug_session(
        original_code=buggy_code,
        user_error="IndexError: list index out of range",
        max_attempts=3,
    ):
        print(f"\n--- Attempt {attempt.attempt_number} ---")
        print(f"Diagnosis: {attempt.diagnosis[:200]}...")
        print(f"Test passed: {attempt.test_passed}")
        print(f"Output: {attempt.test_output[:200]}")
        if attempt.test_passed:
            print("\n✓ Bug fixed!")
            break

    if not session.resolved:
        print("\n✗ Could not fix within max attempts.")
    print("\nDone.")
