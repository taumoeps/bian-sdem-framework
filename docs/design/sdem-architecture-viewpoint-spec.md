# The Architecture viewpoint — one ArchiMate diagram per layer, the same in 2D and 3D (spec)

> **Status: approved and built (2026-11-18) — the owner approved AV1–AV5 as recommended; built in desnre-site (`assets/archview.js`, `tests/archview.test.mjs`).** As built (§9). Replaces the first version of the 3D *Architecture* viewpoint
> ([metamodel viewpoint spec §7](sdem-metamodel-viewpoint-spec.md), AVP-01…AVP-07), whose plates were laid out from the Design
> document's diagrams but drawn on their own, so the two disagreed. Changes DESNRE only (`workbench.html`, `index.html`,
> the agent's guide); no SDEM metamodel change.

## 1. Why the two views differ today — and it was not intended

| | Design document (2D) | 3D Architecture viewpoint |
|---|---|---|
| Which records | what each diagram recipe picks, including records of other layers for context | the records of the plate's own layer that the recipe drew |
| Which lines | a chosen few, per recipe (e.g. the business view draws serving, triggering, assignment) | every link in the data between the records shown |
| Positions | the recipe's own canvas, any width and height | the same positions, stretched to a square plate |
| Shapes | ArchiMate boxes sized to their text, with type icons | the 3D view's fixed blocks |
| Routes | the recipe's elbow lines | the 3D view's own router |
| A1 | **two** diagrams: business view (9.1) and capability map (9.2) | one: the business view |

The level of detail was decided twice, by two pieces of code. The fix is to decide it **once**, as data, and draw it twice.

## 2. The principle

| Id | Rule |
|---|---|
| **ARV-01** | **One view model per layer.** For each plate, one function computes a *view model* from the design's data: the **shapes** (records), the **groupings** (records drawn inside another), the **connections** inside the plate, each one's **position** and **route**. |
| **ARV-02** | **Two renderers, one model.** The Design document draws the view model as an ArchiMate SVG figure; the 3D view draws the same view model on its plate. Neither adds, drops or moves anything. The only differences are the medium: flat or in perspective, and the 3D view's interaction (rotate, zoom, light a trace). |
| **ARV-03** | **One square canvas.** Every plate is laid out on the same canvas, 1000 × 1000, and the 3D plate is square (6 × 6), as in the Metamodel viewpoint — so nothing is stretched, and the 2D figure is square too. Rows, groupings and what they hold are spread to fill it (the owner, 2026-11-18; first built at 1000 × 640). |
| **ARV-04** | **All from the data.** No AI, no per-design drawing, no hand layout: the same workspace always gives the same five diagrams (deterministic order: the data's own order, then by id). |
| **ARV-05** | **The level of detail is the table in §3**, the same for every workspace. A record kind left out is named in the figure's caption with its count ("34 service operations are in table 9.3"), never silently missing. |
| **ARV-06** | **Connections between plates** are the approved connections (and A3's access and stored-in links across A3-1/A3-2/A4). When one end is a record not shown (a service operation), the line goes to the shape that contains it and is marked ×n (as `sdem diagram` does, DG-09). Proposed and rejected connections are not drawn. |
| **ARV-07** | **ArchiMate notation in both:** each shape with its ArchiMate type symbol; each connection in its relationship's own line and end; a structural link shown by nesting is not also drawn as a line (ArchiMate's nesting rule) — the grouping *is* the connection. |

## 3. The level of detail — five plates

Taken from what the example holds (counts in brackets) and what SDEM's metamodel says each layer contains.

### A1 Business Architecture — "who is served, by which steps, for which capability"

| | |
|---|---|
| **Shapes** | business actors (3), business role (1), business interfaces — channels (2), business services (2), products (1), value stream stages (3), business processes (8) |
| **Groupings** | **capability** (3) holds the processes that realise it (realization, 8), sub-capabilities inside their parent (aggregation); **value stream** (1) holds its stages (composition) |
| **Connections** | serving (interface → actor, service → actor); flow (process → process, the chain; stage → stage); realization (process → service, process → stage); assignment (role → process); aggregation (product → service) |
| **Left out** | business requirements (24) — motivation, in the requirements tables (3) and traceability (10) |

This merges today's two A1 diagrams (business view and capability map) into one: the capability map becomes the groupings of the business view. 9.1 and 9.2 then show **the same plate**, one for the conceptual story, one for the detail — see §8, AV1.

### A2 Service Domains — "the BIAN functions used, and how each is organised"

| | |
|---|---|
| **Shapes** | control records (3), service groups (14), asset types (3), functional patterns (2) |
| **Groupings** | **service domain** (3) holds its control record (aggregation) and its service groups (composition) |
| **Connections** | association (service domain → asset type, → functional pattern) |
| **Left out** | service operations (34) and behaviour qualifiers (11) — counted on each group and control record ("7 operations"), listed in table 9.3 |

### A3-1 Data Architecture — "what is held, and its fields"

| | |
|---|---|
| **Shapes** | data attributes — fields (30), each marked key / personal information |
| **Groupings** | **data entity** (4) holds its fields (composition) |
| **Connections** | association (field → the entity it refers to, e.g. `consent_id` → ConsentLedger) |
| **Left out** | nothing |

### A3-2 Application Architecture — "the software, the order a request reaches it, and what it exposes"

| | |
|---|---|
| **Shapes** | application components (8), API operations (5), events (1) |
| **Groupings** | **application interface** (1) holds its API operations (composition) |
| **Connections** | flow (component → component); triggering (component → event); composition (component → interface) |
| **Left out** | nothing |

### A4 Technology Architecture — "where it runs, and how the places connect"

| | |
|---|---|
| **Shapes** | deployments (8), system software (4) |
| **Groupings** | **location** (1) holds the network zones; **network zone** (5) holds its nodes (aggregation); **node** (5) holds what is assigned to it (assignment) — so a deployment sits in its node, in its zone, in its location |
| **Connections** | communication path (4), drawn node to node with its name |
| **Left out** | other environments (one environment at a time, as the metamodel viewpoint, VP-11) — named in the caption |

### Between plates (ARV-06)

A1 → A2 `USES_DOMAIN`, `SUPPORTED_BY` · A2 → A3-2 `REALIZED_BY` (service domain → component), `IMPLEMENTED_BY` (service operation → API operation; drawn from the operation's service group, ×n, since operations are not on A2) · A3-2 → A3-1 access (component or API operation → entity) · A3-1 → A4 `STORED_IN` (entity → system software) · A3-2 → A4 `DEPLOYED_ON` (component → node grouping), `DEPLOYED_AS` (component → deployment), `EXPOSED_THROUGH` (interface → node grouping).

## 4. Layout — one algorithm, both views

| Id | Rule |
|---|---|
| **ARV-08** | **Rows by kind, in reading order** (A1: actors · channels and services · value stream · capabilities with their processes · role; A3-2: interface · components by flow order · event — as today's diagrams). |
| **ARV-09** | **Groupings are sized by what they hold**; a shape belongs to one grouping only — the most specific (as the containment layout, VP-05). |
| **ARV-10** | **Routes are computed once**, orthogonal, around shapes and groupings, and both renderers draw those routes. |
| **ARV-11** | **Labels:** name inside the shape, id above it, wrapped to the shape's width — in both views. The 3D view hides a label only when zoomed out so far that it cannot be read. |

## 5. The Design document

- 9.2 to 9.6 each carry **their plate's figure**, the same drawing as the 3D plate: 9.2 A1, 9.3 A2, 9.4 A3-1, 9.5 A3-2, 9.6 A4.
- The other figures are **summaries, not plates**, and say so in their captions: the value stream at a glance (executive summary), the layered view (8), the conceptual view (9.1).
- Each plate figure has a link "Open in 3D" that brings the 3D view to that plate, flat.

## 6. What changes in the code

- `workbench.html`: the five recipes `ax-business`, `ax-capabilities`, `ax-bian`, `ax-data`, `ax-application`, `ax-technology` are replaced by five *view-model builders* and one SVG renderer; the document's ```` ```desnre arch-A1 ```` … `arch-A4` blocks draw them.
- `index.html`: the Architecture viewpoint draws the posted view model as is — shapes at their positions and sizes, groupings as regions, connections along their routes (no own routing on these plates).
- `agent/guide.py`, `agent/app.py`: the section → figure table (9.2 `arch-A1` … 9.6 `arch-A4`); stored documents keep working (the old `ax-` names are mapped to the new ones).

## 7. Tests

- For every example workspace: the 2D figure and the 3D plate list the **same shape ids, grouping ids and connection ids**, with the same positions (one test over the view model, so a renderer cannot drift).
- Every shape is a record of its plate's layer; every connection is a stored link or approved connection; every left-out kind is named with its count.
- An empty layer gives an empty plate with its name; determinism (same data → same model).

## 8. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| AV1 | A1: one diagram (business view with capabilities as groupings) instead of two | **one** — the plate and the document then agree, and nothing is lost |
| AV2 | Nesting: shown by the grouping only (ArchiMate), or also by a faint line (today's 3D) | **grouping only, in both views** — ArchiMate's rule; the connections view (⇅) still lists every link |
| AV3 | A2 level: service groups shown, operations counted (not drawn) | **as §3** — 34 operations would crowd the plate; table 9.3 lists them |
| AV4 | One canvas proportion for all plates (1000 × 640; square, 1000 × 1000, since 2026-11-18) | **yes** — so 2D and 3D are the same shape |
| AV5 | Build in DESNRE now, after approval | **yes**, in one change, with the §7 test |

## 9. As built

- `assets/archview.js` — `build(data)` gives the five view models; `toPlates(models, data)` the 3D view's model. The Design document's `archFigure` and the 3D view both draw from them.
- **Names:** the document keeps its block names (`ax-capabilities` → A1, `ax-bian` → A2, `ax-data` → A3-1, `ax-application` → A3-2, `ax-technology` → A4; `arch-A1` … `arch-A4` also accepted), so documents already written show the plates without being rewritten. 9.1's business view stays a summary and says so in its caption.
- **Routes** are elbows between the facing sides of two shapes, computed once in the view model; routing around other shapes (ARV-10's "around") is not yet done.
- **"Open in 3D"** on each figure brings the 3D view to that plate, flat.

## 10. Explicit notation and viewpoint definitions (2026-11-19)

> **Status: approved (2026-11-19) — the owner: "write the design spec and then implement"; AV6…AV10 as recommended (§10.5).** The owner's
> point: the Architecture view was *derived implicitly from the metamodel* — which ArchiMate element each record is drawn as, and what
> each plate holds, lived in DESNRE's drawing code (`assets/archview.js`) and in §3's table, not in SDEM. This makes both explicit, as data,
> in SDEM. **It is not a metamodel extension** (it adds nothing a design holds, and cannot be switched off) **and it changes no record**.

### 10.1 What was implicit, and why it matters

| | Where it lived | The gap |
|---|---|---|
| **Which ArchiMate element a type is drawn as** | `archview.js` (its shape kinds, `K3`) and the workbench's layer colours | SDEM's metamodel records where each type's *definition* comes from (`reference`: ArchiMate 3.2 for 23 types, BIAN for every A2 type, SDEM's own for a few) — a **source**, not a **notation**: a BIAN service domain must still be drawn as some ArchiMate element (a business function), and only the site's code said which |
| **What each plate holds** | `archview.js`'s five builders and §3 | a type another extension adds inside a layer (MX-30), or a profile's type, is drawn only if someone edits the site's code |
| **Extensions** | the security pack names an ArchiMate element per type (`archimate`) | the core did not — extensions were more explicit than SDEM itself |

### 10.2 The notation — in SDEM's metamodel

| Id | Rule |
|---|---|
| **ARV-12** | **Every SDEM type has an ArchiMate notation**, in `metamodel/archimate-notation.json` (format `sdem-notation/1`): the ArchiMate element it is drawn as (`Business Function`, `Application Component`, `Node` …) and that element's ArchiMate layer (strategy, business, application, technology, physical, motivation, implementation, other). An abstract type may have one, for its subtypes to inherit. |
| **ARV-13** | **Notation is not source.** A type's `reference` (where its definition comes from) is unchanged; the notation says how it is drawn. They agree where the type *is* an ArchiMate element (`A3.ApplicationComponent` → Application Component); they differ where it is not (`A2.ServiceDomain`, from BIAN, drawn as a Business Function — the reason is written beside it). |
| **ARV-14** | **Every link kind and every cross-layer relationship has its ArchiMate relationship** in the same file — the within-layer kinds are already ArchiMate's (composition, flow, serving …); the cross-layer ones are mapped (`REALIZED_BY` → realization, `DEPLOYED_ON` → assignment, `USES_DOMAIN` → serving …). |
| **ARV-15** | **Profiles and extensions declare theirs; subtypes inherit.** A profile's or a pack's type may name its `archimate` element (security's do); if it does not, it inherits the nearest ancestor's notation — so a network extension's firewall extending `A4.Node` is drawn as a Node with no change to any viewer. |
| **ARV-16** | **SDEM says it.** `sdem types <layer> --json` gives each type's resolved notation (`archimate: {element, layer, from}` — `from` names where it came from: SDEM, an ancestor, a profile, an extension). `sdem viewpoint check` (and SDEM's tests, so CI) fail if an SDEM type has none. |
| **ARV-17** | **Not part of the frozen core.** The notation file, like `export-conventions.json`, is described by the metamodel but is not one of the frozen items (MS-04: entity types, link types, within-layer rules, attributes): changing how a type is *drawn* changes no record and needs no migration or `metamodel_version` change. It is versioned by its own `notation_version`, and listed in the CHANGELOG when it changes. |

### 10.3 The viewpoint definition — the Architecture viewpoint as data

| Id | Rule |
|---|---|
| **ARV-18** | **The Architecture viewpoint is a definition file**, `metamodel/viewpoint-architecture.json` (format `sdem-viewpoint/1`): its plates in order (A1, A2, A3-1, A3-2, A4), and for each the question it answers, its **shapes** (types), its **groupings** (a type and the link kinds by which it holds others), its **connections** (link kinds), and what it **leaves out** (types, with why and where they are listed instead) — §3's table, as data. |
| **ARV-19** | **Types by inheritance.** A plate that names a type includes its subtypes — a profile's or a horizontal extension's (MX-30) — unless the definition says otherwise; a type no plate names is listed as *left out* with its count, never silently dropped (ARV-05). |
| **ARV-20** | **Layout stays an algorithm, named in the definition.** Each plate names its layout (`rows-by-kind`, `nested-groupings`, `zones-nodes-deployments` — §4, ARV-08…ARV-11); viewers implement the named layouts. The definition decides *what* is drawn; the layout decides *where*. |
| **ARV-21** | **SDEM says it.** `sdem viewpoint list` and `sdem viewpoint show <name> [--json]`; `sdem viewpoint check` (and SDEM's tests, so CI) fail if a definition names a type, link kind or layout SDEM does not know, or leaves a type of its layer neither drawn nor named as left out. |
| **ARV-22** | **Extensions add viewpoints, the core keeps its own.** A vertical extension ships its own definition (security's S1–S5, MX-15), named in its manifest's `viewer`; a horizontal one adds none — its types join the core plates by ARV-19. A definition from an extension never changes the core's. |

### 10.4 Viewers read them

| Id | Rule |
|---|---|
| **ARV-23** | **The publisher sends them** with the design: each type's notation (already in `sdem types`) and the viewpoint definitions in use (`viewpoints`) — sdem-desnre 0.8.1. |
| **ARV-24** | **DESNRE draws from them, keeping its code as the fallback.** Plates take their records from the definition (subtypes included, ARV-19); a shape's ArchiMate element, its symbol and its layer colour come from the notation; the caption names what is left out from the definition. A design published before ARV-23 is drawn as before. The same view model still feeds the 2D figure and the 3D plate (ARV-01, ARV-02). |

### 10.5 Decisions (approved 2026-11-19)

| # | Decision | Decided |
|---|---|---|
| AV6 | The notation in SDEM's metamodel, as a file beside the frozen core, versioned on its own (ARV-12…ARV-17) | **yes** |
| AV7 | The Architecture viewpoint as a definition file in SDEM, with layouts named, not encoded (ARV-18…ARV-21) | **yes** |
| AV8 | Subtypes join their parent's plate; unnamed types are counted as left out (ARV-19) | **yes** |
| AV9 | Vertical extensions ship their own viewpoint; horizontal ones join the core plates (ARV-22) | **yes** |
| AV10 | The publisher sends both; DESNRE draws from them with its code as the fallback (ARV-23, ARV-24) | **yes** |

Not yet: the Metamodel viewpoint (VP-…) as a definition too; viewpoint extensions of their own kind (a C4- or TOGAF-style view that adds no data) — later, by spec.

### 10.6 As built (2026-11-19)

- **SDEM:** `metamodel/archimate-notation.json` (49 types declared, the rest inherited; 10 link kinds; 14 cross-layer relationships) and `sdem/notation.py`; `sdem types --json` gives each type's `archimate` (its own, a profile's or an extension's, or inherited — the security pack's types come through as Requirement, Assessment, Grouping); `metamodel/viewpoint-architecture.json` and `sdem viewpoint list|show|check`; `tests/test_notation_viewpoint.py`.
- **sdem-desnre 0.8.1:** sends `viewpoints` with the design (each type's notation was already in `types`).
- **DESNRE:** `assets/archview.js` takes each plate's caption from the definition (left-out groups with their counts and reasons; any unnamed type counted), places a profile's or an extension's type by its nearest SDEM type, and gives each shape its ArchiMate element, shown on hover in the Design document's figures. Without a definition (a design published earlier) the plates are exactly as before — tested.
- Not yet: the five plates' layouts still live in `archview.js` (named in the definition, ARV-20); the Metamodel viewpoint as a definition.
