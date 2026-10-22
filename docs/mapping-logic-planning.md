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
| **A3 → A4** application → infrastructure | None. "The BIAN standard … does not assume or impose any physical properties for the Service Domains" (guide §4.2.3, p. 87); Figure 34 shows BIAN's scope as conceptual, partially logical, **not physical** (p. 90) | **Not covered, by design.** | BIAN contributes nothing. This boundary is purely the institution's: CMDB, deployment manifests, platform inventories. Text won't help (the baseline already showed "Fraud Engine" and "Managed Kubernetes" share no words); the signals are structural — deployment records, container images, environment assignments |

### 1.2 Consequences for the engine design

1. **A2 is the anchor.** It is the only level whose vocabulary *and instances* can be sourced publicly (with an institution's licence to use them). Every A1→A2 and A2→A3 inference is a comparison *against* A2 text. Populating a rich A2 level model from the portal — descriptions, scenarios, operations, control-record attributes — is the first engineering task, and it is an export, not an inference.

2. **The capability boundary has no BIAN answer.** Despite what our earlier provenance assumed, there is no published BCM↔Service Domain alignment to look up. An engine must infer it, and that inference carries the most risk of a plausible-but-wrong proposal. It gets the lowest default confidence and the strongest evidence requirement (`domain_scope_assessment` is already a required evidence kind for `SUPPORTED_BY`).

3. **The API boundary has the most mechanics.** BIAN's REST mapping gives action terms, resource archetypes and HTTP methods. An engine can be *rule-based* here, and its proposals can carry specific findings. Highest default confidence.

4. **The infrastructure boundary is text-free.** `DEPLOYED_ON` / `DEPLOYED_AS` come from deployment data, never from descriptions. The engine needs a structural source: a `relationships` entry in the A4 export that says which artefact runs where, or an attribute on the A3 instance naming its deployment target.

5. **Existing approved mappings are the best evidence of all.** "Domain X is realised by application Y" makes "operation X.op is implemented by Y's API" far more likely. The engine should always read the federated graph before reading any description.

### 1.3 Corrections to the repository arising from this review

- `docs/reference-architecture-provenance.md`, the README and the v0.4 spec cite a "BIAN BCM *Statement of Alignment with the Service Landscape* (2023)" PDF. That URL returns 404 and BIAN's release notes describe the alignment as unfinished and unpublished. The citation is replaced by the v13 and v14 release notes, and `A1.BusinessCapability` keeps `evidence_status: interpreted_from_official_source` with that basis.
- The registry's `SUPPORTED_BY` and `ALIGNED_TO` (value stream) rules carry `authority: bian_alignment_guidance`. That remains correct — BIAN *intends* to provide this guidance and the BCM exists — but the planning assumption that an engine could consult a published alignment is withdrawn.

---

## 2. Engine architecture *(next: to be planned)*

Tier 1 deterministic candidates per boundary, tier 2 model-assisted ranking, evidence and confidence policy, evaluation on a held-out set. Sections 2–5 follow once §1 is agreed.
