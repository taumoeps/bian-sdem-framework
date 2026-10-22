# Mapping logic — planning (v0.6)

**Status:** planning. Nothing in this document is implemented. v0.4 delivered the structural logic (what a mapping *may* be); v0.5 delivered the harness (how an engine is scored). This document plans the semantic logic: how software will *propose* what a mapping *should* be, for an architect to accept or reject.

**Ground rule, restated:** an engine's output is always `status: proposed`. The validator refuses approval without a named reviewer and date. Nothing below changes that.

---

## 1. What BIAN already gives us, boundary by boundary

Before designing any inference, establish what the reference architecture itself provides. The findings below are taken from BIAN's public release notes for Service Landscape 13.0 (June 2025) and 14.0 (February 2026) and the Semantic API Practitioner Guide v8.1 (2020), not from memory. Section and page references are given so they can be checked; no BIAN text is reproduced beyond short attributed phrases.

### 1.1 Coverage matrix

| Boundary | What BIAN publishes | How complete | What an engine can use it for |
|---|---|---|---|
| **A1 → A2** capability → Service Domain | A Business Capability Model exists and is in the repository, but the BCM working group's mapping of capabilities to Service Domains is **work in progress and not documented in the repository** (v13 notes §3; v14 notes §3 — "results are not yet documented… still work in progress"; further detail is on the members-only wiki). Value streams: also WIP, not yet modelled (v14 §3) | **Not published.** No authoritative capability→domain alignment exists publicly | Nothing to look up. The engine must *infer* this boundary from text — capability descriptions against Service Domain descriptions — and from structure (which domains a capability's processes already use). This is the hardest boundary and the one BIAN was expected to cover |
| **A1 → A2** value stream → Business Scenario | Business Scenarios are fully documented as UML sequence diagrams with Service Domain descriptions (v14 §1, §9); value streams are not yet modelled by BIAN | **One side only.** Scenarios are public and rich; value streams have no BIAN counterpart | Scenario text and the Service Domains a scenario invokes are strong evidence. An engine can match a value stream's stages to a scenario's interactions, then propose the domains the scenario uses |
| **A1 → A2** business object → BOM object | Business Object Model and Control Record Model fully documented, with attributes, rationalised in v14 (v14 §1.3) | **Published.** Canonical information concepts with attributes | Name and attribute matching against a public, well-structured target. The most tractable A1→A2 arrow |
| **A2 within** | Service Domains, Functional Patterns, Asset Types, Control Records, Behavior Qualifiers, Service Groups, Service Operations with input/output parameters, Wireframes, First Order Connections (guide §3.2–3.4; v14 §1) | **Complete at conceptual level.** All expressed in ArchiMate 3.2 / UML (v14 §1.1–1.2) | The A2 level model is the one level SDMM can populate almost entirely from the public portal, under an institution's licence. The engine has rich text on every A2 instance |
| **A2 → A3** Service Domain → application | The wireframe technique: "existing or to-be-developed applications can be mapped with the Service Domains corresponding to major functional partitions of the application" (guide §3.4, p. 52). Legacy wrapping aligns existing systems to component boundaries (guide §4.3.1, p. 91). Logical designs are "partially defined" and "quickly start to include site or implementation specific details" (guide §4.2, pp. 78–81) | **Method, not data.** BIAN says *how* to decide which application realises a domain (functional partition overlap), but publishes no application inventory and no realisation data — it cannot | The engine applies BIAN's own criterion: does the application's described functional scope fall inside the domain's responsibilities? Text similarity plus the wireframe's interaction pattern. Existing approved `REALIZED_BY` arrows give strong patterns ("this domain is already realised by…") |
| **A2 → A3** Service Operation → API operation | Semantic API REST mapping: the Service Domain is assumed to match the application boundary of an API, and its service operations make up the API's program interfaces (guide §3.5, p. 52). Control record instance = REST resource; functional patterns map to REST archetypes; HTTP methods assigned (guide §3.5, pp. 52–54). A public Semantic API portal exists | **Published and prescriptive at logical level.** Operation naming, action terms and resource structure are defined | The most mechanical boundary. An engine can compare an institution's API path + method + payload against the BIAN operation's action term, behaviour qualifier and control record. Mismatches are *findings* ("this API realises the operation but omits two mandatory attributes"), not just scores |
| **A2 → A3** BOM object → data entity | BOM attributes are published; the information profile per Service Domain is documented (guide §3.2.7) | **Published.** | Attribute-level matching of an application's data entity against the BOM object |
| **A3 → A4** application → infrastructure | No technology vocabulary and no data: BIAN "does not assume or impose any physical properties for the Service Domains" (guide §4.2.3, p. 87); Figure 34 places BIAN's scope at conceptual and partially logical, not physical (p. 90). But **deployment guidance exists**: §4.2.3 lists software utilities to consider in "a component/container type deployment" (message queues, state machines, event-driven processing, workflow, rules engines); §4.1 describes each Service Domain as a discrete service container and cloud/container environments; §4.3 gives legacy wrapping, parallel core migration (Figure 35) and shared-platform patterns (Figure 37) | **Guidance only.** No entities, no instances, no mapping method — but a published view of how domain-aligned components are expected to be deployed | BIAN contributes *patterns*, not data: "one domain → one deployable container" is a structural expectation an engine can use as a prior when an institution follows it. The actual arrows still come from the institution's deployment data — CMDB, manifests, environment assignments. Text won't help (the baseline already showed "Fraud Engine" and "Managed Kubernetes" share no words) |

### 1.2 BIAN mapping scope by entity

All 44 catalogue entities. **Covered by BIAN** is "Yes" when BIAN defines the concept and publishes its instances, "No" otherwise. **BIAN mapping to next level** says whether BIAN publishes a way to map this entity across the boundary below it: Yes (a published rule or method), Partial, Method only, No, or — where no arrow exists. Entities not covered by BIAN show "n/a" in the BIAN columns so the scope is visible in one table.

Sources: **[SL14]** Service Landscape 14.0 InSite portal · **[RN14]** v14.0 release notes · **[SAPG]** Semantic API Practitioner Guide v8.1 · **[APIP]** BIAN Semantic API portal. (What BIAN offers as *guidance* at each boundary is in §1.3 (BIAN's own mappings) and §1.4 (SDMM's arrows against them).)


#### A1 — Business Architecture — 1 of 10 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source | BIAN mapping to next level |
|---|---|---|---|---|
| `A1.BusinessCapability` | Yes | Business Capability (BCM) | [SL14] Business Capability Map | No — capability→Service Domain mapping is work in progress, unpublished ([RN14] §3) |
| `A1.ValueStream` | No | n/a | n/a | n/a |
| `A1.ValueStreamStage` | No | n/a | n/a | n/a |
| `A1.BusinessProcess` | No | n/a | n/a | n/a |
| `A1.BusinessActivity` | No | n/a | n/a | n/a |
| `A1.BusinessService` | No | n/a | n/a | n/a |
| `A1.BusinessActor` | No | n/a | n/a | n/a |
| `A1.BusinessRole` | No | n/a | n/a | n/a |
| `A1.BusinessObject` | No | n/a | n/a | n/a |
| `A1.BusinessRequirement` | No | n/a | n/a | n/a |

#### A2 — Service Domain Architecture — 15 of 15 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source | BIAN mapping to next level |
|---|---|---|---|---|
| `A2.BusinessArea` | Yes | Business Area | [SL14] Service Landscape views | — (structural; no cross-level arrow) |
| `A2.BusinessDomain` | Yes | Business Domain | [SL14] Service Landscape views | — (structural; no cross-level arrow) |
| `A2.ServiceDomain` | Yes | Service Domain | [SL14] per-domain pages; [SAPG] §2.4–2.5, §3.1–3.2 | Method only — applications mapped by functional partition ([SAPG] §3.4); legacy wrapping (§4.3.1) |
| `A2.FunctionalPattern` | Yes | Functional Pattern | [SL14] MetaModel Overview; [SAPG] §3.2.1 | Partial — patterns → REST archetypes ([SAPG] §3.5) |
| `A2.AssetType` | Yes | Asset Type | [SL14] MetaModel Overview; [SAPG] §3.2.2 | Partial — with the pattern, shapes the REST resource |
| `A2.ControlRecord` | Yes | Control Record | [SL14] Control Record Model Overview; [SAPG] §3.2.3 | Yes — control record = REST resource ([SAPG] §3.5) |
| `A2.ServiceGroup` | Yes | Service Group | [SL14] MetaModel Overview | — |
| `A2.ServiceOperation` | Yes | Service Operation | [SL14] per-domain operations with I/O parameters; [SAPG] §3.2.5 | Yes — REST mapping: action term, behaviour qualifier, HTTP method ([SAPG] §3.5) |
| `A2.BehaviorQualifier` | Yes | Behavior Qualifier | [SL14] MetaModel Overview; [SAPG] §3.2.4 | Yes — part of the REST resource path ([SAPG] §3.5) |
| `A2.BusinessScenario` | Yes | Business Scenario | [SL14] Business Scenarios; [SAPG] §3.3 | Partial — scenarios are BIAN's guidance toward A1 value streams; none toward A3 |
| `A2.BusinessObject` | Yes | Business Object (BOM) | [SL14] Business Object Model Overview; [SAPG] §3.2.7 | Yes — information profile per domain ([SAPG] §3.2.7) |
| `A2.BusinessObjectAttribute` | Yes | Business Object attribute | [SL14] Business Object Model Overview | Yes — attribute level, as above |
| `A2.BOMModel` *(artefact)* | Yes | Business Object Model | [SL14] Business Object Model Overview | — (evidence artefact) |
| `A2.Wireframe` *(artefact)* | Yes | Wireframe | [SL14] Wireframes Overview; [SAPG] §3.4 | — (evidence artefact) |
| `A2.SemanticAPI` *(artefact)* | Yes | Semantic API | [APIP]; [SAPG] §3.5 | — (evidence artefact) |

#### A3 — Application Architecture — 0 of 8 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source | BIAN mapping to next level |
|---|---|---|---|---|
| `A3.ApplicationComponent` | No | n/a | n/a | n/a |
| `A3.ApplicationService` | No | n/a | n/a | n/a |
| `A3.ApplicationInterface` | No | n/a | n/a | n/a |
| `A3.ApplicationFunction` | No | n/a | n/a | n/a |
| `A3.APIOperation` | No | n/a | n/a | n/a |
| `A3.DataEntity` | No | n/a | n/a | n/a |
| `A3.Event` | No | n/a | n/a | n/a |
| `A3.SolutionBuildingBlock` | No | n/a | n/a | n/a |

#### A4 — Technology Architecture — 0 of 11 covered by BIAN

| Entity | Covered by BIAN | BIAN concept | BIAN source | BIAN mapping to next level |
|---|---|---|---|---|
| `A4.InfrastructureComponent` *(abstract)* | No | n/a | n/a | n/a |
| `A4.Deployment` | No | n/a | n/a | n/a |
| `A4.DeploymentEnvironment` | No | n/a | n/a | n/a |
| `A4.Node` | No | n/a | n/a | n/a |
| `A4.Device` | No | n/a | n/a | n/a |
| `A4.SystemSoftware` | No | n/a | n/a | n/a |
| `A4.TechnologyService` | No | n/a | n/a | n/a |
| `A4.TechnologyInterface` | No | n/a | n/a | n/a |
| `A4.CommunicationNetwork` | No | n/a | n/a | n/a |
| `A4.Path` | No | n/a | n/a | n/a |
| `A4.Artifact` | No | n/a | n/a | n/a |

**Totals: 16 of 44 entities covered by BIAN** — one at A1, all fifteen at A2, none at A3, none at A4. Of the sixteen, only the A2→A3 information and API entities (`ControlRecord`, `ServiceOperation`, `BehaviorQualifier`, `BusinessObject`, `BusinessObjectAttribute`) have a published BIAN mapping to the next level; the capability's mapping to Service Domains — the one most expected — is not published.

### 1.3 Existing BIAN mappings between levels

Only mappings that BIAN itself publishes, between a BIAN entity and something on the next level. Nothing SDMM defines appears here. Every row names the artefact it comes from.

#### A1 → A2 — none published

| BIAN mapping | Status |
|---|---|
| Business Capability → Service Domain | **Not published.** The BCM working group mapped capabilities to Service Domains in 2024; "the results are not yet documented in the BIAN BiZZdesign repository because still work in progress" ([RN13] §3, repeated [RN14] §3). Detail is on the members-only wiki |
| Value stream → Business Scenario | **Not published.** Value streams are under study by the BCM working group and "not yet modelled" ([RN14] §3) |

BIAN publishes the A2 **targets** a bank would map to — Service Domains, Business Scenarios, the BOM — but no mapping *from* a bank's A1 to them.

#### A2 → A3 — published, at logical level, in the Semantic API Practitioner Guide v8.1

| # | BIAN mapping | Rule as published | Source |
|---|---|---|---|
| 1 | **Service Domain → API application boundary** | "the assumption is made that the BIAN Service Domain matches the application boundary (the 'A') of the API" | [SAPG] §3.5 p. 52 |
| 2 | **Service Operation → API program interface** | the domain's service operations "make up the collection of program interfaces (the 'PI's) that complete the API's description" | [SAPG] §3.5 p. 52 |
| 3 | **Control Record instance → REST resource** | "a Service Domain control record instance essentially represents the accessed resource" | [SAPG] §3.5 p. 53 |
| 4 | **Functional Pattern generic artefact → REST archetype** | each functional pattern's generic artefact maps to a REST archetype (document, collection or controller; the fourth, store, is not needed) — Figure 24 | [SAPG] §3.5 pp. 53–54 |
| 5 | **Behavior Qualifier → sub-resource** | the qualifier "is used to narrow the reference to a sub-partition of the referenced control record instance"; attributes are filtered by action term for the input/output messages | [SAPG] §3.5 p. 55 |
| 6 | **Action Term → REST form** | action terms are converted to noun form (Create → Creation, Initiate → Initiation, Register → Registration, Evaluate → Evaluation, Provide → Provision, Execute → Execution, Request → Requisition; Update, Control, Exchange, Capture, Grant unchanged); **Retrieve maps directly to HTTP GET**; Notify is not used in the mapping. HTTP methods applied are GET, PUT, POST, (PATCH), DELETE | [SAPG] §3.5 pp. 52, 55 |
| 7 | **Semantic API reference definitions** | per-domain OpenAPI definitions published on the API portal as the reference form of 1–6 | [APIP] |
| 8 | **Service Domain → application functional partition** *(method)* | "existing or to-be-developed applications can be mapped with the Service Domains corresponding to major functional partitions of the application", using the wireframe overlay | [SAPG] §3.4 p. 52 |
| 9 | **Legacy system → Service Domain component boundary** *(method)* | legacy wrapping "compartmentalizes legacy systems aligning to component boundaries" | [SAPG] §4.3.1 p. 91 |

Rows 1–7 are rules: given a BIAN operation, they say what its REST form is. Rows 8–9 are methods: they say *how to decide* which application realises a domain, not *which one does*. All are logical: "BIAN Endpoint descriptions are far from implementation specifications" ([SAPG] §3.5 p. 56). The Information Profile (§3.2.7) is not a mapping — it defines what information a domain governs, as the content any A3 data design must cover.

#### A3 → A4 — none published

| BIAN mapping | Status |
|---|---|
| Application → infrastructure / deployment | **None.** "The BIAN standard … does not assume or impose any physical properties for the Service Domains" ([SAPG] §4.2.3 p. 87). What exists is implementation *guidance* — component/container deployment properties, utilities to consider, legacy wrapping, parallel migration, shared platforms (§4.1–4.3) — which describes patterns, not a mapping |

#### Summary

| Boundary | BIAN mappings that exist |
|---|---|
| A1 → A2 | 0 |
| A2 → A3 | 7 rules + 2 methods, all logical level |
| A3 → A4 | 0 |

**BIAN's published cross-level mapping is confined to one boundary, A2 → A3, and within it to the API and information path.** The capability boundary has no published mapping, and the infrastructure boundary has none by design.

### 1.4 SDMM arrows against BIAN coverage

| Arrow (registry rule) | BIAN source side | BIAN target side | BIAN mapping guidance | Engine approach | Default confidence band |
|---|---|---|---|---|---|
| `A1.BusinessCapability SUPPORTED_BY A2.ServiceDomain` | ● BCM instances | ● domains | ○ unpublished | Text + structure inference; strongest evidence required | **low** |
| `A1.ValueStream ALIGNED_TO A2.BusinessScenario` | ○ | ● scenarios | ◐ scenarios only | Stage text vs scenario interactions | low–medium |
| `A1.BusinessProcess USES_DOMAIN A2.ServiceDomain` | ○ | ● domains | ◐ scenarios as templates | Step text vs operation descriptions; scenario participation | medium |
| `A1.BusinessObject ALIGNED_TO A2.BusinessObject` | ○ | ● BOM | ● BOM attributes | Name + attribute match | medium–high |
| `A2.ServiceDomain REALIZED_BY A3.ApplicationComponent` | ● | ○ | ◐ functional-partition method | Description overlap + composition + existing arrows | medium |
| `A2.ServiceOperation IMPLEMENTED_BY A3.APIOperation` | ● with I/O params | ◐ reference APIs | ● REST mapping rules | Rule-based: action term, qualifier, method, payload attributes; emits findings | **high** |
| `A2.BusinessObject MAPPED_TO A3.DataEntity` | ● BOM | ○ | ● information profile | Attribute-level match | medium–high |
| `A3.ApplicationComponent DEPLOYED_ON A4.InfrastructureComponent` | ○ | ○ | ◐ deployment patterns ([SAPG] §4.1–4.3), no mapping method | Structural: deployment data in the A4 export; BIAN pattern as a prior | high *if* data present, else no proposal |
| `A3.ApplicationComponent DEPLOYED_AS A4.Deployment` | ○ | ○ | ◐ as above — the domain-as-container expectation is this arrow's pattern | As above | As above |

Reading across: **A2 is the only level BIAN fills.** Three of the nine arrows have a published BIAN method on their A2 side (operation→API, object→entity, object→BOM); two have a method only (domain→application, process→domain); the capability arrow — the one most people expect BIAN to answer — has none published; the two A4 arrows have deployment *patterns* but no vocabulary, no data and no mapping method, and need no text at all.

### 1.5 Consequences for the engine design

1. **A2 is the anchor.** It is the only level whose vocabulary *and instances* can be sourced publicly (with an institution's licence to use them). Every A1→A2 and A2→A3 inference is a comparison *against* A2 text. Populating a rich A2 level model from the portal — descriptions, scenarios, operations, control-record attributes — is the first engineering task, and it is an export, not an inference.

2. **The capability boundary has no BIAN answer.** Despite what our earlier provenance assumed, there is no published BCM↔Service Domain alignment to look up. An engine must infer it, and that inference carries the most risk of a plausible-but-wrong proposal. It gets the lowest default confidence and the strongest evidence requirement (`domain_scope_assessment` is already a required evidence kind for `SUPPORTED_BY`).

3. **The API boundary has the most mechanics.** BIAN's REST mapping gives action terms, resource archetypes and HTTP methods. An engine can be *rule-based* here, and its proposals can carry specific findings. Highest default confidence.

4. **The infrastructure boundary is text-free, but not pattern-free.** `DEPLOYED_ON` / `DEPLOYED_AS` come from deployment data, never from descriptions. The engine needs a structural source: a `relationships` entry in the A4 export that says which artefact runs where, or an attribute on the A3 instance naming its deployment target. BIAN's implementation guidance (§4.1–4.3) supplies a *prior* — a domain-aligned component is expected to deploy as a discrete container — which can raise confidence when the data agrees with the pattern, but never substitutes for the data.

5. **Existing approved mappings are the best evidence of all.** "Domain X is realised by application Y" makes "operation X.op is implemented by Y's API" far more likely. The engine should always read the federated graph before reading any description.

### 1.6 Corrections to the repository arising from this review

- `docs/reference-architecture-provenance.md`, the README and the v0.4 spec cite a "BIAN BCM *Statement of Alignment with the Service Landscape* (2023)" PDF. That URL returns 404 and BIAN's release notes describe the alignment as unfinished and unpublished. The citation is replaced by the v13 and v14 release notes, and `A1.BusinessCapability` keeps `evidence_status: interpreted_from_official_source` with that basis.
- The registry's `SUPPORTED_BY` and `ALIGNED_TO` (value stream) rules carry `authority: bian_alignment_guidance`. That remains correct — BIAN *intends* to provide this guidance and the BCM exists — but the planning assumption that an engine could consult a published alignment is withdrawn.

---

## 2. Engine architecture *(next: to be planned)*

Tier 1 deterministic candidates per boundary, tier 2 model-assisted ranking, evidence and confidence policy, evaluation on a held-out set. Sections 2–5 follow once §1 is agreed.
