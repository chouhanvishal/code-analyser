#!/usr/bin/env bash
set -euo pipefail
version="$1"
part="$2"
IFS=. read -r major minor patch <<< "$version"
case "$part" in
  major) major=$((major + 1)) ;;
  minor) minor=$((minor + 1)) ;;
  patch) patch=$((patch + 1)) ;;
  *) echo "unknown part: $part" >&2; exit 2 ;;
esac
echo "$major.$minor.$patch"
