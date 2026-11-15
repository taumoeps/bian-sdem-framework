# Metamodel 0.15.0 — what a full design needs

> **Status: approved by the owner (2026-11-16) — D1–D8 as recommended. Building in slices (D8), each its own additive metamodel version so every release passes the stability policy (MS-05): slice 1 — information model and contracts — **metamodel 0.15.0, built**; slice 2 — links — **metamodel 0.16.0, built** (XL-08 and XL-10 need slice 3's kinds; AID's proposals from attributes, AT-01, next); slice 3 — new kinds and consistency — 0.17.0; Payment Initiation v2 after each.**
>
> **D9 — decided by the owner (2026-11-16): option 1.** Found while building: SDEM stores links between **adjacent** layers only (KG-F-03; high-level spec §6.1, §6.3), so BIAN stays the hub. Adjacency **stays the rule**, with a **named list of direct A1↔A3 link types** — those ArchiMate defines and BIAN has no counterpart for: IM-06 (`MAPPED_TO` A1 business object → A3 data entity), XL-01 (`SERVED_BY`), XL-02 (`AUTOMATED_BY`), XL-03, XL-08, XL-10 (`REALIZED_BY` pairs). Each such link type is marked `skips_level: true` with its reason; the registry check refuses any other level-skipping type; each link still needs its evidence and a person's approval; AID and the engine still infer through A2 first. Alternatives not taken: keep adjacency (the facts as paths through A2), allow any level-skipping.

## 1. Principles

| Id | Principle |
|---|---|
| FD-P1 | **Core or add-on** (the owner's rule, 2026-11-16): the core holds what every organisation's design needs from the public standards (ArchiMate, BIAN) and anything SDEM's own commands rely on; what one organisation needs goes in its profile, what lies outside A1–A4 in added layers (`sdem-layers-spec.md`), new commands in extensions (EXT-01…EXT-15). |
| FD-P2 | **Add, never break.** Every new kind, field and link is optional in 0.15.0; a 0.14.0 workspace passes `sdem check` after `sdem migrate` with nothing else changed. What is now thin is *reported* (a warning "thin"), never refused. |
| FD-P3 | **One fact, one place.** Where a relationship is held both as an attribute and as a link, the **approved link is the fact**; the attribute is evidence `sdem link` proposes the link from, and `sdem check` warns when they disagree. |
| FD-P4 | **Each layer at its own level of detail** (conceptual, logical, physical — the usual split of data architecture): A1 says what information the business uses; A2 the canonical, typed model (BIAN); A3 the stored data, with keys. |
| FD-P5 | **Inferred is not decided.** What `sdem bian import` and `sdem aid` produce is marked with its source and confidence; links between layers are approved by a person (CTL-21). |

## 2. Information model (audit A, G; LA-01…LA-06, LA-13, LA-17, LA-18, LA-33)

| Id | Requirement | Source | Confidence |
|---|---|---|---|
| IM-01 | **A1 stays conceptual.** `A1.BusinessObject` keeps `attributes` (names). New in-layer link: **association** between business objects (a payment *refers to* an account), beside composition, aggregation, specialisation. | [ARCHI] BusinessObject→BusinessObject `cgos` | high |
| IM-02 | **A2 typed fields:** `A2.BusinessObjectAttribute` (exists) gains `required` (boolean), `allowed_values` (list), `identifier` (boolean), `multiplicity` (`1`, `0..1`, `0..n`, `1..n`), `description`; `data_type` takes a fixed list (string, text, integer, decimal, amount, currency_code, date, datetime, boolean, identifier, enum, reference). A business object is **composed of** its attribute records; its `attributes` list, when both exist, must name the same fields (checked). | BIAN Semantic API schemas carry types, `required`, enumerations, references (OpenAPI 3) | high (BIAN publishes them); the data-type list is SDEM's — medium |
| IM-03 | **A2 references between objects:** business objects may be linked (association, composition, aggregation, specialisation); an attribute of `data_type: reference` is **associated with** the business object it refers to. | [ARCHI] `cgos`; OpenAPI `$ref` | high |
| IM-04 | **A3 physical fields — new kind `A3.DataAttribute`** (an SDEM extension: ArchiMate has no attribute element, as for `A2.BusinessObjectAttribute`): `physical_type` (e.g. `varchar(35)`, `numeric(18,2)`), `required`, `primary_key`, `unique`, `allowed_values`, `default`, `personal_information`, `classification`. A data entity is **composed of** its data attributes. | SDEM; field properties as in ISO/IEC 9075 (SQL) — medium | medium |
| IM-05 | **A3 references between entities:** data entities may be **associated** (beside composition, aggregation, specialisation); a data attribute that is a foreign key is **associated with** the entity it refers to. | [ARCHI] DataObject→DataObject `cgos` | high |
| IM-06 | **The chain without BIAN:** `MAPPED_TO` also links an **A1 business object to an A3 data entity** directly, for the organisation's own concepts BIAN has no object for. | [ARCHI] DataObject→BusinessObject `r` | high |
| IM-07 | **Field-level lineage — new link type `FIELD_MAPPED_TO`**: an `A2.BusinessObjectAttribute` → an `A3.DataAttribute`; evidence `data_model`; approved like every link between layers. With IM-06, an A1 object's named field is matched to A2 or A3 fields by name and `field_aliases` (no A1 field records — IM-01; see D1). | SDEM | medium |
| IM-08 | **Checks** (new LC rules): a typed field's `allowed_values` hold its records' values where data is given; a foreign key's target exists and has a primary key; a system-of-record entity has a primary key; `FIELD_MAPPED_TO` between incompatible types (a date to an integer) is a warning; a business object or entity with names but no field records is reported **thin** (FD-P2). | SDEM | — |
| IM-09 | **BIAN import (`sdem bian import --objects`)** reads, from BIAN's own files: each property's type and format → `data_type`; `required` → `required`; `$ref` to another schema → `reference` + the association (IM-03); an enumeration (BIAN's `…TypeValues` schemas, today skipped) → `allowed_values`; descriptions only with `--descriptions` (BI-D3 unchanged). `--only <names>` (as today) limits the objects to those service domains — a design's, not BIAN's hundreds. The shipped base still leaves objects out (BB-D2 unchanged). | BIAN Semantic APIs 14.0.0 (OpenAPI 3) | high |
| IM-10 | **AID carries the information model:** A1 business object → proposed `ALIGNED_TO` a BIAN object (by name, glossary, aliases); A2 business object → an inferred A3 data entity with a data attribute per field (logical → physical type by a fixed table), primary key from the identifier, foreign keys from references, and proposed `MAPPED_TO` / `FIELD_MAPPED_TO`. All marked inferred, confidence low or medium, confirmed or rejected by the person (`sdem aid confirm | reject`). | SDEM (AID-F/R extended) | — |

## 3. Contracts (audit B; LA-07…LA-09, LA-06)

| Id | Requirement | Source | Confidence |
|---|---|---|---|
| CT-01 | `A1.BusinessService.inputs` / `outputs` refer to **A1 business objects** (conceptual: objects, not fields). | ArchiMate: a service accesses business objects [ARCHI] BusinessService→BusinessObject `a` | high |
| CT-02 | **A2 operations access business objects** (new in-layer link `access`, ServiceOperation → BusinessObject), so an operation's information is the objects' typed fields; `input_attributes` / `output_attributes` stay as BIAN names and are checked against the control record's and objects' fields. | BIAN: operations act on the control record and business objects (SAPG) — medium | medium |
| CT-03 | **A3 `APIOperation`** gains `request_fields` and `response_fields` referring to **`A3.DataAttribute`** records, `responses` (status codes) and `parameters`; `payload_fields` (names) stays, deprecated. | OpenAPI 3 (request body, responses, parameters) | high |
| CT-04 | **A4 `Path.carries_data`** refers to **A3 data entities** (beside `carries`, components), so "this path carries personal data" is derived from the entities' fields. | SDEM | medium |

## 4. Links (audit C, D, E; LA-10…LA-24)

### 4.1 Between layers — new pairs and types (all allowed by ArchiMate)

| Id | Link | From → to | ArchiMate | Evidence a person gives |
|---|---|---|---|---|
| XL-01 | **`SERVED_BY`** (new) | A1 BusinessProcess, Activity, Actor, Role → A3 **ApplicationService** | ApplicationService→BusinessProcess/Actor/Role `v` | process model / application architecture |
| XL-02 | **`AUTOMATED_BY`** (new) | A1 BusinessProcess, Activity → A3 **ApplicationFunction** | ApplicationFunction→BusinessProcess `r` | process model |
| XL-03 | **`REALIZED_BY`** (new pair) | A1 **BusinessService** → A3 ApplicationService, ApplicationComponent | ApplicationService/Component→BusinessService `r` | application architecture |
| XL-04 | **`MAPPED_TO`** (new pair) | A1 BusinessObject → A3 DataEntity (IM-06) | DataObject→BusinessObject `r` | data model |
| XL-05 | **`FIELD_MAPPED_TO`** (new) | A2 BusinessObjectAttribute → A3 DataAttribute (IM-07) | — (SDEM) | data model |
| XL-06 | **`SERVED_BY`** (new pair) | A3 ApplicationComponent, ApplicationFunction → A4 **TechnologyService** | TechnologyService→ApplicationComponent/Function `v` | deployment design |
| XL-07 | **`STORED_IN`** (new) | A3 DataEntity → A4 Artifact, SystemSoftware | Artifact→DataObject `r` | deployment design |
| XL-08 | **`REALIZED_BY`** (new pair) | A1 **BusinessEvent** (§5) → A3 Event | ApplicationEvent→BusinessEvent `r` | event design |
| XL-09 | **`IMPLEMENTED_BY`** (new pair) | A2 ServiceOperation (Notify) → A3 Event — the registered candidate | BIAN SAPG §3.5 (Notify has no REST form) | event design |
| XL-10 | **`REALIZED_BY`** (new pair) | A1 **BusinessInterface** (a channel, §5) → A3 ApplicationInterface | ApplicationInterface→BusinessInterface `r` | application architecture |

Each is a registry rule with its evidence, proposed by `sdem link` (from the attributes of §4.3 where present, and by AID), approved by a person, followed by `sdem trace` and `sdem impact`, and drawn in the 3D view.

### 4.2 Inside a layer

| Id | Link | Source |
|---|---|---|
| WL-01 | association between A1 business objects (IM-01), A2 business objects (IM-03), A3 data entities (IM-05); A2 business objects composition, aggregation, specialisation | [ARCHI] `cgos` |
| WL-02 | A2 BusinessObjectAttribute association → BusinessObject (a reference, IM-03); A3 DataAttribute association → DataEntity (a foreign key, IM-05) | SDEM |
| WL-03 | A2 ServiceOperation access → BusinessObject (CT-02) | medium |
| WL-04 | **A4 Path association → Node, Device** (its two ends); `from`, `to` stay as evidence (FD-P3) | [ARCHI] Path→Node `fgiotv` |
| WL-05 | A1 BusinessEvent triggering → BusinessProcess, Activity; BusinessInterface assignment → BusinessService; Product aggregation → BusinessService, BusinessObject; Location aggregation → actors, nodes, devices, facilities' records | [ARCHI] BusinessEvent→BusinessProcess `t`; BusinessInterface→BusinessService `v`… ; Product→BusinessObject `g`; Location→* `g` |

### 4.3 Attributes that duplicate links (FD-P3)

| Id | Requirement |
|---|---|
| AT-01 | The approved link is the fact. These attributes become **evidence** `sdem link` proposes from: `ApplicationComponent.deployed_on`, `deployed_as`, `built_as`, `accesses`; `Device` / `Node` / `SystemSoftware.hosts`; `Artifact.of_component`; `Deployment.component_id`; `DataEntity.stored_in` (→ XL-07); `ApplicationFunction` / `ApplicationService.consumes`, `Event.published_to` (→ XL-06); `ApplicationInterface.exposed_through`; `BusinessActivity.invokes`; `Path.from`, `to`. `sdem check` warns where an attribute and the approved links disagree. |
| AT-02 | **Text becomes a reference:** `BusinessProcess` / `Activity.triggered_by` → A1 BusinessEvent; `BusinessService.channels` → A1 BusinessInterface; `BusinessActor.location` and A4 `site` → Location (§5); `Event.event_source` → A3 ApplicationComponent; `ApplicationComponent.network_zone` → **A4.NetworkZone** (today CommunicationNetwork, LA-21). Text that is not a known id stays valid, reported as unresolved (FD-P2). |

## 5. Scope — kinds that join the core (audit F; LA-25…LA-31)

| Id | New kind | Layer | Fields | ArchiMate |
|---|---|---|---|---|
| SC-01 | **`A1.BusinessEvent`** — something that happens and triggers business behaviour (a payment instruction received, a cut-off reached) | A1 | `event_kind` (external, internal, time), `schedule` | Business Event (high) |
| SC-02 | **`A1.Product`** — a coherent offering to customers (a current account, a payment service) | A1 | `product_kind`, `segment`, `regulated` | Product (high) |
| SC-03 | **`A1.BusinessInterface`** — a channel (branch, mobile app, open-banking API, file) | A1 | `channel_kind`, `customer_facing`, `availability` | Business Interface (high) |
| SC-04 | **Location** — where things are (a country, a region, a site): see D4 for its layer | D4 | `location_kind` (country, region, site, cloud region), `country` (ISO 3166), `parent` | Location (high) |
| SC-05 | **Contract**, **physical elements** (equipment, facility, distribution network, material): **profile**, not core | — | — | high (names) |
| SC-06 | **Motivation** (stakeholder, driver, goal, outcome, principle, constraint), **strategy** (resource, course of action), **implementation and migration** (work package, plateau, gap, deliverable): **added layers** through a profile, not core | — | — | high (names) |
| SC-07 | Business function, collaboration, interaction; application process, collaboration, interaction; technology function, process, event, collaboration: **not added** — covered by capability, application function and the existing kinds; a profile can add them | — | — | — |

## 6. Consistency and tooling (audit H, I; LA-37…LA-45)

| Id | Requirement |
|---|---|
| CN-01 | `A1.ValueStreamStage` **no longer extends `ValueStream`** — it keeps its own fields (entrance and exit criteria, value item) and its links; it stops inheriting `stages`, `stakeholder`, `value_proposition` (LA-43). |
| CN-02 | **Requirements:** `A1.BusinessRequirement` records are the design's business requirements; `requirements.json` holds the measurable ones, with conditions and evidence, and may name the A1 requirement it refines (`derived_from`). Written into the requirements spec; no data change (LA-42). |
| CN-03 | `A1.BusinessActivity` keeps extending `BusinessProcess` (LA-44 — confirmed as meant); `A4.NetworkZone` stays a grouping (LA-45 — no change). |
| TL-01 | **Trace and impact** follow every new link type and in-layer link (IM-03, IM-05, XL-01…XL-10, WL-01…WL-05); impact reaches a field: changing a BIAN attribute shows the data attributes, API fields and paths that carry it. |
| TL-02 | **Documents** (`sdem document`) show each layer's new kinds and the information model: per business object and data entity, its fields with type, key and required; per API, its request and response fields. |
| TL-03 | **Layouts and the 3D view:** A1 events, products, channels and locations placed by the A1 containment layout; data attributes are not shapes (shown with their entity in documents and the workbench); A4 Artifact, TechnologyInterface, TechnologyService placed by the zone layout (LA-40). The DESNRE builder (the `desnre` extension) follows. |
| TL-04 | **Migration 0.14.0 → 0.15.0** (`sdem migrate`): additive; nothing is converted silently; `sdem link` then proposes the links the attributes of AT-01 imply, for a person to approve. The example workspaces and graph stores are migrated and regenerated (the bump procedure). |
| TL-05 | **Not in this release:** onboarding (`sdem transform`) of the new kinds (LA-37) and the BIAN verification register (LA-34, G-09) — not needed for a full design; next. |

## 7. The test — Payment Initiation version 2

Built with the SDEM CLI only (no hand-edited JSON): `sdem new`; A1 by change sets; `sdem bian import --objects --domains …`; `sdem aid`, then confirm or reject; A3 and A4 by change sets; `sdem link`, and the owner's `sdem approve`; `sdem check`, `document`, `trace`, `impact`; `sdem desnre create` and `publish`.

| Id | Passes when |
|---|---|
| V2-01 | every kind of A1–A4 is used, or listed as not applying to payment initiation, with the reason |
| V2-02 | every attribute that applies is filled; no business object, BIAN object or data entity is thin |
| V2-03 | the information chain runs end to end: A1 object → BIAN object and its typed fields → data entity and its fields and keys → where it is stored; field-level lineage for every field of the payment instruction |
| V2-04 | every contract points at fields: business service, BIAN operation, API request and response, network path |
| V2-05 | every link type between layers is used — the ten of 0.14.0 and XL-01…XL-10 — every link approved |
| V2-06 | `sdem check` clean; the four documents; a trace from a business object to its storage; an impact of a field change |
| V2-07 | a report of what SDEM produced (import, AID) against what the person wrote, and what the person rejected |

Anything V2 cannot record is a finding: core or profile by FD-P1.

## 8. Decisions for the owner

| # | Decision | Options | Recommended | Source / reasoning | Confidence |
|---|---|---|---|---|---|
| D1 | Field records in A1 | none (names; conceptual) · `A1.BusinessObjectAttribute` too | **none** — A1 is conceptual (FD-P4); lineage is from A2 down, an A1 name matched by name and aliases (IM-07) | data-architecture levels; ArchiMate has no attribute element | medium |
| D2 | A3 fields | a new kind `A3.DataAttribute` · a typed map on the entity | **a new kind** — fields become records that can be linked (lineage, foreign keys, API fields) and traced | needed by IM-05, IM-07, CT-03, TL-01 | high |
| D3 | Names of the new link types | `SERVED_BY`, `AUTOMATED_BY`, `FIELD_MAPPED_TO`, `STORED_IN`, plus new pairs of `REALIZED_BY`, `MAPPED_TO`, `IMPLEMENTED_BY` · other names | **as proposed** — reuse where the meaning is the same; SDEM's style (upper layer first, a verb) | SDEM's ten | medium |
| D4 | Where Location lives | A4 (`A4.Location`) referred to from A1 · a workspace register beside the layers (like `requirements.json`) · a fifth layer | **A4.Location**, referred to from A1 (`BusinessActor.location`) — one kind of record, checked; data residency rules compare records, not text | ArchiMate Location is cross-layer; SDEM's layers are fixed | medium |
| D5 | Kinds added to the core | event, product, channel, location (SC-01…SC-04) · fewer · more | **those four** — all banks use them; the rest by profile or added layers (SC-05…SC-07) | FD-P1 | medium |
| D6 | Attributes that duplicate links | links are the fact, attributes evidence (AT-01) · attributes stay facts · remove the attributes | **links are the fact** — one place, traced and approved; attributes kept as the easy way in (FD-P2) | LA-20; FD-P3 | high |
| D7 | Payment Initiation v2 | replaces `examples/payment-initiation` (v1 in git history) · beside it | **replaces it** — the bundled example is the full one | — | — |
| D9 | Links that skip a layer (found while building) | a named list of direct A1↔A3 types · keep adjacency · any level-skipping | **a named list** — chosen by the owner, 2026-11-16 | ArchiMate defines them; KG-F-03 keeps the rule for everything else | — |
| D8 | Order of building | all of 0.15.0, then V2 · in slices (information model first), V2 growing with each | **in slices**: (1) information model and contracts, (2) links, (3) new kinds and consistency — V2 built up after each, so a slice that falls short is seen early | — | medium |
