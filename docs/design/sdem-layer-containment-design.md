# Grouping A1–A3 by what owns what — the containment layout

> **Status: approved — the owner approved C1–C6 as recommended (2026-11-15); A2 built (`sdem/containment.py`, `sdem layout --layer A2`, `sdem view`, the 3D view; tests `tests/test_containment.py`); A1 and A3 next.** Built for A2 as designed, with one choice made while building: a container is drawn as its region only — its record anchored at the region's heading, where links from other layers meet it — since in ArchiMate's nested notation the container *is* the box. C7 is recorded as: consistent with Archi's implementation (`NEW_RELATIONS_TYPES`) and an independent review (Gemini, 2026-11-15) that cites ArchiMate 3.2 §5.1.2 (nesting) and §5.7 (derivation); the specification text itself was not read (behind an Open Group sign-in). It asks whether the way A4 is drawn — regions that hold what belongs to them — can be used for A1, A2 and A3 **without deviating from BIAN, ArchiMate or TOGAF** (the owner's condition: only A4 may deviate). Expected to need **no metamodel change**.

## 1. The problem

The 3D view groups A4 by network zone; A1, A2 and A3 are grouped by **record type** — "Components", "APIs", "Data and events", "Operations", "Processes", "Capabilities". Type buckets carry no meaning: a service operation sits far from the service domain it belongs to, and the lines cross the whole plate.

## 2. The principle — what keeps it standard

1. **The regions are existing standard records**, never new ones: a BIAN business area, business domain and service domain; an ArchiMate capability; an ArchiMate application component. (A4's zones were new records because A4 is the physical deployment; A1–A3 are not.)
2. **Something is drawn inside a region only through a structural relationship** — composition, aggregation, assignment or realisation (and specialisation). Access, serving, flow, triggering and association are always drawn as lines.
   - *Basis:* ArchiMate lets nesting stand for a relationship. Archi, the reference tool, creates a relationship from nesting by default for composition, aggregation, assignment, specialisation, realisation **and access** (`PreferenceInitializer.java`, `NEW_RELATIONS_TYPES`, read 2026-11-15). SDEM takes the stricter set, without access, so a drawing is never read as saying more than the data does. The ArchiMate 3.2 specification text is behind an Open Group sign-in and was not read; this is to be checked against it before building (C7).
3. **One primary hierarchy per layer.** A record can have two structural owners — a service operation is in its service group *and* aggregated by a business scenario; a process realises a capability *and* a value stream stage. A drawing nests it once, in the primary hierarchy; its other structural links are drawn as lines, which ArchiMate always allows.
4. **What has no structural owner stays in its own group** — an ArchiMate Grouping by kind, as today: value streams, actors and roles, business objects, data entities, events, scenarios.
5. **Links between regions are derived, never stored.** When parts in two regions are linked, their regions are shown as related — a *potential* derivation in ArchiMate's terms (a link between the parts does not prove the wholes are linked in every sense). SDEM marks them **derived (potential)**, as it does A4's zone connections (ZC-01…ZC-03), and never records them.
6. **Each framework's own names** — business area, business domain, service domain; capability; application, component — never "level 0/1/2" (that is A4's).

## 3. A2 — the BIAN service landscape

The primary hierarchy is BIAN's own, already in SDEM's rules:

| Region | Holds | Rule |
|---|---|---|
| Business area | its business domains | RA2-01 (composition) |
| Business domain | its service domains | RA2-02 (composition) |
| Service domain | its service groups; its control record | RA2-03 (composition); RA2-05 (aggregation) |
| Service group | its service operations | RA2-04 (composition) |
| Control record | its behaviour qualifiers | RA2-11 (composition) |

**In their own groups, linked by lines:** business scenarios (they aggregate operations across domains — RA2-09 — so they cut across the landscape, as in BIAN's scenario views); business objects and their attributes (BIAN's business object model); asset types, functional patterns and semantic APIs.

**Derived:** service domain ↔ service domain, when a business scenario aggregates operations of both — the service domain interactions BIAN draws for a scenario.

**Payment, today:** Payments (business domain) → Payment Initiation (service domain) → its two service groups and six operations, its control record and two qualifiers; Payment Execution and Party Authentication are in the domain but not detailed. The layout shows what SDEM's checks already warn about (LC-10m): the business domain has no business area, and two service domains have no service group or control record — drawn as empty regions, not hidden.

## 4. A1 — the capability map

| Region | Holds | Rule |
|---|---|---|
| Capability | its sub-capabilities | RA1-01 (composition), RA1-02 (aggregation) |
| Capability | the processes and activities that realise it | RA1-08, RA1-16 (realisation) |
| Process | its activities and sub-processes | RA1-24, RA1-25 (composition) |

**In their own groups, linked by lines:** **value streams** with their stages — BIZBOK and TOGAF cross-map value streams to capabilities rather than nesting one in the other, and ArchiMate draws their link as a line; **actors and roles** (assigned to processes — RA1-35…39 — but owned by the organisation, not by a capability); **business objects**; **requirements**.

**Primary owner:** a process realising more than one capability is nested in the most specific one (the deepest in the map); its other realisations are lines.

**Payment:** Payments → Initiate Payment → *Capture and validate payment instruction* (with its two activities) and *Execute and confirm payment* (with its two). The value stream *Make a Payment* and its four stages, the Payments Operations Officer and the two business objects sit in their own groups beside the map.

## 5. A3 — the application structure

| Region | Holds | Rule |
|---|---|---|
| Solution building block (if recorded) | its applications | RA3-30, RA3-31 |
| Application | its components; the services it realises; the functions assigned to it; its interfaces | RA3-01, RA3-02 (composition, aggregation); RA3-06 (realisation); RA3-04 (assignment); RA3-03 (composition) |
| Interface | its API operations | RA3-27 (composition) |

**In their own groups, linked by lines:** **data entities** (accessed — ArchiMate access — not owned; a data entity could be nested under its system of record only where that is recorded by aggregation, which SDEM does not yet record) and **events** (triggered).

**Derived:** application ↔ application, from the flows between their components.

**Payment:** Payments Hub → Instruction Capture, Instruction Validation, Execution Gateway; the Payment Initiation Service it realises; Payments API v2 → its six operations. The three data entities and the PaymentStatusChanged event sit in their own groups.

## 6. What would be built

- **One layout for every layer:** a containment layout (`sdem/containment.py`, `sdem layout --layer …`) that takes a layer's primary hierarchy as data — each region splits along its longer side and gives its parts room by what they hold. A4 keeps its zones; A1–A3 use the hierarchies above. Drawn the same in the 3D view, `sdem view`, and `sdem diagram`.
- **The rules** each layer already has (LC-10m: the minimum links BIAN and the metamodel expect) — shown, not added to. A record with no owner goes in a "Not in a …" strip, as in A4.
- **No metamodel change** expected: no new entity types, no new link types, no new rules between records. If building shows otherwise, it comes back for approval.

## 7. Decisions for the owner

| # | Question | Recommendation |
|---|---|---|
| C1 | Regions are existing standard records only — BIAN's landscape, ArchiMate capabilities and applications — with no new entity types for A1–A3 | **yes** |
| C2 | Nest only through composition, aggregation, assignment and realisation (stricter than Archi's default, which also allows access) | **yes** |
| C3 | One primary hierarchy per layer: A2 business area → domain → service domain → group → operation (control record in its domain); A1 capability → sub-capability → realising process → activity; A3 application → component, service, function, interface → API operation | **yes** |
| C4 | Value streams, actors and roles, business objects, scenarios, data entities and events stay in their own groups, linked by lines | **yes** |
| C5 | Links between regions are derived and marked so — never stored | **yes** |
| C6 | Build A2 first (BIAN's landscape, the most standard), then A1, then A3 | **yes** |
| C7 | Before building, check the nesting and derivation rules against the ArchiMate 3.2 specification text (behind an Open Group sign-in — the owner's access, or a copy the owner holds) | **yes** |
