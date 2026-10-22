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

### 1.2 Consequences for the engine design

1. **A2 is the anchor.** It is the only level whose vocabulary *and instances* can be sourced publicly (with an institution's licence to use them). Every A1→A2 and A2→A3 inference is a comparison *against* A2 text. Populating a rich A2 level model from the portal — descriptions, scenarios, operations, control-record attributes — is the first engineering task, and it is an export, not an inference.

2. **The capability boundary has no BIAN answer.** Despite what our earlier provenance assumed, there is no published BCM↔Service Domain alignment to look up. An engine must infer it, and that inference carries the most risk of a plausible-but-wrong proposal. It gets the lowest default confidence and the strongest evidence requirement (`domain_scope_assessment` is already a required evidence kind for `SUPPORTED_BY`).

3. **The API boundary has the most mechanics.** BIAN's REST mapping gives action terms, resource archetypes and HTTP methods. An engine can be *rule-based* here, and its proposals can carry specific findings. Highest default confidence.

4. **The infrastructure boundary is text-free, but not pattern-free.** `DEPLOYED_ON` / `DEPLOYED_AS` come from deployment data, never from descriptions. The engine needs a structural source: a `relationships` entry in the A4 export that says which artefact runs where, or an attribute on the A3 instance naming its deployment target. BIAN's implementation guidance (§4.1–4.3) supplies a *prior* — a domain-aligned component is expected to deploy as a discrete container — which can raise confidence when the data agrees with the pattern, but never substitutes for the data.

5. **Existing approved mappings are the best evidence of all.** "Domain X is realised by application Y" makes "operation X.op is implemented by Y's API" far more likely. The engine should always read the federated graph before reading any description.

### 1.4 Coverage at entity level

One row per entity. Three questions each: does BIAN **define the concept**, does BIAN **publish instances** of it (so a level model can be exported from the portal), and does BIAN **give guidance for mapping it across a boundary**. ● = yes, publicly · ◐ = partial / method or pattern only · ○ = no. The **BIAN reference source** names the public artefact or document section the row rests on; "—" means BIAN has no artefact for this entity and the concept comes from ArchiMate, TOGAF or SDMM.

Sources: **[SL14]** Service Landscape 14.0 InSite portal, https://bian.org/servicelandscape-14-0-0/ · **[RN13]** v13.0 release notes · **[RN14]** v14.0 release notes · **[SAPG]** Semantic API Practitioner Guide v8.1 (2020) · **[APIP]** BIAN Semantic API portal, https://bian.org/bian-portal/

#### A1 — Business Architecture

BIAN defines one A1 concept (the capability) and publishes its instances; everything else at A1 is the institution's, with BIAN artefacts on the A2 side as targets.

| Entity | BIAN reference source | Concept defined | Instances published | Boundary guidance → A2 | What the engine has to work with |
|---|---|---|---|---|---|
| `A1.BusinessCapability` | [SL14] Business Capability Map (Top Level View, Capability Views); [RN14] §3 | ● BCM | ● capability map on the portal | ○ capability→Service Domain mapping WIP, unpublished ([RN13] §3, [RN14] §3) | Capability description vs domain description; which domains its processes already use |
| `A1.ValueStream` | [RN14] §3 (under study by the BCM working group; not modelled) | ○ (ArchiMate) | ○ | ◐ Business Scenarios exist on the A2 side; nothing links them to value streams | Stage text vs scenario interaction text |
| `A1.ValueStreamStage` | — | ○ (SDMM) | ○ | ○ | As above, per stage |
| `A1.BusinessProcess` | [SL14] Business Scenarios (nearest artefact; BIAN models no bank processes) | ○ (ArchiMate) | ○ | ◐ scenarios as templates; `USES_DOMAIN` is an enterprise rule | Step text vs operation descriptions; scenario sequence as template |
| `A1.BusinessActivity` | — | ○ (SDMM) | ○ | ○ | As above, finer grain |
| `A1.BusinessService` | — | ○ (ArchiMate) | ○ | ○ no SDMM arrow yet | — |
| `A1.BusinessActor` | — (scenario diagrams name parties informally, [SL14] Business Scenarios) | ○ (ArchiMate) | ○ | ○ no SDMM arrow yet | Context only |
| `A1.BusinessRole` | — | ○ (ArchiMate) | ○ | ○ no SDMM arrow yet | Context only |
| `A1.BusinessObject` | [SL14] Business Object Model (alignment target); [RN14] §1.3 | ○ (ArchiMate; aligned to BOM) | ○ the bank's own concepts | ● the BOM is the published target, with attributes | Name and attribute matching against BOM objects |
| `A1.BusinessRequirement` | — | ○ (ArchiMate) | ○ | ○ no SDMM arrow yet | — |

#### A2 — Service Domain Architecture

Every A2 entity is defined *and* instantiated publicly; this is the one level that can be exported from the portal.

| Entity | BIAN reference source | Concept defined | Instances published | Boundary guidance → A3 | What the engine has to work with |
|---|---|---|---|---|---|
| `A2.BusinessArea` | [SL14] Service Landscape V14.0 — Value Chain, Matrix, Overview views | ● | ● | — structural only | Hierarchy; no cross-level arrow |
| `A2.BusinessDomain` | [SL14] Service Landscape views; InSite Business Domain pages | ● | ● | — structural only | Hierarchy; no cross-level arrow |
| `A2.ServiceDomain` | [SL14] landscape views and per-domain pages; [SAPG] §2.4–2.5, §3.1–3.2; [RN14] §4 (rationalised definitions) | ● | ● ~300 with descriptions | ◐ applications mapped by functional partition ([SAPG] §3.4 p. 52); legacy wrapping ([SAPG] §4.3.1 p. 91) | Domain description, pattern, asset type; wireframe interactions; existing `REALIZED_BY` arrows |
| `A2.FunctionalPattern` | [SL14] MetaModel Overview; [SAPG] §3.2.1 | ● fixed vocabulary | ● per domain | ◐ patterns map to REST archetypes ([SAPG] §3.5 pp. 53–54) | Classifies the domain; drives the REST mapping |
| `A2.AssetType` | [SL14] MetaModel Overview; [SAPG] §3.2.2 | ● | ● per domain | ◐ with the pattern, determines the control record's resource shape | Classifies the domain |
| `A2.ControlRecord` | [SL14] Control Record Model Overview; [SAPG] §3.2.3; [RN14] §1.3 | ● | ● per domain, with attributes | ● control record instance = REST resource ([SAPG] §3.5 p. 53) | Resource structure to match an API payload against |
| `A2.ServiceGroup` | [SL14] MetaModel Overview (InSite) | ● | ● per domain | — | Groups operations; organises evidence |
| `A2.ServiceOperation` | [SL14] per-domain operations with input/output parameters ([RN14] §1); [SAPG] §3.2.5 (action terms) | ● | ● per domain, with I/O parameters | ● REST mapping: action term + behaviour qualifier + HTTP method ([SAPG] §3.5) | Path, method, payload comparison — the most mechanical arrow |
| `A2.BehaviorQualifier` | [SL14] MetaModel Overview; [SAPG] §3.2.4 | ● | ● per domain | ● part of the REST resource path ([SAPG] §3.5) | Refines the operation→API match |
| `A2.BusinessScenario` | [SL14] Business Scenarios (by business area); [RN14] §9; [SAPG] §3.3 | ● | ● UML sequence diagrams | ◐ guidance toward A1 (value-stream side); none toward A3 | Interaction sequence and participating domains |
| `A2.BusinessObject` | [SL14] Business Object Model Overview; [SAPG] §3.2.7; [RN14] §1.3 | ● | ● BOM | ● information profile per domain ([SAPG] §3.2.7) | Object-level matching to data entities |
| `A2.BusinessObjectAttribute` | [SL14] Business Object Model Overview (attributes) | ● | ● per object | ● as above, attribute level | Attribute-level matching |
| `A2.BOMModel` *(artefact)* | [SL14] Business Object Model Overview | ● | ● | — evidence, not an endpoint | Citable support |
| `A2.Wireframe` *(artefact)* | [SL14] Wireframes Overview; [SAPG] §3.4; [RN14] §10 | ● | ● | — evidence, not an endpoint | Interaction pattern to compare an application's interfaces against |
| `A2.SemanticAPI` *(artefact)* | [APIP]; [SAPG] §3.5 | ● | ● reference API definitions per domain | — evidence, not an endpoint | Reference contract to compare an institution's API against |

#### A3 — Application Architecture

BIAN defines no A3 entities and publishes no institution data, but it **does cover A3 as guidance**: how applications relate to domains ([SAPG] §3.4 functional partitions, §4.3.1 legacy wrapping, §4.2.2 application clusters), how operations become APIs ([SAPG] §3.5 REST mapping), and — for `APIOperation` only — reference definitions ([APIP]).

| Entity | BIAN reference source | Concept defined | Instances published | Boundary guidance ← A2 · → A4 | What the engine has to work with |
|---|---|---|---|---|---|
| `A3.ApplicationComponent` | [SAPG] §3.4 p. 52 (applications mapped to domains by functional partition); §4.2.2 pp. 84–87 (application clusters: core / external / peripheral domains); §4.3.1 p. 91 (legacy wrapping) | ○ (ArchiMate) | ○ the bank's inventory | ◐ ← functional-partition method and cluster roles · ○ → | Component description vs domain description; composition; existing arrows |
| `A3.ApplicationService` | [SAPG] §3.5 p. 52 (a Semantic API = a domain's operations exposed at the application boundary) | ○ (ArchiMate) | ○ | ◐ ← as stated · ○ → | Service groupings against domain operation sets; no SDMM arrow yet |
| `A3.ApplicationInterface` | [SAPG] §3.5 p. 52; §3.4 (wireframe overlay shows which interfaces APIs can support) | ○ (ArchiMate) | ○ | ◐ ← interface ↔ domain boundary · ○ → | Interface vs wireframe interaction; no SDMM arrow yet |
| `A3.ApplicationFunction` | — | ○ (ArchiMate) | ○ | ○ | Finer realisation evidence only |
| `A3.APIOperation` | [APIP] reference Semantic API definitions per domain (OpenAPI); [SAPG] §3.5 pp. 52–54 (REST mapping: resource archetypes, HTTP methods) | ○ (SDMM) | ◐ BIAN publishes **reference** definitions — logical, not the bank's | ● ← REST mapping rules · ○ → | Path, method, payload vs BIAN operation's action term, qualifier and control-record attributes; rule-based |
| `A3.DataEntity` | [SL14] Business Object Model; [SAPG] §3.2.7 (information profile) | ○ (ArchiMate-aligned) | ○ | ● ← BOM / information profile · ○ → | Entity attributes vs BOM attributes |
| `A3.Event` | [SAPG] §3.6 (Service Domain event triggering — a *proposed* design extension) | ○ (ArchiMate-aligned) | ○ | ◐ ← proposed only · ○ → | Weak; no SDMM arrow yet |
| `A3.SolutionBuildingBlock` | — (TOGAF) | ○ | ○ | ○ | Grouping only |

#### A4 — Technology Architecture

BIAN defines no technology entities and publishes no instances ("does not assume or impose any physical properties", [SAPG] §4.2.3 p. 87; scope stops at logical, Figure 34 p. 90), but it **does cover A4 as implementation guidance**: deployment properties and utilities for component/container deployment (§4.2.3), domain-as-container and cloud/container environments (§4.1), legacy wrapping, parallel core migration and shared platforms (§4.3, Figures 35 and 37).

| Entity | BIAN reference source | Concept defined | Instances published | Boundary guidance ← A3 | What the engine has to work with |
|---|---|---|---|---|---|
| `A4.InfrastructureComponent` *(abstract)* | — | ○ (SDMM compatibility supertype) | — | — | Accepts any concrete A4 entity as a mapping target |
| `A4.Deployment` | [SAPG] §4.1 (each Service Domain as a discrete service container; cloud/container environments); §4.2.3 (component/container deployment properties); §4.3.1 (legacy wrapping); Figure 35 (parallel core migration) | ○ (SDMM) | ○ the bank's | ◐ deployment *pattern*: one domain-aligned component → one deployable container; no mapping method | Pattern prior, confirmed only by deployment data in the A4 export |
| `A4.DeploymentEnvironment` | [SAPG] §4.3.1 (parallel running of legacy and new), Figure 35 | ○ (SDMM) | ○ the bank's | ◐ migration pattern implies environment separation | Environment membership from the A4 export |
| `A4.Node` | — ([SAPG] §4.2.3: no physical properties assumed) | ○ (ArchiMate) | ○ CMDB | ○ | Artefact-to-node assignments in the A4 export |
| `A4.Device` | — | ○ (ArchiMate) | ○ CMDB | ○ | As above |
| `A4.SystemSoftware` | [SAPG] §4.2.3 utilities checklist (message queues and events, state machines, event-driven processing, workflow management, rules engine) | ○ (ArchiMate) | ○ the bank's platforms | ◐ which *kinds* of runtime utility a domain is expected to need | Expectation of platform kinds; cannot name an instance |
| `A4.TechnologyService` | [SAPG] §4.2.3 (utilities and middleware); §4.3.2 shared platforms (Figure 37) | ○ (ArchiMate) | ○ the bank's | ◐ shared-platform pattern | Expectation of shared services; cannot name an instance |
| `A4.TechnologyInterface` | — | ○ (ArchiMate) | ○ | ○ | A4 export only |
| `A4.CommunicationNetwork` | — | ○ (ArchiMate) | ○ | ○ | A4 export only |
| `A4.Path` | — | ○ (ArchiMate) | ○ | ○ | A4 export only |
| `A4.Artifact` | [SAPG] §4.1 (domain functionality packaged as a service container) | ○ (ArchiMate) | ○ build systems | ◐ the container *is* the artefact in BIAN's pattern | Artefact identity from build/deploy data |

### 1.5 Coverage at arrow level

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

### 1.3 Corrections to the repository arising from this review

- `docs/reference-architecture-provenance.md`, the README and the v0.4 spec cite a "BIAN BCM *Statement of Alignment with the Service Landscape* (2023)" PDF. That URL returns 404 and BIAN's release notes describe the alignment as unfinished and unpublished. The citation is replaced by the v13 and v14 release notes, and `A1.BusinessCapability` keeps `evidence_status: interpreted_from_official_source` with that basis.
- The registry's `SUPPORTED_BY` and `ALIGNED_TO` (value stream) rules carry `authority: bian_alignment_guidance`. That remains correct — BIAN *intends* to provide this guidance and the BCM exists — but the planning assumption that an engine could consult a published alignment is withdrawn.

---

## 2. Engine architecture *(next: to be planned)*

Tier 1 deterministic candidates per boundary, tier 2 model-assisted ranking, evidence and confidence policy, evaluation on a held-out set. Sections 2–5 follow once §1 is agreed.
