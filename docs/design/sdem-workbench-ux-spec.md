# SDEM workbench UX — the HTML upgrade (spec)

> **Status: proposed (2026-11-06), for the owner's approval** — except **UX-D01…UX-D08, built** (`sdem document`). Builds on the [dashboard design](sdem-dashboard-design.md) (one engine, the pages only show) and the owner's UX proposal and v2 mockup (2026-11-06); a mockup generated from the Payments example by SDEM's own functions shows every view below with real data. Nothing here changes the metamodel, the CLI's JSON contracts, the rules engine or who decides what.

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

## 3. Navigation — the owner's structure: Solution Workspace and SDEM Framework

One shell with a **Solution Workspace / SDEM Framework** switch in the header (the owner's v2 mockup, `docs/ui/`). SDEM Home stays the entry that lists every workspace.

**Solution Workspace**

| Id | View | Shows | Today |
|---|---|---|---|
| UX-N01 | **Overview** | the four layers (records, checks, share connected to another layer); **everything waiting on a person**: proposals, inferred records to confirm, open change events, requirement breaches, unrecorded edits | dashboard Overview — extend |
| UX-N02 | **Architecture Designs** — A1…A4, each **Document · Catalog · Diagram** | Document: `sdem document` (UX-D*). Catalog: searchable records; the selected record's fields, links, source, status, and links to its graph node, trace, JSON and type definition. Diagram: the layer's own stored links | new |
| UX-N03 | **Data Architecture** — the four datasets and `mappings.json`, each **Table · JSON · Schema** | Table: the records; JSON: a record exactly as stored; Schema: its types from the metamodel | new |
| UX-N04 | **Knowledge Graphs** | the federated graph (four bands, approved connections between layers, links inside layers) or one layer; focus a record to highlight its neighbours; proposals are not drawn | `sdem view` |
| UX-N05 | **Traceability & Impact** | pick a record: trace down and up; pick a change kind: the classified impact, links to supersede; the requirements in scope and the command for their evaluation | dashboard Trace & impact — add requirements |
| UX-N06 | **Reviews & Changes** | proposals weakest first with the evidence each needs; change events with their validation phase (documentation-only marked); work items; unrecorded edits | dashboard Review + Changes & work |
| UX-N07 | **Documents & Evidence** | the four design documents; the source documents records cite (`source_id`); the evidence behind each approved connection | new |

**SDEM Framework**

| Id | View | Shows | Today |
|---|---|---|---|
| UX-N08 | **Overview** | entity types per layer; counts of links allowed inside layers and between them; controls | `sdem home` |
| UX-N09 | **Metamodel Explorer** | every entity type by layer: definition, source, inheritance, attributes (type, required, allowed values, what an id refers to, deprecated), allowed links inside the layer and to other layers with the evidence each needs | `sdem types`, `sdem home` |
| UX-N10 | **Schemas & Configuration** | metamodel version and freeze, BIAN release, the organisation profile (if any), the generated entity schemas | `sdem home` |
| UX-N11 | **Relationship Rules** | inside a layer (the 132 rules, with id and basis) · between layers (the governed relationships: cardinality, authority, evidence a person must give) | `sdem home` |
| UX-N12 | **Engine Health** | `sdem model check`; every control, where it runs, when it was last tested | dashboard Controls |

**Across both**

| Id | Requirement |
|---|---|
| UX-N13 | **Deep links and selection.** The address carries the view and the selected record or type (`#ws/designs/A3/catalog/APP-PAY-HUB`, `#fw/metamodel/A3.ApplicationComponent`); the browser's back button and a copied link restore it. A record links to its type definition, and a type to its records. |
| UX-N14 | **Diagrams and graphs draw stored links only** — never a link the workspace does not hold; the layout comes from `sdem view`'s code. |
| UX-N15 | Any record, document section, graph node or type is **at most three interactions** from either Overview. |

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
3. **Architecture Designs, Data Architecture, Documents & Evidence** (UX-N02, N03, N07) — new, from UX-D and the datasets.
4. **Knowledge Graphs, Traceability & Impact, Reviews & Changes, Overview** (UX-N01, N04–N06) — from `sdem view` and the existing dashboard tabs; add inferred records, requirement breaches and documentation-only events.
5. **The SDEM Framework console** (UX-N08–N12) — from `sdem home`'s tabs, in the same shell.
6. **Quality** (UX-Q*) throughout; the usability test before step 2 and after step 5.

**Deferred:** `sdem serve`, approvals in the browser, chat, a JavaScript framework rewrite.
