#!/usr/bin/env bash
# Estate CI — every estate in estates/ follows the rulebook, builds, and keeps its approved links unchanged.
# Usage: bash ci/check-estates.sh [BASE]
#   BASE  the git revision to compare approved links against (a pull request's base branch); omit to skip that check.
# Exit: 0 all estates pass; 1 an estate fails; 2 SDEM is not installed.
set -uo pipefail
base="${1:-}"
fail=0; n=0

sdem --version || { echo "ERROR: sdem is not installed — run: pip install -r requirements.txt"; exit 2; }

for dir in estates/*/; do
  e="${dir%/}"
  [ -f "$e/mappings.json" ] || continue
  n=$((n + 1))
  echo "::group::$e"

  echo "== $e: follows the rulebook (sdem check)"
  sdem check --estate "$e" || { echo "FAIL $e: does not pass sdem check"; fail=1; }

  if [ -n "$base" ]; then
    echo "== $e: approved links unchanged since $base (sdem diff)"
    if git cat-file -e "$base:$e/mappings.json" 2>/dev/null; then
      sdem diff --git "$base" "$e/mappings.json" || { echo "FAIL $e: an approved link was edited or removed — supersede it with a new record instead"; fail=1; }
    else
      echo "new estate on this branch — nothing to compare"
    fi
  fi

  echo "== $e: builds (sdem build)"
  out="$(mktemp -d)"
  sdem build --estate "$e" --out "$out" > /dev/null || { echo "FAIL $e: does not build"; fail=1; }
  rm -rf "$out"

  if [ -f "$e/designs/design-records.json" ]; then
    echo "== $e: open gaps (for information)"
    sdem designs --estate "$e" --gaps --status open || true
  fi
  echo "::endgroup::"
done

if [ "$n" -eq 0 ]; then echo "no estates yet — each estate is a folder in estates/ with a mappings.json"; exit 0; fi
if [ "$fail" -eq 0 ]; then echo "OK: $n estate(s) pass"; else echo "FAILED: see FAIL lines above"; fi
exit "$fail"
