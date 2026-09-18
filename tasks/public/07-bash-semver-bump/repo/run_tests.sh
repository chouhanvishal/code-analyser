# Runs the repository's own test suite:  bash run_tests.sh
set -euo pipefail
cd "$(dirname "$0")"
bash tests/run.sh
