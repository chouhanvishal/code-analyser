#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source tests/helper.sh
expect "patch bump" "1.2.4" bash bin/bump_version.sh 1.2.3 patch
expect "minor bump resets patch" "1.3.0" bash bin/bump_version.sh 1.2.3 minor
finish
