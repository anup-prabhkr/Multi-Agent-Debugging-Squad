"""
Diagnoser Agent — analyses buggy Python code and explains the root cause.

Uses a local Ollama LLM via LangChain to produce a plain-English diagnosis.
When previous failed attempts are provided, it avoids repeating the same
diagnosis and reasons about why prior fixes failed.
"""

from __future__ import annotations

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from core.models import SessionState

# Default model — change this if you have a different model pulled locally.
DEFAULT_MODEL = "codellama"

SYSTEM_PROMPT = (
    "You are an expert Python debugger with deep knowledge of common runtime "
    "errors, logic bugs, and edge cases. Your job is to read a piece of "
    "buggy Python code (and optionally a traceback or error description), "
    "then explain the root cause of the bug in 2–4 clear, concise sentences "
    "using plain English.\n\n"
    "Rules:\n"
    "- Do NOT output any code — only your diagnosis in plain text.\n"
    "- If previous failed attempts are provided, study them carefully. "
    "Explain why the last fix did not resolve the issue and propose a "
    "different root cause or angle of attack. Never repeat a diagnosis "
    "that has already been tried.\n"
    "- Be specific: mention the exact line, variable, or operation that is "
    "wrong and why."
)


def _build_history_context(state: SessionState) -> str:
    """Format previous attempts into context for the Diagnoser."""
    if not state.attempts:
        return ""

    parts = ["\n--- Previous failed attempts (do NOT repeat these diagnoses) ---"]
    for att in state.attempts:
        parts.append(
            f"\nAttempt {att.attempt_number}:\n"
            f"  Diagnosis: {att.diagnosis}\n"
            f"  Fix result: {'PASSED' if att.test_passed else 'FAILED'}\n"
            f"  Error output: {att.error_message or att.test_output or '(none)'}"
        )
    return "\n".join(parts)


def diagnose(state: SessionState, model_name: str = DEFAULT_MODEL) -> str:
    """
    Analyse the current code + history and return a plain-text diagnosis.

    Args:
        state: The current SessionState containing original code, optional
               user error, and any previous attempts.
        model_name: Ollama model to use.

    Returns:
        A string with the root-cause diagnosis (no code).
    """
    llm = ChatOllama(model=model_name, temperature=0.3)

    # Build the human message with all relevant context
    user_parts = [f"## Buggy Code\n```python\n{state.original_code}\n```"]

    if state.user_provided_error:
        user_parts.append(f"\n## Error / Traceback\n{state.user_provided_error}")

    history_ctx = _build_history_context(state)
    if history_ctx:
        user_parts.append(history_ctx)

    user_msg = "\n".join(user_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ]

    response = llm.invoke(messages)
    return response.content.strip()
