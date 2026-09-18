#!/usr/bin/env python3
"""
grade.py: grade one diff against one task.

    python3 harness/grade.py --task tasks/public/01-pricing-tax --diff candidate.diff [--local]

Stages, in order. The first failing stage decides the verdict.
  1. static   the public rules in public_rules.md (size, encoding, format, paths)
  2. apply    `git apply --check` then `git apply` on a fresh git snapshot of the task's repo/
  3. tests    the task's acceptance_command from task.json, run inside the acceptance
              image with networking disabled (or on the host with --local, for development)

Prints one JSON object: {"task", "verdict": "accept"|"reject", "stage", "reason", "duration_s"}
Exit code 0 on accept, 1 on reject, 2 on harness error.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

MAX_DIFF_BYTES = 200_000
FORBIDDEN_PATH_PREFIXES = (".git/", "acceptance/", "acceptance_tests/")
TEST_TIMEOUT_S = 300   # compiled languages spend part of this on the build
DEFAULT_IMAGE = "acceptance:latest"


# ---------------------------------------------------------------- stage 1
def static_check(diff_bytes: bytes) -> str | None:
    """Return a rejection reason, or None if the diff passes the public rules."""
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


# ---------------------------------------------------------------- snapshot
# Tasks ship as plain, browsable repo/ directories. The git snapshot that the
# service receives and that grading applies diffs to is built here, on demand,
# with a fixed identity and date so every snapshot of a task is identical.
GIT_ENV = {**os.environ,
           "GIT_AUTHOR_NAME": "task", "GIT_AUTHOR_EMAIL": "task@example.com",
           "GIT_COMMITTER_NAME": "task", "GIT_COMMITTER_EMAIL": "task@example.com",
           "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
GIT_CFG = ["-c", "core.autocrlf=false", "-c", "core.filemode=false"]


def materialize_repo(src: Path, dest: Path) -> Path:
    """Copy a task's repo/ directory to dest and turn it into a one-commit git repository."""
    shutil.copytree(src, dest)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "snapshot"]):
        subprocess.run(["git", *GIT_CFG, *args], cwd=dest, env=GIT_ENV, check=True, capture_output=True)
    return dest


def pack_repo(task_dir: Path) -> bytes:
    """The bytes a service receives in repo_archive_b64: a tar.gz of the git snapshot, rooted at repo/."""
    with tempfile.TemporaryDirectory(prefix="pack-") as tmp:
        repo = materialize_repo(task_dir / "repo", Path(tmp) / "repo")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(repo, arcname="repo")
        return buf.getvalue()


# ---------------------------------------------------------------- stage 2


def apply_diff(repo: Path, diff_path: Path) -> str | None:
    check = subprocess.run(["git", "apply", "--check", str(diff_path)], cwd=repo,
                           capture_output=True, text=True)
    if check.returncode != 0:
        return "does not apply cleanly: " + check.stderr.strip()[:500]
    subprocess.run(["git", "apply", str(diff_path)], cwd=repo, check=True,
                   capture_output=True, text=True)
    return None


# ---------------------------------------------------------------- stage 3
def run_acceptance(task_dir: Path, repo: Path, local: bool, image: str) -> tuple[bool, str]:
    """Copy the acceptance suite into the patched snapshot and run the task's acceptance_command."""
    meta = json.loads((task_dir / "task.json").read_text())
    command = meta["acceptance_command"]
    shutil.copytree(task_dir / "acceptance", repo / "acceptance_tests")
    if local:
        argv = ["bash", "-c", command]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "HOME": os.environ.get("HOME", "/tmp")}
        cwd = repo
    else:
        argv = ["docker", "run", "--rm", "--network", "none", "--memory", "1g", "--cpus", "2",
                "--pids-limit", "512", "--read-only", "--tmpfs", "/tmp:exec",
                "-v", f"{repo}:/work:rw", "-w", "/work",
                "-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
                "-e", "GOCACHE=/tmp/gocache", "-e", "GOPATH=/tmp/gopath", "-e", "GOFLAGS=-mod=mod",
                "-e", "CARGO_HOME=/tmp/cargo", "-e", "npm_config_cache=/tmp/npm",
                image, "bash", "-c", command]
        env = os.environ
        cwd = None
    try:
        r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, f"acceptance run exceeded {TEST_TIMEOUT_S}s"
    output = (r.stdout + r.stderr).strip()
    tail = "\n".join(output.splitlines()[-25:])
    return r.returncode == 0, tail


# ---------------------------------------------------------------- driver
def grade(task_dir: Path, diff_path: Path, local: bool, image: str) -> dict:
    started = time.monotonic()
    result = {"task": task_dir.name, "verdict": "reject", "stage": None, "reason": None}

    reason = static_check(diff_path.read_bytes())
    if reason:
        result.update(stage="static", reason=reason)
        return _finish(result, started)

    with tempfile.TemporaryDirectory(prefix="grade-") as tmp:
        repo = materialize_repo(task_dir / "repo", Path(tmp) / "repo")
        reason = apply_diff(repo, diff_path.resolve())
        if reason:
            result.update(stage="apply", reason=reason)
            return _finish(result, started)
        ok, tail = run_acceptance(task_dir, repo, local, image)
        result.update(stage="tests", reason=None if ok else tail, verdict="accept" if ok else "reject")
        return _finish(result, started)


def _finish(result: dict, started: float) -> dict:
    result["duration_s"] = round(time.monotonic() - started, 2)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--task", required=True, type=Path, help="task directory containing task.json, repo/, acceptance/")
    p.add_argument("--diff", required=True, type=Path, help="unified diff to grade")
    p.add_argument("--local", action="store_true", help="run tests on the host instead of the acceptance image")
    p.add_argument("--image", default=DEFAULT_IMAGE, help="acceptance image tag (default: %(default)s)")
    a = p.parse_args()
    try:
        result = grade(a.task, a.diff, a.local, a.image)
    except Exception as exc:  # harness fault, not a candidate fault
        print(json.dumps({"task": a.task.name, "verdict": "error", "reason": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
