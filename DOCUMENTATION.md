# 📚 Multi-Agent Debugging Squad — Technical Documentation

**System Version:** 1.0.0  
**Target Runtime:** Python 3.10+ | Local Ollama (`codellama` / `llama3.2`) | Streamlit  

---

## 1. Executive Summary

The **Multi-Agent Debugging Squad** is an autonomous multi-agent software engineering system designed to automatically diagnose, repair, and empirically verify buggy Python code.

Traditional LLM code generation often suffers from self-confirmation bias and hallucinated syntax because single-prompt completions are never executed or verified. The Multi-Agent Debugging Squad addresses this by combining **LLM-based cognitive reasoning** with **deterministic subprocess sandbox execution** in a dynamic closed-loop feedback cycle.

### Key System Characteristics
- **100% Local & Private:** Powered by Ollama (`codellama` default); no cloud API calls or external keys required.
- **Empirical Verification:** Patched code is executed in an isolated Python subprocess; fixes are only accepted if the process completes with an exit code of `0`.
- **State-Aware Retries:** Failed attempts accumulate in-memory; subsequent agent loops receive full historical context to prevent repeating mistakes.
- **Real-Time Streaming UI:** Built with Streamlit using a Python Generator pattern (`yield`) for live progress rendering.

---

## 2. System Architecture

The system follows a decoupled, layered architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION LAYER                              │
│                                 (app.py)                                    │
│       Streamlit Web UI · Custom CSS · Reactive Generator Rendering          │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ORCHESTRATION LAYER                             │
│                           (core/orchestrator.py)                            │
│           Generator-based Retry Loop · State History Accumulation           │
└───────────────────┬──────────────────┬──────────────────┬───────────────────┘
                    │                  │                  │
                    ▼                  ▼                  ▼
┌──────────────────────┐    ┌────────────────────┐    ┌──────────────────────┐
│  DIAGNOSER AGENT     │    │    FIXER AGENT     │    │     TESTER AGENT     │
│ (agents/diagnoser.py)│    │  (agents/fixer.py) │    │  (agents/tester.py)  │
│ LLM Root-Cause Expl. │    │ Code Rewrite & RegEx│    │ Subprocess Execution │
└──────────────────────┘    └────────────────────┘    └──────────┬───────────┘
                                                                 │
                                                                 ▼
                                                      ┌──────────────────────┐
                                                      │   SANDBOX RUNNER     │
                                                      │  (sandbox/runner.py) │
                                                      │ Subprocess Isolation │
                                                      │ Timeout & UTF-8 Guard│
                                                      └──────────────────────┘
```

---

## 3. Module & Component Deep Dive

### 3.1 Data Layer (`core/models.py`)

Defines the strongly-typed data structures for carrying state between agents and the UI layer.

#### Dataclasses:
- **`Attempt`**:
  ```python
  @dataclass
  class Attempt:
      attempt_number: int
      diagnosis: str
      patched_code: str
      test_passed: bool
      test_output: str
      error_message: str | None
  ```
- **`SessionState`**:
  ```python
  @dataclass
  class SessionState:
      original_code: str
      user_provided_error: str | None
      attempts: list[Attempt] = field(default_factory=list)
      final_code: str | None = None
      resolved: bool = False
      max_attempts: int = 4
  ```

---

### 3.2 Agent Layer (`agents/`)

#### 3.2.1 Diagnoser Agent (`agents/diagnoser.py`)
- **Input:** `SessionState` (original code, optional traceback, and prior attempts) + `model_name`.
- **Role:** Software Diagnostician.
- **Behavior:** Analyzes the code and error log, outputting 2–4 sentences explaining the root cause in plain English (no code).
- **History Awareness:** Formats previous failed diagnoses via `_build_history_context()` so the model explicitly avoids repeating past incorrect hypotheses.

#### 3.2.2 Fixer Agent (`agents/fixer.py`)
- **Input:** `SessionState`, `diagnosis: str`, and `model_name`.
- **Role:** Software Developer.
- **Behavior:** Rewrites the full corrected Python file based on the Diagnoser's findings.
- **Sanitization Pipeline:** Applies `_strip_markdown_fences()` using regex `r"```(?:python|py)?\s*\n(.*?)```"` with `re.IGNORECASE` to extract clean, executable code even if the LLM wraps output in markdown blocks.

#### 3.2.3 Tester Agent (`agents/tester.py`)
- **Input:** `patched_code: str`, `timeout: int = 5`.
- **Role:** QA Automation Engineer.
- **Behavior:** Delegates execution to `sandbox.runner.run_code()`. Returns a structured tuple: `(test_passed: bool, test_output: str, error_message: str | None)`.

---

### 3.3 Sandbox Execution Layer (`sandbox/runner.py`)

Executes arbitrary Python code safely without risking host application instability.

- **Subprocess Isolation:** Uses `subprocess.run([sys.executable, tmp_file.name], ...)` with `shell=False`. Avoids dangerous `exec()` or `eval()` calls.
- **Timeout Protection:** Catches `subprocess.TimeoutExpired` at 5 seconds (configurable) to terminate infinite loops.
- **Cross-Platform UTF-8 Guard:** Specifies explicit `encoding="utf-8"` and `errors="replace"` on both file writing and subprocess streams for robust Windows compatibility.
- **Result Object (`RunResult`)**:
  ```python
  @dataclass
  class RunResult:
      success: bool
      stdout: str
      stderr: str
      exit_code: int
  ```

---

### 3.4 Orchestration Layer (`core/orchestrator.py`)

Manages the multi-agent control loop.

```python
def run_debug_session(
    original_code: str,
    user_error: str | None = None,
    max_attempts: int = 4,
    model_name: str = "codellama",
) -> Generator[tuple[Attempt, SessionState], None, None]:
```

- **Generator Pattern:** Yields `(Attempt, SessionState)` after every test run, giving UI callers real-time streaming progress.
- **Loop Termination Criteria:**
  1. `test_passed == True` → Sets `resolved = True`, assigns `final_code`, yields, and terminates immediately.
  2. `i == max_attempts` → Sets `final_code` to the best attempt, yields, and ends loop.

---

### 3.5 User Interface Layer (`app.py`)

Streamlit web application providing interactive code input, sample loading, live execution monitoring, and downloadable results.

- **Design System:** Custom CSS incorporating `Inter` (sans-serif) and `JetBrains Mono` fonts, gradient hero header, visual pipeline nodes, and dark-mode compatible accent cards.
- **Sample Bug Selector:** Pre-loads sample scenarios (`IndexError`, `TypeError`, `Infinite Loop`).
- **Resilient Connection Handling:** Wraps orchestrator iteration in `try...except` to catch Ollama server connection errors gracefully.

---

## 4. Setup & Running Instructions

### Prerequisites
1. **Python 3.10+** installed
2. **Ollama** installed ([Download Ollama](https://ollama.com/download))

### Step-by-Step Instructions

```bash
# 1. Navigate to project root
cd d:\python_prj\multi-agent-debug-squad

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start Ollama server
ollama serve

# 4. Pull required model
ollama pull codellama

# 5. Launch the Streamlit application
streamlit run app.py
```

Application will open at `http://localhost:8501`.

---

## 5. Verification & Testing

The codebase includes two independent test suites:

### Sandbox Tests (`test_sandbox.py`)
Verifies execution logic, runtime error catching, timeout handling, empty input handling, and sample bugs:
```bash
python test_sandbox.py
```

### Orchestrator Tests (`test_orchestrator.py`)
Verifies generator yielding, state accumulation, attempt limits, and termination logic using mocked agents:
```bash
python test_orchestrator.py
```

---

## 6. Directory Structure Reference

```
multi-agent-debug-squad/
├── app.py                     # Streamlit UI entrypoint
├── requirements.txt           # Dependency specifications
├── README.md                  # Quick-start guide
├── DOCUMENTATION.md           # Full technical documentation
├── test_sandbox.py            # Sandbox runner unit tests
├── test_orchestrator.py       # Orchestrator loop unit tests
├── agents/
│   ├── __init__.py
│   ├── diagnoser.py           # Diagnoser agent (LLM)
│   ├── fixer.py               # Fixer agent (LLM + regex)
│   └── tester.py              # Tester agent (deterministic)
├── core/
│   ├── __init__.py
│   ├── orchestrator.py        # Generator-based retry loop
│   └── models.py              # Data models (Attempt, SessionState)
├── sandbox/
│   ├── __init__.py
│   └── runner.py              # Subprocess execution sandbox
└── sample_bugs/
    ├── bug1_index_error.py    # Sample 1: IndexError
    ├── bug2_type_error.py     # Sample 2: TypeError
    └── bug3_infinite_loop.py  # Sample 3: Infinite loop
```
