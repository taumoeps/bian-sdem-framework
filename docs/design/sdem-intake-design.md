# `sdem intake` — a design authored as SDEM data comes in through one command (IN-01…IN-10)

> **Status: built (2026-11-17) — the owner: "this is fundamentally brittle, we need to fix this"; options A and B of four, then "go".** `sdem/intake.py`, `tests/test_intake.py`; the author's kit: `sdem types authoring --kit` (AU-07). **No metamodel file changes.**

## What was brittle

Getting a design an outside author wrote (an AI assistant, with the [authoring guide](../reference/authoring-guide.md)) into SDEM took three rounds and about eight commands run from memory:

- **Errors surfaced late.** The author wrote everything blind; SDEM checked only at load. Seventeen items refused on the first attempt.
- **The package was a convention, not a format.** Nothing checked the eight files as a set; the suggested links and the *not stated* list were read by the operator, not by SDEM.
- **Loading was manual and ordered by memory** — diff and propose a layer at a time, add BIAN, set the operation, include the patterns, infer, list the links. The order was skipped twice.

## Rules

| Id | Rule |
|---|---|
| IN-01 | **`sdem intake <folder> --check`** checks the whole package — the three layer files, `BIAN-DOMAINS.json`, `CROSS-LAYER-SUGGESTIONS.json`, `NOT-STATED.json` — **with no workspace and nothing written**. Exit 0 when SDEM would take it, 1 with what is wrong, 2 when the folder is not there. `--json`. |
| IN-02 | **It is SDEM's own check, not a copy of it**: the layers are proposed as change sets in a workspace that is thrown away, so what it refuses is exactly what a load would refuse. Because SDEM is the standard library only, **the author runs it** — from the kit's zip, in any Python — before handing over. |
| IN-03 | **Everything wrong is said at once**, each with its file and the reason, in the author's terms: a value that is not allowed (with the allowed ones), a link the metamodel does not allow, a link between layers written inside a layer file, an A2 file, a name that is not a BIAN service domain (with the nearest), an operation the domain does not have (with those it has), a suggestion whose link type does not exist or does not join those two types. |
| IN-04 | *(replaced by IN-11)* **What is not connected and not declared is said, and does not fail the check**: each record SDEM's completeness standard finds unconnected, unless `NOT-STATED.json` names it or — for a link between layers — the package suggests the link. A *not stated* entry that names no record says the design lacks the thing altogether; that is a statement, not an error. |
| IN-05 | **`sdem intake <folder> --workspace <ws> --person <you>`** takes the design in. A person's command (CTL-21). A package with anything refused changes nothing. It starts a design: a workspace that already holds records is refused. `--dry-run` says what it would do. |
| IN-06 | **The one order** (the skill `sdem-complete-draft`), done by the tool: check → the workspace (started if new) → the layers, each under its layer's agent → the BIAN service domains the package names, and the BIAN operations on the processes it says use them → **every pattern SDEM ships that fits, included** → `sdem aid --complete-draft` → `sdem link` → the report. If a step fails it stops there and says which. |
| IN-07 | **It decides nothing that is a decision about the design's truth.** It approves, confirms and rejects nothing. What it does under the person's name — adding the BIAN domains the design names, including the patterns that fit — is recorded as theirs, as the commands it runs record it. |
| IN-08 | **The author's suggestions become proposals.** Those SDEM's own rules also propose are SDEM's; the rest are written beside them (`aid/AUTHOR-proposals.json`), said to be the author's, to approve with evidence like any proposal. |
| IN-09 | **One report** (`intake/report.md`, and `report.json`): what came in; what the author said the design does not state, and what is unconnected and undeclared; the draft — *Completeness* and *Draft*, never merged, and each pattern; then **what is the person's to decide, weakest first**: placed by default, inferred from a name (flagged where the author said *not stated*), brought in by a pattern, links to approve, gaps left open — and the commands. The package is kept as it came (`intake/package/`). |
| IN-10 | Agents: `--check` and `--dry-run` are theirs to run; taking a design in is the person's. |

## Complete, and accepted as authored (the owner, 2026-11-17)

> *"Stop including me in the review. The AI agent should be able to output the correct response with no gaps; it should not require me if the instructions and authoring are black and white."*

The first build of intake still ended in a list for the owner: gaps the author had been told to leave ("where the design does not say, leave it out"), and every link between layers held for approval. Both were by design, and both made the owner the reviewer of an AI's output. Changed:

| Id | Rule |
|---|---|
| IN-11 | **Complete is the bar, and the check tests it.** `sdem intake --check` evaluates the package as it would stand once taken in — its BIAN domains and operations, every pattern SDEM ships that fits, and the links between layers it gives counted as links — and **fails on every record not connected and every part of a fitting pattern not there**: `NOT COMPLETE — …`, each with why it is needed and what to write. Listing something as *not stated* does not excuse it. The author loops on the check until it prints `OK … COMPLETE`. `--allow-gaps` takes or passes a design that is not complete, each gap listed (replaces IN-04). |
| IN-12 | **`--accept`: the design is taken as authored.** Its links between layers are approved under the name of the person who runs the command, each on the evidence of the design section it cites — none is left for review. Off unless given: without it the links are proposals, as before. It is that person's decision, recorded as theirs (CTL-21 holds: an agent's name is refused). |

With both, a complete package comes in with one command and leaves nothing to confirm, approve or decide. What SDEM vouches for is that the design is valid and complete; the design choices are its author's — which is why the [authoring guide](../reference/authoring-guide.md) now makes the author the designer and has every choice the document did not make listed in `DECISIONS.json` (AU-08), kept with the workspace and shown in the report.

## Measured

The same package (Kauri Comet Bank, third authoring): by hand, eight kinds of command and an hour, with one step forgotten; `sdem intake`, one command, 22 seconds, the same workspace and a report.

## Not in this change

A machine-readable schema of the package for tools that can be held to one (option C); a spreadsheet template read by `sdem transform` (option D).
