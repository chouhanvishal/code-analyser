"""Autonomous solver loop orchestrating codebase exploration, patching, and verification."""
from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from service.agent.llm import LLMClient
from service.agent.tools import AgentTools
from service.config import config
from service.gate import DeliveryGate, static_check
from service.sandbox import Sandbox, copy_repo, extract_repo_archive, get_git_diff

logger = logging.getLogger("autonomous_service.solver")

SYSTEM_PROMPT = """You are an expert autonomous software engineer solving a coding task on an offline codebase.
You are given a repository snapshot and a task description.

Your goal is to inspect the codebase, locate the bug or missing feature, make the necessary code changes, and verify your solution using tests.

RULES & CONSTRAINTS:
1. Environment is completely offline (no internet access). Use standard libraries only.
2. The final delivery must be a clean git unified diff that passes all static format checks:
   - Starts with `diff --git `
   - UTF-8 encoded with LF (`\\n`) line endings only.
   - No binary files, no symlinks.
   - Do NOT modify or create files in `.git/`, `acceptance/`, or `acceptance_tests/`.
3. Test early and test often using `run_tests`.
4. If there is a `run_tests.sh` script, it runs the repository's test suite.
5. You can view files, write files, replace specific line ranges, search code, and run tests.
6. When your changes are complete and all tests pass cleanly without errors, provide a brief summary of what was fixed.
"""


def detect_test_command(repo_path: Path) -> str:
    """Detects test command from repository contents."""
    if (repo_path / "run_tests.sh").exists():
        return "bash run_tests.sh"
    if (repo_path / "Makefile").exists():
        return "make test"
    if (repo_path / "Cargo.toml").exists():
        return "cargo test --offline"
    if (repo_path / "go.mod").exists():
        return "go test ./..."
    if (repo_path / "package.json").exists():
        return "npm test"
    return "bash run_tests.sh"


class AutonomousSolver:
    def __init__(self, sandbox: Sandbox | None = None, llm: LLMClient | None = None):
        self.sandbox = sandbox or Sandbox()
        self.llm = llm or LLMClient()
        self.gate = DeliveryGate(self.sandbox)

    def solve(
        self,
        request_id: str,
        repo_archive_b64: str,
        task_description: str,
        deadline_seconds: float = 240.0
    ) -> dict[str, Any]:
        started = time.monotonic()
        logger.info(f"[{request_id}] Starting solver (deadline: {deadline_seconds}s)")

        record: list[dict[str, Any]] = []
        best_verified_diff: str | None = None

        with tempfile.TemporaryDirectory(prefix=f"solve-{request_id}-") as tmp_root:
            tmp_path = Path(tmp_root)
            work_dir = tmp_path / "workspace"
            clean_dir = tmp_path / "pristine"

            # 1. Unpack repository archive
            repo_path = extract_repo_archive(repo_archive_b64, work_dir)
            pristine_repo = copy_repo(repo_path, clean_dir / "repo")

            # 2. Setup tools & detect test command
            test_cmd = detect_test_command(repo_path)
            tools = AgentTools(repo_path, self.sandbox, default_test_cmd=test_cmd)

            # 3. Baseline test run
            baseline_res = tools.run_tests(test_cmd)
            logger.info(f"[{request_id}] Baseline test result: {baseline_res[:100]}...")

            # 4. Prepare prompt & message history
            initial_user_prompt = (
                f"TASK DESCRIPTION:\n{task_description}\n\n"
                f"INITIAL REPOSITORY STRUCTURE:\n{tools.list_dir('.')}\n\n"
                f"DEFAULT TEST COMMAND: `{test_cmd}`\n\n"
                f"BASELINE TEST OUTPUT:\n{baseline_res}\n\n"
                f"Please inspect the files, make the required changes to solve the task, and verify with `run_tests`."
            )

            messages: list[dict[str, Any]] = [
                {"role": "user", "content": initial_user_prompt}
            ]

            turn = 0
            max_turns = config.max_turns
            safety_buffer = config.deadline_safety_buffer_s

            while turn < max_turns:
                turn += 1
                elapsed = time.monotonic() - started
                remaining = deadline_seconds - elapsed

                if remaining <= safety_buffer:
                    logger.warning(f"[{request_id}] Approaching deadline ({remaining:.1f}s left). Concluding agent loop.")
                    break

                try:
                    resp = self.llm.generate(messages, SYSTEM_PROMPT)
                except Exception as exc:
                    logger.error(f"[{request_id}] LLM generation failed: {exc}")
                    # Feed error back or break
                    break

                # Assistant response handling
                assistant_msg: dict[str, Any] = {"role": "assistant"}
                if resp.text:
                    assistant_msg["content"] = resp.text
                    record.append({"role": "assistant", "type": "text", "text": resp.text})

                if resp.tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["input"])
                            }
                        }
                        for tc in resp.tool_calls
                    ]
                    for tc in resp.tool_calls:
                        record.append({
                            "role": "assistant",
                            "type": "tool_call",
                            "name": tc["name"],
                            "input": tc["input"]
                        })

                messages.append(assistant_msg)

                if not resp.tool_calls:
                    # Model produced only text without tool calls
                    break

                # Execute tool calls
                all_tools_passed = True
                tests_executed = False

                for tc in resp.tool_calls:
                    tool_output, is_error = tools.execute_tool(tc["name"], tc["input"])
                    record.append({
                        "role": "tool",
                        "name": tc["name"],
                        "output": tool_output,
                        "is_error": is_error
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_output
                    })

                    if tc["name"] == "run_tests":
                        tests_executed = True
                        if "PASSED" in tool_output and not is_error:
                            current_diff = get_git_diff(repo_path)
                            if current_diff:
                                gate_res = self.gate.verify(pristine_repo, current_diff, test_cmd, timeout_s=30.0)
                                if gate_res.passed:
                                    best_verified_diff = current_diff
                                    logger.info(f"[{request_id}] Successfully verified candidate diff at turn {turn}.")
                        else:
                            all_tools_passed = False

                # If tests were run and passed gate and agent has no pending edits, we can wrap up
                if tests_executed and best_verified_diff and all_tools_passed:
                    break

            # 5. Final Delivery Gate verification
            final_diff: str | None = None
            current_diff = get_git_diff(repo_path)

            if current_diff:
                gate_res = self.gate.verify(pristine_repo, current_diff, test_cmd, timeout_s=30.0)
                if gate_res.passed:
                    final_diff = current_diff
                elif best_verified_diff:
                    final_diff = best_verified_diff
            elif best_verified_diff:
                final_diff = best_verified_diff

            # Format response
            cost_usd = self.llm.get_estimated_cost_usd()
            result_payload = {
                "request_id": request_id,
                "diff": final_diff,
                "record": record,
                "usage": {
                    "estimated_cost_usd": cost_usd,
                    "input_tokens": self.llm.total_input_tokens,
                    "output_tokens": self.llm.total_output_tokens,
                    "turns": turn,
                    "duration_s": round(time.monotonic() - started, 2)
                }
            }

            logger.info(f"[{request_id}] Finished in {result_payload['usage']['duration_s']}s (diff produced: {final_diff is not None}, cost: ${cost_usd:.4f})")
            return result_payload
