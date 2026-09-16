"""
Fixer Agent — rewrites buggy Python code based on the Diagnoser's explanation.

Uses a local Ollama LLM via LangChain to produce a corrected version of the
code. Output is post-processed to strip markdown fences in case the LLM
wraps the code in ```python ... ``` blocks.
"""

from __future__ import annotations

import re

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from core.models import SessionState

# Default model — change this if you have a different model pulled locally.
DEFAULT_MODEL = "codellama"

SYSTEM_PROMPT = (
    "You are an expert Python developer. You will receive a piece of buggy "
    "Python code together with a diagnosis explaining what is wrong.\n\n"
    "Your task: rewrite the FULL corrected Python file based on the "
    "diagnosis. The output must be directly executable Python code.\n\n"
    "Rules:\n"
    "- Output ONLY the corrected Python code — no explanations, no markdown "
    "fences, no commentary before or after the code.\n"
    "- Preserve the original function names, variable names, and overall "
    "structure as much as possible (minimal diff).\n"
    "- If previous patches are provided, study why they failed and take a "
    "different approach.\n"
    "- The code must be complete and runnable as-is — do not omit imports "
    "or the if __name__ == '__main__' block if the original had one."
)


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes add despite instructions.

    Handles patterns like:
        ```python\n...\n```
        ```\n...\n```
    """
    # Try to extract content between fences
    pattern = r"```(?:python|py)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # If no fences found, strip leading/trailing whitespace and return
    return text.strip()


def _build_failed_patches_context(state: SessionState) -> str:
    """Format previous failed patches so the Fixer can avoid repeating them."""
    failed = [a for a in state.attempts if not a.test_passed]
    if not failed:
        return ""

    parts = ["\n--- Previous failed patches (take a different approach) ---"]
    for att in failed:
        parts.append(
            f"\nAttempt {att.attempt_number} patch:\n"
            f"```python\n{att.patched_code}\n```\n"
            f"Result: FAILED — {att.error_message or att.test_output or '(unknown error)'}"
        )
    return "\n".join(parts)


def fix(state: SessionState, diagnosis: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Generate corrected Python code based on the diagnosis.

    Args:
        state: The current SessionState with original code and attempt history.
        diagnosis: The Diagnoser's plain-text explanation of the bug.
        model_name: Ollama model to use.

    Returns:
        A string of corrected, executable Python code (fences stripped).
    """
    llm = ChatOllama(model=model_name, temperature=0.2)

    user_parts = [
        f"## Original Buggy Code\n```python\n{state.original_code}\n```",
        f"\n## Diagnosis\n{diagnosis}",
    ]

    patches_ctx = _build_failed_patches_context(state)
    if patches_ctx:
        user_parts.append(patches_ctx)

    user_msg = "\n".join(user_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ]

    response = llm.invoke(messages)
    return _strip_markdown_fences(response.content)
