# SDEM diagrams — ArchiMate viewpoint templates (spec)

> **Status: approved by the owner (2026-11-06) after the mockup** (`work/diagram-templates-mockup.html`, drawn from a Payments workspace and SDEM's example workspaces); **built** — DG-01…DG-14 (`sdem diagram`, and the workbench's Diagram tabs and the Overview). **Not yet:** the ArchiMate Open Exchange export (DG-15), choosing a focus in the workbench (DG-08 is in `sdem diagram --focus`), routing lines around boxes (DG-11). Part of the [workbench UX spec](sdem-workbench-ux-spec.md) (UX-N02, UX-N04, UX-N14). Nothing here changes the metamodel, the datasets or who decides what.

## 1. Purpose

One standard set of architecture diagrams for **every** workspace: an architect sees each layer — and the four together — in the notation they know (ArchiMate), drawn from what the workspace holds, the same way every time, without drawing anything by hand.

## 2. Principles

| Id | Requirement |
|---|---|
| DG-01 | **Templates are data, not code.** Each template (`sdem/viewpoints.json`) names the metamodel types it shows, in which rows, which types are drawn **inside** which (composition, aggregation), and which stored links it draws. Templates refer to metamodel types and link kinds only — never to a workspace, a record or an id — so the same seven work on any workspace. |
| DG-02 | **Checked against the metamodel.** Every type, link kind and cross-layer relationship a template names must exist in the metamodel and its relationship rules; `sdem model check` fails otherwise (`sdem diagram --check`). |
| DG-03 | **Only what is stored is drawn.** A shape is a record; a line is a stored link inside a layer or an **approved** connection in the registry. Proposals are not drawn. Nothing is inferred, completed or guessed. |
| DG-04 | **Gaps are said, not hidden.** A template lists the shapes in it with no stored link to anything else in the view; the process view says when no sequence (triggering) is recorded between activities; a missing layer dataset is named. |
| DG-05 | **Deterministic.** The same workspace and template give the same SVG, byte for byte; the layout is computed by SDEM (Python), not in the browser; no randomness, no timestamps. |
| DG-06 | **Self-contained and offline.** SVG with its own styles; no script, font or file is loaded. Light and dark follow the system. |

## 3. Notation — ArchiMate, drawn by SDEM

| Id | Requirement |
|---|---|
| DG-07 | **Shapes and lines follow ArchiMate 3.2.** Layer colours (business yellow, BIAN orange, application blue, technology green); each type's ArchiMate shape and icon (process arrow, capability steps, value-stream chevron, object band, component, interface, service pill, 3-D node, system software); a part drawn **inside** its whole for composition and aggregation; lines — realization (dashed, hollow triangle), serving (open arrow), assignment (dot and filled arrow), access (dotted), triggering and flow (filled arrow; flow dashed), association (plain), composition and aggregation when not nested (filled and hollow diamond). Each cross-layer relationship has its ArchiMate reading in the template file's `notation` (e.g. `REALIZED_BY` → realization, the triangle on the realized element). Drawn by SDEM — no icon or image is copied from a tool or a vendor. |

## 4. The templates

| Id | Template | Layer | Shows |
|---|---|---|---|
| T1/T2 | **Capabilities and value stream** (Strategy, Value Stream viewpoints) | A1 | value streams with their stages as chevrons; capabilities containing their sub-capabilities; serving and realization between them |
| T3 | **Business process** (Business Process Cooperation) | A1 | capabilities, roles and business objects; processes containing their activities, in sequence when triggering is stored; the BIAN service domains the processes use |
| T4 | **BIAN service domains** (BIAN service landscape) | A2 | business domains → service domains → service groups → service operations, nested; scenarios, business objects, control records with behaviour qualifiers, asset types, functional patterns; lines drawn at service-domain level (×n) |
| T5 | **Application cooperation** | A3 | components containing their parts and interfaces (interfaces containing API operations); services, events, data entities; realization, assignment, triggering, access |
| T6 | **Technology and deployment** (Technology, Physical) | A4 | the applications hosted (approved `DEPLOYED_ON`/`DEPLOYED_AS`); environments containing deployments; system software, artifacts, networks, technology services |
| T7 | **Layered** (Layered viewpoint) | A1–A4 | four bands — business, BIAN, application, technology — joined by the approved connections between them |

## 5. Layout and reading

| Id | Requirement |
|---|---|
| DG-08 | **Focus.** A template may be drawn for one element (`--focus <id>`): that element, what it contains, what it is inside, and what is linked to any of them — so a large workspace gives a readable picture. |
| DG-09 | **Rolled-up lines.** When a link's end is drawn inside a box that is shown (e.g. a service operation inside its service domain), the line is drawn to the box shown and marked **×n** for the n stored links it stands for; the link ids are in the line's tooltip. A part's own link to its whole is not drawn when the part is inside it. |
| DG-10 | **Order.** Rows follow the template; inside a row, shapes are ordered to reduce crossings (by where their linked shapes are in the rows above), or kept in stored order where the template says so (processes); a container wraps its parts at four per row. |
| DG-11 | Lines are orthogonal, leave and enter on spread ports, use lanes between rows, and pass under a row rather than through shapes in it. *Not yet: routing around containers.* |
| DG-12 | **Every shape opens its record** in the workbench (the record under its type tab); hovering highlights its lines and neighbours; keyboard reachable. |

## 6. Where they appear

| Id | Requirement |
|---|---|
| DG-13 | **Workbench**: each layer's **Diagram** tab offers that layer's templates (A1: T1/T2 and T3; A2: T4; A3: T5; A4: T6); the **Overview** shows T7 under *Architecture designs*, before the A1–A4 cards — a diagram, not the knowledge graph (owner's decision, 2026-11-06); the old Knowledge Graphs link leads there. A layer the workspace does not have says so. Each diagram can be **fitted to the width** of the page or shown at **actual size** with sideways scrolling; the choice is remembered in the browser. |
| DG-14 | **`sdem diagram --workspace <dir> --template <id> [--focus <id>] --format svg|html|json -o <file>`** — the same drawing for Word, Confluence or a review pack; `--list` names the templates; `--check` checks the templates against the metamodel. |
| DG-15 | *Not yet:* **ArchiMate Open Exchange Format** (`--format archimate`) — the elements, relationships and views, to open in Archi or another ArchiMate tool. |
| DG-16 | *Later:* an organisation's own templates in its profile, checked the same way (DG-02). |

## 7. Tests

The seven templates on every example workspace (generate, every shape a record, every line a stored or approved link); a workspace with a missing layer; an empty workspace; determinism (DG-05); the template check (DG-02) catching a type the metamodel does not have; focus (DG-08); the workbench carrying each layer's diagrams.
