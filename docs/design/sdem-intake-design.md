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

## Who fills a gap: SDEM's rules, never an AI, and not the owner (the owner, 2026-11-17)

Two directions from the owner, the same day, which together settle it:

> *"Stop including me in the review … it should not require me if the instructions and authoring are black and white."*
> *"I don't want AI inferring fixes other than AID."*

A first attempt at the former had the author — an AI — decide whatever the design document left open, and list its decisions. That is an AI inferring fixes; it was withdrawn the same day. The settled split:

| Who | Does | Never |
|---|---|---|
| **The author** (an AI assistant, with the guide and SDEM's own check) | translates: writes what the design says, and accounts for every loose end by listing it as *not stated* | decides, guesses or completes anything |
| **SDEM** (`sdem aid`, its written rules) | completes the draft: asks the standards and patterns, infers what the design gives evidence for, places the rest by default — each item marked inferred, with the rule that produced it | presents an inference as a fact |
| **The person who runs intake** | takes the design in, with one command | is asked to review a link the design itself states |

| Id | Rule |
|---|---|
| IN-11 | **Every loose end is accounted for — by the author declaring it, not filling it.** `sdem intake --check` evaluates the package as it would stand once taken in (its BIAN domains and operations, every fitting pattern, its links between layers counted) and fails on each record that is neither connected nor named in `NOT-STATED.json`: `NOT ACCOUNTED FOR — … write the link only if the design says it; otherwise add it to NOT-STATED.json`. What the design does not give — unconnected records that are declared, parts a fitting pattern lacks — is listed **for information**, as what SDEM's rules will go on to complete; the author does nothing about it. `--allow-gaps` passes undeclared ones too. (Replaces IN-04.) |
| IN-12 | **`--accept`: the design's own links are taken as authored.** The links between layers the author wrote from the design are approved under the name of the person who runs the command, each on the evidence of the design section it cites — none is left for review. Off unless given. An agent's name is refused (CTL-21). What SDEM then infers is **not** approved or confirmed by it: it stays marked inferred or proposed. |
| IN-13 | **A first load is not a change to plan.** The change events intake's own loading raises are recorded as the design's first load (`intake/first-load.json`); `sdem status` does not ask for work to be planned from them. Where the design as written is already complete and is accepted, the links SDEM's rules would propose beside the author's are declined under the same decision, and `sdem status` ends *clear*. |

| IN-14 | **`--no-inference`: the design as written and nothing else.** `sdem aid` is not run and SDEM proposes no link: what the package does not give stays open and is listed. For a design whose author has said everything it has to say — the worked example [`examples/payment-initiation-v3`](../../examples/payment-initiation-v3/README.md), translated by an AI reading the narrative, was taken in this way. With `--accept` on a complete design, the links SDEM's rules would still propose are listed only to be declined (IN-13). |

**Measured on one design with an answer key (Payment Initiation v3, 2026-11-18).** The same gaps, filled three ways, scored against the author's own key — requirement links: an AI reading the document, 12 of 15; `sdem aid` from a shared word, 3 of 5; `sdem aid` placed by default (AID-D08), 3 of 19. Structure-based proposals held: deployments 8 of 8, stores 3 of 4. Reading the narrative is the better way to turn it into data; default placement fills a picture with links that are mostly wrong.

**Where that leaves a design that is not complete as written** — the usual case. It is taken in whole; what it states is approved; SDEM's rules complete the draft, and everything they added is marked. `sdem status` reports the two figures apart: *Completeness* (what the design states) and *Draft* (counting what SDEM inferred or proposed). The inferred items are SDEM's, to be confirmed or rejected whenever a person chooses — the design is usable as a draft without that. Nobody, and no AI, has turned an inference into a fact.

## Measured

The same package (Kauri Comet Bank, third authoring): by hand, eight kinds of command and an hour, with one step forgotten; `sdem intake`, one command, 22 seconds, the same workspace and a report.

## Not in this change

A machine-readable schema of the package for tools that can be held to one (option C); a spreadsheet template read by `sdem transform` (option D).
