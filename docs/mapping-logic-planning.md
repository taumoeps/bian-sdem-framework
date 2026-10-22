# Mapping logic — planning (v0.6)

**Status:** planning. Nothing in this document is implemented. v0.4 delivered the structural logic (what a mapping *may* be); v0.5 delivered the harness (how an engine is scored). This document plans the semantic logic: how software will *propose* what a mapping *should* be, for an architect to accept or reject.

**Ground rule, restated:** an engine's output is always `status: proposed`. The validator refuses approval without a named reviewer and date. Nothing below changes that.

---

## 1. BIAN's current mapping model

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

### 1.2 Mappings between BIAN entities

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

## 2. Engine architecture *(in planning)*

### 2.1 Starting point: SDMM's nine arrows against BIAN's mappings

§1 described BIAN's own mapping model. The engine works on **SDMM's** nine arrows (the registry). For each, does a BIAN mapping from §1.2 cover it? Where it does not, §2 has to design the inference.

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

**One arrow of nine is covered by a BIAN mapping; one is partially covered; one has a BIAN method; six have nothing.** The rest of §2 follows this row by row.

### 2.2 Per-arrow design *(next)*

Tier 1 deterministic candidates per arrow, tier 2 model-assisted ranking, evidence and confidence policy, evaluation on a held-out set.
