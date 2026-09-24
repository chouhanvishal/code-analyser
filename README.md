# Autonomous Code-Change Service

An autonomous service that receives repository snapshots and coding task descriptions, uses an LLM-driven agent to inspect, modify, and verify code changes, subjects candidates to an independent delivery gate in an isolated sandbox, and delivers high-reliability unified diffs before deadlines.

---

## 1. Architecture Overview

The system is structured into four decoupled layers designed for correctness, determinism, and deadline adherence:

```
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Service API (app.py)                    │
│   - GET /health                                                 │
│   - POST /solve                                                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Autonomous Solver (solver.py)                 │
│   - Dynamic Test Command Discovery (run_tests.sh, Makefile, etc.)│
│   - Deadline Budgeter (proactive exit buffer)                   │
│   - Task-Derived Test Synthesis & Baseline Verification         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐
│    LLM Agent Loop (llm.py)    │       │   Sandbox Runner (sandbox.py) │
│ - Tools:                      │       │ - Acceptance container        │
│   * view_file                 │◄─────►│ - --network none              │
│   * write_file                │       │ - Resource-constrained        │
│   * replace_lines             │       │   (1GB RAM, 2 CPUs, tmpfs)    │
│   * search_code               │       └───────────────────────────────┘
│   * run_tests                 │                       │
└───────────────────────────────┘                       │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │ Independent Gate (gate.py)    │
                                        │ - Strict Static Rule Checker  │
                                        │ - Pristine Snapshot Isolation │
                                        │ - Rejection fallback to null  │
                                        └───────────────────────────────┘
```

1. **HTTP Service (`service/app.py`)**: Multi-threaded, lightweight server exposing `/health` and `/solve`. Handles base64 repository archive decoding, deadline tracking, and JSON serialization.
2. **Autonomous Solver Loop (`service/agent/solver.py`)**: Explores the repository layout, runs initial baseline tests to capture failing assertions, generates targeted code edits, and iterates based on compiler/test feedback.
3. **Environment Parity Sandbox (`service/sandbox.py`)**: Executes tests inside the `acceptance:latest` Docker image with `--network none`, `--memory 1g`, `--cpus 2`, and tmpfs `/tmp:exec`, matching the exact client grading environment.
4. **Independent Delivery Gate (`service/gate.py`)**: Validates every candidate diff against public formatting/path rules (UTF-8, LF endings, no symlinks, max 200KB, relative paths, no restricted prefixes) and verifies clean application (`git apply --check`) and test pass on an untouched snapshot. Never delivers unverified diffs.

---

## 2. Trade-offs and Design Decisions

- **Single-Turn vs. Multi-Turn Feedback**:
  - *Decision*: We implement an iterative multi-turn agent loop with real-time test execution (`run_tests`).
  - *Trade-off*: Multi-turn agent loops incur higher token latency than single-shot generation, but provide significantly higher pass rates because syntax errors and subtle test failures are repaired interactively.
- **Strict Delivery Gate with Null Fallback**:
  - *Decision*: If a diff fails static format checks, git apply, or test execution, the gate rejects it and delivers `null` (or the last verified passing candidate) if time expires.
  - *Trade-off*: A `null` diff earns zero credit for that request, but prevents pre-execution rejections and guarantees that invalid or corrupt diffs are never submitted.
- **Deadline Safety Budget**:
  - *Decision*: The solver reserves a 15-second safety buffer before `deadline_seconds` to terminate the agent loop and run final delivery gate verification.
  - *Trade-off*: Limits late-stage exploration when time is low, but guarantees 0% missed-deadline rates.
- **Standard Library Tooling**:
  - *Decision*: The core service is built with Python 3.12 standard library components for HTTP serving, git diff management, and subprocess sandbox controls.
  - *Trade-off*: Zero external pip runtime dependencies needed for the server itself, ensuring instant container startup and maximum portability.

---

## 3. How to Run

### Prerequisites
- Docker (for isolated sandbox testing)
- Python 3.10+ (Python 3.12 recommended)
- An LLM API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`)

### Build the Acceptance Image
```bash
bash acceptance/build.sh
```

### Start the Service Locally
```bash
# Set your preferred API key
export OPENAI_API_KEY="your-api-key"
# export ANTHROPIC_API_KEY="your-api-key"
# export GEMINI_API_KEY="your-api-key"

# Start the service
python3 -m service.app --port 8000
```

### Run with Docker Compose
```bash
docker-compose up --build
```

### Run the Evaluation Harness
```bash
python3 harness/run_client.py --url http://localhost:8000 tasks/public/* --concurrency 2 --out results/
```
