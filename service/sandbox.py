"""Docker Sandbox and local execution environment matching acceptance environment."""
from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from typing import NamedTuple

from service.config import config


class ExecutionResult(NamedTuple):
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        out = (self.stdout + "\n" + self.stderr).strip()
        return out


class Sandbox:
    def __init__(self, image: str = config.docker_image, use_docker: bool = config.use_docker):
        self.image = image
        self.use_docker = use_docker

    def run(self, cmd: str, cwd: Path, timeout_s: float = 60.0) -> ExecutionResult:
        """Executes a command inside the acceptance Docker container with networking disabled."""
        started = time.monotonic()
        cwd_resolved = cwd.resolve()

        if self.use_docker:
            argv = [
                "docker", "run", "--rm", "--network", "none", "--memory", "1g", "--cpus", "2",
                "--pids-limit", "512", "--read-only", "--tmpfs", "/tmp:exec",
                "-v", f"{cwd_resolved}:/work:rw", "-w", "/work",
                "-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
                "-e", "GOCACHE=/tmp/gocache", "-e", "GOPATH=/tmp/gopath", "-e", "GOFLAGS=-mod=mod",
                "-e", "CARGO_HOME=/tmp/cargo", "-e", "npm_config_cache=/tmp/npm",
                self.image, "bash", "-c", cmd
            ]
            env = os.environ.copy()
            exec_cwd = None
        else:
            argv = ["bash", "-c", cmd]
            env = {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": os.environ.get("HOME", "/tmp"),
                "GOCACHE": "/tmp/gocache",
                "GOPATH": "/tmp/gopath",
                "GOFLAGS": "-mod=mod",
                "CARGO_HOME": "/tmp/cargo",
                "npm_config_cache": "/tmp/npm"
            }
            exec_cwd = str(cwd_resolved)

        try:
            r = subprocess.run(
                argv,
                cwd=exec_cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s
            )
            duration = round(time.monotonic() - started, 2)
            return ExecutionResult(
                exit_code=r.returncode,
                stdout=r.stdout or "",
                stderr=r.stderr or "",
                duration_s=duration,
                timed_out=False
            )
        except subprocess.TimeoutExpired as exc:
            duration = round(time.monotonic() - started, 2)
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return ExecutionResult(
                exit_code=-1,
                stdout=stdout,
                stderr=f"{stderr}\nCommand timed out after {timeout_s}s".strip(),
                duration_s=duration,
                timed_out=True
            )
        except Exception as exc:
            duration = round(time.monotonic() - started, 2)
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {type(exc).__name__}: {exc}",
                duration_s=duration,
                timed_out=False
            )


def extract_repo_archive(archive_b64: str, target_dir: Path) -> Path:
    """Extracts a base64-encoded tar.gz repository archive to target_dir/repo."""
    archive_bytes = base64.b64decode(archive_b64)
    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        # Safe extraction
        for member in tar.getmembers():
            # Prevent path traversal
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise ValueError(f"Dangerous path in archive: {member.name}")
        tar.extractall(target_dir)
    
    repo_path = target_dir / "repo"
    if not repo_path.exists():
        # Look for the root directory inside target_dir
        subdirs = [d for d in target_dir.iterdir() if d.is_dir()]
        if subdirs:
            repo_path = subdirs[0]
        else:
            repo_path = target_dir
    return repo_path


def copy_repo(src: Path, dest: Path) -> Path:
    """Copies an existing git repo snapshot directory to a clean destination."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=False)
    return dest


def get_git_diff(repo_path: Path) -> str:
    """Generates a clean unified diff from the working tree against HEAD."""
    # Ensure git config avoids crlf and filemode noise
    git_cfg = ["-c", "core.autocrlf=false", "-c", "core.filemode=false"]
    # Stage new tracked/untracked changes if needed or diff HEAD
    subprocess.run(["git", *git_cfg, "add", "-A"], cwd=repo_path, capture_output=True)
    res = subprocess.run(
        ["git", *git_cfg, "diff", "--staged", "--no-color", "--no-prefix=false"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    diff = res.stdout
    # Normalize CRLF to LF
    diff = diff.replace("\r\n", "\n")
    return diff
