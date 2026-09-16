"""
Multi-Agent Debugging Squad — Streamlit UI

Entrypoint: streamlit run app.py

Provides a web interface where users can paste or select buggy Python code,
run it through three AI agents (Diagnoser, Fixer, Tester) in a retry loop,
and see live progress + the final corrected code.
"""

import os
import glob
import time
import streamlit as st

from core.orchestrator import run_debug_session
from core.models import SessionState


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Multi-Agent Debugging Squad",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — the key to not looking "AI-generated"
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ---- Import a nicer font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ---- Global overrides ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    code, pre, .stCode, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ---- Reduce Streamlit's default top padding ---- */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1100px;
    }

    /* ---- Hero / header area ---- */
    .hero-container {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 16px;
        padding: 2.5rem 2.5rem 2rem;
        margin-bottom: 2rem;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.75;
        margin: 0;
        font-weight: 400;
        line-height: 1.5;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 1rem;
        letter-spacing: 0.3px;
    }

    /* ---- Section labels ---- */
    .section-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #6366f1;
        margin-bottom: 0.75rem;
    }

    /* ---- Card styling ---- */
    .card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: box-shadow 0.2s ease;
    }
    .card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    }

    /* Dark mode cards */
    @media (prefers-color-scheme: dark) {
        .card {
            background: #1e1e2e;
            border-color: #313244;
        }
        .card:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        }
    }

    /* ---- Agent step cards ---- */
    .agent-step {
        border-left: 3px solid;
        padding-left: 1rem;
        margin-bottom: 0.75rem;
    }
    .agent-step.diagnoser { border-color: #8b5cf6; }
    .agent-step.fixer     { border-color: #3b82f6; }
    .agent-step.tester    { border-color: #10b981; }

    .agent-tag {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 3px 10px;
        border-radius: 4px;
        margin-bottom: 0.5rem;
    }
    .agent-tag.diagnoser { background: #ede9fe; color: #6d28d9; }
    .agent-tag.fixer     { background: #dbeafe; color: #1d4ed8; }
    .agent-tag.tester-pass { background: #d1fae5; color: #065f46; }
    .agent-tag.tester-fail { background: #fee2e2; color: #991b1b; }

    /* Dark mode agent tags */
    @media (prefers-color-scheme: dark) {
        .agent-tag.diagnoser { background: #2e1065; color: #c4b5fd; }
        .agent-tag.fixer     { background: #172554; color: #93c5fd; }
        .agent-tag.tester-pass { background: #052e16; color: #6ee7b7; }
        .agent-tag.tester-fail { background: #450a0a; color: #fca5a5; }
    }

    /* ---- Attempt header ---- */
    .attempt-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.3rem;
    }
    .attempt-number {
        font-size: 0.8rem;
        font-weight: 600;
        color: #6b7280;
    }
    .attempt-status {
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 12px;
    }
    .attempt-status.pass { background: #d1fae5; color: #065f46; }
    .attempt-status.fail { background: #fee2e2; color: #991b1b; }

    @media (prefers-color-scheme: dark) {
        .attempt-status.pass { background: #052e16; color: #6ee7b7; }
        .attempt-status.fail { background: #450a0a; color: #fca5a5; }
    }

    /* ---- Result banner ---- */
    .result-banner {
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin: 1rem 0;
        text-align: center;
    }
    .result-banner.success {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border: 1px solid #6ee7b7;
    }
    .result-banner.failure {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 1px solid #fbbf24;
    }
    .result-banner h3 {
        margin: 0 0 0.3rem 0;
    }
    .result-banner p {
        margin: 0;
        opacity: 0.8;
        font-size: 0.9rem;
    }

    @media (prefers-color-scheme: dark) {
        .result-banner.success {
            background: linear-gradient(135deg, #052e16 0%, #064e3b 100%);
            border-color: #059669;
        }
        .result-banner.failure {
            background: linear-gradient(135deg, #451a03 0%, #78350f 100%);
            border-color: #d97706;
        }
        .result-banner h3, .result-banner p {
            color: #e5e7eb;
        }
    }

    /* ---- Pipeline visualization ---- */
    .pipeline {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0;
        margin: 1.5rem 0;
        flex-wrap: wrap;
    }
    .pipeline-node {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.6rem 1.2rem;
        border-radius: 10px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .pipeline-node.diagnoser { background: #ede9fe; color: #6d28d9; }
    .pipeline-node.fixer     { background: #dbeafe; color: #1d4ed8; }
    .pipeline-node.tester    { background: #d1fae5; color: #065f46; }
    .pipeline-arrow {
        font-size: 1.1rem;
        color: #9ca3af;
        padding: 0 0.4rem;
    }
    .pipeline-retry {
        font-size: 0.7rem;
        color: #9ca3af;
        padding: 0 0.6rem;
        font-style: italic;
    }

    @media (prefers-color-scheme: dark) {
        .pipeline-node.diagnoser { background: #2e1065; color: #c4b5fd; }
        .pipeline-node.fixer     { background: #172554; color: #93c5fd; }
        .pipeline-node.tester    { background: #052e16; color: #6ee7b7; }
        .pipeline-arrow { color: #6b7280; }
    }

    /* ---- Sidebar polish ---- */
    section[data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #e5e7eb;
    }
    @media (prefers-color-scheme: dark) {
        section[data-testid="stSidebar"] {
            background: #11111b;
            border-right: 1px solid #313244;
        }
    }

    /* ---- Misc ---- */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
    }
    .stDownloadButton button {
        border-radius: 8px !important;
    }
    div[data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid #e5e7eb !important;
        overflow: hidden;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stExpander"] {
            border-color: #313244 !important;
        }
    }

    /* ---- Footer ---- */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem;
        font-size: 0.75rem;
        color: #9ca3af;
    }
    .footer a { color: #6366f1; text-decoration: none; }
    .footer a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    model_name = st.text_input(
        "Ollama model",
        value="codellama",
        help="Name of the Ollama model to use. Must be pulled locally via `ollama pull <name>`.",
    )

    st.markdown("---")

    st.markdown("### 📖 How it works")
    st.markdown("""
    Three specialized AI agents work in a loop:

    **🔍 Diagnoser** reads your code and error,
    explains the root cause in plain English.

    **🔧 Fixer** rewrites the corrected code
    based on the diagnosis.

    **🧪 Tester** runs the patched code in a
    safe sandbox and checks for errors.

    If the fix fails, the loop retries — each
    round aware of all previous attempts.

    > Runs **100% locally** via [Ollama](https://ollama.com).
    > No API keys. No cloud.
    """)


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🐛 Multi-Agent Debugging Squad</div>
    <p class="hero-subtitle">
        Paste buggy Python code. Three AI agents will diagnose, fix, and
        verify it automatically — running entirely on your machine.
    </p>
</div>
""", unsafe_allow_html=True)


# Pipeline visualization
st.markdown("""
<div class="pipeline">
    <div class="pipeline-node diagnoser">🔍 Diagnoser</div>
    <span class="pipeline-arrow">→</span>
    <div class="pipeline-node fixer">🔧 Fixer</div>
    <span class="pipeline-arrow">→</span>
    <div class="pipeline-node tester">🧪 Tester</div>
    <span class="pipeline-retry">⟳ retry if failed</span>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Load sample bugs
# ---------------------------------------------------------------------------
SAMPLE_BUGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_bugs")


@st.cache_data
def load_sample_bugs() -> dict[str, str]:
    """Load all .py files from sample_bugs/ directory."""
    bugs = {"— paste your own code —": ""}
    bug_labels = {
        "bug1_index_error.py": "🟥 IndexError — off-by-one list access",
        "bug2_type_error.py": "🟧 TypeError — string + int concatenation",
        "bug3_infinite_loop.py": "🟨 Infinite Loop — missing decrement",
    }
    pattern = os.path.join(SAMPLE_BUGS_DIR, "*.py")
    for filepath in sorted(glob.glob(pattern)):
        basename = os.path.basename(filepath)
        if basename.startswith("__"):
            continue
        label = bug_labels.get(basename, basename)
        with open(filepath, "r", encoding="utf-8") as f:
            bugs[label] = f.read()
    return bugs


sample_bugs = load_sample_bugs()


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Input</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    selected_sample = st.selectbox(
        "Select sample code",
        options=list(sample_bugs.keys()),
        help="Pick a pre-loaded buggy script or paste your own below.",
    )

with col2:
    max_attempts = st.number_input(
        "Max retries",
        min_value=1,
        max_value=10,
        value=4,
        step=1,
        help="How many diagnose→fix→test cycles to attempt.",
    )

# Pre-fill code area with selected sample
default_code = sample_bugs.get(selected_sample, "")

buggy_code = st.text_area(
    "Buggy Python code",
    value=default_code,
    height=220,
    placeholder="# Paste your buggy Python code here...",
    label_visibility="collapsed",
)

with st.expander("📋 Add a known error or traceback (optional)", expanded=False):
    error_text = st.text_area(
        "Error / traceback",
        value="",
        height=90,
        placeholder="Paste the error message or traceback here...",
        label_visibility="collapsed",
    )

st.markdown("")  # spacing

run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
with run_col2:
    run_button = st.button(
        "▶  Run Debug Squad",
        type="primary",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Run the debugging session
# ---------------------------------------------------------------------------
if run_button:
    # Validate input
    if not buggy_code or not buggy_code.strip():
        st.error("Please paste some Python code to debug.")
        st.stop()

    st.markdown("---")
    st.markdown('<div class="section-label">Debugging Session</div>', unsafe_allow_html=True)

    user_error = error_text.strip() if error_text and error_text.strip() else None
    final_state: SessionState | None = None
    attempt_count = 0

    try:
        for attempt, state in run_debug_session(
            original_code=buggy_code,
            user_error=user_error,
            max_attempts=max_attempts,
            model_name=model_name,
        ):
            final_state = state
            attempt_count += 1

            status_class = "pass" if attempt.test_passed else "fail"
            status_text = "PASSED" if attempt.test_passed else "FAILED"

            with st.expander(
                f"Attempt {attempt.attempt_number} — {status_text}",
                expanded=(attempt.attempt_number == len(state.attempts)),
            ):
                # --- Diagnoser ---
                st.markdown(
                    '<div class="agent-step diagnoser">'
                    '<span class="agent-tag diagnoser">🔍 Diagnoser</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(attempt.diagnosis)
                st.markdown('</div>', unsafe_allow_html=True)

                # --- Fixer ---
                st.markdown(
                    '<div class="agent-step fixer">'
                    '<span class="agent-tag fixer">🔧 Fixer</span>',
                    unsafe_allow_html=True,
                )
                st.code(attempt.patched_code, language="python")
                st.markdown('</div>', unsafe_allow_html=True)

                # --- Tester ---
                tester_class = "tester-pass" if attempt.test_passed else "tester-fail"
                tester_label = "🧪 Tester — Passed" if attempt.test_passed else "🧪 Tester — Failed"
                st.markdown(
                    f'<div class="agent-step tester">'
                    f'<span class="agent-tag {tester_class}">{tester_label}</span>',
                    unsafe_allow_html=True,
                )
                if attempt.test_passed:
                    st.success("Code executed successfully — no errors!")
                else:
                    st.error("Code still has errors.")

                if attempt.test_output and attempt.test_output.strip():
                    st.code(attempt.test_output, language="text")
                st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(
            f"**Error communicating with Ollama**\n\n"
            f"`{type(e).__name__}: {e}`\n\n"
            f"Make sure Ollama is running (`ollama serve`) and the model "
            f"`{model_name}` is pulled (`ollama pull {model_name}`)."
        )
        st.stop()

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown('<div class="section-label">Result</div>', unsafe_allow_html=True)

    if final_state and final_state.resolved:
        st.markdown(f"""
        <div class="result-banner success">
            <h3>✅ Bug Fixed!</h3>
            <p>Resolved in {len(final_state.attempts)} attempt{'s' if len(final_state.attempts) != 1 else ''}.</p>
        </div>
        """, unsafe_allow_html=True)

        st.code(final_state.final_code, language="python")

        dl1, dl2, dl3 = st.columns([1, 2, 1])
        with dl2:
            st.download_button(
                label="📥  Download fixed code",
                data=final_state.final_code,
                file_name="fixed_code.py",
                mime="text/x-python",
                use_container_width=True,
            )

    elif final_state:
        st.markdown(f"""
        <div class="result-banner failure">
            <h3>⚠️ Could Not Fully Resolve</h3>
            <p>Exhausted {len(final_state.attempts)} attempt{'s' if len(final_state.attempts) != 1 else ''}. Showing best effort below.</p>
        </div>
        """, unsafe_allow_html=True)

        if final_state.final_code:
            st.code(final_state.final_code, language="python")

            dl1, dl2, dl3 = st.columns([1, 2, 1])
            with dl2:
                st.download_button(
                    label="📥  Download best attempt",
                    data=final_state.final_code,
                    file_name="best_attempt.py",
                    mime="text/x-python",
                    use_container_width=True,
                )


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("""
<div class="footer">
    Built with <a href="https://streamlit.io">Streamlit</a> ·
    <a href="https://ollama.com">Ollama</a> ·
    <a href="https://python.langchain.com">LangChain</a>
    &nbsp;—&nbsp; runs 100% locally, no API keys required
</div>
""", unsafe_allow_html=True)
