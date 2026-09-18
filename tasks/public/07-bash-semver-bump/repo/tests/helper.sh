#!/usr/bin/env bash
# Minimal test helper. Usage: expect "<description>" "<expected>" <command...>
set -u
failures=0
expect() {
  local desc="$1" want="$2"; shift 2
  local got
  got="$("$@" 2>/dev/null)"
  if [[ "$got" == "$want" ]]; then echo "ok   $desc"; else echo "FAIL $desc: want '$want' got '$got'"; failures=$((failures+1)); fi
}
expect_exit() {
  local desc="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1; local code=$?
  if [[ "$code" == "$want" ]]; then echo "ok   $desc"; else echo "FAIL $desc: want exit $want got $code"; failures=$((failures+1)); fi
}
finish() { if (( failures > 0 )); then echo "$failures failure(s)"; exit 1; fi; echo "all passed"; }
