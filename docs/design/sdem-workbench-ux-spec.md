# SDEM workbench UX — the HTML upgrade (spec)

> **Status: proposed (2026-11-06), for the owner's approval** — except **UX-D01…UX-D08, built** (`sdem document`). Builds on the [dashboard design](sdem-dashboard-design.md) (one engine, the pages only show) and the external UX proposal reviewed on 2026-11-06. Nothing here changes the metamodel, the CLI's JSON contracts, the rules engine or who decides what.

## 1. Purpose

A solution architect opens the generated pages and, without knowing SDEM's commands, can answer three questions:

1. **What does this solution's design say?** — each layer as a readable document, with where every statement came from.
2. **How is it connected, and what is still open?** — approved and proposed connections, inferred records to confirm, requirements and risks, changes in flight.
3. **What does the framework allow?** — the metamodel: types, attributes, the links allowed inside and between layers, and the evidence each needs.

## 2. Principles (from the dashboard design, kept)

| Id | Requirement |
|---|---|
| UX-P01 | **One engine, the pages only show.** Every fact on a page comes from an `sdem` function or command output; the page's script only filters, selects and navigates. No business rule in the browser. |
| UX-P02 | **Offline and self-contained.** No external scripts, styles, fonts or calls; one folder of generated files that opens from disk. |
| UX-P03 | **Nothing invented.** No record, link, status or text the workspace does not hold; what is missing is shown as a gap. |
| UX-P04 | **Read-only.** No control that changes data. Decisions are shown as the exact command for the person to run (copy button). |
| UX-P05 | **Snapshot honesty.** Every page shows the workspace, the input fingerprint and whether the graph store is current (NV-* rules of the dashboard design). |

## 3. Navigation — five workspace sections

The framework stays in **SDEM Home** (`sdem home`), which already lists the workspaces and holds the metamodel tabs. A workspace's pages have five sections, in one shared shell:

| Id | Section | Shows | Today |
|---|---|---|---|
| UX-N01 | **Overview** | layer health; **everything waiting on a person**: proposals to review, inferred records to confirm, open change events, confirmed requirement breaches, unrecorded edits | dashboard Overview — extend with inferred records and breaches |
| UX-N02 | **Designs** — A1…A4, each **Document · Records · Diagram** | Document: `sdem document` (UX-D*). Records: searchable list; the selected record's fields, links, source and its **exact JSON**. Diagram: the layer's own stored links (UX-N07) | new; Records partly in the graph view's panel |
| UX-N03 | **Connections** | proposals weakest first (rule, reasoning, confidence, evidence needed); approved links; the matrices | dashboard Review + Matrices |
| UX-N04 | **Trace, impact & risk** | pick a record: trace down and up; pick a change kind: classified impact and its coverage; the requirements evaluation (breaches, missing evidence, risk findings) | dashboard Trace & impact — add requirements and risk |
| UX-N05 | **Changes** | change events with their validation phase (documentation-only events marked), work items, unrecorded edits; AID runs and their notes | dashboard Changes & work + AID plans |
| UX-N06 | **Deep links and selection.** A record selected anywhere is kept across sections; the address carries it (`#A3/APP-PAY-HUB/document`), so the browser's back button and a copied link restore it. | new |
| UX-N07 | **Diagrams draw stored links only** — the layer's relationships and approved registry links from the graph store, laid out by `sdem view`'s code; never a link the workspace does not hold. | `sdem view` |
| UX-N08 | Any record, section of a document or diagram node is **at most three interactions** from the Overview. | — |

## 4. The design document — `sdem document` (built)

| Id | Requirement | Test |
|---|---|---|
| UX-D01 | **Deterministic**: the same workspace gives the same document, word for word; no timestamps; the input fingerprint says what it was made from. | `test_it_is_deterministic` |
| UX-D02 | **Every record of the layer, nothing else**, grouped by type in metamodel order, each type introduced by its metamodel definition. | `test_every_record_and_nothing_else` |
| UX-D03 | Each record: description, status and version, its attributes (ids shown with names), its links inside the layer both ways, and its connections to other layers with **their status, link id and evidence**. | `test_sources_and_approved_connections` |
| UX-D04 | **Where each record came from**, in words: a design document section (`source_id: document:<file>#<section>`), past design pages (`confluence:`), the BIAN catalogue, AID's inference with rule, confidence and reasoning — *confirmed by* a person or *not yet confirmed* — or no source recorded. | `test_sources_and_approved_connections` |
| UX-D05 | **Gaps and open items** at the end: inferred records not confirmed, records with no approved connection to another layer, placeholder or empty values (`TBD`, `PLACEHOLDER`), requirements not confirmed. | `test_gaps_are_listed` |
| UX-D06 | The layer's **requirements** — owned by it, or about or allocated to its records — with condition and status. | `test_requirements_of_the_layer` |
| UX-D07 | **Markdown** (for people, and for an agent filling a Word template), **HTML** (self-contained, loads nothing, light and dark) and **JSON**. | `test_html_is_self_contained` |
| UX-D08 | Read-only: it writes only the output file(s) asked for. | — |

## 5. Status vocabulary — SDEM's states only

| Id | Requirement |
|---|---|
| UX-S01 | Badges use only states SDEM records: **records** — inferred (not confirmed) · confirmed · lifecycle (planned, active, deprecated, retired); **connections** — proposed · approved · superseded · needs review; **requirements** — proposed · confirmed · retired; **findings** — breached · missing evidence · not confirmed · potential risk · assumption; **change events** — validation pending · validation complete · architect review required · implementation authorised · documentation only. |
| UX-S02 | No badge is derived by the page (e.g. "approved" because a rule passed). A state the workspace does not hold is not shown. |
| UX-S03 | Colour is never the only signal: every badge has its word. |

## 6. Quality

| Id | Requirement |
|---|---|
| UX-Q01 | Keyboard: every control and diagram node reachable and operable; visible focus; ARIA roles for tabs; names for icon-only controls. |
| UX-Q02 | Light and dark, following the system setting. |
| UX-Q03 | Works at phone width without sideways scrolling of the page (tables may scroll inside their box). |
| UX-Q04 | Tested on the Payments example, an empty workspace, an incomplete one (missing layer, no graph store) and a large synthetic one (about 1,000 records): pages generate, open and stay usable; a size budget per page. |
| UX-Q05 | Semantic snapshot tests: what each section shows for a known workspace, not the exact markup. |
| UX-Q06 | Before and after: the [first-time architect usability test](../sdem-usability-test-plan.md) run on today's pages and on the new ones. |

## 7. Order of work

1. **UX-D (built)** — `sdem document`.
2. **The shared shell** — one header, navigation, badge and fingerprint component used by `home`, `dashboard` and `view` (UX-P*, UX-S*, UX-N06).
3. **Designs section** (UX-N02, UX-N07) — Document from UX-D, Records with exact JSON, Diagram from `sdem view`.
4. **Overview, Connections, Trace/impact/risk, Changes** — reorganise the existing dashboard tabs into the five sections; add inferred records, requirement breaches and documentation-only events.
5. **Quality** (UX-Q*) throughout; the usability test before step 2 and after step 4.

**Deferred:** `sdem serve`, approvals in the browser, chat, a JavaScript framework rewrite.
