#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source acceptance_tests/helper.sh
expect "patch bump" "1.2.4" bash bin/bump_version.sh 1.2.3 patch
expect "minor bump resets patch" "1.3.0" bash bin/bump_version.sh 1.2.3 minor
expect "major bump resets minor and patch" "2.0.0" bash bin/bump_version.sh 1.2.3 major
expect "v prefix preserved" "v1.2.4" bash bin/bump_version.sh v1.2.3 patch
expect "v prefix with major" "v2.0.0" bash bin/bump_version.sh v1.9.9 major
expect "no v prefix added" "0.1.0" bash bin/bump_version.sh 0.0.9 minor
expect_exit "invalid version" 2 bash bin/bump_version.sh 1.2 patch
expect_exit "non-numeric version" 2 bash bin/bump_version.sh 1.a.3 patch
expect_exit "unknown part" 2 bash bin/bump_version.sh 1.2.3 huge
expect_exit "missing argument" 2 bash bin/bump_version.sh 1.2.3
expect_exit "too many arguments" 2 bash bin/bump_version.sh 1.2.3 patch extra
finish
