# The SDEM metamodel viewpoint — the design seen as SDEM holds it (spec)

> **Status: proposed (2026-11-18).** §1–§6 document what is built and add no new behaviour; §7 proposes a second viewpoint for the same 3D view — the ArchiMate viewpoint — not built. It names, in one place, the viewpoint the DESNRE 3D view and `sdem view` draw, gathers its rules from the specs that built it, and sets it beside SDEM's ArchiMate viewpoints so a reader knows which picture is which. The rules it gathers stay in their own specs, which remain the source: the [containment layout](sdem-layer-containment-design.md) (approved 2026-11-15) and the [network zones](sdem-network-zones-design.md) (approved 2026-11-14; ZL-01…ZL-06, ZC-01…ZC-03).

## 1. What it is

A design in SDEM is records in four layers and the links between them. The **SDEM metamodel viewpoint** draws every record of a layer where SDEM's metamodel puts it: **by what owns what** in A1–A3, and **by what runs where** in A4. It is the design as SDEM holds it — not a picture chosen for a reader, as an ArchiMate viewpoint is.

| | SDEM metamodel viewpoint | ArchiMate viewpoints |
|---|---|---|
| Question it answers | *What is in this design, and where does each thing belong?* | *What does a reader need to see about one concern?* |
| What it shows | every record and link of the layer | only the records the viewpoint is about |
| Arranged by | SDEM's structural links (A1–A3) and network zones (A4) | the viewpoint's own rows and rules |
| Notation | ArchiMate-like shapes; every link the same line | ArchiMate shapes and each relationship's own line |
| Drawn by | `sdem layout`, `sdem zones --layout`; the DESNRE 3D view, `sdem view` | `sdem diagram` (DG-01…DG-14); the diagrams in DESNRE's Design document |
| Audience | the architect exploring or checking the whole design | a reader of the design: reviewer, sponsor, solution architect |

## 2. The rules

| Id | Rule | Source |
|---|---|---|
| **VP-01** | **One layer per plate.** Each of A1, A2, A3, A4 is drawn on its own plate; the plates are stacked in layer order, and the approved connections between layers are drawn between plates. | the 3D view |
| **VP-02** | **The positions are SDEM's.** Every position comes from `sdem layout --layer A1|A2|A3 --json` and `sdem zones --layout --json`; nothing that draws the viewpoint arranges a record itself. | DP-03 |
| **VP-03** | **A1–A3: a region is an existing standard record** — a BIAN business area, business domain or service domain; an ArchiMate capability or value stream; an application or interface — never a new one. | containment §2.1 |
| **VP-04** | **A1–A3: a record is drawn inside a region only through a structural link** — composition, aggregation, assignment, realisation, specialisation. Access, serving, flow, triggering and association are always lines. | containment §2.2 |
| **VP-05** | **One primary hierarchy per layer.** A record with two structural owners is nested once — in BIAN's own hierarchy in A2, in the most specific capability in A1, in its application in A3 — and its other structural links are lines. | containment §2.3, §3–§5 |
| **VP-06** | **What has no structural owner stays in its own group, named by its kind** — value streams, requirements, actors and roles, channels, business services, data entities, events, business scenarios. | containment §2.4 |
| **VP-07** | **Links between regions are derived, never stored**, and marked *derived (potential)* — two regions are shown as related because parts of them are linked. | containment §2.5 |
| **VP-08** | **Each framework's own names** on the regions — business area, service domain, capability, application — never "level 0/1/2", which is A4's. | containment §2.6 |
| **VP-09** | **A4: a network zone is a region, not a shape.** Level-0 zones share the plate side by side; level-1 zones fill their level 0, level-2 their level 1. | ZL-01 |
| **VP-10** | **A4: a record sits in the zone that holds it**, or under its host in the host's zone (a "runs on" group); what is not deployed — an environment, a network, a path — is drawn in the smallest zone holding what it groups or connects, or *across zones*. | ZL-02, ZL-03 |
| **VP-11** | **A4: one environment at a time** (production by default); retired records are left out. | ZL-04 |
| **VP-12** | **Placement and nesting are shown by position, never a line**; zone connections are arrows between regions, worked out from the structure. | ZL-05, ZC-01…ZC-03 |
| **VP-13** | **Every shape is a record and opens it**; every line is a stored link or an approved connection — the viewpoint draws nothing the design does not hold. | the 3D view, DW-03 |

## 3. What it is not

- **Not an ArchiMate viewpoint.** It uses ArchiMate-like shapes for some kinds of record (a chevron for a value-stream stage, a rounded box for a service, a document shape for a requirement), but **every relationship is drawn as the same line**, and it is arranged by SDEM's structure, not by an ArchiMate viewpoint's rows. A reader who expects ArchiMate is pointed to `sdem diagram` or the Design document's diagrams.
- **Not a choice of what matters.** It shows everything in the layer — A2 shows BIAN's whole catalogue structure for the domains used, not only the domains. It is for exploring and checking, not for explaining.
- **Not editable as a picture.** Moving a shape changes nothing; the design changes only through a change set, and the viewpoint follows the data.

## 4. Where it appears

| Where | What |
|---|---|
| DESNRE — every design's 3D view | all four plates, stacked; a record chosen in the view opens below, and the agent's answers light the records they cite |
| `sdem view` | the same viewpoint, locally |
| `sdem layout`, `sdem zones --layout` | the positions, as JSON, for anything else that draws it |

## 5. Beside SDEM's ArchiMate viewpoints

SDEM already draws ArchiMate viewpoints itself: [`sdem diagram`](sdem-diagram-spec.md), templates T1–T7 in `sdem/viewpoints.json` (capabilities and value stream, business process, BIAN service domains, application cooperation, technology and deployment, layered). DESNRE's Design document draws its own ArchiMate views in the page (`ax-glance`, `ax-layered`, `ax-business`, `ax-capabilities`, `ax-bian`, `ax-data`, `ax-application`, `ax-technology`), written for DESNRE on 2026-11-18. The two cover much the same ground in two places; whether DESNRE should draw from `sdem diagram` instead is an open question for the owner (§6, V2).

## 6. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| V1 | The viewpoint's name in SDEM and DESNRE | **"SDEM metamodel viewpoint"** for the whole; *containment layout* (A1–A3) and *network-zones layout* (A4) for its parts, as the specs already call them |
| V2 | DESNRE's Design-document views and `sdem diagram` | **keep both for now**; when DESNRE's views are next changed, compare them with `sdem diagram`'s templates and draw from SDEM if it covers them — one set of ArchiMate templates instead of two |
| V3 | Lines in the 3D view | **leave as one line style**: the viewpoint shows that a link exists; ArchiMate relationship notation belongs to the ArchiMate views |

## 7. Proposed: the ArchiMate viewpoint in the 3D view

The owner's request (2026-11-18): the 3D view offers **two viewpoints, switched on the view itself** — the *SDEM metamodel viewpoint* (§1–§6, as today) and an *ArchiMate viewpoint* for the architect, built from the diagrams the Design document already draws, one per plate.

### 7.1 The five plates

| Plate | Layer | Drawn as (DESNRE's diagram code) | Holds |
|---|---|---|---|
| **A1 Business Architecture** | A1 | the business view (`ax-business`) | actors, channels (business interfaces), business services, value-stream stages, the processes in the order they trigger one another, the role assigned to them |
| **A2 Service Domains** | A2 | the BIAN view (`ax-bian`) | each service domain (as a business function) with its control record and service groups |
| **A3-1 Data Architecture** | A3 | the data view (`ax-data`), without its technology band | the data objects with their fields (keys and personal information marked) |
| **A3-2 Application Architecture** | A3 | the application view (`ax-application`) | the interface the third party calls, the components in the order a request reaches them, the event raised |
| **A4 Technology Architecture** | A4 | the technology view (`ax-technology`) | location and environment, network zones (groupings), the nodes in each, the system software and deployed artifacts they run, the paths |

A3 is split in two **plates only**: SDEM's four layers, metamodel and data do not change (no metamodel approval needed — AGENTS.md rule 2).

### 7.2 The rules

| Id | Rule |
|---|---|
| **AVP-01** | **Positions come from the diagram code**, not from `sdem layout`: each plate is laid out by the same function that draws its diagram in the Design document, so the plate and the document's figure match. The diagram code is split so that layout (positions) and drawing (SVG) are separate, and both the document and the 3D view use the one layout. |
| **AVP-02** | **Selective, as ArchiMate viewpoints are**: a plate shows what its view shows, not every record of the layer. The view says so — "*n* of *m* A1 records in this viewpoint" — and the metamodel viewpoint remains the place to see everything. |
| **AVP-03** | **ArchiMate notation on the plates**: shapes with their ArchiMate type icons, and each relationship in its own line — serving (open arrow), realization (dashed, hollow triangle), flow (dashed, filled arrow), triggering (solid, filled arrow), access (dotted), assignment (dot and arrow), composition and aggregation by nesting. |
| **AVP-04** | **Between plates, only what the design holds**: approved connections (A1 → A2 *serving*, A2 → A3-2 *realization*, A3-2 → A4 *assignment / deployed as*), A3-2 → A3-1 *access* (the components and API operations that read and write each data object), and A3-1 → A4 *stored in*. Proposed or rejected connections are not drawn in this viewpoint. |
| **AVP-05** | **The same interaction as today**: a shape opens its record; the agent's citations light the records they cite. A cited record not shown in this viewpoint is listed beside the view ("not in this viewpoint: …"), never silently dropped. |
| **AVP-06** | **Every workspace, from its own data**: the plates are drawn from the design's records and links, as the Design document's diagrams are — no AI, no per-design drawing. A plate whose layer is empty is drawn empty, with its name. |
| **AVP-07** | **The switch is part of the 3D view**: two labelled choices — *SDEM metamodel* · *ArchiMate* — on the view's controls; the viewer's choice is remembered on their device. |

### 7.3 Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| V4 | Where it is built | **in the DESNRE project that owns the 3D view** (`index.html`; the workspace view is redesigned there — not changed from the SDEM sessions without the owner's yes). The diagram-code split (AVP-01) is in `workbench.html` and goes with it. |
| V5 | A1's plate: the business view or the capability map | **the business view** — it carries the processes the A2 domains serve, so the lines between plates read; the capability map stays in the Design document (9.2) |
| V6 | Which viewpoint opens first | **the SDEM metamodel viewpoint** for a design's owner (as today); **ArchiMate** for the visitors' example `/example/payment`, where the audience is architects |
