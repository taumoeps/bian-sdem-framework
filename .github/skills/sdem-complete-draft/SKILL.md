---
name: sdem-complete-draft
description: The one fixed order for taking a design to a complete first draft in SDEM — load it, say what was refused or not stated, add the BIAN domains, ask the standards and patterns first, only then let `sdem aid` infer and complete the draft, list every proposed link, show the draft, and hand back weakest first. Use after any design is loaded — from a document, from layer files an outside author wrote, from `sdem transform`, or a new design — and whenever asked to infer, complete, fill gaps in, or draft a design, or to say how complete it is.
---

# A complete first draft — the order, every time

An architect judges a design by seeing it whole, then refines it. So SDEM completes the first draft — **but in one order, and by its written rules only**. The order exists because each step is evidence for the next: a pattern asked after inference finds nothing to say; inference run before the patterns guesses what a pattern would have told it.

**`sdem status --workspace <ws>` prints these steps in this order under "Next" — follow it; do not reorder, and do not skip a step because it "looks done".**

| # | Step | Command | Who |
|---|---|---|---|
| 1 | **Load** the design | a document: skill `sdem-design-from-document` · layer files an outside author wrote (given `sdem types authoring -o <file>` — the authoring guide — beforehand): `sdem change diff <file> --workspace <ws> -o <draft>` then `sdem change propose … --dry-run`, then without · past designs: `sdem transform run` then `sdem load` (a person) · a new design: skill `sdem-new-design` | you (load: a person) |
| 2 | **Say what did not come in** | what a dry run refused (leave it out — never replace it with something SDEM accepts), what the transform could not read (`extraction-report.md`), what the source itself lists as *not stated* | you |
| 3 | **The BIAN domains the design names**, by BIAN's exact names | `sdem bian search <words>` · `sdem bian add "<Domain>" --workspace <ws> --person <architect>` | you prepare; a person decides |
| 4 | **Standards and patterns first** | `sdem status --workspace <ws>` names each pattern SDEM ships that fits · `sdem profile include sdem:<file> --workspace <ws> --person <architect>` | a person decides |
| 5 | **Then infer, and complete the draft** | `sdem aid --workspace <ws> --person <architect> --complete-draft --dry-run`, then without `--dry-run` when the architect asks for it | you, on the architect's request |
| 6 | **Every proposed link in one list** | `sdem link --workspace <ws> --out <ws>/links` | you |
| 7 | **Show the draft** | `sdem status --workspace <ws>` (the *Completeness*, *Draft* and *Pattern* lines) · `sdem pattern draw --id <PAT> --workspace <ws> --anchor <record> -o pattern.html` · the workbench or the 3D view | you |
| 8 | **Hand back, weakest first** | `sdem handback --workspace <ws> --json` | you |
| 9 | **Confirm, reject, approve** | `sdem aid confirm|reject …` · `sdem approve|reject …` | **a person only** |

## What each step must leave behind

- **After 2**, a list the architect can read: refused (with SDEM's message), not read, not stated. Nothing in it is "fixed" by you.
- **After 4**, you can say which standards and patterns apply. `sdem aid` consults every pattern SDEM ships that fits the design even when the profile does not include it, and names each it consulted (`draft.patterns_consulted`) — **read that list back to the architect**. If a fitting pattern is not in it, stop and say so.
- **After 5**, read `draft` in the run record: `domains_added`, `parts_added`, `links` (each with the rule that inferred it and the rule or part that asked for it), `parts_to_name`, `left_open`.
- **After 7**, give the two figures and never merge them: *Completeness* counts only what is stated or confirmed; *Draft* counts what is inferred or proposed as well. A proposed link is drawn dashed and is not a connection until a person approves it.

## The hand-back (step 8) — in this order

1. **Placed by default, no evidence** (`AID-D08`, `AID-D09`; `default: true`) — each one, and that nothing in the design supports it.
2. **Inferred from a name or by elimination** (`AID-D01`, `AID-D02`; `evidence_class` `name_token`) — and any the source itself listed as *not stated*: recommend rejecting those.
3. **What a pattern brought in** (`AID-D05` domains, `AID-D06` parts) and **which record is a part** (`parts_to_name`) — the suggestion, and that a person writes it.
4. **Links between layers to approve**, grouped by type, with the evidence each needs.
5. **Gaps still open**, with SDEM's reason.
6. The exact command for each decision — for the architect to run.

## Never

- **Never write a link from your own judgement** — not to tidy a picture, not because it is obvious. A link comes from the design's own source, from one of SDEM's rules (marked inferred), or from a named person. If you believe a link is right, say so in words in the hand-back.
- **Never run step 5 before step 4**, and never report a draft without saying which patterns were consulted.
- **Never fill a gap quietly.** A gap with no evidence is left open and listed, or — with `--complete-draft` — placed by default and marked so.
- **Never run step 9**, even when given a name (CTL-21). You may preview a decision with `--dry-run` and hand the exact command over.
