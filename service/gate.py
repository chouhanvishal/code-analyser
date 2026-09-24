"""Independent Delivery Gate for validating diffs before submission."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

from service.sandbox import Sandbox, copy_repo

MAX_DIFF_BYTES = 200_000
FORBIDDEN_PATH_PREFIXES = (".git/", "acceptance/", "acceptance_tests/")


class GateResult(NamedTuple):
    passed: bool
    stage: str | None  # "static", "apply", "test", or None
    reason: str | None
    duration_s: float = 0.0


def static_check(diff_text: str | bytes) -> str | None:
    """Validate diff against public pre-execution rules. Return error string or None."""
    if isinstance(diff_text, str):
        diff_bytes = diff_text.encode("utf-8")
    else:
        diff_bytes = diff_text

    if len(diff_bytes) == 0:
        return "empty diff"
    if len(diff_bytes) > MAX_DIFF_BYTES:
        return f"diff is {len(diff_bytes)} bytes; limit is {MAX_DIFF_BYTES}"
    
    try:
        text = diff_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return "diff is not valid UTF-8"

    if "\r\n" in text:
        return "CRLF line endings"
    if "GIT binary patch" in text:
        return "binary patch content"
    if not text.startswith("diff --git "):
        return "not a git unified diff (must start with 'diff --git ')"

    for line in text.splitlines():
        m = re.match(r"^diff --git a/(\S+) b/(\S+)$", line)
        if not m:
            continue
        for path in m.groups():
            if path.startswith("/") or ".." in path.split("/"):
                return f"path escapes repository: {path}"
            if path.startswith(FORBIDDEN_PATH_PREFIXES):
                return f"path is restricted: {path}"
        if line.startswith("new file mode 120000") or line.startswith("new mode 120000"):
            return "symlink creation is not allowed"

    return None


class DeliveryGate:
    def __init__(self, sandbox: Sandbox | None = None):
        self.sandbox = sandbox or Sandbox()

    def verify(
        self,
        clean_repo_template: Path,
        diff_str: str,
        test_cmd: str | None = None,
        timeout_s: float = 45.0
    ) -> GateResult:
        """Applies the diff to a fresh snapshot copy and executes tests independently."""
        # Stage 1: Static Rules Check
        static_err = static_check(diff_str)
        if static_err:
            return GateResult(passed=False, stage="static", reason=static_err)

        # Stage 2: Apply diff on pristine snapshot
        with tempfile.TemporaryDirectory(prefix="gate-verify-") as tmp_dir:
            test_repo = copy_repo(clean_repo_template, Path(tmp_dir) / "repo")
            diff_file = Path(tmp_dir) / "candidate.diff"
            diff_file.write_text(diff_str, encoding="utf-8")

            # Check if diff applies cleanly
            check = subprocess.run(
                ["git", "apply", "--check", str(diff_file)],
                cwd=test_repo,
                capture_output=True,
                text=True
            )
            if check.returncode != 0:
                return GateResult(
                    passed=False,
                    stage="apply",
                    reason=f"does not apply cleanly: {check.stderr.strip()[:500]}"
                )

            # Apply diff
            apply_res = subprocess.run(
                ["git", "apply", str(diff_file)],
                cwd=test_repo,
                capture_output=True,
                text=True
            )
            if apply_res.returncode != 0:
                return GateResult(
                    passed=False,
                    stage="apply",
                    reason=f"git apply failed: {apply_res.stderr.strip()[:500]}"
                )

            # Stage 3: Test execution
            cmd = test_cmd or "bash run_tests.sh"
            exec_res = self.sandbox.run(cmd, test_repo, timeout_s=timeout_s)
            if not exec_res.success:
                tail = "\n".join(exec_res.output.splitlines()[-20:])
                return GateResult(
                    passed=False,
                    stage="test",
                    reason=f"Verification tests failed (exit {exec_res.exit_code}):\n{tail}"
                )

        return GateResult(passed=True, stage=None, reason=None)
