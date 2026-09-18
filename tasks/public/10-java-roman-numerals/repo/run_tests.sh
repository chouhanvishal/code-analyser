# Runs the repository's own test suite:  bash run_tests.sh
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out && javac -d out $(find src -name '*.java') && java -cp out roman.RomanNumeralsTest
