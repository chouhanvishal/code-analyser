# Harness

Three commands, all standard-library Python 3.12.

## Get a task to work in

    python3 harness/snapshot.py tasks/public/01-pricing-tax scratch/01

Copies the task's `repo/` and turns it into a one-commit git repository, byte
for byte the snapshot a service receives in `repo_archive_b64`. Edit it, run
`bash run_tests.sh`, and `git diff` gives a diff for grading.

## Grade one diff

    python3 harness/grade.py --task tasks/public/01-pricing-tax --diff my.diff

Builds a fresh snapshot, applies the static rules, `git apply`, then runs the
task's `acceptance_command` inside the `acceptance:latest` image with networking disabled
(build it first: `docker build -t acceptance:latest acceptance`). Add `--local`
to run on the host during development; grading never uses `--local`.

## Drive a service

    python3 harness/run_client.py --url http://localhost:8000 tasks/public/* --concurrency 3

Checks `/health`, packs each task's snapshot into `repo_archive_b64`, sends it
to `/solve` with its deadline, times the response, grades the diff, and prints
acceptance, pre-execution rejection, missed-deadline, and null-diff rates.
Responses and diffs are saved under `results/`.

## Task layout

    tasks/public/<id>/task.json      request_id, task, deadline_seconds, language, toolchain,
                                     test_command (the repo's own tests), acceptance_command (used by grade.py)
    tasks/public/<id>/repo/          the repository files, plain text
    tasks/public/<id>/acceptance/    the tests grading runs (hidden for private tasks)

The snapshot is always the `repo/` contents as a single commit on `main`, made
with a fixed author and date, so every snapshot of a task is identical. The
acceptance suite is copied into the patched snapshot as `acceptance_tests/`
and `acceptance_command` is run there with `bash -c`. Both commands are
language-specific (`python3 -m unittest`, `node --test`, `go test`,
`cargo test --offline`, `javac` + `java`, `make`), which is why a service
should read them from `task.json` instead of hardcoding one runner.
