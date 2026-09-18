#!/usr/bin/env python3
"""
snapshot.py: turn a task's plain repo/ directory into a local git repository to work in.

    python3 harness/snapshot.py tasks/public/01-pricing-tax scratch/01

The result is byte-for-byte the snapshot the service receives in
repo_archive_b64 (one commit, branch main). Edit it, then `git diff` gives a
diff that grade.py can check.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import materialize_repo  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: snapshot.py <task_dir> <dest_dir>")
    task_dir, dest = Path(sys.argv[1]), Path(sys.argv[2])
    if dest.exists():
        sys.exit(f"{dest} already exists")
    materialize_repo(task_dir / "repo", dest)
    print(f"snapshot ready at {dest}")
