#!/usr/bin/env python3
"""
run_client.py: drive a candidate service through a set of tasks and report the numbers that matter.

    python3 harness/run_client.py --url http://localhost:8000 tasks/public/* [--local] [--concurrency 3] [--out results/]

For each task it POSTs the request contract to /solve, measures wall-clock time
against deadline_seconds, then grades the returned diff with grade.py.

Reports, per task and in aggregate:
  acceptance rate, pre-execution rejection rate (static or apply stage),
  missed-deadline rate, null-diff rate, and mean reported cost.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import grade, pack_repo  # noqa: E402


def health(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=5) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def solve_one(url: str, task_dir: Path, out_dir: Path, local: bool, image: str) -> dict:
    meta = json.loads((task_dir / "task.json").read_text())
    payload = {
        "request_id": meta["request_id"],
        "repo_archive_b64": base64.b64encode(pack_repo(task_dir)).decode(),
        "task": meta["task"],
        "deadline_seconds": meta["deadline_seconds"],
    }
    req = urllib.request.Request(f"{url}/solve", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    row = {"task": task_dir.name, "deadline_s": meta["deadline_seconds"]}
    try:
        with urllib.request.urlopen(req, timeout=meta["deadline_seconds"] + 30) as r:
            body = json.loads(r.read())
    except Exception as exc:
        row.update(elapsed_s=round(time.monotonic() - started, 1), outcome="no_response",
                   reason=f"{type(exc).__name__}: {exc}")
        return row
    elapsed = time.monotonic() - started
    row["elapsed_s"] = round(elapsed, 1)
    row["usage"] = body.get("usage")
    record = body.get("record") or []
    row["record_entries"] = len(record)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{task_dir.name}.response.json").write_text(json.dumps(body, indent=2))

    if elapsed > meta["deadline_seconds"]:
        row.update(outcome="missed_deadline")
        return row
    if not body.get("diff"):
        row.update(outcome="null_diff")
        return row
    diff_path = out_dir / f"{task_dir.name}.diff"
    diff_path.write_text(body["diff"])
    verdict = grade(task_dir, diff_path, local, image)
    row.update(outcome=verdict["verdict"], stage=verdict["stage"], reason=verdict["reason"])
    return row


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    count = lambda pred: sum(1 for r in rows if pred(r))
    costs = [r["usage"]["estimated_cost_usd"] for r in rows
             if isinstance(r.get("usage"), dict) and isinstance(r["usage"].get("estimated_cost_usd"), (int, float))]
    return {
        "tasks": n,
        "acceptance_rate": round(count(lambda r: r["outcome"] == "accept") / n, 3),
        "pre_execution_rejection_rate": round(count(lambda r: r.get("stage") in ("static", "apply")) / n, 3),
        "missed_deadline_rate": round(count(lambda r: r["outcome"] in ("missed_deadline", "no_response")) / n, 3),
        "null_diff_rate": round(count(lambda r: r["outcome"] == "null_diff") / n, 3),
        "mean_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tasks", nargs="+", type=Path)
    p.add_argument("--url", required=True)
    p.add_argument("--local", action="store_true", help="grade on the host instead of the acceptance image")
    p.add_argument("--image", default="acceptance:latest")
    p.add_argument("--concurrency", type=int, default=1, help="overlapping requests to send")
    p.add_argument("--out", type=Path, default=Path("results"))
    a = p.parse_args()

    if not health(a.url):
        print(json.dumps({"error": f"{a.url}/health did not return 200"}))
        return 2

    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        rows = list(pool.map(lambda t: solve_one(a.url, t, a.out, a.local, a.image), a.tasks))

    report = {"summary": summarize(rows), "tasks": rows}
    (a.out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
