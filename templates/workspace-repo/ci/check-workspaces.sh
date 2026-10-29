#!/usr/bin/env bash
# Workspace CI — every workspace in workspaces/ follows the metamodel, builds, and keeps its approved links unchanged.
# Usage: bash ci/check-workspaces.sh [BASE]
#   BASE  the git revision to compare approved links against (a pull request's base branch). Omitted: origin/main, else
#         main — so a local run checks everything CI checks; if neither exists, that one check is skipped and the run says so.
# Exit: 0 all workspaces pass; 1 a workspace fails; 2 SDEM is not installed.
set -uo pipefail
base="${1:-}"
if [ -z "$base" ]; then
  for b in origin/main main; do
    if git rev-parse --verify --quiet "$b" > /dev/null 2>&1; then base="$b"; break; fi
  done
  if [ -n "$base" ]; then echo "comparing approved links with $base (give another base as the first argument)"
  else echo "NOTE: no main branch to compare with — the 'approved links unchanged' check is skipped"; fi
fi
fail=0; n=0

sdem --version || { echo "ERROR: sdem is not installed — run: pip install -r requirements.txt"; exit 2; }

for dir in workspaces/*/; do
  e="${dir%/}"
  [ -f "$e/mappings.json" ] || continue
  n=$((n + 1))
  echo "::group::$e"

  echo "== $e: follows the metamodel (sdem check)"
  sdem check --workspace "$e" || { echo "FAIL $e: does not pass sdem check"; fail=1; }

  if [ -n "$base" ]; then
    echo "== $e: approved links unchanged since $base (sdem diff)"
    if git cat-file -e "$base:$e/mappings.json" 2>/dev/null; then
      sdem diff --git "$base" "$e/mappings.json" || { echo "FAIL $e: an approved link was edited or removed — supersede it with a new record instead"; fail=1; }
    else
      echo "new workspace on this branch — nothing to compare"
    fi
  fi

  echo "== $e: builds (sdem build)"
  out="$(mktemp -d)"
  sdem build --workspace "$e" --out "$out" > /dev/null || { echo "FAIL $e: does not build"; fail=1; }
  rm -rf "$out"

  if [ -f "$e/designs/design-records.json" ]; then
    echo "== $e: open gaps (for information)"
    sdem designs --workspace "$e" --gaps --status open || true
  fi
  echo "::endgroup::"
done

if [ "$n" -eq 0 ]; then echo "no workspaces yet — each workspace is a folder in workspaces/ with a mappings.json"; exit 0; fi
if [ "$fail" -eq 0 ]; then echo "OK: $n workspace(s) pass"; else echo "FAILED: see FAIL lines above"; fi
exit "$fail"
