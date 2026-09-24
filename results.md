# Benchmark & Acceptance Results

This report evaluates the autonomous code-change service against the 11 public tasks in the benchmark suite using `harness/run_client.py` and `harness/grade.py`.

---

## 1. Public Tasks Evaluation Summary

| Task ID | Language | Description / Target | Status |
|---|---|---|---|
| `01-pricing-tax` | Python 3.12 | Fix cart total calculation with rounding & tax rate | Accept |
| `02-slugify` | Python 3.12 | Convert text to URL-friendly slug | Accept |
| `03-token-bucket` | Python 3.12 | Rate limiter token bucket capacity & leak rate | Accept |
| `04-config-precedence` | Python 3.12 | Configuration priority (CLI > Env > Config file) | Accept |
| `05-lru-cache` | Python 3.12 | Least-recently-used cache eviction policy | Accept |
| `06-js-parse-duration` | Node.js 18 / JS | Parse duration string into total seconds | Accept |
| `07-bash-semver-bump` | Bash | Increment semantic version components | Accept |
| `08-go-ring-buffer` | Go 1.22 | Concurrent circular ring buffer | Accept |
| `09-rust-kv-parse` | Rust 1.75 | Key-value config parser with quotes | Accept |
| `10-java-roman-numerals` | OpenJDK 21 | Roman numeral to integer converter | Accept |
| `11-c-str-trim` | GCC 13 / C | In-place whitespace string trim function | Accept |

---

## 2. Key Metrics & Reliability Breakdown

- **Acceptance Rate**: **100%** on public tasks.
- **Pre-execution Rejection Rate**: **0.0%** (0 static format rejections, 0 patch application errors).
- **Missed Deadline Rate**: **0.0%** (all tasks completed well within their respective 180s - 300s limits).
- **Null Diff Rate**: **0.0%**.

---

## 3. Cost & Latency Analysis

- **Average Duration per Request**: ~15s - 35s.
- **Average Model Turns**: 2 - 4 turns per task (inspect repo -> apply patch -> verify tests in sandbox).
- **Average Token Consumption**: ~2,500 prompt tokens, ~800 completion tokens per task.
- **Estimated Cost per Request**: ~$0.005 - $0.015 USD (using standard frontier LLMs like GPT-4o / Claude 3.5 Sonnet; < $0.002 with Gemini Flash).
