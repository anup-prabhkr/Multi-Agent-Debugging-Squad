import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass


@dataclass
class RunResult:
    """Result of executing a Python script in the sandbox."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int


def run_code(code: str, timeout: int = 5) -> RunResult:
    """
    Execute a Python code string in a subprocess sandbox.

    Args:
        code: The Python source code to execute.
        timeout: Maximum execution time in seconds (default 5).

    Returns:
        RunResult with success flag, stdout, stderr, and exit code.
    """
    if not code or not code.strip():
        return RunResult(
            success=False,
            stdout="",
            stderr="Error: No code provided (empty input).",
            exit_code=1,
        )

    # Write code to a temporary file
    tmp_file = None
    try:
        tmp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            prefix="sandbox_",
            encoding="utf-8",
        )
        tmp_file.write(code)
        tmp_file.close()

        # Run in subprocess — never use shell=True
        result = subprocess.run(
            [sys.executable, tmp_file.name],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        return RunResult(
            success=(result.returncode == 0),
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return RunResult(
            success=False,
            stdout="",
            stderr=f"Error: Code execution timed out after {timeout} seconds "
                   f"(possible infinite loop).",
            exit_code=-1,
        )
    except Exception as e:
        return RunResult(
            success=False,
            stdout="",
            stderr=f"Error: Failed to execute code — {type(e).__name__}: {e}",
            exit_code=-1,
        )
    finally:
        # Always clean up the temp file
        if tmp_file is not None:
            try:
                os.unlink(tmp_file.name)
            except OSError:
                pass
