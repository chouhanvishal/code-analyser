# Public validation rules

These rules are checked before any code runs. A delivery that breaks any of
them is rejected without executing tests. They are deterministic and fully
visible, so a service that implements them locally should never be rejected
at this stage.

## Format

1. The diff must be a git unified diff as produced by `git diff` (no `--binary`).
   The first line must start with `diff --git `.
2. UTF-8 encoded, LF line endings only.
3. No binary patch content (`GIT binary patch` sections are rejected).
4. No symlink creation (`new file mode 120000` or `new mode 120000`).

## Size

5. At most 200,000 bytes.
6. An empty diff is rejected.

## Paths

7. Every path must be relative to the repository root. Absolute paths and any
   `..` component are rejected.
8. Paths under `.git/`, `acceptance/`, or `acceptance_tests/` are rejected.

## Application

9. The diff must apply cleanly to the exact repository snapshot that was sent:
   `git apply --check <diff>` must exit 0 on a fresh snapshot of the task's
   `repo/` directory (`harness/snapshot.py` produces the identical snapshot).
   Context drift, already-applied hunks, and whitespace mismatches all fail
   this rule.

## Reference implementation

`harness/grade.py` contains the exact checks used for grading
(`static_check()` for rules 1 to 8 and `apply_diff()` for rule 9). Match it.
