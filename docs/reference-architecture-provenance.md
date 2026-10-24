# Reference architecture provenance

> **Terminology (v0.7.0).** SDMM was renamed **SDEM — Service Domain Enterprise Metamodel**. This document keeps its original wording as a record, so read: *mapping set* / *mapping document* = **Architecture Relationship Registry**; *mapping model*, *plan* / *new mappings* = **Architecture Relationship Rules Model**; *registry* (the nine relationship types) = **relationship type catalogue**, part of the **Architecture Metamodel**; *mapping engine* / *executor* = **Architecture Relationship Inference Engine**; *local graph* / *federated graph* = **local / federated architecture knowledge graph**. Commands shown as `sdmm-*` and paths under `sdmm/` are now `sdem-*` and `sdem/` (the old names still work in v0.7 and are removed in v0.8.0). See [`sdem-overview.md`](sdem-overview.md).

**Purpose.** Every entity in the SDEM vocabulary is derived from a **publicly available reference architecture** — BIAN, ArchiMate or TOGAF — or is a documented SDEM extension of one. No entity is derived from, named after, or copied from any institution's own architecture model. This table is the evidence for that claim and must be kept current whenever the catalogue changes.

**How to read it.** *Reference architecture* is the public standard the entity is drawn from; *concept* is that standard's own name for it; *classification* is SDEM's `definition_source` / `alignment_kind`; *public source* is where the concept's definition is published; BIAN sources are open, Open Group sources need a free account to read online. SDEM paraphrases definitions and never reproduces standard text, diagrams or datasets.

| `definition_source` | Meaning |
|---|---|
| `bian_reference` | The concept is a named element of the BIAN Service Landscape, BOM or Control Record Model, readable on the public InSite portal. Status stays `pending_release_validation` until a verification-register entry records a check against the pinned release |
| `bian_aligned` | SDEM concept grounded in BIAN alignment guidance rather than a landscape element |
| `archimate_native` | Exact correspondence to an ArchiMate 3.2 element |
| `archimate_aligned` | Related to an ArchiMate 3.2 element; not claimed as identical |
| `togaf_informed` | Drawn from TOGAF 10 content guidance |
| `sdmm_extension` | SDEM's own portable concept, introduced where the standards leave a gap; origin recorded |

Public sources used throughout:

- **[BIAN-SL]** BIAN Service Landscape 14.0, InSite portal — https://bian.org/servicelandscape-14-0-0/ (publicly browsable; no licence text displayed; treated as read-only)
- **[BIAN-BCM]** BIAN Business Capability Model, as described in the Service Landscape release notes — v13.0 (June 2025): https://bian.org/wp-content/uploads/2025/06/BIAN-v13.0-Release-Notes-v0.3.pdf ; v14.0 (February 2026): https://bian.org/wp-content/uploads/2026/02/BIAN-v14.0-Release-Notes-v1.0_-Final-Version.pdf. Note: the BCM↔Service Domain mapping is stated there to be work in progress and not yet in the repository; no separate alignment document is published
- **[BIAN-API]** BIAN Semantic API Practitioner Guide — https://bian.org/wp-content/uploads/2024/12/BIAN-Semantic-API-Pactitioner-Guide-V8.1-FINAL.pdf
- **[AM]** ArchiMate® 3.2 Specification, The Open Group — https://pubs.opengroup.org/architecture/archimate3-doc/ (chapter numbers below refer to this edition: 6 Motivation, 7 Strategy, 8 Business, 9 Application, 10 Technology). Reading online requires a free Open Group account (SSO); the PDF is a licensed download. Element names and definitions are publicly documented; verifying a specific relationship claim against the normative tables needs an account
- **[TOGAF]** The TOGAF® Standard, 10th Edition — https://pubs.opengroup.org/togaf-standard/ (free Open Group account required to read online)

---

## A1 — Business Architecture

| Entity | Reference architecture | Concept | Classification | Public source |
|---|---|---|---|---|
| `A1.BusinessCapability` | BIAN BCM; ArchiMate Strategy layer | Business Capability; Capability | `bian_aligned` / conceptual | [BIAN-BCM]; [AM] ch. 7 |
| `A1.ValueStream` | ArchiMate Strategy layer; BIAN BCM alignment | Value Stream | `archimate_native` / exact | [AM] ch. 7; [BIAN-BCM] |
| `A1.ValueStreamStage` | SDEM extension of ArchiMate Value Stream | — (stage decomposition) | `sdmm_extension` / specialization | [AM] ch. 7 (parent) |
| `A1.BusinessProcess` | ArchiMate Business layer | Business Process | `archimate_native` / exact | [AM] ch. 8 |
| `A1.BusinessActivity` | SDEM extension of ArchiMate Business Process | — (process decomposition) | `sdmm_extension` / conceptual | [AM] ch. 8 (parent) |
| `A1.BusinessService` | ArchiMate Business layer | Business Service | `archimate_native` / exact | [AM] ch. 8 |
| `A1.BusinessActor` | ArchiMate Business layer | Business Actor | `archimate_native` / exact | [AM] ch. 8 |
| `A1.BusinessRole` | ArchiMate Business layer | Business Role | `archimate_native` / exact | [AM] ch. 8 |
| `A1.BusinessObject` | ArchiMate Business layer; aligned to BIAN BOM | Business Object | `archimate_native` + `bian_aligned` | [AM] ch. 8; [BIAN-SL] BOM |
| `A1.BusinessRequirement` | ArchiMate Motivation | Requirement | `archimate_native` / exact | [AM] ch. 6 |

## A2 — Service Domain Architecture

All `bian_reference`; all `pending_release_validation` until registered against release 14.0.

| Entity | Reference architecture | Concept | Classification | Public source |
|---|---|---|---|---|
| `A2.BusinessArea` | BIAN Service Landscape | Business Area | `bian_reference` / exact | [BIAN-SL] Service Landscape views |
| `A2.BusinessDomain` | BIAN Service Landscape | Business Domain | `bian_reference` / exact | [BIAN-SL] Service Landscape views |
| `A2.ServiceDomain` | BIAN Service Landscape | Service Domain | `bian_reference` / exact | [BIAN-SL] MetaModel Overview |
| `A2.FunctionalPattern` | BIAN Service Landscape | Functional Pattern | `bian_reference` / exact | [BIAN-SL] MetaModel Overview |
| `A2.AssetType` | BIAN Service Landscape | Asset Type | `bian_reference` / exact | [BIAN-SL] MetaModel Overview |
| `A2.ControlRecord` | BIAN Control Record Model | Control Record | `bian_reference` / exact | [BIAN-SL] Control Record Model |
| `A2.ServiceGroup` | BIAN Service Landscape | Service Group | `bian_reference` / exact | [BIAN-SL] MetaModel Overview |
| `A2.ServiceOperation` | BIAN Service Landscape; Semantic APIs | Service Operation | `bian_reference` / exact | [BIAN-SL]; [BIAN-API] |
| `A2.BehaviorQualifier` | BIAN Service Landscape; Semantic APIs | Behavior Qualifier | `bian_reference` / exact | [BIAN-SL]; [BIAN-API] |
| `A2.BusinessScenario` | BIAN Business Scenarios | Business Scenario (illustrative) | `bian_reference` / exact | [BIAN-SL] Business Scenarios |
| `A2.BusinessObject` | BIAN Business Object Model | Business Object | `bian_reference` / exact | [BIAN-SL] Business Object Model |
| `A2.BusinessObjectAttribute` | BIAN Business Object Model | attribute of a Business Object | `bian_reference` / exact | [BIAN-SL] Business Object Model |
| `A2.BOMModel` *(artefact)* | BIAN Business Object Model | the model artefact itself | `sdmm_extension` wrapper | [BIAN-SL] Business Object Model |
| `A2.Wireframe` *(artefact)* | BIAN Service Landscape | Wireframe | `bian_reference` artefact | [BIAN-SL] Wireframes Overview |
| `A2.SemanticAPI` *(artefact)* | BIAN Semantic APIs | Semantic API definition | `bian_aligned` artefact | [BIAN-API] |

## A3 — Application Architecture

| Entity | Reference architecture | Concept | Classification | Public source |
|---|---|---|---|---|
| `A3.ApplicationComponent` | ArchiMate Application layer | Application Component | `archimate_native` / exact | [AM] ch. 9 |
| `A3.ApplicationService` | ArchiMate Application layer | Application Service | `archimate_native` / exact | [AM] ch. 9 |
| `A3.ApplicationInterface` | ArchiMate Application layer | Application Interface | `archimate_native` / exact | [AM] ch. 9 |
| `A3.ApplicationFunction` | ArchiMate Application layer | Application Function | `archimate_native` / exact | [AM] ch. 9 |
| `A3.APIOperation` | SDEM extension; aligned to BIAN Semantic API operations and OpenAPI | — | `sdmm_extension` / aligned | [BIAN-API] |
| `A3.DataEntity` | ArchiMate Application layer | Data Object | `archimate_aligned` / related | [AM] ch. 9 |
| `A3.Event` | ArchiMate Application layer | Application Event | `archimate_aligned` / related | [AM] ch. 9 |
| `A3.SolutionBuildingBlock` | TOGAF Architecture Content | Solution Building Block | `togaf_informed` / conceptual | [TOGAF] Architecture Content |

## A4 — Technology Architecture

| Entity | Reference architecture | Concept | Classification | Public source |
|---|---|---|---|---|
| `A4.InfrastructureComponent` *(abstract)* | SDEM compatibility supertype | — | `sdmm_extension` | — |
| `A4.Deployment` | SDEM extension of ArchiMate Artifact assigned to Node | — | `sdmm_extension` / composite | [AM] ch. 10 (parents) |
| `A4.DeploymentEnvironment` | SDEM extension of ArchiMate Node grouping | — | `sdmm_extension` | [AM] ch. 10 (parent) |
| `A4.Node` | ArchiMate Technology layer | Node | `archimate_native` / exact | [AM] ch. 10 |
| `A4.Device` | ArchiMate Technology layer | Device | `archimate_native` / exact | [AM] ch. 10 |
| `A4.SystemSoftware` | ArchiMate Technology layer | System Software | `archimate_native` / exact | [AM] ch. 10 |
| `A4.TechnologyService` | ArchiMate Technology layer | Technology Service | `archimate_native` / exact | [AM] ch. 10 |
| `A4.TechnologyInterface` | ArchiMate Technology layer | Technology Interface | `archimate_native` / exact | [AM] ch. 10 |
| `A4.CommunicationNetwork` | ArchiMate Technology layer | Communication Network | `archimate_native` / exact | [AM] ch. 10 |
| `A4.Path` | ArchiMate Technology layer | Path | `archimate_native` / exact | [AM] ch. 10 |
| `A4.Artifact` | ArchiMate Technology layer | Artifact | `archimate_native` / exact | [AM] ch. 10 |

## Profile entities (not core; shipped only as examples)

Each extends a core ArchiMate-derived entity. They exist to show how a profile specialises the vocabulary; an institution's own profile would define its own.

| Profile entity | Extends | Reference architecture of the parent |
|---|---|---|
| `example-cloud:ComputeResource` | `A4.Node` | ArchiMate Node |
| `example-cloud:ContainerPlatform` | `A4.SystemSoftware` | ArchiMate System Software |
| `example-cloud:DatabasePlatform` | `A4.SystemSoftware` | ArchiMate System Software |
| `example-cloud:StorageResource` | `A4.TechnologyService` | ArchiMate Technology Service |
| `example-cloud:NetworkSegment` | `A4.CommunicationNetwork` | ArchiMate Communication Network |
| `example-cloud:NetworkComponent` | `A4.Node` | ArchiMate Node |
| `example-cloud:SecurityControl` | `A4.TechnologyService` | ArchiMate Technology Service |
| `example-cloud:IdentityAccessComponent` | `A4.SystemSoftware` | ArchiMate System Software |

---

## Provenance statement

1. **Origin.** Of the 41 core entities, 13 derive from BIAN (12 `bian_reference`, 1 `bian_aligned`), 21 from ArchiMate 3.2, 1 from TOGAF, and 6 are SDEM extensions (`ValueStreamStage`, `BusinessActivity`, `APIOperation`, `Deployment`, `DeploymentEnvironment`) or the compatibility supertype `InfrastructureComponent`. All reference material is publicly readable at the sources above.
2. **No institutional content.** No entity, name, definition or relationship in this catalogue is taken from any bank's or vendor's architecture model. Institution-specific entities belong in that institution's private profile and never in this repository.
3. **No reproduction.** Definitions in the catalogue are SDEM paraphrases. No text, diagram, identifier list or dataset from BIAN or The Open Group is reproduced. `reference.uri` fields point to the public source; they do not substitute for it.
4. **Verification.** `bian_reference` entities are published as `pending_release_validation` and become `confirmed_in_official_source` only through an entry in a BIAN verification register recording who checked what, where and when — planned as `metamodel/verification/` (now v0.13; not yet created).
5. **Trademarks.** BIAN®, ArchiMate® and TOGAF® are trademarks of their respective owners. SDEM is independent and not endorsed by BIAN or The Open Group.
