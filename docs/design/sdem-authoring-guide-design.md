# The authoring guide — a full design as SDEM data, written by an outside author (AU-01…AU-06)

> **Status: built (2026-11-17), at the owner's request.** `sdem/authorguide.py`, `tests/test_authoring_guide.py`; the guide itself is [`docs/reference/authoring-guide.md`](../reference/authoring-guide.md) (generated). **No metamodel file changes.**

## Why

A design is written as a narrative; SDEM holds data. Something turns one into the other. When that something is an AI assistant that does not run SDEM (ChatGPT, asked to "write this design as SDEM files"), it guesses SDEM's vocabulary. Measured on one design (Kauri Comet Bank, 2026-11-17):

| | Written without SDEM's vocabulary | Written with it |
|---|---|---|
| Items SDEM refused at load | 17 | 0 |
| Records connected on arrival | 30 of 79 (38%) | 64 of 93 (69%) |
| Requirements nothing met | 20 | 0 |
| A BIAN file with invented service domains | yes | no |
| Gaps that were real (the design never says) | hidden among the rest | 4 — each one also in the author's own *not stated* list |

The first attempt knew the answers and wrote them in forms SDEM does not accept (a requirement *associated* with a process, not realised by it; a database as a node). The second was given one generated file and the conversion added no gaps of its own.

## Rules

| Id | Rule |
|---|---|
| AU-01 | **One file to hand over, from one command**: `sdem types authoring [-o FILE]` writes the guide for the installed version. It stands alone — the author needs nothing else but the design. |
| AU-02 | **It says how, not only what**: the eight files to hand over (three layer files, the BIAN domains named, the links between layers *suggested*, what the design does *not state*, the author's own checklist, a read-me); the method, layer by layer and in order; ten rules; the hand-over checks. |
| AU-03 | **The vocabulary is generated from the metamodel**: every kind of record an author may write in A1, A3 and A4 with its attributes, which are required, and the allowed values; every link inside a layer, in both directions; every link type between layers with the types it joins and the evidence a person gives to approve it. A2 is not written: BIAN's records come from BIAN (CTL-24). |
| AU-04 | **What SDEM will check is generated from what SDEM ships**: the completeness standard's rules and each shipped pattern's parts — so an author knows what "connected" means before writing, and the guide cannot drift from the check. |
| AU-05 | **It asks for honesty in a form SDEM can use**: a value the design does not give is left out and listed in `NOT-STATED.json`; nothing is invented to complete — SDEM completes the draft by its own rules, marked inferred (`sdem aid --complete-draft`), and an invented fact in the author's files cannot be told from a stated one. |
| AU-07 | **The kit**: `sdem types authoring --kit <folder>` writes the guide and SDEM itself as a zip — its source and data, nothing else, since SDEM is the standard library only. The guide's last section tells the author to run `python -m sdem intake <folder> --check` from it before handing over ([intake](sdem-intake-design.md) IN-02), so the files arrive already passing SDEM's own check. |
| AU-08 | **The author is the designer, and hands over a complete design** (the owner, 2026-11-17: nobody reviews the files to fill them in). Where the design document is silent on something a complete design needs, the author decides it, writes it, and lists it in `DECISIONS.json` with its reason; `NOT-STATED.json` is for optional attribute values only and excuses no missing record or link. A decision is a choice a designer could defend, never a made-up fact about the world. The test is the check: done when it prints `OK … COMPLETE`. *(Replaces AU-05's "nothing is invented to complete".)* |
| AU-06 | The guide is a generated document: `docs/reference/authoring-guide.md` is kept current by `sdem model regenerate` and `sdem model check` fails when it is stale. |

## After the author hands the files over

One command: `sdem intake <folder> --workspace <ws> --person <you>` ([design](sdem-intake-design.md)) — it checks, loads, adds the BIAN domains the author named, includes the patterns that fit, completes the first draft and writes one report, in the order of the skill `sdem-complete-draft`.
