# Runs the repository's own test suite:  bash run_tests.sh
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
