# SDMM Mapping Model Design Specification — engine input (v0.6 draft)

> New to SDMM? Read `docs/mapping-model-design.md` first — it explains how the local graphs, mapping model, mapping engine, mapping set and federated graph fit together.

Generated from the records by `python -m sdmm.spec`; the test suite checks it is current. This specification merges the three records — the entity catalogue, the within-level structure (`metamodel/level-relationships.json`) and the cross-level mapping model (`schema/relationship-types.json`, `metamodel/new-mappings.json`) — with the export conventions, the mapping procedure and the test results, into one statement of **what a mapping engine must consume, do, refuse and produce**. Every requirement names the record rows it derives from and the use-case runs that validated it; nothing here claims more than a record and a run support.

**Terms, as in `docs/mapping-model-design.md`.** This document is the **mapping model**: the **rules** — the registry (§4.1), the plan rows (§4.2–4.3) and the export conventions (§5) — stated over entity **types**. The **mapping set** is the engine's output: **links** between real instances, in the form fixed by `schema/mapping.schema.json` (§7). The companion diagram `docs/mapping-model-diagram.puml` draws the mapping model: every within-level row (`RA…`) and every cross-level rule (`S…`) by ID, between entity types; it does not draw the mapping set.

 Narrative sources: `docs/mapping-logic-planning.md` (why the model is shaped this way), `docs/mapping-execution.md` (the procedure as the executor ran it), `docs/relationships-planning.md` (within-level rows), `docs/use-case-testing.md` (the runs). Those remain the places to read the reasoning; this document is the contract.

## 1. Purpose, scope and non-goals

**Purpose.** Propose cross-level mappings between four independently governed architecture models (A1 Business, A2 BIAN Service Domain, A3 Application, A4 Technology) from their exports, with evidence and confidence, for an architect to approve; never approve; refuse where the data does not support a connection.

**In scope.** Loading and validating level exports; the structural steps 1–5 of the procedure; proposals, candidate reports and the inference log; scoring against sealed gold; traceability and impact over approved mappings.

**Non-goals.** Semantic inference beyond step 5's bounded text rule; approval or lifecycle transitions (those are the validator's and the architect's); any institution-specific entity or rule (those belong in a private profile); reproduction of BIAN, ArchiMate or TOGAF text.

## 2. Vocabulary — the entity catalogue

44 entities across four levels (`metamodel/a1…a4-*.json`), each with public provenance (README › *Reference architecture provenance*). By standard: ArchiMate 21, BIAN 17, SDMM extension 5, TOGAF 1. **The entity ID is its type string** (e.g. `A3.ApplicationComponent`); every mapping, relationship row and export instance refers to it by that string.

| ID | Level | Kind | Extends | Reference concept |
|---|---|---|---|---|
| `A1.BusinessCapability` | A1 | concrete | — | BIAN BCM: Business Capability |
| `A1.ValueStream` | A1 | concrete | — | ArchiMate 3.2: Value Stream |
| `A1.ValueStreamStage` | A1 | concrete | A1.ValueStream | SDMM: Value Stream Stage |
| `A1.BusinessProcess` | A1 | concrete | — | ArchiMate 3.2: Business Process |
| `A1.BusinessActivity` | A1 | concrete | A1.BusinessProcess | SDMM: Business Activity |
| `A1.BusinessService` | A1 | concrete | — | ArchiMate 3.2: Business Service |
| `A1.BusinessActor` | A1 | concrete | — | ArchiMate 3.2: Business Actor |
| `A1.BusinessRole` | A1 | concrete | — | ArchiMate 3.2: Business Role |
| `A1.BusinessObject` | A1 | concrete | — | ArchiMate 3.2: Business Object |
| `A1.BusinessRequirement` | A1 | concrete | — | ArchiMate 3.2: Requirement |
| `A2.BusinessArea` | A2 | concrete | — | BIAN Service Landscape: Business Area |
| `A2.BusinessDomain` | A2 | concrete | — | BIAN Service Landscape: Business Domain |
| `A2.ServiceDomain` | A2 | concrete | — | BIAN Service Landscape: Service Domain |
| `A2.FunctionalPattern` | A2 | concrete | — | BIAN Service Landscape: Functional Pattern |
| `A2.AssetType` | A2 | concrete | — | BIAN Service Landscape: Asset Type |
| `A2.ControlRecord` | A2 | concrete | — | BIAN Service Landscape: Control Record |
| `A2.ServiceGroup` | A2 | concrete | — | BIAN Service Landscape: Service Group |
| `A2.ServiceOperation` | A2 | concrete | — | BIAN Service Landscape: Service Operation |
| `A2.BehaviorQualifier` | A2 | concrete | — | BIAN Service Landscape: Behavior Qualifier |
| `A2.BusinessScenario` | A2 | concrete | — | BIAN Service Landscape: Business Scenario |
| `A2.BusinessObject` | A2 | concrete | — | BIAN Service Landscape: Business Object |
| `A2.BusinessObjectAttribute` | A2 | concrete | — | BIAN Service Landscape: Business Object attribute |
| `A2.BOMModel` | A2 | artefact | — | BIAN Service Landscape: Business Object Model |
| `A2.Wireframe` | A2 | artefact | — | BIAN Service Landscape: Wireframe |
| `A2.SemanticAPI` | A2 | artefact | — | BIAN Semantic API: Semantic API |
| `A3.ApplicationComponent` | A3 | concrete | — | ArchiMate 3.2: Application Component |
| `A3.ApplicationService` | A3 | concrete | — | ArchiMate 3.2: Application Service |
| `A3.ApplicationInterface` | A3 | concrete | — | ArchiMate 3.2: Application Interface |
| `A3.ApplicationFunction` | A3 | concrete | — | ArchiMate 3.2: Application Function |
| `A3.APIOperation` | A3 | concrete | — | BIAN Semantic API: Service Operation (API) |
| `A3.DataEntity` | A3 | concrete | — | ArchiMate 3.2: Data Object |
| `A3.Event` | A3 | concrete | — | ArchiMate 3.2: Application Event |
| `A3.SolutionBuildingBlock` | A3 | concrete | — | TOGAF: Solution Building Block |
| `A4.InfrastructureComponent` | A4 | abstract | — | SDMM: Infrastructure Component |
| `A4.Deployment` | A4 | concrete | A4.InfrastructureComponent | SDMM: Deployment |
| `A4.DeploymentEnvironment` | A4 | concrete | A4.InfrastructureComponent | SDMM: Deployment Environment |
| `A4.Node` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Node |
| `A4.Device` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Device |
| `A4.SystemSoftware` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: System Software |
| `A4.TechnologyService` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Technology Service |
| `A4.TechnologyInterface` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Technology Interface |
| `A4.CommunicationNetwork` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Communication Network |
| `A4.Path` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Path |
| `A4.Artifact` | A4 | concrete | A4.InfrastructureComponent | ArchiMate 3.2: Artifact |

## 3. Within-level structure — what an export may contain

132 constraint rows (`metamodel/level-relationships.json`, documented row by row in `docs/relationships-planning.md`): A1 Business Architecture 48, A2 Service Domain Architecture 17, A3 Application Architecture 31, A4 Technology Architecture 36. Verification: verified_against_archi 113, verified 16, unverified_togaf 2, sdmm_reading 1. Association is permitted between any two entities of one level. The 12 catalogue inheritance links are listed there as `X` rows.

| Level | Derived from | Rows | The structure in one line |
|---|---|---|---|
| A1 | ArchiMate 3.2 ch. 6–8 | 48 | capabilities serve value streams; processes (and activities, is-a process) realise capabilities, value streams, services and requirements, access objects, compose activities; actors assigned to roles assigned to processes |
| A2 | BIAN Service Landscape metamodel (B02–B15) | 17 | area ⊃ domain ⊃ Service Domain; a domain has an asset type, a functional pattern, a control record and service groups of operations; operations act on the control record and may be qualified; scenarios sequence operations; objects type the control record |
| A3 | ArchiMate 3.2 ch. 9; TOGAF (SBB) | 31 | a component composes interfaces (which compose API operations) and sub-components, is assigned to functions, realises services; interfaces are assigned to services; behaviour accesses data entities and triggers events; a solution building block aggregates components |
| A4 | ArchiMate 3.2 ch. 10; SDMM deployment extensions | 36 | nodes compose nodes and interfaces, aggregate devices, are assigned system software, artifacts and deployments, realise technology services; interfaces are assigned to services; networks realise paths; environments aggregate deployments and platform elements |

### 3.1 All within-level rows

Full description, source, reasoning, inference and confidence per row: `docs/relationships-planning.md`.

| ID | Official | Source | Kind | Target | Verification |
|---|---|---|---|---|---|
| RA2-01 | B02 | A2.BusinessArea | composition | A2.BusinessDomain | verified |
| RA2-02 | B03 | A2.BusinessDomain | composition | A2.ServiceDomain | verified |
| RA2-03 | B09 | A2.ServiceDomain | composition | A2.ServiceGroup | verified |
| RA2-04 | B10 | A2.ServiceGroup | composition | A2.ServiceOperation | verified |
| RA2-05 | B06 | A2.ServiceDomain | aggregation | A2.ControlRecord | verified |
| RA2-06 | B04 | A2.ServiceDomain | association | A2.FunctionalPattern | verified |
| RA2-07 | B05 | A2.ServiceDomain | association | A2.AssetType | verified |
| RA2-08 | — | A2.ServiceOperation | association | A2.BehaviorQualifier | verified |
| RA2-09 | B13 | A2.BusinessScenario | aggregation | A2.ServiceOperation | verified |
| RA2-10 | — | A2.BusinessObject | composition | A2.BusinessObjectAttribute | verified |
| RA2-11 | B07 | A2.ControlRecord | composition | A2.BehaviorQualifier | verified |
| RA2-12 | B08 | A2.ControlRecord | association | A2.BusinessObject | verified |
| RA2-13 | B11 | A2.ServiceOperation | access | A2.ControlRecord | verified |
| RA2-14 | B12 | A2.ServiceDomain | flow | A2.ServiceDomain | verified |
| RA2-15 | B14 | A2.Wireframe | association | A2.ServiceDomain | verified (not enforceable) |
| RA2-16 | B15 | A2.SemanticAPI | realization | A2.ServiceDomain | verified (not enforceable) |
| RA2-17 | — | A2.BOMModel | aggregation | A2.BusinessObject | sdmm_reading (not enforceable) |
| RA1-01 | — | A1.BusinessCapability | composition | A1.BusinessCapability | verified_against_archi |
| RA1-02 | — | A1.BusinessCapability | aggregation | A1.BusinessCapability | verified_against_archi |
| RA1-03 | — | A1.BusinessCapability | serving | A1.ValueStream | verified_against_archi |
| RA1-04 | — | A1.BusinessCapability | serving | A1.ValueStreamStage | verified_against_archi |
| RA1-05 | — | A1.ValueStream | composition | A1.ValueStreamStage | verified_against_archi |
| RA1-06 | — | A1.ValueStreamStage | triggering | A1.ValueStreamStage | verified_against_archi |
| RA1-07 | — | A1.ValueStreamStage | flow | A1.ValueStreamStage | verified_against_archi |
| RA1-08 | — | A1.BusinessProcess | realization | A1.BusinessCapability | verified_against_archi |
| RA1-09 | — | A1.BusinessProcess | realization | A1.ValueStream | verified_against_archi |
| RA1-10 | — | A1.BusinessProcess | realization | A1.ValueStreamStage | verified_against_archi |
| RA1-11 | — | A1.BusinessProcess | realization | A1.BusinessService | verified_against_archi |
| RA1-12 | — | A1.BusinessProcess | access | A1.BusinessObject | verified_against_archi |
| RA1-13 | — | A1.BusinessProcess | realization | A1.BusinessRequirement | verified_against_archi |
| RA1-14 | — | A1.BusinessProcess | triggering | A1.BusinessProcess | verified_against_archi |
| RA1-15 | — | A1.BusinessProcess | flow | A1.BusinessProcess | verified_against_archi |
| RA1-16 | — | A1.BusinessActivity | realization | A1.BusinessCapability | verified_against_archi |
| RA1-17 | — | A1.BusinessActivity | realization | A1.ValueStream | verified_against_archi |
| RA1-18 | — | A1.BusinessActivity | realization | A1.ValueStreamStage | verified_against_archi |
| RA1-19 | — | A1.BusinessActivity | realization | A1.BusinessService | verified_against_archi |
| RA1-20 | — | A1.BusinessActivity | access | A1.BusinessObject | verified_against_archi |
| RA1-21 | — | A1.BusinessActivity | realization | A1.BusinessRequirement | verified_against_archi |
| RA1-22 | — | A1.BusinessActivity | triggering | A1.BusinessActivity | verified_against_archi |
| RA1-23 | — | A1.BusinessActivity | flow | A1.BusinessActivity | verified_against_archi |
| RA1-24 | — | A1.BusinessProcess | composition | A1.BusinessActivity | verified_against_archi |
| RA1-25 | — | A1.BusinessProcess | composition | A1.BusinessProcess | verified_against_archi |
| RA1-26 | — | A1.BusinessActivity | composition | A1.BusinessActivity | verified_against_archi |
| RA1-27 | — | A1.BusinessService | serving | A1.BusinessProcess | verified_against_archi |
| RA1-28 | — | A1.BusinessService | serving | A1.BusinessActivity | verified_against_archi |
| RA1-29 | — | A1.BusinessService | serving | A1.BusinessRole | verified_against_archi |
| RA1-30 | — | A1.BusinessService | serving | A1.BusinessActor | verified_against_archi |
| RA1-31 | — | A1.BusinessService | composition | A1.BusinessService | verified_against_archi |
| RA1-32 | — | A1.BusinessService | access | A1.BusinessObject | verified_against_archi |
| RA1-33 | — | A1.BusinessService | realization | A1.BusinessRequirement | verified_against_archi |
| RA1-34 | — | A1.BusinessCapability | realization | A1.BusinessRequirement | verified_against_archi |
| RA1-35 | — | A1.BusinessActor | assignment | A1.BusinessRole | verified_against_archi |
| RA1-36 | — | A1.BusinessRole | assignment | A1.BusinessProcess | verified_against_archi |
| RA1-37 | — | A1.BusinessRole | assignment | A1.BusinessActivity | verified_against_archi |
| RA1-38 | — | A1.BusinessActor | assignment | A1.BusinessProcess | verified_against_archi |
| RA1-39 | — | A1.BusinessActor | assignment | A1.BusinessActivity | verified_against_archi |
| RA1-40 | — | A1.BusinessActor | composition | A1.BusinessActor | verified_against_archi |
| RA1-41 | — | A1.BusinessActor | aggregation | A1.BusinessActor | verified_against_archi |
| RA1-42 | — | A1.BusinessRole | composition | A1.BusinessRole | verified_against_archi |
| RA1-43 | — | A1.BusinessRole | aggregation | A1.BusinessRole | verified_against_archi |
| RA1-44 | — | A1.BusinessObject | composition | A1.BusinessObject | verified_against_archi |
| RA1-45 | — | A1.BusinessObject | aggregation | A1.BusinessObject | verified_against_archi |
| RA1-46 | — | A1.BusinessObject | specialization | A1.BusinessObject | verified_against_archi |
| RA1-47 | — | A1.BusinessRequirement | composition | A1.BusinessRequirement | verified_against_archi |
| RA1-48 | — | A1.BusinessRequirement | specialization | A1.BusinessRequirement | verified_against_archi |
| RA3-01 | — | A3.ApplicationComponent | composition | A3.ApplicationComponent | verified_against_archi |
| RA3-02 | — | A3.ApplicationComponent | aggregation | A3.ApplicationComponent | verified_against_archi |
| RA3-03 | — | A3.ApplicationComponent | composition | A3.ApplicationInterface | verified_against_archi |
| RA3-04 | — | A3.ApplicationComponent | assignment | A3.ApplicationFunction | verified_against_archi |
| RA3-05 | — | A3.ApplicationFunction | realization | A3.ApplicationService | verified_against_archi |
| RA3-06 | — | A3.ApplicationComponent | realization | A3.ApplicationService | verified_against_archi |
| RA3-07 | — | A3.ApplicationInterface | assignment | A3.ApplicationService | verified_against_archi |
| RA3-08 | — | A3.ApplicationService | serving | A3.ApplicationComponent | verified_against_archi |
| RA3-09 | — | A3.ApplicationService | serving | A3.ApplicationFunction | verified_against_archi |
| RA3-10 | — | A3.ApplicationComponent | flow | A3.ApplicationComponent | verified_against_archi |
| RA3-11 | — | A3.ApplicationComponent | serving | A3.ApplicationComponent | verified_against_archi |
| RA3-12 | — | A3.ApplicationComponent | triggering | A3.ApplicationComponent | verified_against_archi |
| RA3-13 | — | A3.ApplicationFunction | composition | A3.ApplicationFunction | verified_against_archi |
| RA3-14 | — | A3.ApplicationFunction | triggering | A3.ApplicationFunction | verified_against_archi |
| RA3-15 | — | A3.ApplicationFunction | flow | A3.ApplicationFunction | verified_against_archi |
| RA3-16 | — | A3.ApplicationComponent | access | A3.DataEntity | verified_against_archi |
| RA3-17 | — | A3.ApplicationFunction | access | A3.DataEntity | verified_against_archi |
| RA3-18 | — | A3.ApplicationService | access | A3.DataEntity | verified_against_archi |
| RA3-19 | — | A3.DataEntity | composition | A3.DataEntity | verified_against_archi |
| RA3-20 | — | A3.DataEntity | aggregation | A3.DataEntity | verified_against_archi |
| RA3-21 | — | A3.DataEntity | specialization | A3.DataEntity | verified_against_archi |
| RA3-22 | — | A3.ApplicationComponent | triggering | A3.Event | verified_against_archi |
| RA3-23 | — | A3.ApplicationFunction | triggering | A3.Event | verified_against_archi |
| RA3-24 | — | A3.Event | triggering | A3.ApplicationFunction | verified_against_archi |
| RA3-25 | — | A3.Event | triggering | A3.ApplicationComponent | verified_against_archi |
| RA3-26 | — | A3.Event | access | A3.DataEntity | verified_against_archi |
| RA3-27 | — | A3.ApplicationInterface | composition | A3.APIOperation | verified_against_archi |
| RA3-28 | — | A3.ApplicationComponent | composition | A3.APIOperation | verified_against_archi |
| RA3-29 | — | A3.APIOperation | access | A3.DataEntity | verified_against_archi |
| RA3-30 | — | A3.SolutionBuildingBlock | aggregation | A3.ApplicationComponent | unverified_togaf |
| RA3-31 | — | A3.SolutionBuildingBlock | composition | A3.SolutionBuildingBlock | unverified_togaf |
| RA4-01 | — | A4.Node | composition | A4.Node | verified_against_archi |
| RA4-02 | — | A4.Node | aggregation | A4.Node | verified_against_archi |
| RA4-03 | — | A4.Node | aggregation | A4.Device | verified_against_archi |
| RA4-04 | — | A4.Node | assignment | A4.SystemSoftware | verified_against_archi |
| RA4-05 | — | A4.Device | assignment | A4.SystemSoftware | verified_against_archi |
| RA4-06 | — | A4.SystemSoftware | assignment | A4.SystemSoftware | verified_against_archi |
| RA4-07 | — | A4.Node | assignment | A4.Artifact | verified_against_archi |
| RA4-08 | — | A4.Node | realization | A4.TechnologyService | verified_against_archi |
| RA4-09 | — | A4.Node | composition | A4.TechnologyInterface | verified_against_archi |
| RA4-10 | — | A4.TechnologyService | serving | A4.Node | verified_against_archi |
| RA4-11 | — | A4.Node | assignment | A4.Deployment | verified_against_archi |
| RA4-12 | — | A4.Device | assignment | A4.Artifact | verified_against_archi |
| RA4-13 | — | A4.Device | realization | A4.TechnologyService | verified_against_archi |
| RA4-14 | — | A4.Device | composition | A4.TechnologyInterface | verified_against_archi |
| RA4-15 | — | A4.TechnologyService | serving | A4.Device | verified_against_archi |
| RA4-16 | — | A4.Device | assignment | A4.Deployment | verified_against_archi |
| RA4-17 | — | A4.SystemSoftware | assignment | A4.Artifact | verified_against_archi |
| RA4-18 | — | A4.SystemSoftware | realization | A4.TechnologyService | verified_against_archi |
| RA4-19 | — | A4.SystemSoftware | composition | A4.TechnologyInterface | verified_against_archi |
| RA4-20 | — | A4.TechnologyService | serving | A4.SystemSoftware | verified_against_archi |
| RA4-21 | — | A4.SystemSoftware | assignment | A4.Deployment | verified_against_archi |
| RA4-22 | — | A4.TechnologyInterface | assignment | A4.TechnologyService | verified_against_archi |
| RA4-23 | — | A4.TechnologyService | composition | A4.TechnologyService | verified_against_archi |
| RA4-24 | — | A4.Node | flow | A4.Node | verified_against_archi |
| RA4-25 | — | A4.Node | triggering | A4.Node | verified_against_archi |
| RA4-26 | — | A4.CommunicationNetwork | realization | A4.Path | verified_against_archi |
| RA4-27 | — | A4.CommunicationNetwork | composition | A4.CommunicationNetwork | verified_against_archi |
| RA4-28 | — | A4.Artifact | composition | A4.Artifact | verified_against_archi |
| RA4-29 | — | A4.Artifact | aggregation | A4.Artifact | verified_against_archi |
| RA4-30 | — | A4.Device | aggregation | A4.Device | verified_against_archi |
| RA4-31 | — | A4.DeploymentEnvironment | aggregation | A4.Deployment | verified_against_archi |
| RA4-32 | — | A4.DeploymentEnvironment | aggregation | A4.Node | verified_against_archi |
| RA4-33 | — | A4.DeploymentEnvironment | aggregation | A4.Device | verified_against_archi |
| RA4-34 | — | A4.DeploymentEnvironment | aggregation | A4.SystemSoftware | verified_against_archi |
| RA4-35 | — | A4.Deployment | aggregation | A4.Artifact | verified_against_archi |
| RA4-36 | — | A4.Device | composition | A4.Device | verified_against_archi |

| ID | Entity | extends |
|---|---|---|
| XA1-01 | A1.ValueStreamStage | A1.ValueStream |
| XA1-02 | A1.BusinessActivity | A1.BusinessProcess |
| XA4-01 | A4.Deployment | A4.InfrastructureComponent |
| XA4-02 | A4.DeploymentEnvironment | A4.InfrastructureComponent |
| XA4-03 | A4.Node | A4.InfrastructureComponent |
| XA4-04 | A4.Device | A4.InfrastructureComponent |
| XA4-05 | A4.SystemSoftware | A4.InfrastructureComponent |
| XA4-06 | A4.TechnologyService | A4.InfrastructureComponent |
| XA4-07 | A4.TechnologyInterface | A4.InfrastructureComponent |
| XA4-08 | A4.CommunicationNetwork | A4.InfrastructureComponent |
| XA4-09 | A4.Path | A4.InfrastructureComponent |
| XA4-10 | A4.Artifact | A4.InfrastructureComponent |

## 4. Cross-level mapping model

### 4.1 The registry — the nine relationship types a mapping may carry

| Mapping type | Source → target | Relationship | Perspective | Authority | Required evidence | Meaning |
|---|---|---|---|---|---|---|
| CAPABILITY_SUPPORTED_BY_DOMAIN | A1.BusinessCapability → A2.ServiceDomain | `SUPPORTED_BY` | architecture | bian_alignment_guidance | business_architecture_document, domain_scope_assessment | The capability's responsibilities are (partly) fulfilled by the functional scope of the selected Service Domain. |
| VALUE_STREAM_ALIGNED_TO_SCENARIO | A1.ValueStream → A2.BusinessScenario | `ALIGNED_TO` | process | bian_alignment_guidance | process_model, scenario_suitability_review | The value stream's stages are realised by the interactions described in the Business Scenario. |
| PROCESS_USES_DOMAIN | A1.BusinessProcess → A2.ServiceDomain | `USES_DOMAIN` | process | enterprise_rule | process_model | A process activity invokes one or more Service Operations of the Service Domain. |
| BUSINESS_OBJECT_ALIGNED_TO_BIAN_OBJECT | A1.BusinessObject → A2.BusinessObject | `ALIGNED_TO` | information | bian_alignment_guidance | business_glossary, object_alignment_review | The bank business concept carries the same meaning as (or specialises) the BIAN business object. |
| DOMAIN_REALIZED_BY_COMPONENT | A2.ServiceDomain → A3.ApplicationComponent | `REALIZED_BY` | architecture | enterprise_rule | application_architecture_document | The application component implements some or all of the Service Domain's functional responsibilities. |
| OPERATION_IMPLEMENTED_BY_API | A2.ServiceOperation → A3.APIOperation | `IMPLEMENTED_BY` | architecture | enterprise_rule | api_contract | The API operation exposes the behaviour of the Service Operation; semantic gaps must be documented. |
| BIAN_OBJECT_MAPPED_TO_DATA_ENTITY | A2.BusinessObject → A3.DataEntity | `MAPPED_TO` | information | enterprise_rule | data_model | The application data entity stores (part of) the BIAN business object; transformations and partial coverage are recorded. |
| COMPONENT_DEPLOYED_ON_INFRASTRUCTURE | A3.ApplicationComponent → A4.InfrastructureComponent | `DEPLOYED_ON` | architecture | enterprise_rule | deployment_design | The application component runs on the infrastructure component in a named environment. |
| COMPONENT_DEPLOYED_AS_DEPLOYMENT | A3.ApplicationComponent → A4.Deployment | `DEPLOYED_AS` | architecture | enterprise_rule | deployment_design | The application component is instantiated as this deployment in a named environment. |

Only these nine may appear in the mapping set (form: `schema/mapping.schema.json`); adjacency is A(n) → A(n+1) only; BIAN authorities require `bian_release` and a `canonical_id` on the A2 endpoint before approval. Everything else the model knows is a **candidate report**, never a registry proposal.

### 4.2 Plan rows — the 69 rules by decision

Every cross-level pair the mapping model considers (`metamodel/new-mappings.json`; reasoning per row in `docs/mapping-logic-planning.md` §5.3). The decision says what the engine does with the row: only **registry rules** produce links in the mapping set; the others are reported as candidates or not used.

| Decision | Rows | Engine behaviour |
|---|---|---|
| registry rule | 9 | propose, at the step and band stated |
| candidate rule | 5 | report in the candidate file; never propose until adopted into the registry |
| conditional rule | 5 | report when the institution data it fires on is present |
| derived path | 17 | compute as a closure over other arrows; report; never store |
| institution only | 14 | report from the export key named in `data_needed`; never infer |
| bian internal | 14 | not cross-level: A2 structure, enforced by §3 |
| not a mapping / historical / subsumed / not encodable | 5 | do nothing; the plan says why |

### 4.3 The 50 rules drawn in the mapping-model diagram, with the run that validated each

| ID | Pair | Decision | Step | Band | Validation |
|---|---|---|---|---|---|
| S01 | BusinessCapability → ServiceDomain (SUPPORTED_BY) | registry rule | 3 | medium | validated with findings: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (4 hits, 1 false — fixed) |
| S02 | ValueStream → BusinessScenario (ALIGNED_TO) | registry rule | 4 | medium | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (1 hits, 0 false) |
| S03 | ValueStreamStage → BusinessScenario (candidate) | derived path | 4 | low | validated: C1 (3 hits, 0 false) |
| S04 | BusinessProcess → ServiceDomain (USES_DOMAIN) | registry rule | 3 | medium | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (1 hits, 0 false) |
| S06 | BusinessActivity → ServiceOperation (candidate) | institution only | 1 | medium | validated: C1, H1, H2, H2 r2, M1 (4 hits, 0 false) |
| S07 | BusinessActivity → ServiceDomain (candidate) | derived path | 3 | medium | validated: C1 (4 hits, 0 false) |
| S08 | BusinessService → ServiceDomain (candidate) | institution only | 5 | low | validated: C1 (2 hits, 0 false) |
| S09 | BusinessService → ServiceOperation (candidate) | institution only | 4 | low | validated: C1 (2 hits, 0 false) |
| S12 | BusinessObject → BusinessObject (ALIGNED_TO) | registry rule | 4 | medium | validated: C1, H1, H2, H2 r2, M1 (2 hits, 0 false) |
| S13 | BusinessRequirement → ServiceDomain (candidate) | institution only | 3 | low | validated: C1 (3 hits, 0 false) |
| S14 | BusinessRequirement → ServiceOperation (candidate) | institution only | 3 | low | validated: C1 (2 hits, 0 false) |
| S15 | BusinessArea → ApplicationComponent (candidate) | derived path | 3 | high | validated: C1 (2 hits, 0 false) |
| S16 | BusinessDomain → ApplicationComponent (candidate) | derived path | 3 | high | validated: C1 (2 hits, 0 false) |
| S17 | ServiceDomain → ApplicationComponent (REALIZED_BY) | registry rule | 3 | high | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (20 hits, 0 false) |
| S18 | FunctionalPattern → ApplicationFunction (candidate) | institution only | 3 | low | validated: C2 (3 hits, 0 false) |
| S19 | AssetType → DataEntity (candidate) | institution only | 4 | low | validated: C2 (3 hits, 0 false) |
| S20 | ControlRecord → DataEntity (candidate) | candidate rule | 4 | high | validated: C2, H1, H2, H2 r2, M1, M2 (2 hits, 0 false) |
| S21 | ControlRecord → ApplicationFunction (candidate) | candidate rule | 3 | medium | validated: C2 (3 hits, 0 false) |
| S22 | ServiceGroup → ApplicationService (candidate) | derived path | 3 | medium | validated: C2, M1 (2 hits, 0 false) |
| S23 | ServiceGroup → ApplicationInterface (candidate) | derived path | 3 | medium | validated: C2, H1, H2, H2 r2, M0, M1 (2 hits, 0 false) |
| S24 | ServiceOperation → APIOperation (IMPLEMENTED_BY) | registry rule | 2 | high | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (60 hits, 0 false) |
| S25 | ServiceOperation → ApplicationService (candidate) | candidate rule | 3 | high | validated: C2, H1, H2, H2 r2, M0, M1, M2 (6 hits, 0 false) |
| S26 | BehaviorQualifier → APIOperation (candidate) | derived path | 2 | high | validated: C2 (2 hits, 0 false) |
| S27 | BehaviorQualifier → DataEntity (candidate) | derived path | 4 | medium | validated: C2 (1 hits, 0 false) |
| S28 | BusinessScenario → ApplicationService (candidate) | candidate rule | 3 | medium | validated: C2 (2 hits, 0 false) |
| S29 | BusinessScenario → ApplicationComponent (candidate) | candidate rule | 3 | medium | validated: C2 (2 hits, 0 false) |
| S30 | BusinessObject → DataEntity (MAPPED_TO) | registry rule | 4 | high | validated: C1, C2, C3, H1, H2, H2 r2, M1, M2 (16 hits, 0 false) |
| S31 | BusinessObjectAttribute → DataEntity (candidate) | derived path | 4 | high | validated: C2 (4 hits, 0 false) |
| S32 | ApplicationComponent → Deployment (DEPLOYED_AS) | registry rule | 1 | high | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (23 hits, 0 false) |
| S33 | ApplicationComponent → InfrastructureComponent (DEPLOYED_ON) | registry rule | 1 | high | validated with findings: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (20 hits, 1 false — fixed) |
| S34 | ApplicationComponent → Node (candidate) | conditional rule | 1 | low | validated: C3 (2 hits, 0 false) |
| S35 | ApplicationComponent → Device (candidate) | institution only | 1 | low | validated: C3 (1 hits, 0 false) |
| S37 | ApplicationComponent → CommunicationNetwork (candidate) | institution only | 1 | low | validated: C3 (2 hits, 0 false) |
| S38 | ApplicationComponent → Path (candidate) | institution only | 1 | low | validated: C3 (1 hits, 0 false) |
| S39 | ApplicationComponent → Artifact (candidate) | conditional rule | 1 | medium | validated: C3 (2 hits, 0 false) |
| S40 | ApplicationComponent → DeploymentEnvironment (candidate) | derived path | 3 | high | validated: C3, H1, H2, H2 r2, M0, M1 (2 hits, 0 false) |
| S41 | ApplicationService → TechnologyService (candidate) | conditional rule | 1 | medium | validated: C3, H1, H2, H2 r2, M1, M2 (3 hits, 0 false) |
| S42 | ApplicationService → TechnologyInterface (candidate) | derived path | 3 | low | validated with findings: C3 (2 hits, 1 false — fixed) |
| S43 | ApplicationInterface → TechnologyInterface (candidate) | institution only | 1 | low | validated: C3 (2 hits, 0 false) |
| S44 | ApplicationInterface → TechnologyService (candidate) | institution only | 1 | low | validated: C3 (2 hits, 0 false) |
| S45 | ApplicationFunction → TechnologyService (candidate) | conditional rule | 1 | medium | validated: C3, M1 (2 hits, 0 false) |
| S46 | ApplicationFunction → SystemSoftware (candidate) | derived path | 3 | low | validated: C3 (3 hits, 0 false) |
| S47 | APIOperation → Deployment (candidate) | derived path | 3 | high | validated: C3, H1, H2, H2 r2, M0, M1 (6 hits, 0 false) |
| S48 | APIOperation → TechnologyInterface (candidate) | derived path | 3 | medium | validated: C3 (6 hits, 0 false) |
| S49 | DataEntity → Artifact (candidate) | conditional rule | 1 | medium | validated: C3, H1, H2, M1 (1 hits, 0 false) |
| S50 | DataEntity → SystemSoftware (candidate) | institution only | 1 | medium | validated: C3, H1, H2, H2 r2, M0, M1, M2 (3 hits, 0 false) |
| S51 | Event → TechnologyService (candidate) | institution only | 1 | low | validated: C3 (1 hits, 0 false) |
| S52 | SolutionBuildingBlock → InfrastructureComponent (candidate) | derived path | 3 | medium | validated: C3 (3 hits, 0 false) |
| S53 | SolutionBuildingBlock → Deployment (candidate) | derived path | 3 | medium | validated: C3 (2 hits, 0 false) |
| S54 | SolutionBuildingBlock → Node (candidate) | derived path | 3 | low | validated: C3 (1 hits, 0 false) |

## 5. Data requirements — the export conventions

Join keys the exports must carry for the steps to run without inference (`metamodel/export-conventions.json`). A key absent from an export is a *no proposal* for the rows that need it, reported as such — never guessed.

| ID | Entity | Key | Purpose |
|---|---|---|---|
| KA2-01 | A2.ServiceOperation | `action_term` | one of BIAN's 17 action terms |
| KA2-02 | A2.ServiceOperation | `behavior_qualifier` | qualifier name or null |
| KA2-03 | A2.ServiceOperation | `input_attributes` | list of control-record attribute names consumed |
| KA2-04 | A2.ServiceOperation | `output_attributes` | list produced |
| KA2-05 | A2.ControlRecord | `attributes` | list of attribute names (BIAN control-record make-up) |
| KA2-06 | A2.ControlRecord | `lifecycle_states` | ordered list of the record's lifecycle states (S21 reasoning; informational) |
| KA2-07 | A2.BusinessObject | `attributes` | list of BOM attribute names |
| KA2-08 | A2.BusinessScenario | `operation_sequence` | ordered list of A2.ServiceOperation ids |
| KA1-01 | A1.BusinessCapability | `description` | scope statement (schema field, not attribute) |
| KA1-02 | A1.BusinessProcess | `invokes` | list of A2.ServiceOperation ids the process steps call (optional; enables step 3 for USES_DOMAIN) |
| KA1-03 | A1.BusinessActivity | `invokes` | list of A2.ServiceOperation ids |
| KA1-04 | A1.ValueStream | `stages` | ordered list of A1.ValueStreamStage ids |
| KA1-05 | A1.BusinessObject | `attributes` | list of attribute names from the business glossary |
| KA1-06 | A1.BusinessObject | `field_aliases` | map of the bank's glossary attribute names to canonical attribute names (S12 step 4), e.g. lc_number → letter_of_credit_reference; institution data |
| KA3-01 | A3.APIOperation | `method` | HTTP method |
| KA3-02 | A3.APIOperation | `path` | resource path |
| KA3-03 | A3.APIOperation | `payload_fields` | list of request/response field names |
| KA3-04 | A3.ApplicationComponent | `deployed_on` | list of A4 platform/node ids (join key for DEPLOYED_ON, S36) |
| KA3-05 | A3.ApplicationComponent | `deployed_as` | list of A4.Deployment ids (join key for DEPLOYED_AS) |
| KA3-06 | A3.ApplicationComponent | `built_as` | list of A4.Artifact ids (S39) |
| KA3-07 | A3.ApplicationComponent | `network_zone` | A4.CommunicationNetwork id (S37) |
| KA3-08 | A3.ApplicationService | `consumes` | list of A4.TechnologyService ids (join key for S41) |
| KA3-09 | A3.DataEntity | `attributes` | list of attribute names |
| KA3-10 | A3.DataEntity | `stored_in` | list of A4 ids: A4.SystemSoftware (S50) or A4.Artifact such as an object store (S49) |
| KA3-11 | A3.DataEntity | `field_aliases` | optional map of column names to canonical attribute names; overrides the field_aliases inherited from the interfaces of components that access the entity |
| KA4-01 | A4.Deployment | `component_id` | the A3.ApplicationComponent deployed |
| KA4-02 | A4.Deployment | `environment_id` | A4.DeploymentEnvironment id |
| KA4-03 | A4.Deployment | `platform_id` | A4 platform/node id |
| KA4-04 | A4.SystemSoftware | `hosts` | list of A3.ApplicationComponent ids (alternative join key) |
| KA4-05 | A4.Node | `hosts` | list of A3.ApplicationComponent ids |
| KA2-09 | A2.ServiceDomain | `asset_type` | id of the A2.AssetType the domain manages (join key for step 2 rule 1 reverse and S17 step-4 fallback) |
| KA2-10 | A2.ServiceDomain | `functional_pattern` | id of the A2.FunctionalPattern |
| KA2-11 | A2.AssetType | `aliases` | list of tokens the institution's estate uses for this asset (join key for the step-2 boundary gate and the S17 fallback); e.g. Financial Position → balance, position, posting, ledger |
| KA2-12 | A2.BehaviorQualifier | `aliases` | list of tokens the institution's APIs use for this qualifier (step-2 check 3); e.g. Closure → close |
| KA3-12 | A3.ApplicationInterface | `field_aliases` | map of the interface's product field names to canonical attribute names (step-2 check 4, S30/S20 step 4); e.g. sender → debtor_account_reference. Institution data from interviews or contract review, never inferred |
| KA3-13 | A3.ApplicationInterface | `exposed_through` | list of A4.TechnologyInterface ids — gateway ingress, listener (S43; S44, S48 derived) |
| KA1-07 | A1.BusinessService | `inputs` | attribute names the service takes (S09: matched against operation input_attributes) |
| KA1-08 | A1.BusinessService | `outputs` | attribute names the service returns (S09: matched against output_attributes) |
| KA1-09 | A1.BusinessRequirement | `applies_to` | list of A1.BusinessProcess / A1.BusinessActivity ids the requirement constrains (S13 via S04, S14 via S06) |
| KA3-14 | A3.ApplicationFunction | `exposed_through` | list of A3.APIOperation ids the function is reached through (S18, S21 via S24) |
| KA3-15 | A3.ApplicationFunction | `consumes` | list of A4.TechnologyService ids (S45; S46 derived) |
| KA3-16 | A3.Event | `published_to` | list of A4.TechnologyService ids — broker (S51) |
| KA3-17 | A3.SolutionBuildingBlock | `components` | list of A3.ApplicationComponent ids the block aggregates (S52–S54 derived) |
| KA4-06 | A4.Device | `hosts` | list of A3.ApplicationComponent ids (S35; DEPLOYED_ON with a Device target) |
| KA4-07 | A4.CommunicationNetwork | `connects` | list of A4.Node / A4.Device ids on the network (S37 with the component's network_zone) |
| KA4-08 | A4.Path | `from` | A4 endpoint id |
| KA4-09 | A4.Path | `to` | A4 endpoint id |
| KA4-10 | A4.Path | `network` | A4.CommunicationNetwork id |
| KA4-11 | A4.Path | `carries` | list of A3.ApplicationComponent ids whose traffic uses the path (S38) |
| KA4-12 | A4.TechnologyInterface | `of_service` | A4.TechnologyService id the interface belongs to (S42, S44 derived) |
| KA4-13 | A4.TechnologyInterface | `exposes` | list of A3.ApplicationInterface ids reachable through it (S43) |
| KA4-14 | A4.Artifact | `of_component` | A3.ApplicationComponent id the artefact is a build of (S39) |

**BIAN action terms.** [SAPG] §3.2.5 Figure 14 — 17 action terms in four categories; §3.5: Retrieve maps to HTTP GET; Notify is not used in the BIAN REST mapping

## 6. The procedure — steps as requirements

The steps are specified in `docs/mapping-execution.md` §3 exactly as the executor ran them; this section states them as engine requirements. Order: A4 from data, A2 from BIAN, A3 where they meet, A1 last.

| Step | Requirement | Derives from | Validated by |
|---|---|---|---|
| REQ-P-01 Step 0 — BIAN export | Load the A2 export as BIAN structure; apply no inference to it. | RA2-*; B02–B15 | every run |
| REQ-P-02 Step 1 — data join | Fill `DEPLOYED_ON` and `DEPLOYED_AS` and the step-1 institution-only rows by exact key join (`deployed_on`, `deployed_as`, `hosts`, `component_id`/`platform_id`, `consumes`, `stored_in`, `built_as`, `network_zone`, `published_to`, `exposed_through`, `carries`); `DEPLOYED_ON` is environment-agnostic and fans out one arrow per host layer, logged under S33 / S34 / S35 by target entity. | S32, S33, S34, S35, S37–S39, S41, S43, S45, S49–S51 | M0, M1 (UAT hosting), H1, H2, C3 |
| REQ-P-03 Step 2 — REST decision procedure | For each operation × API pair: boundary **gate** (approved `REALIZED_BY`, or token gate over asset-type name and aliases against camel/snake-split names, paths, descriptions and accessed-entity names, with structural nouns on the stop list) — a gate, never a vote; then three checks, each pass / fail / neutral: action term ↔ method (17 terms; Retrieve ⇔ GET verified; the marked conventions for the rest, including Control ⇔ DELETE and Execute ⇔ POST on a qualifier sub-resource), qualifier ↔ path (qualifier aliases; a non-qualifier segment is ignored), attributes ↔ payload (≥ 50 %, ≥ 2 matched, best payload match, through field aliases). Decide: propose at band when 2 and 4 pass and 3 is not fail; one band lower with a finding when only the method fails and the API is the unique best payload match; otherwise none. Disambiguate one-to-one to a fixpoint; contention by overlap count, ratio, qualifier; ties are no proposal with both named. | S24, S26 | M0, M1 (planted Retrieve-on-POST), H1 (all POST, reverse), H2 (hostile; 0.78 → 1.00), C2 (6 of 6) |
| REQ-P-04 Step 2 — non-HTTP and systematic deviations | A non-HTTP `method` (BATCH, MQ, FILE) is *not applicable*, never forced through check 2; a deviation shared by every operation of an interface is reported once and referenced; Notify operations have no REST form and are reported against an `A3.Event` as a candidate. | S24; new_connection_candidates | H1 (batch jobs; all-POST finding once), M1 (Notify) |
| REQ-P-05 Step 3 — derivation | Close over approved arrows and this run's own step-1/2 proposals, saying which: S01 from all processes of a capability (cap = weakest input), S17 from any implemented operation (cap = strongest input; a recorded systematic deviation does not lower it; fallback A over an entity `MAPPED_TO` the domain's object; fallback B over asset aliases in paths; no description-only fallback), S07, S13–S16, S22, S23, S25, S28, S29, S40, S42 (over S43/S44 exposure, never consumption), S44, S46–S48, S52–S54. | derived_path and step-3 rows | M0 run 2, M1, H1 (module level), H2, C1, C2, C3 (S42 corrected) |
| REQ-P-06 Step 4 — structural matching | Attribute and token matching with thresholds: S30/S20/S31 one-to-one to a fixpoint at ≥ 50 % of the BIAN object's attributes; S02 as coverage of the scenario's operations by stage action terms (≥ 60 %; the asset noun is not evidence); S12 by glossary attributes through aliases; S09 by service inputs ∪ outputs (≥ 50 %, ≥ 2, one-to-one); S19 and S27 by alias tokens in entity names; S18 and S21 through `exposed_through` and the step-2 arrows; S06 by `invokes` (step 1) else name match. | step-4 rows | M0 (S02 as coverage), M1, H1, H2 (partition table kept out; qualifier claims it), C1, C2 |
| REQ-P-07 Step 5 — bounded text inference | Only for S01 when step 3 produced nothing and for the A1 side of reverse cases, and S08: count shared non-generic concepts; propose at most one domain per capability, low, when the best shares ≥ 2 and leads by ≥ 1; the candidate set is the full exported landscape (two domains count) or at least three; otherwise no proposal. | S01, S08 | H1 (four right, two refused), C1 |
| REQ-P-08 Design targets | When no export exists below a level, state *mapping ends at <level>* and, only from BIAN's container pattern, generate planned A3/A4 instances with the `DSN-*` convention, canonical REST forms, low confidence, `created_by` naming the pattern and a rationale beginning *TARGET DESIGN, not a mapping*; never a platform or a data entity; traces mark planned instances as design. | guide § Design targets; M2 case | M2 (12 of 12; boundary stated) |
| REQ-P-09 Refusal discipline | No working → no proposal. Every attempt, including suppressed pairs, failed gates and ties, is logged with its data read, rule values, decision and outcome; negatives are the measure of precision. | guide §2 | every run: zero false proposals after v0.5.4 across M1, H1, H2 ×2, M2, C1, C2 (one in C3, fixed by rule) |

## 7. Outputs, scoring and governance

| ID | Output | File | Content | Scored by |
|---|---|---|---|---|
| OUT-01 | Mapping-set records | `<uc>-proposals.json` | links between real instances, from registry rules only; `status: proposed`, plan band, typed evidence, rationale with the working | `sdmm-eval` against `<uc>-gold-mappings.json` (approved) — P / R / F1 per relationship |
| OUT-02 | Candidate reports (not part of the mapping set) | `<uc>-candidates.json` | one record per candidate / conditional / institution-only / derived row, `relationship` = plan ID | `sdmm-eval` against `<uc>-gold-candidates.json` — per plan ID |
| OUT-03 | Inference log | `<uc>-inference-log.json` | every attempt: plan ID, data read, rule values, step assigned / used, fallback, confidence predicted / given, outcome; no-proposal register; findings | the coverage table in `docs/use-case-testing.md` is regenerated from it |
| OUT-04 | Design exports | `<uc>-design-a3.json`, `-a4.json` | planned instances (M2 only) | `sdmm-graph check`; trace marks design hops |

Governance stays outside the engine: `sdmm-validate` (structure, registry, evidence, anchoring), `sdmm-diff` (lifecycle transitions, immutability of approved records; supersession via `previous_mapping_id`), impact classification per `schema/impact-rules.json` (modify, replace, retire, rehost).

## 8. Acceptance — the runs the engine must reproduce

The eleven executor runs are the acceptance test: the engine, given the same inputs, must reach the same proposals and candidate reports and score at least the same against the sealed gold (`docs/use-case-testing.md` › Results and Plan coverage).

| ID | Case | Estate | Hidden | Executor result |
|---|---|---|---|---|
| ACC-01 | E1, E2 | card-fraud-alerts, customer-onboarding | nothing (query and governance) | all checks exact |
| ACC-02 | M0 | card-fraud-alerts | 6 arrows | run 2: 6 of 6, 1 false (rule withdrawn) |
| ACC-03 | M1 | payment-initiation (68 instances) | 12 → 13 arrows, planted mismatch | 13 of 13 under the restated gold; mismatch caught |
| ACC-04 | H1 | legacy-core-ledger (87; SOAP, all POST; empty given) | 28 arrows | 28 of 28, 0 false |
| ACC-05 | H2 | acquired-fintech (116; no A1; hostile names) | 41 arrows | run 1: 32 of 41, 0 false; run 2 with aliases: 41 of 41 |
| ACC-06 | M2 | digital-lending (greenfield, no A3/A4) | 12 design arrows | 12 of 12; boundary stated |
| ACC-07 | C1, C2, C3 | trade-finance (85; one estate, three level pairs) | 19 registry + 100 candidate | 19 of 19; 100 of 101 (one fixed by rule) |

Plan coverage after the suite: 45 rows validated clean, 5 validated with findings fixed, 19 n/a by decision, 0 not exercised. Within-level structure: 131 rows enforced, 113 verified against the Archi oracle, 0 contradicted.

## 9. Verification status and open items

| ID | Item | Status |
|---|---|---|
| OPEN-01 | A2 structure and B rows | verified on public BIAN pages; `pending_release_validation` against a licensed release remains |
| OPEN-02 | A1 / A3 / A4 within-level rows | 113 verified against the open-source Archi relationship matrix (commit cited in the record); 2 TOGAF rows unverified |
| OPEN-03 | Official S rows citing ArchiMate / W135 (S34, S39, S41, S45, S49; S04, S05) | unverified: login-gated; the five ArchiMate rows can be checked against the Archi oracle next |
| OPEN-04 | API contention tie-break (step 2 clause 4) | **proposed** — chosen with a gold already seen; validated only when it decides a pair on an unseen gold |
| OPEN-05 | One-author caveat | all estates and gold authored by SDMM; one blind case (data and gold by someone else) retires it |
| OPEN-06 | Confidence bands | assigned by hand and calibrated conservative (every low inference confirmed); could be re-derived from the logs' predicted-vs-observed outcomes |

## 10. Requirements index

33 requirements. Groups: V vocabulary, S structure, M mapping model, D data, P procedure, O outputs, A acceptance.

| ID | Requirement | Derives from | Validated by |
|---|---|---|---|
| REQ-V-01 | Resolve every instance type in an export to a catalogue entity, through `extends` (is-a) and the registry's type aliases; reject unknown types, instantiated abstract entities and artefacts used as mapping endpoints. | entity catalogue; `schema/relationship-types.json` type_aliases | E1, E2 (every example export loads); relationships test T4.6 |
| REQ-S-01 | Accept a within-level relationship only when its (source entity, kind, target entity) matches a constraint row for that level through inheritance, or its kind is `association`; report the offending triple and the level's basis otherwise. | RA1-01 … RA4-36 | relationships test T4.1–T4.9 (131 accepted, 25 rejected); `examples/reference-structure` (129 rows on committed data) |
| REQ-S-02 | Walk within-level part-whole links (composition, aggregation) in traces and derivations — part → whole downstream, whole → parts upstream — and never assignment or realization. | rows of kind composition / aggregation; `sdmm-graph trace --follow-composition` | H1 (module → ledger → platform); C3 (API → interface → component → deployment → environment) |
| REQ-S-03 | Treat the three A2 artefact rows as provenance only: Wireframe, Semantic API and BOM artefacts are never instantiated and never mapping endpoints. | RA2-15, RA2-16, RA2-17 (enforceable=false) | relationships test T4 (not testable by construction) |
| REQ-M-01 | Emit registry proposals only for the nine relationship types, with the record fields the schema requires, at status `proposed`, with `confidence` as the plan's band and `evidence` typed against `required_evidence`. | schema/relationship-types.json; schema/mapping.schema.json | every run: `sdmm-validate --strict` on each proposal file |
| REQ-M-02 | S01: propose `SUPPORTED_BY` A1.BusinessCapability → A2.ServiceDomain at step 3 (medium); data: approved USES_DOMAIN for the capability's processes (step 3); fallback step 5 requires the full exported A2 landscape or at least 3 candidate domains — with fewer, no proposal (single-candidate inference is vacuous) | S01 | validated with findings: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (4 hits, 1 false — fixed) |
| REQ-M-03 | S02: propose `ALIGNED_TO` A1.ValueStream → A2.BusinessScenario at step 4 (medium); data: A1.ValueStream attributes.stages (ordered) and A2.BusinessScenario attributes.operation_sequence; scored as coverage of the scenario's operations by stages, not a stage count | S02 | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (1 hits, 0 false) |
| REQ-M-04 | S04: propose `USES_DOMAIN` A1.BusinessProcess → A2.ServiceDomain at step 3 (medium); data: A1.BusinessProcess (or its activities) attributes.invokes naming A2.ServiceOperation ids; otherwise step 4 verb+noun match of step text to operation names. A process exported without activities may be matched directly to operations by the S06 rule (E1 finding) | S04 | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (1 hits, 0 false) |
| REQ-M-05 | S12: propose `ALIGNED_TO` A1.BusinessObject → A2.BusinessObject at step 4 (medium); data: A1.BusinessObject attributes.attributes; A2.BusinessObject attributes.attributes (BOM) | S12 | validated: C1, H1, H2, H2 r2, M1 (2 hits, 0 false) |
| REQ-M-06 | S17: propose `REALIZED_BY` A2.ServiceDomain → A3.ApplicationComponent at step 3 (high); data: approved or step-2 IMPLEMENTED_BY instances plus A3 structure (component composes interface; interface composes API operations) (step 3; confidence capped at the weakest input's band); fallback step 4: A2.ServiceDomain.attributes.asset_type's name in the component's API paths / data entity names; description comparison alone is step 5 | S17 | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (20 hits, 0 false) |
| REQ-M-07 | S24: propose `IMPLEMENTED_BY` A2.ServiceOperation → A3.APIOperation at step 2 (high); data: A2.ServiceOperation attributes.action_term / behavior_qualifier / input_attributes / output_attributes; A2.ControlRecord attributes.attributes; A3.APIOperation attributes.method / path / payload_fields (export-conventions.json); A2.ServiceDomain.attributes.asset_type for rule 1 in reverse cases; A2.AssetType.attributes.aliases for the token boundary gate in reverse cases; A2.BehaviorQualifier.attributes.aliases and A3.ApplicationInterface.attributes.field_aliases for product-named estates | S24 | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (60 hits, 0 false) |
| REQ-M-08 | S30: propose `MAPPED_TO` A2.BusinessObject → A3.DataEntity at step 4 (high); data: A2.BusinessObject attributes.attributes; A3.DataEntity attributes.attributes; data catalogue export where available | S30 | validated: C1, C2, C3, H1, H2, H2 r2, M1, M2 (16 hits, 0 false) |
| REQ-M-09 | S32: propose `DEPLOYED_AS` A3.ApplicationComponent → A4.Deployment at step 1 (high); data: A4.Deployment instances with attributes.component_id / environment_id / platform_id, or A3.ApplicationComponent attributes.deployed_as (export-conventions.json) | S32 | validated: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (23 hits, 0 false) |
| REQ-M-10 | S33: propose `DEPLOYED_ON` A3.ApplicationComponent → A4.InfrastructureComponent at step 1 (high); data: A3.ApplicationComponent attributes.deployed_on, or A4 platform/node attributes.hosts (export-conventions.json) | S33 | validated with findings: C1, C2, C3, H1, H2, H2 r2, M0, M1, M2 (20 hits, 1 false — fixed) |
| REQ-M-11 | report (candidate rule): S20, S21, S25, S28, S29 — each with the working and the plan band, in `<uc>-candidates.json` with `relationship` = plan ID. | S20, S21, S25, S28, S29 | validated |
| REQ-M-12 | report when its data is present (conditional rule): S34, S39, S41, S45, S49 — each with the working and the plan band, in `<uc>-candidates.json` with `relationship` = plan ID. | S34, S39, S41, S45, S49 | validated |
| REQ-M-13 | report from the export key (institution-only): S06, S08, S09, S13, S14, S18, S19, S35, S37, S38, S43, S44, S50, S51 — each with the working and the plan band, in `<uc>-candidates.json` with `relationship` = plan ID. | S06, S08, S09, S13, S14, S18, S19, S35, S37, S38, S43, S44, S50, S51 | validated |
| REQ-M-14 | compute as a closure and report (derived path): S03, S07, S15, S16, S22, S23, S26, S27, S31, S40, S42, S46, S47, S48, S52, S53, S54 — each with the working and the plan band, in `<uc>-candidates.json` with `relationship` = plan ID. | S03, S07, S15, S16, S22, S23, S26, S27, S31, S40, S42, S46, S47, S48, S52, S53, S54 | validated; validated with findings |
| REQ-D-01 | Read every join key listed in §5 by exact name; treat a missing key as *no proposal* for the rows that depend on it, recorded in the no-proposal register with the key named. | metamodel/export-conventions.json | E1 (missing `deployed_on` found and added), M1–C3 (keys present) |
| REQ-D-02 | Read institution aliases as data, never invent them: asset-type aliases (boundary gate), behaviour-qualifier aliases (check 3), interface and data-entity field aliases (check 4, S30/S20), business-object glossary aliases (S12). | A2.AssetType.aliases; A2.BehaviorQualifier.aliases; A3.ApplicationInterface.field_aliases; A3.DataEntity.field_aliases; A1.BusinessObject.field_aliases | H1 (token gate), H2 run 1 → run 2 (recall 0.78 → 1.00 with aliases supplied), C1 |
| REQ-P-01 | Step 0 — BIAN export: Load the A2 export as BIAN structure; apply no inference to it. | RA2-*; B02–B15 | every run |
| REQ-P-02 | Step 1 — data join: Fill `DEPLOYED_ON` and `DEPLOYED_AS` and the step-1 institution-only rows by exact key join (`deployed_on`, `deployed_as`, `hosts`, `component_id`/`platform_id`, `consumes`, `stored_in`, `built_as`, `network_zone`, `published_to`, `exposed_through`, `carries`); `DEPLOYED_ON` is environment-agnostic and fans out one arrow per host layer, logged under S33 / S34 / S35 by target entity. | S32, S33, S34, S35, S37–S39, S41, S43, S45, S49–S51 | M0, M1 (UAT hosting), H1, H2, C3 |
| REQ-P-03 | Step 2 — REST decision procedure: For each operation × API pair: boundary **gate** (approved `REALIZED_BY`, or token gate over asset-type name and aliases against camel/snake-split names, paths, descriptions and accessed-entity names, with structural nouns on the stop list) — a gate, never a vote; then three checks, each pass / fail / neutral: action term ↔ method (17 terms; Retrieve ⇔ GET verified; the marked conventions for the rest, including Control ⇔ DELETE and Execute ⇔ POST on a qualifier sub-resource), qualifier ↔ path (qualifier aliases; a non-qualifier segment is ignored), attributes ↔ payload (≥ 50 %, ≥ 2 matched, best payload match, through field aliases). Decide: propose at band when 2 and 4 pass and 3 is not fail; one band lower with a finding when only the method fails and the API is the unique best payload match; otherwise none. Disambiguate one-to-one to a fixpoint; contention by overlap count, ratio, qualifier; ties are no proposal with both named. | S24, S26 | M0, M1 (planted Retrieve-on-POST), H1 (all POST, reverse), H2 (hostile; 0.78 → 1.00), C2 (6 of 6) |
| REQ-P-04 | Step 2 — non-HTTP and systematic deviations: A non-HTTP `method` (BATCH, MQ, FILE) is *not applicable*, never forced through check 2; a deviation shared by every operation of an interface is reported once and referenced; Notify operations have no REST form and are reported against an `A3.Event` as a candidate. | S24; new_connection_candidates | H1 (batch jobs; all-POST finding once), M1 (Notify) |
| REQ-P-05 | Step 3 — derivation: Close over approved arrows and this run's own step-1/2 proposals, saying which: S01 from all processes of a capability (cap = weakest input), S17 from any implemented operation (cap = strongest input; a recorded systematic deviation does not lower it; fallback A over an entity `MAPPED_TO` the domain's object; fallback B over asset aliases in paths; no description-only fallback), S07, S13–S16, S22, S23, S25, S28, S29, S40, S42 (over S43/S44 exposure, never consumption), S44, S46–S48, S52–S54. | derived_path and step-3 rows | M0 run 2, M1, H1 (module level), H2, C1, C2, C3 (S42 corrected) |
| REQ-P-06 | Step 4 — structural matching: Attribute and token matching with thresholds: S30/S20/S31 one-to-one to a fixpoint at ≥ 50 % of the BIAN object's attributes; S02 as coverage of the scenario's operations by stage action terms (≥ 60 %; the asset noun is not evidence); S12 by glossary attributes through aliases; S09 by service inputs ∪ outputs (≥ 50 %, ≥ 2, one-to-one); S19 and S27 by alias tokens in entity names; S18 and S21 through `exposed_through` and the step-2 arrows; S06 by `invokes` (step 1) else name match. | step-4 rows | M0 (S02 as coverage), M1, H1, H2 (partition table kept out; qualifier claims it), C1, C2 |
| REQ-P-07 | Step 5 — bounded text inference: Only for S01 when step 3 produced nothing and for the A1 side of reverse cases, and S08: count shared non-generic concepts; propose at most one domain per capability, low, when the best shares ≥ 2 and leads by ≥ 1; the candidate set is the full exported landscape (two domains count) or at least three; otherwise no proposal. | S01, S08 | H1 (four right, two refused), C1 |
| REQ-P-08 | Design targets: When no export exists below a level, state *mapping ends at <level>* and, only from BIAN's container pattern, generate planned A3/A4 instances with the `DSN-*` convention, canonical REST forms, low confidence, `created_by` naming the pattern and a rationale beginning *TARGET DESIGN, not a mapping*; never a platform or a data entity; traces mark planned instances as design. | guide § Design targets; M2 case | M2 (12 of 12; boundary stated) |
| REQ-P-09 | Refusal discipline: No working → no proposal. Every attempt, including suppressed pairs, failed gates and ties, is logged with its data read, rule values, decision and outcome; negatives are the measure of precision. | guide §2 | every run: zero false proposals after v0.5.4 across M1, H1, H2 ×2, M2, C1, C2 (one in C3, fixed by rule) |
| REQ-O-01 | Write the three output files in the shapes above; never write `approved` (except rules an architect has declared auto-approved); never edit an existing mapping set; proposals must pass `sdmm-validate --strict` with draft warnings only. | guide §4, §4b, §4c | every run |
| REQ-O-02 | Log every attempt, not only proposals: the inference log is the evidence base for the coverage table and for confidence calibration. | guide §4b | eleven logs, 812+ attempts |
| REQ-A-01 | Reproduce every executor run from the committed inputs with precision ≥ the executor's and recall ≥ the executor's on each sealed gold; any difference is a finding on the engine or on the guide. | docs/use-case-testing.md | baseline established by the eleven runs |
| REQ-A-02 | Validate every example export and `examples/reference-structure` clean, and reject the relationships-test probes (reversed, mistyped, abstract, cross-level, uncatalogued). | §3 rows; relationships test T4 | Phase 1 probes; CI |

