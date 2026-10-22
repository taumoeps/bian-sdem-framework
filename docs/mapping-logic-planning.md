# Mapping logic — planning (v0.6)

**Status:** planning. Nothing in this document is implemented. v0.4 delivered the structural logic (what a mapping *may* be); v0.5 delivered the harness (how an engine is scored). §1 is the Official BIAN-Only Mapping (what BIAN itself defines), §2 is the Official BIAN with Support Framework Mappings (what ArchiMate, TOGAF and W135 add where BIAN stops — every claim source-verified before use), and §3 plans the semantic logic: how software will *propose* what a mapping *should* be, for an architect to accept or reject.

**Ground rule, restated:** an engine's output is always `status: proposed`. The validator refuses approval without a named reviewer and date. Nothing below changes that.

---

## 1. Official BIAN-Only Mapping

What BIAN itself defines: its entities (§1.1), the mappings it defines between them (§1.2), and what it does not map (§1.3). Everything is taken from BIAN's public release notes for Service Landscape 13.0 and 14.0 and the Semantic API Practitioner Guide v8.1, with section and page references; no BIAN text is reproduced beyond short attributed phrases.

### 1.1 BIAN entities

All 44 catalogue entities. **Covered by BIAN** is "Yes" when BIAN defines the concept and publishes its instances, "No" otherwise; uncovered entities show "n/a". The BIAN entities (16) are the nodes of BIAN's own mapping model, described in §1.2 and §1.3.

Sources: **[SL14]** Service Landscape 14.0 InSite portal · **[RN14]** v14.0 release notes · **[SAPG]** Semantic API Practitioner Guide v8.1 · **[APIP]** BIAN Semantic API portal.


#### A1 — Business Architecture — 1 of 10 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source |
|---|---|---|---|
| `A1.BusinessCapability` | Yes | Business Capability (BCM) | [SL14] Business Capability Map |
| `A1.ValueStream` | No | n/a | n/a |
| `A1.ValueStreamStage` | No | n/a | n/a |
| `A1.BusinessProcess` | No | n/a | n/a |
| `A1.BusinessActivity` | No | n/a | n/a |
| `A1.BusinessService` | No | n/a | n/a |
| `A1.BusinessActor` | No | n/a | n/a |
| `A1.BusinessRole` | No | n/a | n/a |
| `A1.BusinessObject` | No | n/a | n/a |
| `A1.BusinessRequirement` | No | n/a | n/a |

#### A2 — Service Domain Architecture — 15 of 15 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source |
|---|---|---|---|
| `A2.BusinessArea` | Yes | Business Area | [SL14] Service Landscape views |
| `A2.BusinessDomain` | Yes | Business Domain | [SL14] Service Landscape views |
| `A2.ServiceDomain` | Yes | Service Domain | [SL14] per-domain pages; [SAPG] §2.4–2.5, §3.1–3.2 |
| `A2.FunctionalPattern` | Yes | Functional Pattern | [SL14] MetaModel Overview; [SAPG] §3.2.1 |
| `A2.AssetType` | Yes | Asset Type | [SL14] MetaModel Overview; [SAPG] §3.2.2 |
| `A2.ControlRecord` | Yes | Control Record | [SL14] Control Record Model Overview; [SAPG] §3.2.3 |
| `A2.ServiceGroup` | Yes | Service Group | [SL14] MetaModel Overview |
| `A2.ServiceOperation` | Yes | Service Operation | [SL14] per-domain operations with I/O parameters; [SAPG] §3.2.5 |
| `A2.BehaviorQualifier` | Yes | Behavior Qualifier | [SL14] MetaModel Overview; [SAPG] §3.2.4 |
| `A2.BusinessScenario` | Yes | Business Scenario | [SL14] Business Scenarios; [SAPG] §3.3 |
| `A2.BusinessObject` | Yes | Business Object (BOM) | [SL14] Business Object Model Overview; [SAPG] §3.2.7 |
| `A2.BusinessObjectAttribute` | Yes | Business Object attribute | [SL14] Business Object Model Overview |
| `A2.BOMModel` *(artefact)* | Yes | Business Object Model | [SL14] Business Object Model Overview |
| `A2.Wireframe` *(artefact)* | Yes | Wireframe | [SL14] Wireframes Overview; [SAPG] §3.4 |
| `A2.SemanticAPI` *(artefact)* | Yes | Semantic API | [APIP]; [SAPG] §3.5 |

#### A3 — Application Architecture — 0 of 8 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source |
|---|---|---|---|
| `A3.ApplicationComponent` | No | n/a | n/a |
| `A3.ApplicationService` | No | n/a | n/a |
| `A3.ApplicationInterface` | No | n/a | n/a |
| `A3.ApplicationFunction` | No | n/a | n/a |
| `A3.APIOperation` | No | n/a | n/a |
| `A3.DataEntity` | No | n/a | n/a |
| `A3.Event` | No | n/a | n/a |
| `A3.SolutionBuildingBlock` | No | n/a | n/a |

#### A4 — Technology Architecture — 0 of 11 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source |
|---|---|---|---|
| `A4.InfrastructureComponent` *(abstract)* | No | n/a | n/a |
| `A4.Deployment` | No | n/a | n/a |
| `A4.DeploymentEnvironment` | No | n/a | n/a |
| `A4.Node` | No | n/a | n/a |
| `A4.Device` | No | n/a | n/a |
| `A4.SystemSoftware` | No | n/a | n/a |
| `A4.TechnologyService` | No | n/a | n/a |
| `A4.TechnologyInterface` | No | n/a | n/a |
| `A4.CommunicationNetwork` | No | n/a | n/a |
| `A4.Path` | No | n/a | n/a |
| `A4.Artifact` | No | n/a | n/a |

**Totals: 16 of 44 entities covered by BIAN** — one at A1, all fifteen at A2, none at A3, none at A4.

### 1.2 Official BIAN Only Mapping

The relationships BIAN itself defines among its sixteen entities — its own mapping model. All are within the Service Domain Architecture (A2) except the first, which is the only BIAN relationship reaching A1 and is unpublished.

| # | From | Mapping | To | What it says | Source |
|---|---|---|---|---|---|
| 1 | `A1.BusinessCapability` | aligns to | `A2.ServiceDomain` | **Unpublished** — mapped by the BCM working group in 2024, "not yet documented in the BIAN BiZZdesign repository" | [RN13] §3, [RN14] §3 |
| 2 | `A2.BusinessArea` | contains | `A2.BusinessDomain` | The landscape hierarchy, top level | [SL14] Service Landscape views |
| 3 | `A2.BusinessDomain` | contains | `A2.ServiceDomain` | Each Service Domain sits in exactly one Business Domain | [SL14] Service Landscape views |
| 4 | `A2.ServiceDomain` | applies | `A2.FunctionalPattern` | Every domain applies one generic behaviour pattern (e.g. Fulfil, Track, Analyse) | [SL14] MetaModel Overview; [SAPG] §3.2.1 |
| 5 | `A2.ServiceDomain` | manages | `A2.AssetType` | Every domain manages one class of asset through its lifecycle | [SL14] MetaModel Overview; [SAPG] §3.2.2 |
| 6 | `A2.ServiceDomain` | governs | `A2.ControlRecord` | Every domain has one control record: the lifecycle state of its pattern applied to its asset | [SL14] Control Record Model; [SAPG] §3.2.3 |
| 7 | `A2.ControlRecord` | is partitioned by | `A2.BehaviorQualifier` | Qualifiers divide the control record into sub-partitions of equivalent operational properties | [SL14] MetaModel Overview; [SAPG] §3.2.4 |
| 8 | `A2.ControlRecord` | attributes typed by | `A2.BusinessObject` / `A2.BusinessObjectAttribute` | Control record attributes draw on the Business Object Model; rationalised together in 14.0 | [SL14] BOM Overview; [RN14] §1.3 |
| 9 | `A2.ServiceDomain` | offers | `A2.ServiceGroup` | Operations are grouped per domain | [SL14] MetaModel Overview |
| 10 | `A2.ServiceGroup` | contains | `A2.ServiceOperation` | Each operation belongs to one group | [SL14] MetaModel Overview |
| 11 | `A2.ServiceOperation` | acts on | `A2.ControlRecord` (or a qualifier partition) | An operation's action term says what it does to the control record instance; attributes are filtered by action term for input/output | [SAPG] §3.2.5, §3.5 |
| 12 | `A2.ServiceDomain` | connects to | `A2.ServiceDomain` | First-order connections: which domains a domain typically exchanges with | [SAPG] §3.2.6 |
| 13 | `A2.BusinessScenario` | sequences | `A2.ServiceOperation` across domains | A scenario is an illustrative sequence of operation calls between domains (UML sequence diagram) | [SL14] Business Scenarios; [SAPG] §3.3 |
| 14 | `A2.Wireframe` | depicts | `A2.ServiceDomain` connections | Archetypal interaction pattern among a set of domains | [SL14] Wireframes Overview; [SAPG] §3.4 |
| 15 | `A2.SemanticAPI` | derived from | `A2.ServiceDomain` + its `A2.ServiceOperation`s | The reference API is the domain's operations in REST form | [APIP]; [SAPG] §3.5 |

Rows 2–15 are what `metamodel/level-relationships.json` encodes as the fixed A2 structure. Row 1 is the one BIAN mapping SDMM's `SUPPORTED_BY` arrow would rely on, and it does not exist publicly.

### 1.3 What BIAN does not map

| Would-be mapping | Status | Source |
|---|---|---|
| Business Capability → Service Domain | Work in progress, unpublished. Confirmed still in progress in June 2026: a working group is developing "an L1/L2 Business Capability taxonomy, a Value Stream catalogue and stage definitions, and the alignment of stages to Business Domains and orchestrating Service Domains" | [RN13] §3, [RN14] §3, [WQA26] |
| Value stream / stage → Business Domain and Service Domain | Not yet modelled. **Announced intent** (June 2026): value streams and stages will enter the BIAN metamodel, with each stage mapped to Business Domain(s) and a primary orchestrating Service Domain. When published, this becomes BIAN's first A1→A2 mapping and SDMM's `ALIGNED_TO` / `USES_DOMAIN` arrows gain a BIAN basis | [WQA26] |
| A bank's business process → Service Domain / operation | Never in scope; scenarios are illustrative, not a bank's processes | [SAPG] §3.3 |
| A bank's application → Service Domain | Method only (wireframe functional partition, legacy wrapping); BIAN holds no application data | [SAPG] §3.4, §4.3.1 |
| Anything → infrastructure or deployment | "does not assume or impose any physical properties"; implementation guidance only (§4.1–4.3) | [SAPG] §4.2.3 p. 87, Figure 34 p. 90 |

**Summary: BIAN's mapping model is 15 relationships among its own entities, 14 of them inside A2. It publishes nothing from A1 to A2 (the capability mapping is unfinished), nothing to a bank's applications beyond a method, and nothing to physical infrastructure.**

### 1.4 Consequences for the engine design

1. **A2 is the anchor.** It is the only level whose vocabulary *and instances* can be sourced publicly (with an institution's licence to use them). Every A1→A2 and A2→A3 inference is a comparison *against* A2 text. Populating a rich A2 level model from the portal — descriptions, scenarios, operations, control-record attributes — is the first engineering task, and it is an export, not an inference.

2. **The capability boundary has no BIAN answer.** Despite what our earlier provenance assumed, there is no published BCM↔Service Domain alignment to look up. An engine must infer it, and that inference carries the most risk of a plausible-but-wrong proposal. It gets the lowest default confidence and the strongest evidence requirement (`domain_scope_assessment` is already a required evidence kind for `SUPPORTED_BY`).

3. **The API boundary has the most mechanics.** BIAN's REST mapping gives action terms, resource archetypes and HTTP methods. An engine can be *rule-based* here, and its proposals can carry specific findings. Highest default confidence.

4. **The infrastructure boundary is text-free, but not pattern-free.** `DEPLOYED_ON` / `DEPLOYED_AS` come from deployment data, never from descriptions. The engine needs a structural source: a `relationships` entry in the A4 export that says which artefact runs where, or an attribute on the A3 instance naming its deployment target. BIAN's implementation guidance (§4.1–4.3) supplies a *prior* — a domain-aligned component is expected to deploy as a discrete container — which can raise confidence when the data agrees with the pattern, but never substitutes for the data.

5. **Existing approved mappings are the best evidence of all.** "Domain X is realised by application Y" makes "operation X.op is implemented by Y's API" far more likely. The engine should always read the federated graph before reading any description.

### 1.5 Corrections to the repository arising from this review

- `docs/reference-architecture-provenance.md`, the README and the v0.4 spec cite a "BIAN BCM *Statement of Alignment with the Service Landscape* (2023)" PDF. That URL returns 404 and BIAN's release notes describe the alignment as unfinished and unpublished. The citation is replaced by the v13 and v14 release notes, and `A1.BusinessCapability` keeps `evidence_status: interpreted_from_official_source` with that basis.
- The registry's `SUPPORTED_BY` and `ALIGNED_TO` (value stream) rules carry `authority: bian_alignment_guidance`. That remains correct — BIAN *intends* to provide this guidance and the BCM exists — but the planning assumption that an engine could consult a published alignment is withdrawn.

---

## 2. Official BIAN with Support Framework Mapping

**Status:** merged from `SDMM_Reference_Architecture_Entity_Mappings_A1_A4.md` (22 October 2026). **Step one — done in §2.6 — is to confirm each claimed mapping against its stated source before anything is changed.** A *Verification* column has been added to every row of §2.3 and §2.4 with the result. Analysis of what to adopt follows in §2.7. §1 established that BIAN's published mapping model stops at A2. This section inventories what the other reference frameworks — ArchiMate 3.2, TOGAF 10 and The Open Group's W135 (TOGAF–BIAN integration, 2013) — supply for the links BIAN leaves open, pair by pair, with a conservative statement of how official each contribution is.

### 2.1 Purpose

Three frameworks can fill gaps, in different ways:

| Framework | What it can supply | What it cannot |
|---|---|---|
| **ArchiMate 3.2** | Cross-layer *relationship semantics* between its own native elements (Business ↔ Application ↔ Technology: serving, realization, assignment, access), with normative allowed-relationship tables | Any correspondence between a BIAN instance and a bank's instance; BIAN entities are not ArchiMate elements |
| **TOGAF 10** | Architecture-content guidance: building blocks (ABB/SBB), content metamodel, how layers relate in a method | A fixed BIAN-to-SDMM element correspondence |
| **W135** (The Open Group, 2013) | The one published attempt to integrate TOGAF with the BIAN Service Landscape — scenario/process analysis, application overlay | Currency: it predates BIAN 14.0 and TOGAF 10; informational, not a conformance mapping |

Additional source key for this section: **[W135]** The Open Group White Paper W135, *Integrating the TOGAF® Standard with the BIAN Service Landscape*, Paul Bonnie, Thomas Obitz and the TOGAF–BIAN Collaboration Work Group, 22 October 2013, 43 pp., supersedes W120 (13 February 2012); written for BIAN Service Landscape 2.0 — https://publications.opengroup.org/w135 (free, **login required to download**)

### 2.2 Status vocabulary — read this before the tables

- **BIAN internal only:** BIAN officially defines an A2 structural or behavioural relationship, but that is **not** an official mapping to A1 or A3.
- **Guidance only:** an official publication discusses alignment, but does **not** supply a definitive instance-level or exact entity-type crosswalk.
- **ArchiMate native relationship support:** the modelling language defines cross-layer relationship semantics for **native ArchiMate elements**, subject to its normative relationship constraints. It does **not** map BIAN domain instances to a bank's application instances.
- **Not officially mapped:** no specific published official mapping for the SDMM pair was established in this review. This does not prove no publication exists.
- **BIAN artefact only:** the artefact is official evidence but is not a mapping endpoint.
- **TOGAF guidance only:** TOGAF supplies architecture-content guidance, not a fixed BIAN-to-SDMM element correspondence.

An entity can be **officially defined** without any **official cross-standard mapping** to another entity. An official *relationship type* is not a published list of *mapped instances*. Every adjacent-level target below is a **candidate mapping endpoint**, not an assertion that the two instances always match.

### 2.3 Candidate adjacent-level pairs — exhaustive for the documented set

It lists **every adjacent-level entity pairing identified in the entity-by-entity guidance**, including potential connections that **have no official mapping** and pairs **not supported by the current SDMM registry**. It is exhaustive **for the documented candidate set**, *not* every mathematically possible pair of the 41 entities, and not a claim that an arbitrary pair is semantically valid.

**Official coverage:** “ArchiMate modelling relationship” means the standard provides relevant relation semantics for its own native concepts, **not** a certified BIAN–ArchiMate correspondence and not necessarily a permitted exact SDMM pair. “Guidance only” means published method, **not** an exact entity crosswalk. “No verified official mapping” includes plausible but unverified candidate pairs. Neither implies a bank-specific mapping instance has been published. Only `SUPPORTED_BY`, `ALIGNED_TO`, `USES_DOMAIN`, `REALIZED_BY`, `IMPLEMENTED_BY`, `MAPPED_TO`, `DEPLOYED_AS`, `DEPLOYED_ON` are presently in the appropriate adjacent-level SDMM registry (including two different `ALIGNED_TO` types).

#### A1 → A2 — 14 candidate entity pairs

| Source entity | Target entity | Official mapping coverage | Current SDMM rule | Mapping guidance / caveat  Verification (this review) |
|---|---|---|---|---|---|
| `A1.BusinessCapability` | `A2.ServiceDomain` | **Official guidance only; no exact cross-standard entity pair** | `SUPPORTED_BY` | BIAN BCM alignment; v14 crosswalk not verified/published | **Verified as *intent only*** — [RN14] §3, [WQA26]: mapping unpublished |
| `A1.ValueStream` | `A2.BusinessScenario` | **SDMM mapping only; no official equivalent** | `ALIGNED_TO` | Value Stream→scenario is SDMM-specific | n/a — SDMM definition, no external claim |
| `A1.ValueStreamStage` | `A2.BusinessScenario` | **No verified official cross-standard mapping** | Not implemented | Proposed stage→scenario interpretation | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessProcess` | `A2.ServiceDomain` | **Official guidance only; no exact cross-standard entity pair** | `USES_DOMAIN` | Process/domain matching is SDMM-specific; W135 scenario methodology | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A1.BusinessProcess` | `A2.BusinessScenario` | **Official guidance only; no exact cross-standard entity pair** | Not implemented | W135 process/scenario guidance, not a direct prescribed correspondence | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A1.BusinessActivity` | `A2.ServiceOperation` | **No verified official cross-standard mapping** | Not implemented | Activity-level candidate mappings | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessActivity` | `A2.ServiceDomain` | **No verified official cross-standard mapping** | Not implemented | Activity-level candidate mappings | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessService` | `A2.ServiceDomain` | **No verified official cross-standard mapping** | Not implemented | No published equivalence for this SDMM pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessService` | `A2.ServiceOperation` | **No verified official cross-standard mapping** | Not implemented | No published equivalence for this SDMM pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessActor` | `A2.BusinessScenario` | **No verified official cross-standard mapping** | Not implemented | Actor participation needs bank evidence | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessRole` | `A2.BusinessScenario` | **No verified official cross-standard mapping** | Not implemented | Role participation needs bank evidence | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessObject` | `A2.BusinessObject` | **Official guidance only; no exact cross-standard entity pair** | `ALIGNED_TO` | BOM semantic alignment; matching not predefined | **Verified as target only** — [SL14] BOM is published; no A1→A2 mapping method |
| `A1.BusinessRequirement` | `A2.ServiceDomain` | **No verified official cross-standard mapping** | Not implemented | Requirement traceability needs local design | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A1.BusinessRequirement` | `A2.ServiceOperation` | **No verified official cross-standard mapping** | Not implemented | Requirement traceability needs local design | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |

#### A2 → A3 — 17 candidate entity pairs

| Source entity | Target entity | Official mapping coverage | Current SDMM rule | Mapping guidance / caveat  Verification (this review) |
|---|---|---|---|---|---|
| `A2.BusinessArea` | `A3.ApplicationComponent` | **No verified official cross-standard mapping** | Not implemented | Indirect only via A2.BusinessDomain and A2.ServiceDomain | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.BusinessDomain` | `A3.ApplicationComponent` | **No verified official cross-standard mapping** | Not implemented | Indirect only via A2.ServiceDomain | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.ServiceDomain` | `A3.ApplicationComponent` | **Official guidance only; no exact cross-standard entity pair** | `REALIZED_BY` | BIAN overlay guidance; bank-specific concrete allocation | **Verified** — [SAPG] §3.4 p. 52 (functional partition), §4.3.1 p. 91 |
| `A2.FunctionalPattern` | `A3.ApplicationFunction` | **No verified official cross-standard mapping** | Not implemented | Classification is official within BIAN, not cross-standard | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.AssetType` | `A3.DataEntity` | **No verified official cross-standard mapping** | Not implemented | Business asset meaning may inform data design | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.ControlRecord` | `A3.DataEntity` | **Official guidance only; no exact cross-standard entity pair** | Not implemented | BIAN logical design guidance, not fixed pairing | **Verified** — [SAPG] §4.2.2 pp. 80–87 (logical design extensions) |
| `A2.ControlRecord` | `A3.ApplicationFunction` | **Official guidance only; no exact cross-standard entity pair** | Not implemented | BIAN logical design guidance, not fixed pairing | **Verified** — [SAPG] §4.2.2 pp. 80–87 (logical design extensions) |
| `A2.ServiceGroup` | `A3.ApplicationService` | **No verified official cross-standard mapping** | Not implemented | ServiceGroup→ServiceOperation official only within BIAN | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.ServiceGroup` | `A3.ApplicationInterface` | **No verified official cross-standard mapping** | Not implemented | ServiceGroup→ServiceOperation official only within BIAN | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.ServiceOperation` | `A3.APIOperation` | **Official guidance only; no exact cross-standard entity pair** | `IMPLEMENTED_BY` | BIAN Semantic API/implementation alignment | **Verified** — [SAPG] §3.5 pp. 52–55 (REST mapping); [APIP] |
| `A2.ServiceOperation` | `A3.ApplicationService` | **Official guidance only; no exact cross-standard entity pair** | Not implemented | Service allocation requires local mapping | **Verified** — [SAPG] §3.5 p. 52 (operations = program interfaces of the application boundary) |
| `A2.BehaviorQualifier` | `A3.APIOperation` | **No verified official cross-standard mapping** | Not implemented | No verified exact cross-standard qualifier bridge | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.BehaviorQualifier` | `A3.DataEntity` | **No verified official cross-standard mapping** | Not implemented | No verified exact cross-standard qualifier bridge | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A2.BusinessScenario` | `A3.ApplicationService` | **Official guidance only; no exact cross-standard entity pair** | Not implemented | BIAN Wireframes/scenarios can inform application overlay | **Verified** — [SAPG] §3.4 (wireframe overlay), §3.3 |
| `A2.BusinessScenario` | `A3.ApplicationComponent` | **Official guidance only; no exact cross-standard entity pair** | Not implemented | BIAN Wireframes/scenarios can inform application overlay | **Verified** — [SAPG] §3.4 (wireframe overlay), §3.3 |
| `A2.BusinessObject` | `A3.DataEntity` | **Official guidance only; no exact cross-standard entity pair** | `MAPPED_TO` | BIAN BOM logical information mapping guidance | **Verified** — [SAPG] §3.2.7; [SL14] BOM |
| `A2.BusinessObjectAttribute` | `A3.DataEntity` | **No verified official cross-standard mapping** | Not implemented | Attribute-level mapping lacks specific A3 attribute type | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |

#### A3 → A4 — 23 candidate entity pairs

| Source entity | Target entity | Official mapping coverage | Current SDMM rule | Mapping guidance / caveat  Verification (this review) |
|---|---|---|---|---|---|
| `A3.ApplicationComponent` | `A4.Deployment` | **SDMM mapping only; no official equivalent** | `DEPLOYED_AS` | SDMM-specific Deployment entity | n/a — SDMM definition, no external claim |
| `A3.ApplicationComponent` | `A4.InfrastructureComponent` | **SDMM mapping only; no official equivalent** | `DEPLOYED_ON` | Abstract compatibility supertype only | n/a — SDMM definition, no external claim |
| `A3.ApplicationComponent` | `A4.Node` | **ArchiMate modelling relationship; exact endpoint constraint to verify** | Not implemented | Indirect/realisation/deployment pattern; exact constraint needs check | **Unverified** — [AM] SSO-gated; not corroborated by the secondary sources read |
| `A3.ApplicationComponent` | `A4.Device` | **No verified official cross-standard mapping** | Not implemented | Potential indirect implementation/hosting paths; no direct prescribed pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationComponent` | `A4.SystemSoftware` | **No verified official cross-standard mapping** | Not implemented | Potential indirect implementation/hosting paths; no direct prescribed pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationComponent` | `A4.CommunicationNetwork` | **No verified official cross-standard mapping** | Not implemented | Potential indirect implementation/hosting paths; no direct prescribed pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationComponent` | `A4.Path` | **No verified official cross-standard mapping** | Not implemented | Potential indirect implementation/hosting paths; no direct prescribed pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationComponent` | `A4.Artifact` | **ArchiMate modelling relationship; exact endpoint constraint to verify** | Not implemented | ArchiMate Artifact realization pattern; direction/constraint to check | **Unverified** — [AM] SSO-gated; not corroborated by the secondary sources read |
| `A3.ApplicationComponent` | `A4.DeploymentEnvironment` | **SDMM mapping only; no official equivalent** | Not implemented | Indirect via A4.Deployment; SDMM extension | n/a — SDMM definition, no external claim |
| `A3.ApplicationService` | `A4.TechnologyService` | **ArchiMate modelling relationship; exact endpoint constraint to verify** | Not implemented | Technology service serves application architecture, not fixed instances | **Unverified against [AM] normative tables** (SSO-gated); pattern corroborated by secondary sources (technology service serves application behaviour / technology object realizes data object) |
| `A3.ApplicationService` | `A4.TechnologyInterface` | **No verified official cross-standard mapping** | Not implemented | Indirect via TechnologyService, not prescribed direct mapping | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationInterface` | `A4.TechnologyInterface` | **No verified official cross-standard mapping** | Not implemented | Both standard entities, but no one-to-one interface correspondence | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationInterface` | `A4.TechnologyService` | **No verified official cross-standard mapping** | Not implemented | Both standard entities, but no one-to-one interface correspondence | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.ApplicationFunction` | `A4.TechnologyService` | **ArchiMate modelling relationship; exact endpoint constraint to verify** | Not implemented | Technology serving application behaviour; constraint check required | **Unverified against [AM] normative tables** (SSO-gated); pattern corroborated by secondary sources (technology service serves application behaviour / technology object realizes data object) |
| `A3.ApplicationFunction` | `A4.SystemSoftware` | **No verified official cross-standard mapping** | Not implemented | Indirect via technology services | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.APIOperation` | `A4.Deployment` | **SDMM mapping only; no official equivalent** | Not implemented | APIOperation is SDMM extension; indirect via component/interface | n/a — SDMM definition, no external claim |
| `A3.APIOperation` | `A4.TechnologyInterface` | **SDMM mapping only; no official equivalent** | Not implemented | APIOperation is SDMM extension; indirect via component/interface | n/a — SDMM definition, no external claim |
| `A3.DataEntity` | `A4.Artifact` | **ArchiMate modelling relationship; exact endpoint constraint to verify** | Not implemented | ArchiMate Data Object→Artifact pattern; DataEntity is only aligned, not native | **Unverified against [AM] normative tables** (SSO-gated); pattern corroborated by secondary sources (technology service serves application behaviour / technology object realizes data object) |
| `A3.DataEntity` | `A4.SystemSoftware` | **No verified official cross-standard mapping** | Not implemented | May be indirectly hosted through runtime/database platform | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.Event` | `A4.TechnologyService` | **No verified official cross-standard mapping** | Not implemented | Indirect possibility; no cross-standard event/technology pair | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.SolutionBuildingBlock` | `A4.InfrastructureComponent` | **No verified official cross-standard mapping** | Not implemented | TOGAF SBB concept does not prescribe these SDMM correspondences | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.SolutionBuildingBlock` | `A4.Deployment` | **No verified official cross-standard mapping** | Not implemented | TOGAF SBB concept does not prescribe these SDMM correspondences | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |
| `A3.SolutionBuildingBlock` | `A4.Node` | **No verified official cross-standard mapping** | Not implemented | TOGAF SBB concept does not prescribe these SDMM correspondences | **Confirmed none** in [SL14], [SAPG], [RN14]; [AM], [TOGAF], [W135] not readable in this review |

#### Reference artefacts that are not mapping endpoints

| BIAN evidence artefact | Applicable entity mapping context | Official status | SDMM endpoint? |
|---|---|---|---|
| `A2.BOMModel` | `A1.BusinessObject` → `A2.BusinessObject` → `A3.DataEntity` | Official BIAN model artefact; **not** an official cross-standard entity pair | No |
| `A2.Wireframe` | `A1.BusinessProcess` / `A2.BusinessScenario` → `A3.ApplicationComponent` | Official BIAN modelling/evidence artefact; no bank-independent application pair | No |
| `A2.SemanticAPI` | `A2.ServiceOperation` → `A3.APIOperation` | Official BIAN API artefact; implementation correspondence is guidance | No |

#### Counts and limits

- **54 adjacent-level candidate pair rows:** A1→A2: 14, A2→A3: 17, A3→A4: 23.
- **Nine current SDMM relationship definitions**, whose endpoints are not necessarily the same as all candidate pairs above.
- **Three BIAN artefacts** documented separately because they are evidence, not legal mapping endpoints in the SDMM model.
- **Not covered:** within-layer relationships (already documented in the repo), non-adjacent direct links, and arbitrary unsupported cross-products.

### 2.4 Entity-by-entity gap table

> **Scope:** The original reference architecture and concept/source columns are retained. Mapping Guidance names potential participating entities and the authority of their relationship; it does not assert a mapping between two standards unless an official source establishes it. W135 (2013) is informational, aligns an older BIAN/TOGAF baseline, and should not be treated as proof of BIAN 14.0 + TOGAF 10 conformance.

**A1 — Business Architecture**

| Entity                   | Reference architecture                  | Concept                         | Source             | Direction | Adjacent-level mapped entity/entities | Official mapping coverage | Mapping Guidance  Verification (this review) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `A1.BusinessCapability` | BIAN BCM; ArchiMate Strategy | Business Capability; Capability | [RN14] §3; [AM] ch. 7 | A1→A2 | A2.ServiceDomain | **Guidance only** | BIAN BCM supports capability/domain alignment as an objective; no verified published release-14 entity crosswalk. SDMM SUPPORTED_BY. | **Verified as *intent only*** — [RN14] §3, [WQA26] |
| `A1.ValueStream` | ArchiMate Strategy | Value Stream | [AM] ch. 7; [RN14] §3 | A1→A2 | A2.BusinessScenario | **Not officially mapped** | SDMM ALIGNED_TO; ArchiMate defines Value Stream, but no official BIAN scenario pairing verified. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A1.ValueStreamStage` | SDMM extension of Value Stream | — | [AM] ch. 7 (parent) | A1→A2 | A2.BusinessScenario | **Not officially mapped** | Stage is SDMM-specific; no official stage-to-scenario pair. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A1.BusinessProcess` | ArchiMate Business | Business Process | [AM] ch. 8 | A1→A2 | A2.BusinessScenario; A2.ServiceDomain | **Guidance only** | W135 scenario/process analysis is methodological, not a normative one-to-one map; SDMM USES_DOMAIN. | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A1.BusinessActivity` | SDMM extension of Business Process | — | [AM] ch. 8 (parent) | A1→A2 | A2.ServiceOperation; A2.ServiceDomain | **Not officially mapped** | Activity granularity is SDMM-specific; proposed trace via a process and scenario/operation. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A1.BusinessService` | ArchiMate Business | Business Service | [AM] ch. 8 | A1→A2 | A2.ServiceDomain; A2.ServiceOperation | **Not officially mapped** | No official BusinessService=ServiceDomain equivalence. ArchiMate's native Business Service relations do not bridge BIAN automatically. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A1.BusinessActor` | ArchiMate Business | Business Actor | [AM] ch. 8 | A1→A2 | A2.BusinessScenario | **Not officially mapped** | May participate in scenario context; no verified published BIAN–ArchiMate actor correspondence. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A1.BusinessRole` | ArchiMate Business | Business Role | [AM] ch. 8 | A1→A2 | A2.BusinessScenario | **Not officially mapped** | Role/scenario involvement requires an SDMM-specific mapping; not present in the current registry. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A1.BusinessObject` | ArchiMate Business; aligned to BIAN BOM | Business Object | [AM] ch. 8; [SL14] | A1→A2 | A2.BusinessObject | **Guidance only** | BIAN BOM informs semantic information alignment; exact enterprise-object equivalence must be assessed (SDMM ALIGNED_TO). | **Verified** — [SL14] BOM; [SAPG] §3.2.7 |
| `A1.BusinessRequirement` | ArchiMate Motivation | Requirement | [AM] ch. 6 | A1→A2 | A2.ServiceDomain; A2.ServiceOperation | **Not officially mapped** | Trace through requirements/decisions locally; no fixed published requirement-to-domain map. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |

**A2 — Service Domain Architecture** — all BIAN reference, all `pending_release_validation` until verified against release 14.0

| Entity                                          | Reference architecture                                              | Concept                          | Source                       | Direction | Adjacent-level mapped entity/entities | Official mapping coverage | Mapping Guidance  Verification (this review) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `A2.BusinessArea` | BIAN Service Landscape | Business Area | [SL14] | A1↔A2; A2→A3 | A1.BusinessCapability; A3.ApplicationComponent (indirect) | **BIAN internal only** | BIAN hierarchy BusinessArea→BusinessDomain→ServiceDomain is defined; no direct official bank component mapping. | **Verified** — [SAPG] §3.1–3.2; [RN14] §1 |
| `A2.BusinessDomain` | BIAN Service Landscape | Business Domain | [SL14] | A1↔A2; A2→A3 | A1.BusinessCapability; A3.ApplicationComponent (indirect) | **BIAN internal only** | BIAN BusinessDomain→ServiceDomain grouping; implementation through ServiceDomain, not domain-to-application identity. | **Verified** — [SAPG] §3.1–3.2; [RN14] §1 |
| `A2.ServiceDomain` | BIAN Service Landscape | Service Domain | [SL14] MetaModel Overview | A1→A2→A3 | A1.BusinessCapability → A2.ServiceDomain → A3.ApplicationComponent | **Guidance only** | BIAN capability alignment and W135 application overlay are guidance; SDMM SUPPORTED_BY/REALIZED_BY are SDMM registry rules. | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A2.FunctionalPattern` | BIAN Service Landscape | Functional Pattern | [SL14] MetaModel Overview | A2→A3 | A3.ApplicationFunction | **Not officially mapped** | BIAN classification within A2 is official; no verified cross-standard functional-pattern/function identity. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A2.AssetType` | BIAN Service Landscape | Asset Type | [SL14] MetaModel Overview | A2→A3 | A3.DataEntity | **Not officially mapped** | BIAN asset semantics may inform data design; no direct published asset-type-to-data-entity map. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A2.ControlRecord` | BIAN Control Record Model | Control Record | [SL14] Control Record Model | A2→A3 | A3.DataEntity; A3.ApplicationFunction | **Guidance only** | BIAN lifecycle/control record modelling supports logical design, not a canonical institution-specific data mapping. | **Verified** — [SAPG] §4.2.2 |
| `A2.ServiceGroup` | BIAN Service Landscape | Service Group | [SL14] MetaModel Overview | A2→A3 | A3.ApplicationService; A3.ApplicationInterface | **Not officially mapped** | BIAN ServiceGroup→ServiceOperation internal structure official; no exact cross-standard service-group map. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A2.ServiceOperation` | BIAN Service Landscape; Semantic APIs | Service Operation | [SL14]; [SAPG] | A2→A3 | A3.APIOperation; A3.ApplicationService | **Guidance only** | BIAN Semantic API and W135 guide implementation; bank APIOperation linkage is SDMM IMPLEMENTED_BY. | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A2.BehaviorQualifier` | BIAN Service Landscape; Semantic APIs | Behavior Qualifier | [SL14]; [SAPG] | A2→A3 | A3.APIOperation; A3.DataEntity | **Not officially mapped** | Official BIAN qualifier structure only; API/data correspondence needs local interpretation. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A2.BusinessScenario` | BIAN Business Scenarios | Business Scenario (illustrative) | [SL14] Business Scenarios | A1↔A2→A3 | A1.BusinessProcess; A3.ApplicationService; A3.ApplicationComponent | **Guidance only** | BIAN defines participating operations/domains; W135 scenario-to-process/application analysis is guidance, not fixed bank mappings. | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A2.BusinessObject` | BIAN Business Object Model | Business Object | [SL14] BOM | A1→A2→A3 | A1.BusinessObject → A2.BusinessObject → A3.DataEntity | **Guidance only** | BIAN BOM semantics and W135 logical data alignment; SDMM MAPPED_TO requires actual bank data mapping. | **Unverified** — rests on [W135], not readable in this review (login required); existence, date and SL 2.0 basis confirmed |
| `A2.BusinessObjectAttribute` | BIAN Business Object Model | BOM attribute | [SL14] BOM | A2→A3 | A3.DataEntity (attributes) | **Not officially mapped** | BIAN attributes are defined; SDMM has no separate A3 DataAttribute entity or official attribute-level bridge. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A2.BOMModel` *(artefact)* | BIAN Business Object Model artefact | BOM model artefact | [SL14] BOM | Evidence across A1→A2→A3 | A1.BusinessObject; A2.BusinessObject; A3.DataEntity | **BIAN artefact only** | Official BIAN evidence/model artefact, not an SDMM mapping endpoint. | **Verified** — [SL14]; [SAPG] §3.4–3.5 |
| `A2.Wireframe` *(artefact)* | BIAN Wireframes artefact | Wireframe artefact | [SL14] Wireframes | Evidence across A1→A2→A3 | A2.BusinessScenario; A3.ApplicationComponent | **BIAN artefact only** | Official BIAN view used for design guidance; not an entity-level mapping endpoint. | **Verified** — [SL14]; [SAPG] §3.4–3.5 |
| `A2.SemanticAPI` *(artefact)* | BIAN Semantic APIs artefact | Semantic API artefact | [SAPG] | Evidence across A2→A3 | A2.ServiceOperation; A3.APIOperation | **BIAN artefact only** | Published BIAN semantic contract guidance; not an SDMM mapping endpoint. | **Verified** — [SL14]; [SAPG] §3.4–3.5 |

**A3 — Application Architecture**

| Entity                     | Reference architecture                                 | Concept                 | Source   | Direction | Adjacent-level mapped entity/entities | Official mapping coverage | Mapping Guidance  Verification (this review) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `A3.ApplicationComponent` | ArchiMate Application | Application Component | [AM] ch. 9 | A2→A3→A4 | A2.ServiceDomain → A3.ApplicationComponent → A4.Deployment / A4.Node | **ArchiMate A3→A4 only** | BIAN→component pairing is enterprise-specific; ArchiMate permits cross-layer application/technology relations, but SDMM DEPLOYED_AS is an extension. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A3.ApplicationService` | ArchiMate Application | Application Service | [AM] ch. 9 | A2→A3→A4 | A2.ServiceOperation → A3.ApplicationService → A4.TechnologyService | **ArchiMate A3→A4 only** | BIAN service correspondence needs review; ArchiMate technology service can serve application elements subject to relationship constraints. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A3.ApplicationInterface` | ArchiMate Application | Application Interface | [AM] ch. 9 | A2→A3→A4 | A2.ServiceOperation → A3.ApplicationInterface → A4.TechnologyInterface | **Not officially mapped end-to-end** | ArchiMate defines both interface types, but no universal direct interface-to-interface bridge or BIAN endpoint map. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A3.ApplicationFunction` | ArchiMate Application | Application Function | [AM] ch. 9 | A2→A3→A4 | A2.ServiceDomain / A2.ServiceOperation → A3.ApplicationFunction → A4.TechnologyService | **ArchiMate A3→A4 only** | Application behaviour can be served by technology services in ArchiMate; BIAN function allocation remains local. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A3.APIOperation` | SDMM extension; aligned to BIAN Semantic API / OpenAPI | — | [SAPG] | A2→A3→A4 | A2.ServiceOperation → A3.APIOperation → A4.Deployment (via ApplicationComponent) | **Guidance only to A3** | BIAN semantic operation correspondence is implementation guidance; APIOperation is an SDMM extension, no direct official A3→A4 pair. | **Verified** — [SAPG] |
| `A3.DataEntity` | ArchiMate Application (related) | Data Object | [AM] ch. 9 | A2→A3→A4 | A2.BusinessObject → A3.DataEntity → A4.Artifact | **ArchiMate A3→A4 analogue only** | ArchiMate Data Object/Artifact realization is modelled officially; SDMM DataEntity is aligned, not exactly that standard type. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A3.Event` | ArchiMate Application (related) | Application Event | [AM] ch. 9 | A2→A3→A4 | A2.BusinessScenario / A2.ServiceOperation → A3.Event → A4.TechnologyService (indirect) | **Not officially mapped** | ArchiMate Application Event has native relationships; no direct BIAN event crosswalk or fixed event-to-technology bridge. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A3.SolutionBuildingBlock` | TOGAF Architecture Content | Solution Building Block | [TOGAF] | A2→A3→A4 | A2.ServiceDomain → A3.SolutionBuildingBlock → A4.InfrastructureComponent | **TOGAF guidance only** | TOGAF describes SBBs, but does not prescribe BIAN domain-to-SBB or SBB-to-SDMM infrastructure pairing. | **Unverified** — [TOGAF] SSO-gated |

**A4 — Technology Architecture**

| Entity                                    | Reference architecture                          | Concept               | Source              | Direction | Adjacent-level mapped entity/entities | Official mapping coverage | Mapping Guidance  Verification (this review) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `A4.InfrastructureComponent` *(abstract)* | SDMM compatibility supertype of every A4 entity | — | — | A3→A4 | A3.ApplicationComponent → A4.InfrastructureComponent | **Not officially mapped** | SDMM abstract compatibility type, not a named ArchiMate entity; legacy DEPLOYED_ON registry rule. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A4.Deployment` | SDMM extension of Artifact assigned to Node | — | [AM] ch. 10 (parents) | A3→A4 | A3.ApplicationComponent → A4.Deployment | **Not officially mapped** | SDMM DEPLOYED_AS; ArchiMate deployment can be modelled through Artifact/Node relationships, but Deployment is not a native ArchiMate type. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A4.DeploymentEnvironment` | SDMM extension of Node grouping | — | [AM] ch. 10 (parent) | A3→A4 | A3.ApplicationComponent → A4.DeploymentEnvironment (via Deployment) | **Not officially mapped** | SDMM extension; no exact BIAN/TOGAF/ArchiMate cross-standard pair. | **Confirmed none** in BIAN sources; [AM]/[TOGAF]/[W135] not readable in this review |
| `A4.Node` | ArchiMate Technology | Node | [AM] ch. 10 | A3→A4 | A3.ApplicationComponent; A3.ApplicationService (via technology services/artifacts) | **ArchiMate native relationship support** | Official ArchiMate cross-layer structure and Artifact-on-Node modelling; no official BIAN ServiceDomain→Node mapping. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.Device` | ArchiMate Technology | Device | [AM] ch. 10 | A3→A4 | A3.ApplicationComponent (indirect through A4.Node / A4.Artifact) | **ArchiMate native relationship support** | Official technology modelling; no direct universal application-component-to-device assignment. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.SystemSoftware` | ArchiMate Technology | System Software | [AM] ch. 10 | A3→A4 | A3.ApplicationComponent (via A4.Node / A4.TechnologyService) | **ArchiMate native relationship support** | Official runtime element and relationships; specific applications/instances need bank evidence. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.TechnologyService` | ArchiMate Technology | Technology Service | [AM] ch. 10 | A3→A4 | A3.ApplicationService; A3.ApplicationFunction; A3.ApplicationComponent | **ArchiMate native cross-layer support** | Official ArchiMate technology service serving semantics; no fixed BIAN service-operation mapping. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.TechnologyInterface` | ArchiMate Technology | Technology Interface | [AM] ch. 10 | A3→A4 | A3.ApplicationInterface (via technology services) | **ArchiMate native model only** | Official technology-interface associations; no guaranteed cross-layer 1:1 interface equivalence. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.CommunicationNetwork` | ArchiMate Technology | Communication Network | [AM] ch. 10 | A3→A4 | A3.ApplicationComponent (indirect via A4.Node / A4.Path) | **ArchiMate native model only** | Official network/node technology representation; no universal direct A3 component-to-network mapping. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.Path` | ArchiMate Technology | Path | [AM] ch. 10 | A3→A4 | A3.ApplicationComponent (indirect via A4.Node) | **ArchiMate native model only** | Official technology connectivity modelling; no direct cross-standard component-to-path identity. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |
| `A4.Artifact` | ArchiMate Technology | Artifact | [AM] ch. 10 | A3→A4 | A3.ApplicationComponent; A3.DataEntity | **ArchiMate native cross-layer support** | ArchiMate Artifact can realize application components/data objects and be deployed to nodes; bank-specific artifact linkage needed. | **Unverified against [AM] normative tables** (SSO-gated); general pattern corroborated by secondary sources |

### 2.5 Reference material and verification boundary

1. [BIAN Service Landscape 14.0](https://bian.org/servicelandscape-14-0-0/) — definitions, BIAN internal domain semantics.
2. [BIAN Semantic API Practitioner Guide v8.1](https://bian.org/wp-content/uploads/2024/12/BIAN-Semantic-API-Pactitioner-Guide-V8.1-FINAL.pdf) — implementation and operation/API guidance.
3. [BIAN 14.0 release notes](https://bian.org/wp-content/uploads/2026/02/BIAN-v14.0-Release-Notes-v1.0_-Final-Version.pdf) — BCM-to-domain mapping publication status; release context.
4. [The Open Group W135 — Integrating the TOGAF Standard with the BIAN Service Landscape](https://www.opengroup.org/ogsys/catalog/W135) — historical BIAN–TOGAF integration guidance (2013); **not** a certified BIAN 14.0/TOGAF 10 mapping.
5. [ArchiMate 3.2 specification](https://pubs.opengroup.org/architecture/archimate3-doc/) — chapters 6–10, cross-layer relationships, and normative allowed relationship tables. ArchiMate relations are directional, and exact permitted combinations must be validated against those tables before claiming conformance.
6. [TOGAF Standard, 10th Edition](https://pubs.opengroup.org/togaf-standard/) — architecture content and building block concepts.

**Not yet established:** exact section/table-level adjudication of each W135 counterpart against BIAN 14.0 and TOGAF 10; automated checking against the ArchiMate normative relationship matrix; live licensed BIAN instance reconciliation. These rows consequently use conservative support labels rather than pretending all entities have an official mapping.

### 2.6 Source verification — result

Every source cited in §2.3–2.5 was checked for accessibility and, where readable, its cited statements were read.

| Source | Accessible without login? | Read in this review? | What it verifies in §2 |
|---|---|---|---|
| [SL14] BIAN Service Landscape 14.0 portal | **Yes** | Portal structure and page inventory; MetaModel Overview, BOM and Control Record pages cited but not read page by page | BIAN entity existence and instances |
| [SAPG] Semantic API Practitioner Guide v8.1 | **Yes** (public PDF) | **Yes, in full** (110 pp., text extracted) | All "BIAN internal", "guidance only" and A2→A3 rows that cite it — **verified** with section and page |
| [RN13] / [RN14] release notes | **Yes** | **Yes, in full** | BCM status; A2 artefact inventory — **verified** |
| [WQA26] webinar Q&A, June 2026 | **Yes** | **Yes, in full** | Capability / value-stream mapping still in progress — **verified** |
| [APIP] BIAN Semantic API portal | **Yes** | Index only | Existence of reference API definitions |
| [AM] ArchiMate® 3.2 Specification | **No** — every edition on pubs.opengroup.org (3.2, 3.0, 2.1) redirects to Open Group SSO; the archive copy is not reachable from this environment | **No** | Nothing in §2 resting on ArchiMate is verified against the primary text. Two secondary sources corroborate the general cross-layer pattern (lower-layer *service* serves higher-layer element; lower-layer *object* realizes higher-layer object) but not the normative allowed-relationship tables |
| [TOGAF] Standard, 10th Edition | **No** — SSO | **No** | TOGAF rows unverified |
| [W135] Open Group White Paper W135 | Catalogue entry yes; **PDF requires login** | **No** — metadata only | W135 exists (22 Oct 2013, 43 pp., Bonnie/Obitz, supersedes W120, written for Service Landscape 2.0); its content is **unverified**, and every §2.4 cell that invokes "W135 scenario/process analysis", "W135 application overlay" or "W135 logical data alignment" is therefore unverified |

#### Verdict by claim class

| Claim class in §2.3–2.4 | Rows | Result |
|---|---|---|
| BIAN internal / BIAN artefact | A2 structural rows | **Verified** ([SAPG] §3.1–3.5, [RN14]) |
| Official guidance only, citing BIAN | `REALIZED_BY`, `IMPLEMENTED_BY`, `MAPPED_TO`, `USES_DOMAIN`, control-record and scenario rows | **Verified** with section/page |
| Official guidance only, capability alignment | `SUPPORTED_BY` rows | **Verified as intent only** — the mapping is unpublished ([RN14] §3, [WQA26]) |
| Official guidance only, citing W135 | process/scenario, application overlay, logical data rows in §2.4 | **Unverified** — W135 not readable |
| ArchiMate modelling relationship / native support | A3→A4 rows | **Unverified against the normative tables**; three pairs corroborated in pattern by secondary sources (ApplicationService ← TechnologyService, ApplicationFunction ← TechnologyService, DataEntity ← Artifact); ApplicationComponent → Node and ApplicationComponent → Artifact not corroborated by the sources read |
| TOGAF guidance only | SBB rows | **Unverified** |
| SDMM mapping only | `DEPLOYED_ON`, `DEPLOYED_AS`, value-stream rows | n/a — SDMM's own definitions, no external claim |
| No verified official mapping | remaining rows | **Confirmed none in the BIAN sources**; the three gated sources could not be searched |

#### Corrections required before §2 is used

1. **[AM] and [TOGAF] are not "publicly readable".** `docs/reference-architecture-provenance.md` and the README describe ArchiMate 3.2 and TOGAF 10 as public; both now require a free Open Group account (SSO) to read online, and the PDF is a licensed download. The wording is corrected in this commit. The entities derived from ArchiMate remain legitimately sourced — the standard is public in the ordinary sense — but *verification* of a specific relationship claim needs someone with an account.
2. **[W135] location and status.** Citations now point to https://publications.opengroup.org/w135 with the document's metadata; the earlier catalogue URL is dead.
3. **W135 is a 2013 document for Service Landscape 2.0.** Even once read, it is evidence of a *method* that predates the Service Landscape's current structure by twelve releases; §2.4 cells should cite it as historical method, never as a BIAN 14.0 mapping.

**Bottom line:** of §2's claims, everything that rests on BIAN is verified; everything that rests on ArchiMate, TOGAF or W135 is unverified in this review because the primary texts are login-gated. Nothing from §2 is adopted into the registry until the gated sources have been read by someone with access — which is a one-afternoon task with a free Open Group account.

### 2.7 Analysis *(next, after §2.6 is closed)*

Which candidate pairs should become registry rules, which framework supplies the authority for each, and which remain institution-only.

## 3. Engine architecture *(in planning)*

### 3.1 Starting point: SDMM's nine arrows against BIAN's mappings

§1 described BIAN's own mapping model. The engine works on **SDMM's** nine arrows (the registry). For each, does a BIAN mapping from §1.2 cover it? Where it does not, §3 has to design the inference, drawing on §2 for what other frameworks supply.

| SDMM arrow (registry rule) | Covered by a BIAN mapping? | Which one | What is left to the institution |
|---|---|---|---|
| `A1.BusinessCapability SUPPORTED_BY A2.ServiceDomain` | **No** | — (BCM→Service Domain unpublished) | The whole mapping |
| `A1.ValueStream ALIGNED_TO A2.BusinessScenario` | **No** | — (value streams not modelled) | The whole mapping; scenarios are a published target |
| `A1.BusinessProcess USES_DOMAIN A2.ServiceDomain` | **No** | — | The whole mapping; scenarios usable as templates |
| `A1.BusinessObject ALIGNED_TO A2.BusinessObject` | **No** | — (BOM is a target, not a mapping) | The whole mapping; BOM attributes are the published target |
| `A2.ServiceDomain REALIZED_BY A3.ApplicationComponent` | **Method only** | wireframe functional partition; legacy wrapping ([SAPG] §3.4, §4.3.1) | Deciding which application; BIAN says how to decide, not what |
| `A2.ServiceOperation IMPLEMENTED_BY A3.APIOperation` | **Yes** | REST mapping and reference APIs ([SAPG] §3.5; [APIP]) | Comparing the bank's API to the reference form |
| `A2.BusinessObject MAPPED_TO A3.DataEntity` | **Partial** | control record = REST resource ([SAPG] §3.5) | Matching the bank's data entity to the BOM object |
| `A3.ApplicationComponent DEPLOYED_ON A4.InfrastructureComponent` | **No** | — (deployment patterns only) | The whole mapping, from deployment data |
| `A3.ApplicationComponent DEPLOYED_AS A4.Deployment` | **No** | — (domain-as-container is a pattern, not a mapping) | The whole mapping, from deployment data |

**One arrow of nine is covered by a BIAN mapping; one is partially covered; one has a BIAN method; six have nothing.** The rest of §3 follows this row by row.

### 3.2 Per-arrow design *(next)*

Tier 1 deterministic candidates per arrow, tier 2 model-assisted ranking, evidence and confidence policy, evaluation on a held-out set.
