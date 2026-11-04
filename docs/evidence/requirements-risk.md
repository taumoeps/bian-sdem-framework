# Requirements and risk analysis — what was built and how it was tested

> **Status: released in v0.11.0 (2026-11-01).** Made-up data only. Requirements: [requirements and risk spec](../design/sdem-requirements-risk-spec.md) (RR-D01…RR-G05). The owner's original specification was not received; its five scenarios are implemented as named, and the 20 acceptance tests here (AT-RR-01…20) are reconstructed from the owner's instructions — to be reconciled with the original.

## The question it answers

*An infrastructure architect is about to rehost the production Kubernetes platform. What does that do to the business?*

```bash
sdem requirements evaluate --workspace <dir> --record INF-K8S-PAY-PROD --change rehost --proposed INF-K8S-PAY-PROD2
```

One answer, all deterministic: the dependent A3 applications and A2 service domains (structural impact and its coverage), the A1 obligations exposed, the requirements in scope and whether each holds now and on the proposed platform, the confirmed breaches, the potential risks, the missing evidence and incomplete links — each with the decision it needs. Then, for the change itself, the same analysis is stored with the change event's four-layer impact validation, every layer's agent assesses it, and a person decides every breach before implementation is authorised.

## End to end — the rehost

[Transcript](requirements-risk/transcript.txt), on a fresh copy of the payments example:

| Step | What happened |
|---|---|
| Before the change | 4 **confirmed breaches** on the proposed platform — availability 99.9 % against 99.95 % (REQ-AV-02), region AU against NZ (REQ-RES-02), no event streaming (REQ-RT-02), no second-region replica (REQ-RC-02); **missing evidence** for performance (REQ-PF-01), recovery time (REQ-RC-01) and the end-to-end business objectives (REQ-AV-01, REQ-RES-01, REQ-RT-01 — the platform's figures do not establish them); **potential risks** per category, including interruption during the cutover; **assumptions** in every layer with unlinked records; A1 obligations REQ-AV-01 and REQ-RES-01 exposed. A1 and A2: *no structural impact* — and still *missing evidence*, never *satisfied*. |
| The A4 change set | CS-001 → CE-001; `sdem events validate` stores the analysis with the validation |
| A downstream change too early | the A3 agent's change set **refused** (AG-V08): its records are affected by CE-001, not yet authorised |
| Assessments | A4 confirms and names **ART-PAYHUB-IMG** (linked inside A4; also listed by the coverage) — kept as an *additional record*; A2 confirms no structural impact and reports the **missing link** SD-PE REALIZED_BY CMP-PAY-EXEC |
| New evidence | a proposed performance measurement for the Payments Hub → acceptance **refused** (RR-G02: changed since the analysis); `sdem events analyse` → REQ-PF-01 now *satisfied*; the layers re-assess |
| The architect | acceptance **refused** until each confirmed breach is decided (RR-K04); accepted with four named residual risks and reasons |
| Implementation | `sdem work plan`: work items for APP-PAY-HUB, CMP-PAY-EXEC — and **ART-PAYHUB-IMG**, from the A4 agent's finding |
| `sdem check` | passes — layers, links, coordination records, the requirements registry |

## Tests

`tests/test_requirements_risk.py` — **all pass**:

| | Test | Checks |
|---|---|---|
| S1 | availability and migration downtime | REQ-AV-02 breached on the proposed platform; REQ-AV-01 not shown; the cutover scenario |
| S2 | performance degradation | satisfied now, not shown on the proposed platform; potential risk |
| S3 | data residency and compliance | REQ-RES-02 breached (AU); the A1 obligation exposed; only its owner changes it |
| S4 | real-time processing | REQ-RT-02 breached; REQ-RT-01 in scope by allocation; the SD-PE gap as an assumption |
| S5 | disaster recovery degradation | REQ-RC-02 breached; RTO compared as durations |
| — | the whole flow | A4 change → impact → requirements → risks → A1–A4 → acceptance with residual risks → work items including ART-PAYHUB-IMG |
| AT-RR-01…05 | registry checks; governed writes (only a person confirms; versions); traceability A4→A1 and to A1.BusinessRequirement; scope with reasons; an allocated figure never satisfies an end-to-end requirement |
| AT-RR-06…10 | exact comparisons and units; the proposed architecture from the change set; no registry is not satisfied; a reached layer without requirements is flagged; unconfirmed requirements are not obligations |
| AT-RR-11…14 | five finding types, nothing invented; a breach carries evidence, rule, decision; incomplete links are assumptions; the analysis lives in the validation record |
| AT-RR-15…17 | stale assessments re-done (finding ids stable); breaches decided by a person; a change after acceptance voids it |
| AT-RR-18…20 | additional records visible and planned; no downstream change before authorisation; the infrastructure architect's whole question answered; identity recorded as a claim |

The v0.10.0 impact validation tests (T1–T12), use-case example 3 and the rest of the suite pass unchanged in behaviour, with and without an install.

**Found while building:** finding ids were first numbered in order, so re-running the analysis after new evidence renumbered them — an acceptance could have named the wrong finding. They are now derived from what each finding is about (`RF-BREACH-REQ-RC-02`) and are stable; a test holds that.

## Known limitations

- **Live Copilot behaviour is not verified by these tests.** Whether the agents read the analysis, name additional records and leave every breach to the architect needs a real run.
- **`--person` is a claim.** SDEM records the OS and git user beside it; the control is the reviewed pull request (code owners on `coordination/` and `requirements.json`).
- **Evaluation needs measurements.** A requirement without one is *not evaluable* — by design; SDEM never estimates a value.
- **The substitution is read from attributes that move** (a deployment's platform); a change that replaces a record some other way needs `--proposed` or a proposed measurement on the subject.
- **Risk scenarios are only as broad as `schema/risk-rules.json`** — six rules today, one per category and a general one.
