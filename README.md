# Take-home task: autonomous code-change service

## Overview

Build a small service that receives a repository snapshot and a task description, uses an LLM-driven agent to produce a code change, verifies that change independently, and delivers it before a deadline. Deliveries are graded by a private acceptance suite that the candidate never sees.

The point of the exercise is not to show that a model can write code. It is to show that a service built around a model can be trusted to be right, on time, and available, with no feedback beyond accept or reject.

## Scenario

A client operates a private acceptance pipeline. For each request it sends the service a repository snapshot and a task, receives a code change, applies that change to a clean copy inside an offline, resource-limited environment, and runs acceptance tests the service cannot see.

Acceptance is binary. A change that passes earns nearly full credit regardless of speed. A change that fails, does not apply cleanly, violates a formatting rule, or arrives late earns nothing. A service that is unreachable is treated as having failed every request it did not answer. The client returns only accept or reject.

## What is provided

- `acceptance/Dockerfile`: the acceptance environment, one image for every stack a task may use: Python 3.12, Node.js 18 (with the TypeScript compiler), Go 1.22, Rust 1.75, Java 21, GCC 13, Bash, and git 2.43, on Ubuntu 24.04, running as an unprivileged user. Grading runs inside it with networking disabled. Build it with `acceptance/build.sh` (or `docker build -t acceptance:latest acceptance`).
- `public_rules.md`: the pre-execution validation rules. The exact checks are in `harness/grade.py`.
- `tasks/public/`: seven tasks for development, in Python (3), JavaScript, Bash, Go, and C. Each has `task.json` (task text, deadline in seconds, `language`, `toolchain`, and the `test_command` that runs the repository's own tests), `repo/` (the repository files, plain and browsable), and `acceptance/` (the tests grading runs).
- `harness/`: `snapshot.py` turns a task's `repo/` into a local git repository to work in; `grade.py` grades one diff against one task; `run_client.py` drives a running service through the tasks and reports acceptance, pre-execution rejection, and missed-deadline rates. See `harness/README.md`.
- Four private tasks in the same format are withheld, including stacks that do not appear in the public set. Grading runs against them. A service must therefore take the language and test command from `task.json` rather than assuming Python.

## What this repository contains and runs

Every file here is plain text and can be read in the browser before cloning. There are no archives, no binaries, and no package installs. The only code that executes on your machine is the harness (standard-library Python 3.12, no dependencies), git, and Docker. The task repositories under `tasks/public/*/repo/` are ordinary source files; the harness turns them into a git snapshot on demand, and that snapshot is what arrives in `repo_archive_b64`.

## Request and response contract

`POST /solve`

```json
{
  "request_id": "string",
  "repo_archive_b64": "string (tar.gz, git repository)",
  "task": "string",
  "deadline_seconds": 240
}
```

Response, returned before `deadline_seconds` elapses:

```json
{
  "request_id": "string",
  "diff": "string (unified diff) or null",
  "record": [
    { "role": "assistant", "type": "tool_call", "name": "string", "input": {} },
    { "role": "assistant", "type": "text", "text": "string" },
    { "role": "tool", "name": "string", "output": "string", "is_error": false }
  ]
}
```

`record` is the ordered list of model turns and tool results from the run that produced `diff`.

`GET /health` returns 200 when the service can accept work. The harness checks it before sending tasks.

A `null` diff is a valid response and is graded as a failure; it exists so the service never sends something it has not verified.

## Requirements

### 1. Environment parity

Every local build and test run happens inside the provided image with networking disabled. Running tests on the host is a failing condition.

### 2. Verification against unseen tests

The service must construct its own evidence: run the repository's existing build and tests using the `test_command` from `task.json`, add at least one check derived from the task description, and, when time allows, generate more than one candidate change and keep the one that survives the most checks. Nothing may depend on a network download at test time; every task repository is standard-library only.

### 3. Independent delivery gate

A separate code path applies the final diff to an untouched copy of the repository and runs the checks itself. Nothing is delivered unless that gate has seen it pass. If the gate fails and time remains, the failure is fed back to the agent for repair. If time does not remain, the best diff that has already passed is delivered, or `null`.

## Constraints

- Python preferred; any language accepted.
- Any model provider; state which and why.
- Do not attempt to locate, infer, or read the private acceptance tests. Any request that reaches outside the repository snapshot is a failing condition.

## Deliverables

1. A repository containing the service and a `Dockerfile` or `docker-compose.yml` to run it.
2. `README.md`: how to run it, the architecture in a few paragraphs, and the trade-offs taken.
3. `results.md`: the `harness/run_client.py` report on the public tasks and the cost per request observed.
4. A short note on what would change in production: scaling, monitoring, cost control, and how a breaking change to the request contract would be absorbed.

## Submission

- Do not fork this repository; forks are visible to other candidates. Clone it, work in a private repository of your own, and share access with [reviewer].
- Questions are welcome. Clarifications are shared with all candidates.
- Timeline: 5 business days from receiving this task.
