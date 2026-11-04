# SDEM requirements and risk analysis — specification

> **Status: built (v0.11.0, 2026-11-01).** Owner's decisions (2026-11-01): Option A — a governed requirements registry per workspace; reuse A1.BusinessRequirement; no new A2–A4 entity types; integrate with the four-layer impact validation ([agent platform spec §11](sdem-agent-platform-spec.md#11-four-layer-impact-validation-owners-requirement-2026-11-01)); no second engine, lifecycle or orchestrator. Code: `sdem/requirements.py`; schemas `schema/requirements.schema.json`, `schema/risk-rules.json`; tests `tests/test_requirements_risk.py`. The owner's original *Cross-Layer Requirements & Risk Analysis* specification was not received; the five scenarios and AT-RR-01…20 below are reconstructed from the owner's two implementation messages and are to be reconciled with it.

## Why

Real GitHub Copilot testing of the Kubernetes rehost (CE-001) showed: the A4 agent found an affected artifact (ART-PAYHUB-IMG) the structural calculation did not name; the A2 agent found a missing approved link (SD-PE REALIZED_BY CMP-PAY-EXEC); the stored graph was stale; and A1 and A2 were *no impact* although nobody had asked whether continuity, availability, recovery, performance or compliance still held. **A finding of no structural change never means no business or operational risk.**

## Separation

| Engine | Decides | Where |
|---|---|---|
| Structural impact | which records and approved links a change reaches | `sdem/graph.py` (unchanged rules; coverage adds what it could not see) |
| Requirements and constraints | whether confirmed requirements hold, now and in the proposed architecture | `sdem/requirements.py` |
| Risk analysis | evidence-backed findings: confirmed breaches, potential scenarios, missing evidence, assumptions | `sdem/requirements.py` + `schema/risk-rules.json` |
| Impact assurance | review and decision — each layer's specialist, then a person | the existing validation record and acceptance (`sdem events …`) |

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| RR-D01 | **A governed registry**, `<workspace>/requirements.json` (schema `requirements.schema.json`): each requirement has an id, a version, a status (`proposed`, `confirmed`, `retired`, `superseded`), a name and statement, an owning layer (A1–A4) and owner, a category, a scope (`end_to_end` or `component`), a **subject**, records it is **allocated to**, the requirements or A1.BusinessRequirement records it is **derived from**, a **measurable condition** (metric, operator, value, unit, period), evidence, provenance and a history. | AT-RR-01 |
| RR-D02 | **Measurements**: stated values for a record and metric, `current` or `proposed`, each with evidence and provenance. A proposed measurement may name a record that does not exist yet. | AT-RR-06, S1–S5 |
| RR-D03 | **Governed changes**: `sdem requirements propose` adds requirements (one, a list or a registry) or new versions, always as *proposed*; only a **person** confirms (`confirm`) or retires it; every step is in its history; measurements (`measure`) are recorded against a person (and the agent, if any). Every write is checked first. | AT-RR-02 |
| RR-D04 | **Traceability**: `sdem requirements trace` shows a requirement's subject and allocations through the layers (what they serve and depend on, by approved links) and its derivation both ways. | AT-RR-03 |
| RR-D05 | `sdem check --workspace` checks the registry (schema, unique ids, references, histories, evidence on confirmed requirements); the ledger tracks `requirements.json`, so an edit made outside `sdem` is noticed. | AT-RR-01, AT-RR-20 |
| RR-D06 | **No registry is not no requirements**: a workspace without one, or a reached layer without confirmed requirements, is reported as such and raises a *missing evidence* finding — never *satisfied*. | AT-RR-08, AT-RR-09 |
| RR-E01 | **Scope**: a requirement is in scope when its subject or an allocated record is changed or reached by the structural impact (or replaces a changed record); a requirement it is derived from is then in scope too. Each says why. | AT-RR-04 |
| RR-E02 | **Exact comparisons**: numbers, percentages, durations (`ms` … `d`, also written `2h`), booleans, `in`/`not_in`; different units or kinds are *not evaluable*, never guessed. | AT-RR-06 |
| RR-E03 | **The proposed architecture** is read from the change set: a record whose attribute moved from S to T (a deployment's platform) makes T replace S. Before a change set exists, `--proposed` names the replacement. | AT-RR-07 |
| RR-E04 | **Applicability**: a requirement is judged on its **subject** only. A measurement of an allocated record never satisfies it — a platform's availability does not establish a business process's end-to-end availability (the evaluation says so). A subject the change does not affect keeps its current evidence; an affected one needs proposed evidence. Unconfirmed requirements are reported, never evaluated as obligations. | AT-RR-05, AT-RR-10 |
| RR-E06 | **Current and proposed compliance, kept apart** (v0.11.2): each requirement has a `disposition` — `compliant`, `current_breach_remediated` (breached today, the proposed architecture meets it — shown by a proposed measurement), `proposed_breach` (introduced by the change), `unresolved_breach` (breached today and in the proposed architecture), `missing_evidence` or `not_confirmed`. **`overall` describes the proposed state** (analysis `contract: 2`); today's result stays in `current`. Only a proposed-state breach is a `confirmed_breach` needing a person's decision; a remediated breach stays visible as a `remediated_breach` finding. An analysis from before v0.11.2 (no `contract`) is never reinterpreted: acceptance refuses it until `sdem events analyse` re-runs it. | Test A, B, C (`tests/test_governance_hardening.py`) |
| RR-E05 | **Per layer**: `breached`, `missing_evidence`, `satisfied`, `no_requirements_recorded` or `requirements_registry_missing` — beside, never instead of, the structural result. | AT-RR-20 |
| RR-K01 | **Finding types**: `confirmed_breach` (a proposed-state breach), `potential_risk`, `missing_evidence`, `assumption`, `remediated_breach` (informational: breached today, met by the proposed architecture — no decision needed), `accepted_residual_risk` (set only by a person on acceptance). | AT-RR-11, Test B |
| RR-K02 | A **confirmed breach** names the requirement, the measurements (evidence), the rule, the decision it needs and mitigations to consider. | AT-RR-12 |
| RR-K03 | **Assumptions**: a layer whose links are incomplete raises an assumption — that its unlinked records carry no requirement or dependency the change affects — to confirm or correct. | AT-RR-13 |
| RR-K04 | **Every confirmed breach is decided by a person** before implementation: the design changes (and the analysis is re-run), or it is accepted as a residual risk with a reason (`sdem events accept --accept-risk RF-…="…"`). | AT-RR-16 |
| RR-K05 | **Nothing invented**: scenarios, decisions and mitigations come from `schema/risk-rules.json` (governed, versioned); no likelihood, probability, loss, score, obligation or target appears anywhere — only what confirmed requirements and their evidence say. | AT-RR-11 |
| RR-K06 | **Before any change**: `sdem requirements evaluate --record <id> --change <kind> [--proposed <id>]` gives the structural impact, coverage, requirements, obligations and findings in one answer. | AT-RR-20 |
| RR-G01 | The analysis is stored **in the change event's validation record** when validation opens; `sdem events show` gives it with the assessments. | AT-RR-14 |
| RR-G02 | **Freshness**: the analysis and every assessment record the checksum of what they rest on (the layers, the registry, the requirements). `sdem events analyse` recomputes (earlier analyses kept); assessments made against other evidence — or before the analysis existed (no checksum: v0.10.0) — are **stale** and re-done; acceptance is refused while anything is stale; `sdem work plan` is refused if anything changed after acceptance. Validation reads the workspace's datasets, never a stored graph. | AT-RR-15, AT-RR-17 |
| RR-G03 | **Additional records**: records a specialist names that the calculation did not are kept apart (`additional_records`), shown, and get work items once accepted — in the changed layer too. Records linked inside the changed layer, which the impact rules do not follow, are listed in the coverage (`related_within_layer`). | AT-RR-18 |
| RR-G04 | **No bypass**: a layer agent's change set that touches records a not-yet-authorised change event affects is refused unless it answers an authorised work item; every change set records whether it is `initial` or `downstream`. A person may still make an initial change, on record. | AT-RR-19 |
| RR-G05 | **Trust boundary** (see [governance](sdem-governance.md)): `--person` is a claim, not authentication. Acceptance records beside it what the machine reports (OS user, git user) and says so; the control is the reviewed pull request — code owners on `coordination/` and `requirements.json` in the workspace template, branch protection, and CI. | AT-RR-20 |

## The five scenarios (synthetic payments data, `examples/payment-initiation/requirements.json`)

The A4 rehost of `INF-K8S-PAY-PROD` to `INF-K8S-PAY-PROD2`:

| # | Scenario | Requirements | Outcome |
|---|---|---|---|
| S1 | Availability and migration downtime | REQ-AV-01 (A1, end to end, PRC-PAY-01, ≥ 99.95 %) → REQ-AV-02 (A4, the platform) | REQ-AV-02 **breached** (99.9 % proposed); REQ-AV-01 **not shown** (no end-to-end evidence; the platform's figure does not establish it); potential risk: interruption during the cutover |
| S2 | Performance degradation | REQ-PF-01 (A3, Payments Hub p95 ≤ 300 ms) | satisfied today (220 ms), **no evidence** for the proposed platform; potential risk |
| S3 | Data residency and compliance | REQ-RES-01 (A1 obligation: New Zealand only) → REQ-RES-02 (A4 platform region) | REQ-RES-02 **breached** (AU); the A1 obligation exposed; decision: only its owner changes it |
| S4 | Real-time processing | REQ-RT-01 (A2, SD-PE ≤ 2 s) → REQ-RT-02 (A4 event streaming) | REQ-RT-02 **breached** (no streaming); REQ-RT-01 not shown; **assumption**: SD-PE has no approved link |
| S5 | Disaster recovery degradation | REQ-RC-01 (A3 RTO ≤ 2 h) → REQ-RC-02 (A4 second-region replica) | REQ-RC-02 **breached**; REQ-RC-01 satisfied today (1 h), not shown for the proposed platform |

Scenario tests: `tests/test_requirements_risk.py` (`Scenarios`), with the whole flow — A4 change → structural impact → requirements → risks → A1–A4 assessments (A4 naming ART-PAYHUB-IMG, A2 reporting the missing link) → acceptance with the four breaches accepted as residual risks → work items including the artifact.
