# SDEM A1–A4 layer audit

> **Status: audit — findings only, no decisions (2026-11-16).** Asked for by the owner before a full design is built to test the metamodel and data architecture. Each finding has an id (LA-…), its source, and a confidence: **high** only where the public source was checked in this audit. Nothing here changes the metamodel; changes need the owner's approval (AGENTS.md rule 2) and come in a design that cites these ids.

## 1. How it was done

| What was compared | Against | Source |
|---|---|---|
| Every kind of record SDEM 0.18.0 / metamodel 0.14.0 defines (41, plus 1 abstract): its fields, the links allowed inside its layer and to other layers | ArchiMate 3.2's relationship tables | `sdem types A1…A4 --json`; Archi's implementation of the tables, `com.archimatetool.model/model/relationships.xml` (`version="3.2"`, github.com/archimatetool/archi, master, read 2026-11-16) — the same reference SDEM's B1 link review uses ([ARCHI]) |
| ArchiMate's elements | the kinds SDEM has | ArchiMate 3.2 element list (the Open Group's text is behind a sign-in: **medium** where only the element list is used) |
| What BIAN publishes | what SDEM reads and ships | `sdem/bian.py` (reader, packer); `bian/README.md`; BB-D1, BB-D2, BI-D3, BI-D4 |
| Each kind | the tooling that handles it: inference rules, AID, layouts, onboarding, requirements | the code (`sdem/*.py`, `metamodel/transform-rules.json`) — by name: **medium** (a generic handler may cover a kind it does not name) |
| Earlier audits | — | `metamodel/metamodel-spec-gaps.json` (G-01…G-18), `docs/design/inference-audit.md` (2026-10-23: 32 relationships held as attributes) |
| The examples | the metamodel | `examples/payment-initiation` |

## 2. Summary

| Theme | Findings | Layers | Most important |
|---|---|---|---|
| A. Information model | LA-01 … LA-06 | A1, A2, A3 (A4 refers to it) | business objects and data entities are lists of names: no types, keys, required fields, or references between them |
| B. Contracts | LA-07 … LA-09 | A1, A2, A3, A4 | what a service, operation, API or network path takes and carries is names, not the information model's fields |
| C. Links between layers ArchiMate defines and SDEM lacks | LA-10 … LA-16 | A1↔A3, A3↔A4 | an application service serving the business; automation of a process; data entity realising a business object without BIAN in between; technology service serving an application |
| D. Links inside a layer | LA-17 … LA-19 | A1, A2, A3, A4 | association between business objects and between data entities |
| E. Relationships held as attributes or plain text | LA-20 … LA-24 | all | two ways to say the same thing; text where a reference belongs |
| F. ArchiMate elements not modelled | LA-25 … LA-31 | all, and outside A1–A4 | business event, product, contract, business interface (channel), location; motivation, strategy and migration beyond what SDEM has |
| G. BIAN coverage | LA-32 … LA-36 | A2 | the reader drops types, required fields, references, enumerations; verification register not built |
| H. Tooling coverage | LA-37 … LA-41 | all | onboarding does not extract 19 kinds; AID infers along the main chain only |
| I. Consistency | LA-42 … LA-45 | A1, A3, A4 | two places for requirements; inheritance that carries the wrong fields |
| J. The example | LA-46 | all | 33 of 41 kinds used; information model thin |

**Not a gap (checked):** A4's structure — eleven kinds with typed, specific fields (zones, hosting, paths, interfaces), recently built out; A2's behavioural model (service domains, operations, control records, qualifiers, scenarios); the ten link types between layers, each with its evidence.

## 3. Findings

### A. Information model

| Id | Finding | Source | Confidence |
|---|---|---|---|
| LA-01 | **A1 `BusinessObject.attributes` is a list of names** — fine for a conceptual model, but nothing says which names are identifiers or which carry personal data, beyond one flag for the whole object. | `sdem types A1` | high |
| LA-02 | **A2 `BusinessObject.attributes` is a list of names**; `BusinessObjectAttribute` exists (data_type, iso20022_ref, personal_information) but nothing creates or requires it, and it has no `required`, `allowed values`, or key. | `sdem types A2`; `sdem/bian.py` (`--objects` writes only the names) | high |
| LA-03 | **A3 `DataEntity.attributes` is a list of names** — no field kind: no type, length, key, required, or reference to another entity. A physical data model cannot be expressed. | `sdem types A3` | high |
| LA-04 | **The information chain needs BIAN in the middle**: A1 BusinessObject → `ALIGNED_TO` → A2 BusinessObject → `MAPPED_TO` → A3 DataEntity. Where BIAN has no object for it (an organisation's own concept), an A1 object cannot reach its data entity. ArchiMate lets a data object realise a business object directly. | link types; [ARCHI] `DataObject → BusinessObject: r` | high |
| LA-05 | **Field-level lineage is not possible**: with fields as names, "this A1 attribute is this BIAN attribute is this column" can be said only by matching names (`field_aliases` maps names, not records). | `sdem types A1–A3` | high |
| LA-06 | **A4 refers to information by name**: `Path.carries` lists A3 components (not data); where data is stored is said only from A3 (`DataEntity.stored_in`). No way to say a path carries personal data. | `sdem types A4` | high |

### B. Contracts

| Id | Finding | Source | Confidence |
|---|---|---|---|
| LA-07 | **A1 `BusinessService.inputs` / `outputs`** are names, with no reference to business objects or their attributes (unlike `consumers`, which refers to actors and roles). | `sdem types A1` | high |
| LA-08 | **A2 `ServiceOperation.input_attributes` / `output_attributes`** and **`ControlRecord.attributes`** are names (BIAN publishes the schemas behind them, with types — see LA-33). | `sdem types A2`; `sdem/bian.py` `_props` | high |
| LA-09 | **A3 `APIOperation.payload_fields`** are names, request and response together; no reference to data entity fields, no error responses, no parameters. | `sdem types A3` | high |

### C. Links between layers ArchiMate defines and SDEM lacks

All allowed by ArchiMate 3.2 ([ARCHI], read 2026-11-16, relation letters in brackets).

| Id | Missing link | Today | Confidence |
|---|---|---|---|
| LA-10 | **Application service serves a business process, actor or role** [`v`] | nothing: A3 `ApplicationService` has no link to another layer | high |
| LA-11 | **Application function (or process) realises a business process — automation** [`r`] | the A1 attribute `automation_level` (text); `ApplicationFunction` has no link to another layer | high |
| LA-12 | **Application component or service realises a business service** [`r`] | nothing: A1 `BusinessService` has no link to another layer | high |
| LA-13 | **Data entity realises a business object** directly (see LA-04) [`r`] | only through A2 | high |
| LA-14 | **Technology service serves an application component or function** [`v`] | the attributes `consumes` / `published_to` (A3 → A4.TechnologyService) — not a link type, so not proposed, approved, traced or drawn | high |
| LA-15 | **Artifact realises a data entity** [`r`] (and an application component — SDEM has `BUILT_AS`) | the attribute `DataEntity.stored_in` | high |
| LA-16 | **Application event realises or triggers a business event or process** [`r`, `t`]; BIAN Notify operations ↔ A3 events | nothing: A3 `Event` has no link to another layer; the Notify ↔ Event pair is a registered candidate | high (ArchiMate); high (candidate: `relationship-rules.json` `new_connection_candidates`) |

Kinds with no link to another layer at all: **A1** Actor, Requirement, Role, Service; **A2** AssetType, BehaviorQualifier, BusinessArea, BusinessDomain, BusinessObjectAttribute, ControlRecord, FunctionalPattern, ServiceGroup; **A3** ApplicationFunction, ApplicationService, Event, SolutionBuildingBlock; **A4** CommunicationNetwork, DeploymentEnvironment, NetworkZone, Path, TechnologyInterface, TechnologyService. Most A2 and A4 ones are reached through their parents (by design); the A1 and A3 ones are LA-10 … LA-16.

### D. Links inside a layer

| Id | Finding | Source | Confidence |
|---|---|---|---|
| LA-17 | **A2 business objects cannot be linked to each other** (ArchiMate allows composition, aggregation, specialisation, association between objects [`cgos`]); A2's only object link is composition to its attributes. | `sdem types A2`; [ARCHI] `BusinessObject → BusinessObject: cgos` | high |
| LA-18 | **No association between business objects (A1) or data entities (A3)** — "a payment refers to an account" (a reference, not a part) has no link kind; only composition, aggregation and specialisation are allowed. | `sdem types A1, A3`; [ARCHI] `DataObject → DataObject: cgos` | high |
| LA-19 | **A4 `Path` endpoints are attributes** (`from`, `to`, `network`), not links: a node is not linked to its paths (ArchiMate: node ↔ path association [`o`]). | `sdem types A4`; [ARCHI] `Node → Path: fotv` | high |

### E. Relationships held as attributes or plain text

| Id | Finding | Source | Confidence |
|---|---|---|---|
| LA-20 | **Two ways to say the same thing**: `ApplicationComponent.deployed_on` / `deployed_as` / `built_as`, `Device`/`Node`/`SystemSoftware.hosts`, `Artifact.of_component`, `Deployment.component_id` (attributes) beside the link types `DEPLOYED_ON`, `DEPLOYED_AS`, `BUILT_AS` (approved links). Which one wins when they disagree is not stated in the metamodel. | `sdem types A3, A4`; inference-audit.md (32 relationships held as attributes) | high (that both exist); medium (that it is unstated — the engine may treat attributes as evidence only) |
| LA-21 | **`ApplicationComponent.network_zone` refers to `A4.CommunicationNetwork`**, though network zones are records of their own, `A4.NetworkZone` (`sdem-network-zones-design.md`). | `sdem types A3, A4` | high |
| LA-22 | **Text where a reference belongs**: `BusinessProcess/Activity.triggered_by` (an event), `Event.event_source`, `BusinessActor.location`, A4 `site` / `region`, `BusinessService.channels`, `BusinessRequirement.derived_from` (a regulation or decision). | `sdem types` | high |
| LA-23 | **`BusinessActivity.invokes` refers to BIAN operations** — a cross-layer fact held as an attribute beside `USES_DOMAIN`. | `sdem types A1` | high |
| LA-24 | **A3 attributes that name A4 records** (`consumes`, `published_to`, `exposed_through`, `stored_in`) are cross-layer facts outside the link types (see LA-14, LA-15). | `sdem types A3` | high |

### F. ArchiMate elements not modelled

Whether each belongs in SDEM is a scope decision; listed so it is a decision, not an omission. ArchiMate element names: **medium** (the Open Group's text is behind a sign-in; the names match Archi's model).

| Id | Not modelled | Where it would sit | Why it may matter to a bank's designs |
|---|---|---|---|
| LA-25 | **Business event** | A1 | what triggers a process (today text: LA-22); the business side of an application event (LA-16) |
| LA-26 | **Product** and **contract** | A1 | banking products (an account, a card) grouping business services; contracts as business objects with terms |
| LA-27 | **Business interface** (a channel) | A1 | `BusinessService.channels` is text; channels (branch, app, API) are a core bank concept |
| LA-28 | **Business function**, **collaboration**, **interaction**; **application process**, **collaboration**, **interaction**; **technology function**, **process**, **event**, **collaboration** | A1, A3, A4 | partly covered by capability (A1) and function (A3); the rest rarely needed |
| LA-29 | **Location** | across layers | `site`, `region`, `country`, `location` are text; data residency rules compare text |
| LA-30 | **Physical elements** (equipment, facility, distribution network, material) | A4 | data centres and branches as facilities; rarely needed beyond `site` |
| LA-31 | **Motivation** beyond requirements (stakeholder, driver, goal, outcome, principle, constraint); **strategy** (resource, course of action); **implementation and migration** (work package, plateau, gap, deliverable) | outside A1–A4 | SDEM has requirements, baselines and change events; a profile can add layers (`sdem-layers-spec.md`), so these may stay out of the core |

### G. BIAN coverage

| Id | Finding | Source | Confidence |
|---|---|---|---|
| LA-32 | **Intended:** the shipped base leaves out BIAN's descriptions and business objects (BB-D2: no BIAN prose, small file); `--objects` / `--descriptions` import them from BIAN's own files on request (BI-D3, BI-D4). | `sdem-bian-base-design.md`, `sdem-bian-import-design.md` | high |
| LA-33 | **Not decided anywhere — the reader drops** property types and formats, which properties are required, `$ref`s between schemas, enumerations (`…TypeValues` skipped), descriptions below the domain, response bodies other than 200, parameters, examples. So `--objects` can only ever give names. | `sdem/bian.py` `read_domain`, `_props` | high |
| LA-34 | **BIAN verification register not built** (G-09; planned v0.14): no record that each BIAN reference is valid in the release used. | `metamodel-spec-gaps.json` G-09 | high |
| LA-35 | **The Service Landscape** (business areas and domains) and asset type / functional pattern for 66 domains are not in BIAN's API files; SDEM fills them by inference (`inferences-14.0.0.json`, marked SDEM's). | `bian/README.md` | high |
| LA-36 | **BIAN business scenarios** are not in the base: `A2.BusinessScenario` exists, but nothing imports BIAN's published scenarios. | `sdem/bian.py` (no scenario reading) | medium |

### H. Tooling coverage (by name in the code — medium unless stated)

| Id | Finding | Kinds |
|---|---|---|
| LA-37 | **Onboarding (`sdem transform`) does not extract 19 kinds**: none of A2 (by design: BIAN comes from BIAN), and from A1–A4 `ValueStreamStage`, `APIOperation`, `SolutionBuildingBlock`, `Deployment`, `DeploymentEnvironment`, `NetworkZone`, `Path`. | `metamodel/transform-rules.json` (22 kinds named) — high |
| LA-38 | **AID infers along the main chain only**: capability and process → service domain → component and API → deployment. It infers no A1 service, actor, role or object; no A3 function, service, data entity or event; nothing in A4 beyond deployments. | `sdem/aid.py`, `aid-spec.md` §3–4 |
| LA-39 | **Requirements subjects**: the requirements registry is wired to `A1.BusinessRequirement` by name; whether a requirement can apply to every kind (e.g. a data entity's retention) needs checking. | `sdem/requirements.py` |
| LA-40 | **Layouts and the 3D view**: A4 `Artifact`, `TechnologyInterface`, `TechnologyService` are not named by the containment or zone layouts. | `sdem/containment.py`, `sdem/zone_layout.py` |
| LA-41 | **Trace and impact** follow links; everything held as an attribute (section E) is invisible to them unless the engine turns it into a link. | `sdem/trace.py` (no kind named — generic) |

### I. Consistency

| Id | Finding | Source | Confidence |
|---|---|---|---|
| LA-42 | **Requirements in two places**: `A1.BusinessRequirement` records and the `requirements.json` registry (RR-D01 reuses the A1 kind). How a designer chooses between them is not obvious from the metamodel. | `sdem-requirements-risk-spec.md` | medium |
| LA-43 | **`ValueStreamStage` extends `ValueStream`**, so a stage inherits `stages`, `stakeholder`, `value_proposition` — fields of the whole stream, not of a stage. | `sdem types A1` | high |
| LA-44 | **`BusinessActivity` extends `BusinessProcess`** — fine for links; it also inherits `invokes` and `level` (the activity adds `sequence`). Worth confirming it is meant. | `sdem types A1` | medium |
| LA-45 | **`A4.NetworkZone` does not extend `InfrastructureComponent`** (by design: a grouping, not a thing) but carries none of the common A4 fields (`site`, `region`, `cloud_provider`) a zone often has. | `sdem types A4` | medium |

### J. The example

| Id | Finding |
|---|---|
| LA-46 | `examples/payment-initiation` uses 33 of 41 kinds (not: BusinessActor, BusinessService, BusinessRequirement, ApplicationFunction, SolutionBuildingBlock, Device, Path, TechnologyInterface); 19 links between layers, all ten link types, several variants never (e.g. `DEPLOYED_ON` a device, `ALIGNED_TO` a value-stream stage); 2 + 2 + 3 business objects / data entities. It is a starter slice, not a full design — so it cannot show most of A–I. |

## 4. What the owner decides next

No decision is taken here. The findings group into four pieces of work; each would be its own design with decisions:

| Work | Findings | Needs a metamodel change |
|---|---|---|
| **1. Information model and contracts** — fields as records with types, keys, required; references between objects and entities; contracts pointing at fields; the BIAN reader taking types, required, references, enumerations; AID carrying it | LA-01 … LA-09, LA-13, LA-17, LA-18, LA-33, LA-38 (part) | yes |
| **2. Links between layers ArchiMate already defines** — application service / function / event to the business; technology service to applications; artifact to data; attributes that duplicate links resolved | LA-10 … LA-16, LA-19 … LA-24 | yes |
| **3. Scope** — which ArchiMate elements join the core (business event, product, contract, channel, location) and which stay with profiles | LA-25 … LA-31 | yes, for what joins |
| **4. Tooling and consistency** — onboarding, AID, layouts, requirements subjects, verification register, inheritance fixes | LA-34 … LA-45 | some (LA-43 … LA-45) |

Then **a full made-up design** (all 41 kinds, every link variant, the information chain end to end) tests the result (LA-46).
