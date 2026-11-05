# SDEM Workbench v2 — HTML UX design specification

**Status:** proposed UX design, implementation not yet performed  
**Reference:** `sdem-workbench-v2-mockup.html`  
**Target baseline:** [`taumoeps/bian-sdem-framework` tag `v0.18.0`](https://github.com/taumoeps/bian-sdem-framework/tree/v0.18.0)  
**Scope:** user-friendliness and read-only presentation; **no change** to SDEM's metamodel semantics, CLI, data persistence, rules engine, approval boundaries or agent architecture.

## 1. Problem and intended experience

Existing SDEM HTML output already provides `sdem home` (framework/metamodel and workspace entry), `sdem dashboard` (workspace health and review), and `sdem view` (A1–A4 graph). Each is useful, but users must navigate among separate generated files and understand internal function names. Large four-band graphs are dense. Current technical data is not equivalent to a human-readable architecture design document.

**Goal:** help a solution architect answer three questions without knowing which SDEM command to use:

1. **Framework** — What does the configured enterprise metamodel permit? Entity types, attributes, inheritance, intra- and cross-layer relations, inference mappings, applicable configuration and controls.
2. **Data** — What does *this solution* contain? Four A1–A4 datasets, local relationships, cross-layer approved mapping registry, derived federated graph, provenance, validation and gaps.
3. **Design** — What does each A1–A4 solution design mean? Readable, structured design-document views derived from authoritative SDEM instances, preserving source/evidence and gaps.

## 2. Navigation architecture

Two explicit top-level contexts:

### Solution Workspace — defaults to current workspace

| View | Main experience | Existing source |
| --- | --- | --- |
| Overview | Solution purpose, A1–A4 layer status, tasks requiring attention, quick links | `sdem/dashboard.py`, workspace data |
| Architecture Designs | A1 / A2 / A3 / A4; subviews **Document**, **Catalog**, **Diagram** | workspace datasets, graph reader, proposed document formatter |
| Data Architecture | Dataset selector; **Table**, **JSON**, **Schema**; selected-record details | A1–A4 JSON, mappings registry, actual types/validation |
| Knowledge Graphs | Federated vs individual layers; visible approved vs projected vs missing | `sdem/view.py`, `sdem/store.py` |
| Traceability & Impact | Pick entity; upstream/downstream trace, change impacts | existing `trace` and `impact` engine functions |
| Reviews & Changes | Relationship proposals, evidence, confidence, change sets, work, audit | `sdem/dashboard.py`, `sdem/agents.py` |
| Documents & Evidence | Four document views, source documents, evidence/gaps | existing design ingestion/provenance where supported; document formatter as new read-only presentation |

### SDEM Framework — separately scoped global console

| View | Main experience | Existing source |
| --- | --- | --- |
| Overview | Framework context/links | `sdem/home.py` |
| Metamodel Explorer | Visual map and catalog of all actual A1–A4 entity types, inheritance, attributes | `sdem/home.py`, metamodel files |
| Schemas & Configuration | Active schema structures and approved profile/extension settings | actual metamodel/config |
| Relationship Rules | Permitted within-layer and cross-layer mappings, inference rules, evidence | `sdem/home.py`, relationship-rule model |
| Engine Health | Current generated artifacts, controls, acceptance checks, timestamps | `sdem/home.py` |

**Navigation rule:** one consistent header and navigation system, including breadcrumbs and links from a workspace entity to its design document, catalog row, graph and relevant metamodel definition. Keep technical diagnostic detail available as secondary content.

## 3. Core architecture model views

### Architecture Designs

A1 Business / A2 BIAN Service Domain / A3 Application / A4 Technology are **schema-specific model instances** in the selected workspace, not four chatbot agents. Each layer has:

- **Document**: reader-friendly headings, descriptions, tables and relationships generated *deterministically* from the workspace as far as data permits. No fabricated missing content; surface unknown, unverified, candidate, or absent facts. Optional source citations and provenance links where available.
- **Catalog**: searchable records, type, ID and detailed attributes, relationships, version, lifecycle/status, source and evidence where supported. Click linked records to navigate to their actual layer, preserve context.
- **Diagram**: filtered layer-level relationships, fit/reset, entity selection, cross-layer navigation. Use actual registry links and graph store; never draw invented edges.

### Data Architecture

- Four named datasets (`a1-business.json`, `a2-service-domain.json`, `a3-application.json`, `a4-technology.json`) and mappings registry.
- **Table** lists actual instance records, linked records, type and status.
- **JSON** displays the exact selected instance from SDEM, not lossy invented pseudo-JSON.
- **Schema** reads actual metamodel entity definitions and constraints rather than deriving them from observed records.
- Source-of-truth distinction: workspace JSON and approved registry vs derived graph/HTML/report output.

### Knowledge Graphs

- **Federated** and layer-focused graphs; use `sdem/view.py` and its layout/source data where possible.
- Legend and presentation for approved cross-layer links, intra-layer links, projected/AID elements, evidence status and disconnected nodes. Styling never substitutes for semantic status.
- Entity search, relationship-type filter, fit to content, focus on element. Preserve existing trace controls and optional AID overlays.
- Individual layer diagrams show actual same-layer relationships, not sequential arbitrary lists.

### Metamodel

- Distinguish **types and permitted relationships** (the metamodel) from **instances and approved relationships** (a workspace).
- Show actual inheritance, own vs inherited attributes, cardinality/constraints, intra-layer relationship definitions, cross-layer types, rules and evidence requirements.
- A high-level view across A1–A4, then progressive drilling by entity type or mapping rule.
- Show active configuration context and any workspace-specific profile separately, only if supported and actually present.

## 4. Interaction rules

- Scope must stay visible: `SDEM Framework` vs `Payment Initiation / Solution Workspace`.
- Preferred selection flow: search/select entity → details → links → trace/impact → document section, without forcing re-entry of IDs.
- Use human labels first and technical IDs second, with copyable IDs where useful.
- Badges must unambiguously represent authoritative `approved`, `proposed`, `projected`, `unverified`, and `missing` states when defined; do not infer an `approved` status simply because a rule validated.
- Every read-only snapshot shows generated time, input/workspace baseline and graph freshness. Regeneration updates the snapshot.
- Never expose a UI action that appears to approve or mutate data until backend authorization/governance exists. Phase 1 is read-only, with copyable exact CLI commands where already supported.
- Keep existing offline, self-contained output; no external JS/CSS/network calls or browser-side business rules.
- Responsive layouts, keyboard navigation, focus indicators, accessible names and meaningful empty/error states.

## 5. Existing implementation to reuse

Source inspection of v0.18.0 found:

- `sdem/home.py` — generated offline HTML for framework and workspaces; entity map, health, rules and configuration tabs.
- `sdem/dashboard.py` — generated offline workspace dashboard: overview, review, trace/impact, matrices, change work, designs/gaps, AID, controls.
- `sdem/view.py` — self-contained graph view with A1–A4 bands, filters, selected record panel, trace highlights and projected-AID overlay.
- `docs/design/sdem-dashboard-design.md` — phase 1 generated read-only HTML; `sdem serve` phase 2 proposed, not approved.
- `docs/design/sdem-workbench-design.md` — VS Code/CLI/Copilot workflows, not a live hosted frontend.

Avoid replacing these functions with separate JavaScript logic. Refactor/generate shared presentation components only if it reduces duplication and preserves output compatibility.

## 6. Proposed phased implementation

**Phase A: navigation and information hierarchy (P0)**

- Shared, recognizable Framework vs Workspace scope and clear entry links among Home/Dashboard/Graph.
- Consolidate user-facing task navigation; keep advanced diagnostics available.
- Prominent A1–A4 entry points with focused layer selection and preserved selection/query context.

**Phase B: data and visualization usability (P0/P1)**

- Actual schema/dataset catalog and selected entity details, sourced from existing stores.
- Layer-focused graph, search and relationship filters, fit-to-selection; existing graph remains a supported output.
- Metamodel visual exploration of real permitted relationship types with drill-down.

**Phase C: document-view presentation (P1)**

- Deterministic Markdown/HTML renderers for individual A1–A4 designs, with source references and explicit gap sections.
- Output is derived only from existing data; no AI summarization is required to browse a workspace.
- Word templating and document ingestion are agent/MVP follow-on features **not assumed already working**.

**Deferred (P2):** `sdem serve`, live agents, natural-language chat, in-browser approvals, external hosting, database migration, React/Next.js rewrite.

## 7. Acceptance criteria

1. A novice architect can open the generated workspace output and reach A1, A2, A3 or A4 **Document**, **Catalog** and **Diagram** views in at most three user interactions.
2. Actual records, attributes and approved relationships come from the workspace. A missing architecture layer or absent link is reported, not silently fabricated.
3. A user can select a record and reach its relationships, upstream/downstream trace and document section without retyping its ID; navigation back restores selection.
4. A user can inspect framework metamodel definitions independently of solution data and see where the active rules allow cross-layer mappings.
5. Generated files work without a server/network, and display snapshot timestamp/freshness and source workspace.
6. Existing SDEM CLI commands, JSON contracts, deterministic engine behavior and governance constraints remain unchanged unless an independently justified defect is discovered.
7. Test small, sparse, incomplete and larger synthetic workspaces, plus missing graph/corrupt data/empty review cases.
8. Keyboard and accessible controls work for graph entity selection and cross-view navigation.
9. Existing tests continue to pass; add HTML-generation and semantic snapshot tests.

## 8. Mockup data warning

The attached HTML file is a standalone UX demonstration. The example records, relationships, document prose and BIAN operation label are illustrative only. It intentionally does **not** implement real SDEM schema parsing, evidence adjudication, CLI calls, saved workspaces, agents, uploads or approvals. The implementation must replace all synthetic content with authoritative v0.18.0 model data and remove unsupported actions.
