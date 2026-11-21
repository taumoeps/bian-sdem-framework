#!/bin/sh
# Rebuild this example's data from the narrative design, step by step — and its SDEM workspace, if a folder for one is given.
# Run from the repository root:   sh examples/payment-initiation-v3/scripts/build.sh <output folder> [<workspace folder> <your name>]
# No sdem transform and no sdem aid: steps 1, 3 and 4 are what an AI read in, and decided about, narrative/design.md.
set -e
S="$(dirname "$0")"; OUT="${1:?give an output folder}"; PY="${PYTHON:-python3}"
mkdir -p "$OUT/drafts" "$OUT/data"
"$PY" "$S/1_stated_in_the_document.py" "$OUT/drafts"              # what the document states: records, and the links it states outright
"$PY" "$S/2_as_a_package.py" "$OUT/drafts" "$OUT/data"            # the same, as the package sdem intake takes
"$PY" "$S/3_implied_by_the_document.py" "$OUT/data"               # + the links that follow from its sentences  -> added-by-reading.json
"$PY" "$S/4_decided_by_the_ai.py" "$OUT/data"                     # + what it does not say, decided              -> decided-by-ai.json
"$PY" -m sdem intake "$OUT/data" --check | head -1
if [ -n "$2" ]; then "$PY" -m sdem intake "$OUT/data" --workspace "$2" --person "${3:?give your name}" --accept --no-inference | head -1; fi
