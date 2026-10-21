# BIAN Service Domain Mapping Model (SDMM)
## v0.4 track — Entity Metamodel, Bank Architecture Profiles and BIAN Verification Register

**Status:** Proposed design baseline for implementation (not a BIAN or Open Group standard)
**Version:** 0.4-draft.3 (supersedes 0.3-draft.1 after review; renumbered because v0.3 is published as `sdmm-trace`; §14 decisions recorded)
**Prepared:** 22 October 2026
**Architecture scope:** SDMM-defined A1 Business / A2 BIAN Service Domain / A3 Application / A4 Infrastructure
**Compatibility commitment:** every v0.2.1 mapping document validates unchanged under every v0.4.x release.

---

## 1. Purpose and outcome

The v0.4 track gives SDMM a **bank-neutral, standards-traceable entity vocabulary** for all four levels, an **entity hierarchy** so the existing relationship registry can accept specialised endpoint entities, an **Architecture Profile** mechanism that maps an institution's own A1–A4 concepts onto that vocabulary, and a **verification register** that records how each BIAN-derived claim was checked without reproducing BIAN content.

A successful v0.4 enables a sample bank to (a) register its own `BusinessFunction`, `SolutionBuildingBlock` and `CloudResource` types, (b) map them to SDMM core entities through a profile, (c) resolve actual instance IDs and versions, (d) validate an authored A1→A4 chain, and (e) see, for every BIAN-derived type, whether its definition has been verified against a named release. It **does not** infer which BIAN domain is semantically correct, store within-level relationships, implement a persistent federated graph, or perform impact analysis.

### 1.1 Normative boundary

1. **`bian_reference`:** authoritative only for definitions and relations present in a pinned BIAN release and recorded in the verification register.
2. **`archimate_native` / `archimate_aligned`:** SDMM abstraction corresponding to an ArchiMate 3.2 concept; `native` only when definition and semantics match.
3. **`togaf_informed`:** content governance, building blocks and tailoring methodology; TOGAF is not SDMM's element-type vocabulary.
4. **`sdmm_extension`:** portable neutral types introduced for the A1–A4 lifecycle, with origin recorded.
5. **`bank_extension`:** a profile's own types. A profile mapping asserts equivalence only to the degree its `alignment_kind` states.

SDMM's A1–A4 decomposition is local to SDMM and is not an official BIAN layering convention. BIAN Service Domains are logical partitions of banking functionality, not deployable microservices. BIAN Business Scenarios are illustrative, not prescriptive.

### 1.2 Two taxonomies, deliberately distinct

| Taxonomy | Applies to | Values | Lives in |
|---|---|---|---|
| **`definition_source`** | **entities** (the vocabulary) | `bian_reference`, `bian_aligned`, `archimate_native`, `archimate_aligned`, `togaf_informed`, `sdmm_extension`, `bank_extension` | `metamodel/` |
| **`authority`** (v0.2) | relationship **rules** | `bian_reference`, `bian_alignment_guidance`, `enterprise_rule` | `schema/relationship-types.json` |

Registry self-check (new): a rule with `bian_*` authority must have at least one endpoint type whose `definition_source` is `bian_*`.

---

## 2. Reference architecture inventory

| Ref | Source | Contributes | SDMM use | Caveat |
|---|---|---|---|---|
| R1 | BIAN Service Landscape 14.0 — InSite portal, publicly browsable at https://bian.org/servicelandscape-14-0-0/ | Business Areas/Domains, Service Domains, Service Groups/Operations, Functional Patterns, Asset Types, Control Records, Wireframes, MetaModel Overview | A2 structural anchor | Browsable without login; **no licence text on the portal**, so reproduction of definitions, diagrams or datasets is treated as not permitted. Verification = reading and recording, never copying |
| R2 | BIAN BCM and *Statement of Alignment with the Service Landscape* (2023) | Capabilities, BCM↔Service Landscape alignment, value stream/scenario comparison | A1→A2 methodology | Guidance, not an algorithm |
| R3 | BIAN Business Object Model and Control Record Model (InSite views) | Business Objects, attributes, information views | A2 information anchor | A BOM is a model artefact, not an entity |
| R4 | BIAN Semantic APIs / Service Operations / Business Scenarios | Operations, interfaces, behaviour qualifiers, scenarios | A2 behaviour; A2→A3 contract alignment | Logical contracts, not the bank's physical APIs |
| R5 | ArchiMate 3.2 (The Open Group) | Business, Application, Technology, Motivation concepts and relationships | A1/A3/A4 core element types | Synonyms tagged `aligned` or `extension`, never passed off as native |
| R6 | TOGAF 10, Architecture Content | Building blocks, content governance, tailoring | Profiles; `SolutionBuildingBlock` | No cloud-specific vocabulary |
| R7 | SDMM v0.2.1 registry, schema, validator, `sdmm-diff` | Eight cross-level relationship types, approvals, evidence, immutability | Compatibility baseline | Edge names are SDMM proposals |

---

## 3. Entity record

**Vocabulary.** An **entity** is an item of the SDMM vocabulary — a kind of thing, such as `A2.ServiceDomain`; there are 31 in core. An **entity instance** is an actual element of a bank's architecture of that kind — `SD-044`, the Fraud Detection domain — and lives in the bank's own level model. A mapping's endpoints are **entity references**: pointers to instances, carrying the instance's `id`, its entity (the `type` field) and its `version`.

Every entity in `metamodel/` records:

```jsonc
{
  "type": "A2.ServiceDomain",
  "level": "A2",
  "abstract": false,
  "extends": null,                                   // parent SDMM entity, or null
  "definition": "Discrete functional scope of the bank and its responsibilities",   // SDMM paraphrase, never quoted text
  "definition_source": "bian_reference",
  "alignment_kind": "exact",                         // exact | specialization | related | conceptual | none
  "reference": { "standard": "BIAN Service Landscape", "release": "14.0", "concept": "Service Domain",
                 "uri": "https://bian.org/servicelandscape-14-0-0/" },
  "evidence_status": "pending_release_validation",   // flips to confirmed_in_official_source only via a verification record (§9)
  "artefact": false                                  // true for model artefacts that are not mapping endpoints
}
```

**Rules**

- `bian_reference` types ship as `pending_release_validation`. No row in this document is "confirmed"; confirmation is a register entry, not a spec assertion.
- `artefact: true` types (BOM model, wireframe, Semantic API document) may be cited as evidence but may **not** be mapping endpoints.
- Entities are matched **is-a**: a registry rule naming `A4.InfrastructureComponent` accepts any type whose `extends` chain reaches it.

---

## 4. Entity reference (mapping endpoint)

Unchanged from v0.2.1, with optional additions:

| Field | Required | Notes |
|---|---|---|
| `id`, `type`, `version` | yes | as v0.2.1 |
| `canonical_id` | for A2 ends of `bian_*` rules | as v0.2.1 |
| `source_system` | no | which level model / tool holds the instance; profiles may require it |
| `source_entity_id` | no | the entity's native id if it differs from `id` |

`lifecycle_status` is **not** a reference field: a reference is a pointer, and the instance's status belongs to the level model and is returned by the resolver.

Document-level pins: `registry_version` (existing), **`metamodel_version`** and **`profile_id`** (new, optional).

---

## 5. Core entity catalogue

Counts: v0.2.1 ships 11 types. The 0.3 draft proposed 53. v0.4 core is **31**; the rest move to profiles or to the artefact list.

### 5.1 A1 — Business (10)

| Type | Definition | Reference concept | Source / alignment |
|---|---|---|---|
| `A1.BusinessCapability` | Business ability independent of implementation | BIAN BCM Capability; ArchiMate Capability | `bian_aligned` / conceptual |
| `A1.ValueStream` | Stages by which stakeholders receive value | ArchiMate Value Stream; R2 | `archimate_native` / exact |
| `A1.ValueStreamStage` | Named segment of a value stream | Value stream decomposition | `sdmm_extension` / specialization |
| `A1.BusinessProcess` | Coordinated business behaviour | ArchiMate Business Process | `archimate_native` / exact |
| `A1.BusinessActivity` | Fine-grained activity within a process | Process decomposition | `sdmm_extension` / conceptual |
| `A1.BusinessService` | Business behaviour exposed to consumers | ArchiMate Business Service | `archimate_native` / exact |
| `A1.BusinessActor` | Individual or organisation capable of behaviour | ArchiMate Business Actor | `archimate_native` / exact |
| `A1.BusinessRole` | Responsibility for a class of behaviour | ArchiMate Business Role | `archimate_native` / exact |
| `A1.BusinessObject` | Business-level information concept | ArchiMate Business Object; BIAN BOM where aligned | `archimate_native` + `bian_aligned` reference |
| `A1.BusinessRequirement` | Expressed architectural requirement | ArchiMate Requirement | `archimate_native` / exact |

### 5.2 A2 — BIAN Service Domain (12 entities + 3 artefacts)

All `bian_reference`, all `pending_release_validation` until registered (§9).

| Type | Definition | BIAN concept |
|---|---|---|
| `A2.BusinessArea` | Top-level Service Landscape grouping | Business Area |
| `A2.BusinessDomain` | Coarse functional grouping | Business Domain |
| `A2.ServiceDomain` | Discrete functional scope and responsibilities | Service Domain |
| `A2.FunctionalPattern` | Generic behaviour applied within a domain | Functional Pattern |
| `A2.AssetType` | Class of asset managed through its lifecycle | Asset Type |
| `A2.ControlRecord` | Lifecycle/control information for domain activity | Control Record |
| `A2.ServiceGroup` | Grouping of Service Operations | Service Group |
| `A2.ServiceOperation` | Operation exposed by a domain | Service Operation |
| `A2.BehaviorQualifier` | Refines generic domain behaviour | Behavior Qualifier |
| `A2.BusinessScenario` | Illustrative collaboration of operations (non-prescriptive) | Business Scenario |
| `A2.BusinessObject` | Canonical business information concept | BOM Business Object |
| `A2.BusinessObjectAttribute` | Property of a BOM object | BOM attribute |

Artefacts (`artefact: true`, citable as evidence, not endpoints): `A2.BOMModel`, `A2.Wireframe`, `A2.SemanticAPI`.

### 5.3 A3 — Application (8)

| Type | Definition | Reference concept | Source / alignment |
|---|---|---|---|
| `A3.ApplicationComponent` | Modular application structure | ArchiMate Application Component | `archimate_native` / exact |
| `A3.ApplicationService` | Externally exposed application behaviour | ArchiMate Application Service | `archimate_native` / exact |
| `A3.ApplicationInterface` | Access point to an application service | ArchiMate Application Interface | `archimate_native` / exact |
| `A3.ApplicationFunction` | Internal application behaviour | ArchiMate Application Function | `archimate_native` / exact |
| `A3.APIOperation` | Callable operation of an API contract | BIAN Semantic API / OpenAPI operation | `sdmm_extension` / aligned to R4 |
| `A3.DataEntity` | Application-level logical data entity | ArchiMate Data Object | `archimate_aligned` / related |
| `A3.Event` | Event produced or consumed by applications | ArchiMate Application Event | `archimate_aligned` / related |
| `A3.SolutionBuildingBlock` | Organisation-defined reusable solution grouping | TOGAF SBB | `togaf_informed` / conceptual |

Dropped from core: `A3.Application` (an application *system* is an `ApplicationComponent` with a profile-defined `kind`, not a second type); `A3.Integration` (deferred; model as `Flow` in the level model).

### 5.4 A4 — Infrastructure (11)

| Type | Definition | Reference concept | Source / alignment |
|---|---|---|---|
| `A4.InfrastructureComponent` | **Abstract** supertype of every A4 endpoint | — | `sdmm_extension` (v0.2 compatibility) |
| `A4.Deployment` | An application deployed into an environment | ArchiMate Artifact assigned to Node | `sdmm_extension` / composite |
| `A4.DeploymentEnvironment` | Governed runtime boundary (prod, test…) | Node grouping convention | `sdmm_extension` |
| `A4.Node` | Computational host, physical or logical | ArchiMate Node | `archimate_native` / exact |
| `A4.Device` | Physical computing hardware | ArchiMate Device | `archimate_native` / exact |
| `A4.SystemSoftware` | Platform/runtime software | ArchiMate System Software | `archimate_native` / exact |
| `A4.TechnologyService` | Technical behaviour delivered to consumers | ArchiMate Technology Service | `archimate_native` / exact |
| `A4.TechnologyInterface` | Access point for a technology service | ArchiMate Technology Interface | `archimate_native` / exact |
| `A4.CommunicationNetwork` | Communication infrastructure | ArchiMate Communication Network | `archimate_native` / exact |
| `A4.Path` | Route between nodes | ArchiMate Path | `archimate_native` / exact |
| `A4.Artifact` | Deployable technology-level artefact | ArchiMate Artifact | `archimate_native` / exact |

All ten concrete A4 types `extends: A4.InfrastructureComponent`.

Moved to the **`example-cloud` profile** (§7): `ComputeResource`, `ContainerPlatform`, `NetworkSegment`, `NetworkComponent`, `StorageResource`, `DatabasePlatform`, `SecurityControl`, `IdentityAccessComponent`. Each extends the appropriate core entity (e.g. `ContainerPlatform extends A4.SystemSoftware`). Rationale: the 0.3 draft's own caution — a cloud service may be a Technology Service, System Software or Node depending on purpose — is an argument for profile-level specialisation, not core entities.

---

## 6. Relationships

### 6.1 Within-level relationships are out of scope — decided

SDMM stores **only** cross-level edges. Relationships inside a level (capability decomposition, component composition, deployment-runs-on-node) belong to that level's own model and are never SDMM mapping records. The registry self-check continues to reject same-level and level-skipping rules. Profiles may *describe* a bank's within-level relationship types for documentation, but nothing in SDMM reads or validates them.

### 6.2 Cross-level registry

v0.2.1's eight rules are retained verbatim. One rule is added:

| Source | Relationship | Target | Perspective | Authority |
|---|---|---|---|---|
| `A3.ApplicationComponent` | `DEPLOYED_AS` | `A4.Deployment` | architecture | `enterprise_rule` |

`DEPLOYED_ON → A4.InfrastructureComponent` is retained; with is-a matching it now accepts any concrete A4-entity. No mapping is migrated from `DEPLOYED_ON` to `DEPLOYED_AS` in place — immutability applies; a migration is a superseding record, and `sdmm-diff` enforces that.

### 6.3 Derived relationships

Level-skipping traceability (A1 requirement → A4 control) is a **query** over stored edges, returned with provenance to each approved edge on the path. Never a record. (`sdmm-trace`, v0.3.)

---

## 7. Bank Architecture Profiles

### 7.1 Shape (JSON; no new dependencies)

```jsonc
{
  "profile_id": "example-bank",
  "profile_version": "1.0",
  "metamodel_version": "0.4.0",
  "entity_type_mappings": [
    { "source_type": "ExampleBank.BusinessFunction", "target_type": "A1.BusinessCapability",
      "alignment_kind": "related", "identity_field": "function_id", "version_field": "effective_version",
      "where": { "has_capability_semantics": true } },
    { "source_type": "ExampleBank.SolutionBuildingBlock", "target_type": "A3.ApplicationComponent",
      "alignment_kind": "specialization", "identity_field": "block_id",
      "where": { "category": "application_component" } },
    { "source_type": "ExampleBank.CloudResource", "target_type": "example-cloud:ComputeResource",
      "alignment_kind": "specialization", "identity_field": "resource_id",
      "where": { "kind": ["vm", "compute_instance"] },
      "exclude_ids": ["bucket-*"] }
  ],
  "types": [
    { "type": "example-cloud:ComputeResource", "extends": "A4.Node", "definition_source": "bank_extension", "definition": "Compute capacity instance" }
  ]
}
```

**Decided:** no expression language. `where` is equality / set-membership on attributes; `include_ids` / `exclude_ids` are literal or glob. This satisfies the S3-bucket test (`kind: s3_bucket` matches no `where`; or it is excluded by id). Expressions are reconsidered only if real profiles demonstrate the need, and would never be evaluated with `eval`.

A profile may add types (`types[]`, always `extends` a core entity) and may require optional reference fields. It may not redefine a core entity or any `bian_reference` entity.

### 7.2 Resolution interfaces

```python
class EntityResolver(Protocol):
    def resolve_entity(self, ref: EntityReference) -> ResolvedEntity | None: ...
    # v0.2.1 signature resolve_entity(id, type, version) remains supported via a thin adapter

class ReferenceResolver(Protocol):                      # unchanged from v0.2.1
    def resolve(self, canonical_id: str, release: str) -> ReferenceBinding | None: ...
```

`ResolvedEntity` carries `id`, `type`, `version`, `source_system`, `lifecycle_status`, `attributes`. A missing or unauthorised lookup yields **`unverified`**, never a pass.

---

## 8. Validation stages and verdicts

| Stage | Question | Outcome field |
|---|---|---|
| 1 Schema | Is the document well-formed? | `structural` |
| 2 Metamodel | Does each endpoint type exist in the catalogue (is-a), is the relationship registered for those types? | `structural` |
| 3 Profile | Does each bank type satisfy its mapping's `where` / id rules? | `structural` |
| 4 Identity | Do both endpoints resolve at the stated version? | `referential` (`pass` / `fail` / `unverified` when no resolver) |
| 5 BIAN | Is each `canonical_id` valid in the stated release, with the right element class? | `bian` (`pass` / `fail` / `unverified`) |
| 6 Governance | Evidence kinds, reviewer, timestamp, baseline, supersession, transitions (`sdmm-diff`) | `governance` |
| 7 Semantics | Does the evidence justify the relationship? | always `unverified` in v0.4 — out of scope |

`--json` gains a `verdicts` map per mapping: `{structural, referential, bian, governance, semantic}`. These are **never** collapsed into one flag. `approved` is a lifecycle status, not a verdict.

---

## 9. BIAN verification register

Verification is possible against the public InSite portal (R1). Reproduction is not. The register records the act of checking, not the content.

```jsonc
// metamodel/verification/bian-14.0.json
{
  "release": "14.0",
  "portal": "https://bian.org/servicelandscape-14-0-0/",
  "verified_by": "<name or role>", "verified_at": "2026-11-03",
  "access": "public InSite portal, read only",
  "checks": [
    { "type": "A2.ServiceDomain", "concept": "Service Domain", "where": "MetaModel Overview",
      "result": "confirmed_in_official_source", "note": "element class and relationship to Business Domain confirmed" },
    { "type": "A2.BehaviorQualifier", "concept": "Behavior Qualifier", "where": "MetaModel Overview",
      "result": "interpreted_from_official_source", "note": "term present; multiplicity to Service Domain not stated" }
  ]
}
```

Rules: an entity's `evidence_status` is computed from the register at load time, never hand-edited; a check without `verified_by` / `verified_at` is ignored; the register contains no definitions, diagrams or identifiers beyond the concept name needed to locate it. This is the employer's licensed seat doing the reading and the public repo recording that it was done.

---

## 10. Compatibility and migration

- v0.2.1 documents validate unchanged: new reference fields are optional; new document pins are optional; eight rules unchanged; `A4.InfrastructureComponent` remains a legal (now abstract) endpoint via is-a.
- `tests/test_v02_compatibility.py` is a release gate: both shipped examples must pass under the v0.4 catalogue with zero issues and zero new warnings.
- Unknown entities become an **error** in v0.4.0 (today only the registry triple catches them). Example documents already use only catalogued types.

---

## 11. Sequencing

| Release | Scope | Acceptance |
|---|---|---|
| **v0.3** (published) | `sdmm-trace` | Reviewer's Card Fraud Alerts demo runs from the CLI |
| **v0.4.0** Entity metamodel (additive) | `metamodel/` catalogue (31 core), `extends`/`abstract`, is-a matching, `DEPLOYED_AS`, verdicts in `--json`, `metamodel_version` pin, taxonomy self-check | v0.2.1 examples unchanged; `DEPLOYED_ON → A4.Node` passes; unknown type fails |
| **v0.4.1** Profiles and resolution | JSON profiles, static `where`/id rules, `resolve_entity(ref)`, `example-bank` and `example-cloud` profiles, `profile_id` pin | BusinessFunction / SBB / CloudResource resolve; S3 bucket → ComputeResource rejected |
| **v0.4.2** BIAN verification register | `metamodel/verification/`, computed `evidence_status`, register-driven report | Zero `bian_reference` types confirmed without a register entry |

Then v0.5 impact analysis, v0.6 BIAN reference adapter, v0.7 AI-assisted proposals, v1.0 conformance profile.

---

## 12. Repository layout (v0.4.0 → v0.4.2)

```text
metamodel/
├── entity.schema.json          # shape of an entity record (§3)
├── l0-business.json
├── l1-bian.json                     # entities + artefacts
├── l2-application.json
├── l3-infrastructure.json
└── verification/
    └── bian-14.0.json               # v0.4.2
profiles/
├── profile.schema.json              # v0.4.1
├── example-bank.json
└── example-cloud.json
sdmm/
├── metamodel.py                     # load catalogue, is-a, evidence_status from register
├── profiles.py                      # v0.4.1
├── reference.py                     # ReferenceResolver, EntityResolver (unchanged home)
├── validate.py                      # stages 1–6, verdicts
├── diff.py
└── trace.py                         # v0.3
tests/
├── test_metamodel.py
├── test_profiles.py
└── test_v02_compatibility.py
```

No `sdmm/resolver.py`: resolvers stay in `reference.py`.

---

## 13. References and licensing boundary

- **[R1]** BIAN Service Landscape 14.0, InSite portal: https://bian.org/servicelandscape-14-0-0/ (publicly browsable; no licence text displayed; treated as read-only reference)
- **[R1]** BIAN Service Landscape releases: https://bian.org/deliverables/service-landscape/
- **[R2]** BIAN BCM, *Statement of Alignment*: https://bian.org/wp-content/uploads/2023/08/BIAN-BCM-Relationship-with-BIAN-Service-Landscape-Final.pdf
- **[R4]** BIAN Semantic API Practitioner Guide: https://bian.org/wp-content/uploads/2024/12/BIAN-Semantic-API-Pactitioner-Guide-V8.1-FINAL.pdf
- **[R5]** ArchiMate 3.2: https://www.opengroup.org/archimate-licensed-downloads
- **[R6]** TOGAF Standard: https://www.opengroup.org/togaf
- **[R7]** SDMM: https://github.com/taumoeps/bian-sdmm-framework

Nothing from R1–R6 is reproduced in this repository. Type `definition` fields are SDMM paraphrases. `reference.uri` points to the official source; it never substitutes for it. SDMM is independent of, and not endorsed by, BIAN or The Open Group.

---

## 14. Decisions recorded for v0.4.0

| # | Question | Decision |
|---|---|---|
| 1 | Core entity list | The 31 types in §5 are confirmed. `A3.Application` and `A3.Integration` are out of core; `A4.Deployment` is in |
| 2 | `DEPLOYED_AS` rule | `authority: enterprise_rule`, `perspective: architecture`, `required_evidence: ["deployment_design"]` — identical governance to `DEPLOYED_ON` |
| 3 | Register `verified_by` | A **role** (e.g. `lead-domain-architect`) in the public register. An institution's private copy may record the individual |
| 4 | `source_system` on references | Optional in core. Mandatory in the institution's own profile from first use, because it is trivial to add at authoring time and costly to backfill |

**Approval criterion (unchanged):** no SDMM entity may claim canonical-standard status without a release-specific verification record.
