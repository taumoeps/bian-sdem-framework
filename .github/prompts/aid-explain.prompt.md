---
name: aid-explain
description: "Explain an AID projection: what was projected, from what, how sure"
agent: agent
argument-hint: "projection folder, e.g. work/prj"
---

Explain the AID projection in ${input:projection:work/prj}.

1. Run `sdem aid check ${input:projection}` and say whether it is valid.
2. Summarise what was projected per layer, from which real records, by which steps (F1–F3, R1–R3, M), at what confidence; use `sdem explain <id> --projection ${input:projection}` for detail.
3. Stress that projected records (`PRJ-`) are a plan, never real data, and say what the architect should check first (the weakest elements).
