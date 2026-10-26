# Use-case example 1 — testing the rulebook

> **Status: run 2026-10-27 — results below.**

## Key words

- **Metamodel** — the rulebook: what records may exist, what they hold, how they may link.
- **Architecture dataset** — a file of one layer's records: business, BIAN, application or technology.
- **Rejected** — SDEM refuses data that breaks a rule, and says why.
- **Trace** — following the links from a server up to the business.

## Goal

Prove the rulebook works:

1. good data is **accepted**, bad data is **rejected**;
2. the four datasets get **linked** correctly;
3. you can **trace** from server to business.

## Test data

Payment-initiation example: 4 datasets, 68 records, **no links between them**, and an answer key of **18 links**.

## Is the engine simulated?

**No.** The real engine runs — a Python program (`sdem/rules_engine.py`), no AI, same result every time.

How it works: it reads the four datasets, applies the 69 link-finding rules step by step, and writes out the links it proposes, each with its reason.

Only **approval** is simulated — done by hand, standing in for an architect, until an approve command exists.

## What we test

| # | Rule | Example |
|---|---|---|
| 1 | Record types | only 44 known kinds of record |
| 2 | Record information | criticality must be high, medium or low |
| 3 | Links inside a layer | a process may contain activities, not a capability |
| 4 | Links between layers | only 9 kinds, e.g. *application runs on server* |
| 5 | Finding links | 69 rules for working out the links |
| 6 | Approving links | approved links can't be changed |
| 7 | Sources | every rule says where it comes from |

## Two runs

**Run 1 — good data.** Expect: all accepted · 18 of 18 links correct · trace complete.
**Result: ✅ all accepted · ✅ 18 of 18 correct · ✅ trace complete** (one link held back at approval — its BIAN identifier is missing from the data, and SDEM will not invent one).

**Run 2 — planted mistakes.** Expect each one caught:

| Mistake | Expect | Result |
|---|---|---|
| unknown kind of record | rejected | ✅ rejected |
| criticality "urgent" | rejected | ✅ rejected |
| process contains a capability | rejected | ✅ rejected |
| link between the wrong kinds of record | rejected | ✅ rejected |
| application doesn't say its server | no link made | ✅ safer than expected — the data is rejected before linking (a deployment must name its server) |
| edit an approved link | rejected | ✅ rejected |
| rule with no source | test fails | ✅ test fails |

Expected results are written down before the run.

## Output

Each result names the **control** that acted ([`controls-register.md`](controls-register.md)) and links to its **evidence** file.


| Rule | Data | Should | Did | ✅/❌ |
|---|---|---|---|---|
| 2 | criticality "urgent" | be rejected | *(when run)* | |

Plus: the 18 links found, the trace, and any gaps.

## Gaps already known

- **G-A** — the link-finding rules and the engine's code aren't checked against each other.
- **G-B** — limits on how many links of a kind may exist aren't checked.

## Limits

Made-up data · rules tuned on this example · approval by hand for now.

## Results — run 2026-10-27

**Verdict: 16 of 16 tests pass · 18 of 18 links correct · trace complete · gaps: G-A confirmed, G-B confirmed, no risk today.**

### How we know these results are right

| Proof | Where to see it |
|---|---|
| **The expected results were fixed before the run.** The plan with every expected result was committed before the first run. | git history of this document (plan commits precede the results commit) |
| **Each result is the control's own message**, not a summary we wrote. | the "Did" column quotes it; the evidence file holds the full output |
| **Every control is shown working both ways** — accepting good data and rejecting bad. | run 1 and run 2 rows below |
| **Every control is registered**: what it enforces, where it is built, where its outcome is recorded, what monitors it. | [`controls-register.md`](controls-register.md) |
| **The evidence is kept and tamper-evident**: 19 files with SHA-256 checksums, the code commit and the run date. | [`evidence/use-case-example-1/manifest.json`](evidence/use-case-example-1/manifest.json) |
| **It is reproducible and monitored**: the run is deterministic and re-runs on every push in CI. | `python scripts/use_case_example_1.py`; `tests/test_use_case_example_1.py` |

**What would still strengthen it:** an answer key written by someone other than the project, and a real architect approving instead of the simulated one.

### 1. Tests

| # | Rule area | Data given | Should | Did | Control | Evidence | ✅/❌ |
|---|---|---|---|---|---|---|---|
| 1 | 1–3 Records, information, links inside a layer | the four datasets as they are (68 records, 69 links inside layers) | accepted | accepted — 0 errors, 6 completeness warnings | CTL-01, CTL-02, CTL-03 | [run1-01-check.json](evidence/use-case-example-1/run1-01-check.json) | ✅ |
| 2 | Knowledge graph | build the graph store with no links between layers | built; 0 links between layers | accepted; 0 links between layers | CTL-15 | [run1-02-load-record.json](evidence/use-case-example-1/run1-02-load-record.json) | ✅ |
| 3 | 5 Finding links | engine applies the 69 link-finding rules | 18 links, all correct | 18 proposed — 18 correct, 0 wrong, 0 missed | CTL-09, CTL-10 | [run1-03-proposals.json](evidence/use-case-example-1/run1-03-proposals.json), [run1-04-inference-log.json](evidence/use-case-example-1/run1-04-inference-log.json), [run1-05-score.json](evidence/use-case-example-1/run1-05-score.json) | ✅ |
| 4 | 4 Links between layers | the 18 proposed links | all valid | valid | CTL-05, CTL-08 | [run1-06-validate-proposals.json](evidence/use-case-example-1/run1-06-validate-proposals.json) | ✅ |
| 5 | 6 Approving links | approve the 18 links with no evidence attached | rejected — each link type requires evidence | rejected — 22 problems, e.g. "evidence missing required kind(s) ['deployment_design']" | CTL-06 | [run1-07-approve-without-evidence.json](evidence/use-case-example-1/run1-07-approve-without-evidence.json) | ✅ |
| 6 | 6 Approving links | approve the 18 links with the required evidence | accepted, except a link whose BIAN identifier is missing from the data (never invented) | 17 accepted; 1 blocked — bian_alignment_guidance mapping requires canonical_id on its A2 target | CTL-06 | [run1-08-approve-with-evidence.json](evidence/use-case-example-1/run1-08-approve-with-evidence.json) | ✅ |
| 7 | 6 Approving links | edit an approved link afterwards | rejected | rejected — "P-UCE1-001: approved record is immutable but field(s) changed: ['rationale']" | CTL-07 | [run1-10-edit-after-approval.json](evidence/use-case-example-1/run1-10-edit-after-approval.json) | ✅ |
| 8 | Trace | from the production server up to the business | reaches the Payment Initiation domain, the payment processes and the Initiate Payment capability | reached: APP-PAY-HUB, CAP-PAY-010, CMP-PAY-EXEC, PRC-PAY-01, PRC-PAY-02, SD-PI | output (trace) | [run1-12-trace-and-impact.json](evidence/use-case-example-1/run1-12-trace-and-impact.json) | ✅ |
| 9 | Trace | from the Initiate Payment capability down to technology | reaches the production server | reached: APP-PAY-HUB, DEP-PAYHUB-PROD, DEP-PAYHUB-UAT, INF-K8S-PAY-PROD, INF-K8S-PAY-UAT, SD-PI | output (trace) | [run1-12-trace-and-impact.json](evidence/use-case-example-1/run1-12-trace-and-impact.json) | ✅ |
| 10 | 1 Record types | a record of an unknown kind (A1.BusinessWidget) | rejected | rejected — "instance PRC-PAY-01: entity 'A1.BusinessWidget' is not in the metamodel" | CTL-01 | [run2-1-unknown-type.json](evidence/use-case-example-1/run2-1-unknown-type.json) | ✅ |
| 11 | 2 Record information | a process with criticality "urgent" | rejected | rejected — "attribute 'criticality' value 'urgent' is not one of ['high', 'medium', 'low'] (LC-06)" | CTL-02 | [run2-2-bad-value.json](evidence/use-case-example-1/run2-2-bad-value.json) | ✅ |
| 12 | 3 Links inside a layer | a process that "contains" a capability | rejected | rejected — "A1 relationship A1.BusinessProcess -composition-> A1.BusinessCapability does not match the ArchiMate 3.2 / TOG" | CTL-03 | [run2-3-disallowed-link.json](evidence/use-case-example-1/run2-3-disallowed-link.json) | ✅ |
| 13 | 4 Links between layers | a "uses domain" link from a capability (only processes may use a domain) | rejected | rejected — "relationship (A1.BusinessCapability, USES_DOMAIN, A2.ServiceDomain) is not in the registry" | CTL-05 | [run2-4-wrong-link-type.json](evidence/use-case-example-1/run2-4-wrong-link-type.json) | ✅ |
| 14 | 5 Finding links | 5a — the Payments Hub no longer names its server, but its deployment records still do | the "runs on" links still found from the deployment records; nothing invented | 2 "runs on" links found, from the deployment records; 0 wrong | CTL-09, CTL-10 | [run2-5a-application-silent.json](evidence/use-case-example-1/run2-5a-application-silent.json) | ✅ |
| 15 | 5 Finding links | 5b — nothing names the Payments Hub's server (its deployments drop it too) | no "runs on" link made; nothing invented | stricter than expected: the data is rejected before the engine runs — "required attribute 'platform_id' missing (LC-04)" | CTL-02, CTL-15 | [run2-5b-no-server.json](evidence/use-case-example-1/run2-5b-no-server.json) | ✅ |
| 16 | 7 Sources | rule B01 with its source removed | the completeness test fails | fails — AssertionError: True is not false : rule B01 | CTL-11 | [run2-7-rule-without-source.json](evidence/use-case-example-1/run2-7-rule-without-source.json) | ✅ |

### 2. Links found (run 1) — 18

| From | Link | To | Rule | Why | Confidence | Matches answer key |
|---|---|---|---|---|---|---|
| APP-PAY-HUB | DEPLOYED_AS | DEP-PAYHUB-PROD | S32 | data join; a4 DEP-PAYHUB-PROD.component_id = APP-PAY-HUB; a3 APP-PAY-HUB.deployed_as lists DEP-PAYHUB-PROD | 0.8 | ✅ |
| APP-PAY-HUB | DEPLOYED_AS | DEP-PAYHUB-UAT | S32 | data join; a4 DEP-PAYHUB-UAT.component_id = APP-PAY-HUB; a3 APP-PAY-HUB.deployed_as lists DEP-PAYHUB-UAT | 0.8 | ✅ |
| CMP-PAY-EXEC | DEPLOYED_AS | DEP-PAYEXEC-PROD | S32 | data join; a4 DEP-PAYEXEC-PROD.component_id = CMP-PAY-EXEC; a3 CMP-PAY-EXEC.deployed_as lists DEP-PAYEXEC-PROD | 0.8 | ✅ |
| APP-PAY-HUB | DEPLOYED_ON | INF-K8S-PAY-PROD | S33 | data join (S36 subsumed in S33); a3 APP-PAY-HUB.deployed_on lists INF-K8S-PAY-PROD; a4 INF-K8S-PAY-PROD.hosts … | 0.8 | ✅ |
| APP-PAY-HUB | DEPLOYED_ON | INF-K8S-PAY-UAT | S33 | data join (S36 subsumed in S33); a3 APP-PAY-HUB.deployed_on lists INF-K8S-PAY-UAT; a4 INF-K8S-PAY-UAT.hosts li… | 0.8 | ✅ |
| CMP-PAY-EXEC | DEPLOYED_ON | INF-K8S-PAY-PROD | S33 | data join (S36 subsumed in S33); a3 CMP-PAY-EXEC.deployed_on lists INF-K8S-PAY-PROD; a4 INF-K8S-PAY-PROD.hosts… | 0.8 | ✅ |
| SO-PI-01 | IMPLEMENTED_BY | API-PI-01 | S24 | decision 1: Initiate ↔ POST; no qualifier, none in path; payload 8 matched (100%): ['amount', 'creditoraccount… | 0.8 | ✅ |
| SO-PI-02 | IMPLEMENTED_BY | API-PI-02 | S24 | decision 1: Evaluate ↔ POST; qualifier in path; payload 3 matched (100%): ['authorisationstatu', 'paymentinstr… | 0.8 | ✅ |
| SO-PI-03 | IMPLEMENTED_BY | API-PI-03 | S24 | decision 1: Execute ↔ PUT; qualifier in path; payload 3 matched (100%): ['executionreference', 'paymentinstruc… | 0.8 | ✅ |
| SO-PI-05 | IMPLEMENTED_BY | API-PI-05 | S24 | decision 1: Update ↔ PATCH; no qualifier, none in path; payload 5 matched (100%): ['amount', 'creditoraccountr… | 0.8 | ✅ |
| SO-PI-04 | IMPLEMENTED_BY | API-PI-04 | S24 | decision 2: Retrieve on POST; no qualifier, none in path; payload 4 matched (100%): ['authorisationstatu', 'ex… | 0.6 | ✅ |
| BBO-PAY-INSTR | MAPPED_TO | ENT-PAY-INSTR | S30 | 8/8 BOM attributes matched (100%): ['amount', 'creditoraccountreference', 'currency', 'debtoraccountreference'… | 0.8 | ✅ |
| BO-PAY-INSTR | ALIGNED_TO | BBO-PAY-INSTR | S12 | 4/8 BOM attributes covered by the glossary (50%) | 0.6 | ✅ |
| VS-MAKE-PAYMENT | ALIGNED_TO | BS-CREDIT-TRANSFER | S02 | 4/4 scenario operations covered in order by stage verbs (100%): [('SO-PI-01', 'VSS-P1'), ('SO-PI-02', 'VSS-P2'… | 0.6 | ✅ |
| SD-PI | REALIZED_BY | APP-PAY-HUB | S17 | implements SO-PI-01 via API-PI-01 (P-UCE1-007); SO-PI-02 via API-PI-02 (P-UCE1-008); SO-PI-03 via API-PI-03 (P… | 0.8 | ✅ |
| PRC-PAY-01 | USES_DOMAIN | SD-PI | S04 | invokes SO-PI-01 (PRC-PAY-01.invokes); SO-PI-02 (PRC-PAY-01.invokes) | 0.6 | ✅ |
| PRC-PAY-02 | USES_DOMAIN | SD-PI | S04 | invokes SO-PI-03 (PRC-PAY-02.invokes); SO-PI-04 (PRC-PAY-02.invokes) | 0.6 | ✅ |
| CAP-PAY-010 | SUPPORTED_BY | SD-PI | S01 | all 2 processes of the capability use the domain | 0.6 | ✅ |

Refused by the engine, with the reason (2):

| Rule | What | Why refused |
|---|---|---|
| S24 | SO-PI-06 → API-PI-06 | no decision: action term 'Notify' has no REST form; no qualifier, none in path; payload 1 matched (50%): ['paymentinstructionreference'] |
| S01 | CAP-PAY-000 | parent capability — report-only, never proposed (M0 run 2) |

### 3. Trace

Links between layers after approval: 17 (one link blocked at approval — test 6).

**Up from the production server:**

- P-UCE1-004 DEPLOYED_ON → APP-PAY-HUB
- P-UCE1-015 REALIZED_BY → SD-PI
- P-UCE1-016 USES_DOMAIN → PRC-PAY-01
- P-UCE1-017 USES_DOMAIN → PRC-PAY-02
- P-UCE1-018 SUPPORTED_BY → CAP-PAY-010
- P-UCE1-006 DEPLOYED_ON → CMP-PAY-EXEC

**Down from the Initiate Payment capability:**

- P-UCE1-018 SUPPORTED_BY → SD-PI
- P-UCE1-015 REALIZED_BY → APP-PAY-HUB
- P-UCE1-001 DEPLOYED_AS → DEP-PAYHUB-PROD
- P-UCE1-002 DEPLOYED_AS → DEP-PAYHUB-UAT
- P-UCE1-004 DEPLOYED_ON → INF-K8S-PAY-PROD
- P-UCE1-005 DEPLOYED_ON → INF-K8S-PAY-UAT

**Impact of rehosting the production server:** INF-K8S-PAY-PROD (A4, design_change_required), APP-PAY-HUB (A3, design_change_required), SD-PI (A2, no_impact), PRC-PAY-01 (A1, no_impact), PRC-PAY-02 (A1, no_impact), CAP-PAY-010 (A1, no_impact), CMP-PAY-EXEC (A3, design_change_required)

### 4. Gaps

| Gap | Finding | Detail |
|---|---|---|
| G-A | confirmed | the engine reads only each rule's step and confidence from the rulebook; how a rule matches is in the engine's code, and nothing checks it against the rule's description |
| G-B | confirmed, no risk today | link-type limits are not checked, but all 9 link types are many_to_many, so there is no limit to break yet |
