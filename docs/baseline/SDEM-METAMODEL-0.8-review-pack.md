# SDEM-METAMODEL-0.8 — Baseline Review Pack

> Prepared 2026-10-25 by `python scripts/baseline_pack.py` from the records at commit `a38dfe2`. A snapshot for review, not a living document.

## 1. What a baseline is, and what you are asked to approve

A **baseline** freezes one reviewed version of the SDEM blueprint under a name, **SDEM-METAMODEL-0.8**. Tool adapters build against it, approved relationship records point to it, and later changes are made as new versions with a change log. Approving it means: *the model is fit to receive real architecture data, and its sources, reasoning and confidence ratings are credible.* It does not mean every rating is high — the limitations in §4 are part of what is approved.

**Who should review.** An architect independent of the author, familiar with at least one of BIAN, ArchiMate or TOGAF. They need no employer data: everything here is public or synthetic. Expected effort: about a day for §5, longer if they re-check sources.

## 2. What is being baselined

| Part | Records | Count | Rendered as |
|---|---|---|---|
| Entity types | `metamodel/a1…a4-*.json` | 44 (40 instance types, 3 artefacts, 1 abstract) | `docs/architecture-entity-design.md` |
| Within-level relationships | `metamodel/level-relationships.json` | 132 rows + 12 inheritance | `docs/relationships-planning.md` |
| Cross-level relationship types | `schema/relationship-types.json` | 9 | `docs/relationship-registry-spec.md` |
| Relationship rules | `metamodel/relationship-rules.json` | 69 | `docs/relationship-rules-spec.md` |
| Attributes | `metamodel/entity-attributes.json` | 9 core, 11 common, 135 entity-specific, 3 derived (1 deprecated kept for compatibility) | `docs/architecture-attribute-design.md` |
| Logical data model | `sdem/logical.py`, `sdem/conformance.py` | 14 rules, all enforced | `docs/logical-data-model.md` |
| Physical data model | `schema/entities/*/*.schema.json` | 40 JSON Schemas | `docs/physical-data-model.md` |
| Data-model review records | `metamodel/drafts/a1…a4-descriptive-attributes.json` | 4 (all approved) | `docs/drafts/data-model-a1…a4-draft.md` |

Not in scope: the inference engine (not built), the Relationship Registry contents (institution data), and the example estates (synthetic test data).

## 3. Evidence

| Check | Result |
|---|---|
| Unit tests | 197 tests — OK |
| Example estates against the enforced data model (`sdem-graph check`) | 8 estates, 527 instances: **0 errors**, 46 warnings, all minimum-cardinality completeness gaps (an example, or the generated reference-structure estate, holds part of BIAN's structure) |
| Example instances against the physical schemas | 527 instances, **0 failing** |
| Within-level rows checked against a standard | 16 against BIAN public material, 113 against the Archi oracle (open-source ArchiMate relationship tables); 2 TOGAF-only, 1 SDEM reading |
| Cross-level rules | all 69 plan rows covered by the use-case runs: 45 validated, 5 validated with findings, 19 not applicable (`docs/relationships-testing.md`, `docs/use-case-testing.md`) |
| Source references | every entity, row, type, rule and attribute names its source; enforced by test |
| Confidence | one rule (`sdem/confidence.py`) assigns every rating; CI fails if any record disagrees |
| Generated documents | every document and schema is generated from the records; CI fails if any is stale |

**Confidence across 340 rated definitions** (entities, within-level rows, relationship types, core, common and entity-specific attributes): **237 high (70%), 81 medium (24%), 22 low (6%)**. High = defined by a public standard and checked; medium = built on a standard concept, or a standard that could not be checked; low = SDEM-defined with no standard basis.

| Layer | High | Medium | Low |
|---|---|---|---|
| Entity types | 32 | 12 | 0 |
| Within-level rows | 129 | 2 | 1 |
| Relationship types | 3 | 6 | 0 |
| Core fields | 9 | 0 | 0 |
| Common attributes | 9 | 2 | 0 |
| A1 attributes | 8 | 19 | 13 |
| A2 attributes | 18 | 6 | 1 |
| A3 attributes | 17 | 17 | 3 |
| A4 attributes | 12 | 17 | 4 |
| Relationship rules (basis; 5 rows n/a — not used: not encodable or a historical method) | 22 | 42 | 0 |

## 4. Known limitations (approved as part of the baseline)

1. **Login-gated standards not checked.** TOGAF and the ArchiMate specification text need an Open Group login. Affected: `A3.SolutionBuildingBlock`, `RA3-30`, `RA3-31`, `A3.SolutionBuildingBlock.components`. ArchiMate relationships were checked against the open-source Archi implementation instead.
2. **BIAN below A2.** BIAN publishes no capability-to-Service-Domain mapping and almost nothing below A2, so most cross-level rules are SDEM's design, validated by the use cases rather than by a standard.
3. **BIAN portal Service Domain pages** returned "not found" during the A2 review; no attribute rests on them. The HTTP-method default (DV-A2-02) rests partly on BIAN's published API files, not yet checked (medium).
4. **ISO 3166** could not be opened (iso.org 403); `country` is medium.
5. **21 SDEM-defined (low) attributes** — kept deliberately because they answer frequent design questions no open standard covers: `A1.BusinessCapability.strategic_importance`, `A1.BusinessCapability.maturity_current`, `A1.BusinessCapability.maturity_target`, `A1.ValueStreamStage.entrance_criteria`, `A1.ValueStreamStage.exit_criteria`, `A1.BusinessProcess.criticality`, `A1.BusinessProcess.frequency`, `A1.BusinessProcess.automation_level`, `A1.BusinessService.customer_facing`, `A1.BusinessService.channels`, `A1.BusinessService.service_level`, `A1.BusinessActor.external`, `A1.BusinessRequirement.priority`, `A2.ServiceDomain.adoption_status`, `A3.ApplicationComponent.disposition`, `A3.DataEntity.system_of_record`, `A3.DataEntity.retention_period`, `A4.DeploymentEnvironment.environment_kind`, `A4.Device.end_of_support`, `A4.SystemSoftware.end_of_support`, `A4.Path.encrypted`.
6. **1 within-level row(s) resting on an SDEM reading** with no standard relationship: `RA2-17` (A2.BOMModel aggregation A2.BusinessObject).
7. **Licensed BIAN validation** has not been done (needs BIAN membership).
8. **No real data yet.** Everything has been exercised on synthetic estates only; the first adapter on real data may find gaps.

## 5. Review checklist

Answer each with **yes / no / comment**. A "no" on 1–6 blocks the baseline; others can be accepted as findings.

| # | Question | Where to look |
|---|---|---|
| 1 | Are the entity types the right set for business, BIAN service domain, application and technology architecture — nothing essential missing, nothing redundant? | `architecture-entity-design.md` |
| 2 | Do the within-level relationships reflect BIAN and ArchiMate as you understand them? Spot-check ten rows against the cited source. | `relationships-planning.md` |
| 3 | Are the nine cross-level relationship types meaningful and distinct? | `relationship-registry-spec.md` |
| 4 | Spot-check ten attributes rated **high**: does the cited section really define that attribute? | `architecture-attribute-design.md` |
| 5 | Is any attribute rated higher than its source justifies? | same |
| 6 | Is there any sign of proprietary content (BIAN or Open Group text reproduced, employer entities or IDs)? | all documents |
| 7 | Are the low (SDEM-defined) attributes worth keeping? | §4 item 5 |
| 8 | Are the required/optional choices sensible (almost everything optional)? | `physical-data-model.md` |
| 9 | Are derived attributes (criticality, HTTP method default) the right choice over stored ones? | `architecture-attribute-design.md` §4 |
| 10 | Do the 14 logical rules make sense as errors vs warnings? | `logical-data-model.md` |
| 11 | Could an adapter author build an exporter from the physical schemas alone? | `schema/entities/` |
| 12 | Are the limitations in §4 acceptable for a first baseline? | §4 |

## 6. Sign-off

| Role | Name | Decision (approve / approve with findings / reject) | Date |
|---|---|---|---|
| Model owner | Steven Taumoepeau | | |
| Independent reviewer | | | |


**Note on "generated documents".** CI proves each document matches what its generator produces from the records; it cannot prove the wording inside the records is current. Wording was reviewed by reading all of `docs/` on 2026-10-25.

Findings: record each as a GitHub issue labelled `baseline-0.8` and list them here.

## 7. On approval

1. Record the approval in `metamodel/baseline.json` (baseline name, commit, reviewer, date, accepted findings).
2. Set `metamodel_version` to `0.8.0` in the four level files and the example exports.
3. Remove what was kept only for compatibility: the deprecated `accesses` attribute definition and the `sdmm` package and commands (planned for v0.8.0).
4. Tag the commit `SDEM-METAMODEL-0.8` and publish release v0.8.0 (with your approval).
5. From then on, model changes go through a change record and a new version.

