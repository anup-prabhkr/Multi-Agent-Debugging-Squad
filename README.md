# 🐛 Multi-Agent Debugging Squad

A Python application where three AI agents — **Diagnoser**, **Fixer**, and **Tester** — collaborate in a loop to automatically debug user-submitted Python code. The system actually executes the code to verify fixes, retries on failure, and shows the full reasoning trail in a simple web UI.

Runs **100% locally** using [Ollama](https://ollama.com) — no paid APIs, no cloud calls.

---

## 🏗️ Architecture

```
User submits buggy code
        │
        ▼
┌─────────────────────────────────────────┐
│           Orchestrator Loop             │
│                                         │
│  ┌──────────┐  ┌────────┐  ┌────────┐  │
│  │ Diagnoser│→ │ Fixer  │→ │ Tester │  │
│  │  (LLM)   │  │ (LLM)  │  │(sandbox│  │
│  │          │  │        │  │  exec) │  │
│  └──────────┘  └────────┘  └────────┘  │
│       ↑                         │       │
│       └─── retry if failed ─────┘       │
│                                         │
└─────────────────────────────────────────┘
        │
        ▼
  Streamlit UI shows live progress
```

- **Diagnoser**: Reads the code + error, explains the root cause in plain English.
- **Fixer**: Rewrites the full corrected code based on the diagnosis.
- **Tester**: Executes the patched code in a subprocess sandbox (5s timeout).
- Loop retries up to N times, with each attempt aware of all previous failures.

---

## 📋 Prerequisites

1. **Python 3.10+** installed
2. **Ollama** installed and running — [Download Ollama](https://ollama.com/download)
3. A model pulled locally (default: `codellama`)

---

## 🚀 Quick Start

```bash
# 1. Install Ollama (if not already installed)
#    Download from https://ollama.com/download and install

# 2. Start the Ollama server (if not already running)
ollama serve

# 3. Pull the model (in a separate terminal)
ollama pull codellama

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 📁 Project Structure

```
multi-agent-debug-squad/
├── app.py                     # Streamlit UI entrypoint
├── requirements.txt
├── README.md
├── agents/
│   ├── __init__.py
│   ├── diagnoser.py           # Diagnoser agent logic + prompt
│   ├── fixer.py               # Fixer agent logic + prompt
│   └── tester.py              # Tester agent + code execution
├── core/
│   ├── __init__.py
│   ├── orchestrator.py        # Runs the Diagnose→Fix→Test loop
│   └── models.py              # Shared dataclasses
├── sandbox/
│   ├── __init__.py
│   └── runner.py              # Subprocess-based code execution
└── sample_bugs/
    ├── bug1_index_error.py
    ├── bug2_type_error.py
    └── bug3_infinite_loop.py
```

---

## ⚙️ Configuration

| Setting | Where | Default |
|---|---|---|
| Ollama model | Sidebar in the UI, or `DEFAULT_MODEL` in `agents/diagnoser.py` and `agents/fixer.py` | `codellama` |
| Max retry attempts | UI slider | 4 |
| Sandbox timeout | `sandbox/runner.py` → `run_code(timeout=5)` | 5 seconds |
| Streamlit port | `streamlit run app.py --server.port XXXX` | 8501 |

If you have a different model pulled (e.g., `llama3.2`), just type its name in the sidebar model input field.

---

## 🧪 Running Tests

```bash
# Test the sandbox runner (no Ollama needed)
python test_sandbox.py

# Test the orchestrator wiring (no Ollama needed — uses mock agents)
python test_orchestrator.py
```

---

## 📝 License

MIT
