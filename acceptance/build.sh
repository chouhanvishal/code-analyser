#!/usr/bin/env bash
# Build the acceptance image. Run from the repository root.
set -euo pipefail
cd "$(dirname "$0")"
docker build -t acceptance:latest .
echo "built acceptance:latest"
