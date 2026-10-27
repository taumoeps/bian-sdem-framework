# SDEM Dashboard — Specification

> **Status: phase 1 approved and built 2026-10-28 (with the main dashboard, `sdem home`); phase 2 proposed.** Requirements for the design in [`sdem-dashboard-design.md`](sdem-dashboard-design.md). Each requirement has an ID (DB-*), a status and how it is accepted.

## 1. Generation

| ID | Requirement | Status |
|---|---|---|
| DB-G01 | `sdem dashboard --estate DIR [--proposals FILE] [--projection DIR --catalogue FILE] [--graph DIR] -o FILE.html` writes one self-contained HTML file: data, script and style inline; no network access; opens offline in a browser or VS Code's Simple Browser. | built |
| DB-G02 | All results are computed by SDEM's Python functions (check, engine, trace, impact, matrix, AID gaps, controls) at generation; the page only displays them. | built |
| DB-G03 | Without `--proposals`, the rules engine runs on the estate (approved links excluded) so the Review tab shows what it would propose now. | built |
| DB-G04 | The page shows when it was generated, from which estate, and warns when a given graph store is older than the data. | built |
| DB-G05 | Read-only: the page cannot change any file; each action is shown as the exact `sdem` command, with a copy button. | built |

## 2. Content

| ID | Tab | Requirement | Status |
|---|---|---|---|
| DB-C01 | Overview | per layer: records, errors and advice (each message in full); the registry's links; the coordination check; coverage per layer (records with at least one approved cross-layer link of an expected type); what needs attention (proposals, open work, direct edits, errors) | built |
| DB-C02 | Review | proposals weakest first: link with record names, rule, confidence, reasoning, the evidence kinds approval needs, the `sdem approve` command | built |
| DB-C03 | Trace & impact | choose a record (search by id or name): its trace down and up, with link ids; its impact for each change kind (modify, rehost, replace, retire) with classification, path and links to supersede; print | built |
| DB-C04 | Matrices | capability → domain, domain → application, application → technology, and the end-to-end chain capability → domain → application → technology, from approved links | built |
| DB-C05 | Changes & work | change events (with impact summary), change sets, work items with history; direct edits waiting to be adopted | built |
| DB-C06 | AID plans | with `--projection`: what was projected per layer (step, rule, confidence, reasoning), and the gap results against the real design | built |
| DB-C07 | Controls | every control with status, where it runs, and its last tested result | built |
| DB-C08 | Accessibility | readable in light and dark mode; keyboard-navigable tabs; works at narrow widths; prints cleanly | built |

## 2a. The main dashboard — `sdem home`

| ID | Requirement | Status |
|---|---|---|
| DB-H01 | `sdem home [-o DIR] [--root DIR …] [--estate DIR …]` writes `DIR/index.html` and one project dashboard per estate in `DIR/projects/`, each linking back home; offline, read-only. Default: the estates in `examples/`. | built |
| DB-H02 | Home: SDEM health at a glance, the metamodel in numbers, every project with what needs attention. | built |
| DB-H03 | The metamodel exactly as the rulebook files hold it: entity types (definition, source standard, evidence status, attributes own and inherited), links inside each architecture, link types between architectures (with evidence to approve), the engine's rules (step, decision, confidence, published source); filterable. | built |
| DB-H04 | A metamodel picture: entity types in four bands, the link types between architectures as arrows; a clicked type shows its details. | built |
| DB-H05 | Health computed when the page is generated: every generator's `--check`, the rules engine's acceptance cases (precision and recall against the floor), controls, known gaps, the gap register. | built |
| DB-H06 | Configuration: where each setting lives, confidence bands, link statuses and allowed changes, impact rules, the agents. | built |

## 3. New CLI outputs

| ID | Requirement | Status |
|---|---|---|
| DB-K01 | `sdem matrix --estate DIR` (or files, or `--graph DIR`): the matrices of DB-C04 as text; `--md FILE` writes Markdown; `--json` | built |
| DB-K02 | `sdem impact <id> --change <kind> … --report FILE.md`: a printable impact report — the change and its reason, every affected record (layer, id, name, classification, path of link ids), links to supersede, and "Classification is structural; an architect confirms before any design changes." | built |

## 4. Phase 2 — proposed (DB-D05)

| ID | Requirement | Status |
|---|---|---|
| DB-S01 | `sdem serve --estate DIR` — a local web app on `localhost` only (Python standard library), live data | proposed |
| DB-S02 | Buttons for check, link, build, approve (person + evidence), claim work, revert — each calling the same functions as the CLI, so CTL-16…22 apply | proposed |
| DB-S03 | A record editor with forms per entity type, validated against the schemas and the rulebook as you type | proposed |
| DB-S04 | Approval in the GUI still needs the person's name and evidence (CTL-21) and still becomes final in a reviewed pull request | proposed |

## 5. Acceptance

| ID | Test | Automated? |
|---|---|---|
| AT-DB-01 | The dashboard generates for every example estate; the embedded data parses; the file has no `http(s)://` references to load | yes — `tests/test_dashboard.py` |
| AT-DB-02 | The overview's counts, errors and coverage equal `sdem check` and `sdem query --unmapped` for the same estate | yes |
| AT-DB-03 | The trace and impact shown for a record equal `sdem trace` and `sdem impact` | yes |
| AT-DB-04 | The matrix for payment-initiation lists Initiate Payment → Payment Initiation → Payments Hub → the production cluster | yes |
| AT-DB-05 | The Review tab lists the same proposals as `sdem review`, weakest first, each with an `sdem approve` command | yes |
| AT-DB-07 | `sdem home` links every estate's dashboard; its metamodel figures equal the rulebook files; its health shows every generator current and 8 of 8 acceptance cases | yes — `tests/test_home.py` |
| AT-DB-06 | An architect new to SDEM finds the estate's open issues and a record's impact without using the terminal | walkthrough |
