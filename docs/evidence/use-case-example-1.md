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

Each result names the **control** that acted ([`controls-register.md`](../reference/controls-register.md)) and links to its **evidence** file.


| Rule | Data | Should | Did | ✅/❌ |
|---|---|---|---|---|
| 2 | criticality "urgent" | be rejected | *(when run)* | |

Plus: the 18 links found, the trace, and any gaps.

## Gaps already known

- **G-A** — the link-finding rules and the engine's code aren't checked against each other.
- **G-B** — limits on how many links of a kind may exist aren't checked.

## Limits

Made-up data · rules tuned on this example · approval by hand for now.

## Results — run 2026-10-31

**Verdict: 30 of 30 tests pass · 18 of 18 links correct · trace complete · gaps: G-A partly closed (CTL-22), G-B confirmed, no risk today.**

### How we know these results are right

| Proof | Where to see it |
|---|---|
| **The expected results were fixed before the run.** The plan with every expected result was committed before the first run. | git history of this document (plan commits precede the results commit) |
| **Each result is the control's own message**, not a summary we wrote. | the "Did" column quotes it; the evidence file holds the full output |
| **Every control is shown working both ways** — accepting good data and rejecting bad. | run 1 and run 2 rows below |
| **Every control is registered**: what it enforces, where it is built, where its outcome is recorded, what monitors it. | [`controls-register.md`](../reference/controls-register.md) |
| **The evidence is kept and tamper-evident**: 34 files with SHA-256 checksums, the code commit and the run date. | [`evidence/use-case-example-1/manifest.json`](use-case-example-1/manifest.json) |
| **It is reproducible and monitored**: the run is deterministic and re-runs on every push in CI. | `python scripts/use_case_example_1.py`; `tests/test_use_case_example_1.py` |

**What would still strengthen it:** an answer key written by someone other than the project, and a real architect approving instead of the simulated one.

### Controls output — what each control did

Every control in the [controls register](../reference/controls-register.md), tested with good data (it must accept) and bad data (it must reject).

| Control | Enforces | Good data | Bad data | Output (the control's own message) | Evidence |
|---|---|---|---|---|---|
| CTL-01 | Every record is a known, concrete kind of thing (not abstract, not an artefact), of its dataset's layer | ✅ | ✅ | rejected — "instance PRC-PAY-01: entity 'A1.BusinessWidget' is not in the metamodel" | [run1-01-check.json](use-case-example-1/run1-01-check.json), [run2-1-unknown-type.json](use-case-example-1/run2-1-unknown-type.json) |
| CTL-02 | Attribute types, allowed values, required attributes, references and natural keys | ✅ | ✅ | rejected — "attribute 'criticality' value 'urgent' is not one of ['high', 'medium', 'low'] (LC-06)" | [run1-01-check.json](use-case-example-1/run1-01-check.json), [run2-2-bad-value.json](use-case-example-1/run2-2-bad-value.json) … |
| CTL-03 | Only allowed link kinds between the right record types; link-count limits | ✅ | ✅ | rejected — "A1 relationship A1.BusinessProcess -composition-> A1.BusinessCapability does not match the ArchiMate 3.2 / TOG" | [run1-01-check.json](use-case-example-1/run1-01-check.json), [run2-3-disallowed-link.json](use-case-example-1/run2-3-disallowed-link.json) |
| CTL-04 | Each record matches its per-entity JSON Schema (the format an adapter writes) | ✅ | ✅ | fails — "$.attributes.criticality: must be one of ['high', 'medium', 'low']" | [run1-13-schemas.json](use-case-example-1/run1-13-schemas.json), [run2-8-schema-bad-value.json](use-case-example-1/run2-8-schema-bad-value.json) |
| CTL-05 | A cross-layer link is one of the 9 types, between the right kinds of record, adjacent layers, no artefact ends | ✅ | ✅ | rejected — "relationship (A1.BusinessCapability, USES_DOMAIN, A2.ServiceDomain) is not in the registry" | [run1-06-validate-proposals.json](use-case-example-1/run1-06-validate-proposals.json), [run2-4-wrong-link-type.json](use-case-example-1/run2-4-wrong-link-type.json) |
| CTL-06 | Approval needs a reviewer, a date, the evidence kinds the link type requires, and for BIAN-anchored types a BIAN release and identifier | ✅ | ✅ | rejected — 22 problems, e.g. "evidence missing required kind(s) ['deployment_design']" | [run1-07-approve-without-evidence.json](use-case-example-1/run1-07-approve-without-evidence.json), [run1-08-approve-with-evidence.json](use-case-example-1/run1-08-approve-with-evidence.json) |
| CTL-07 | Approved links are never edited; only allowed status changes | ✅ | ✅ | rejected — "P-UCE1-001: approved record is immutable but field(s) changed: ['rationale']" | [run1-09b-proposed-to-approved.json](use-case-example-1/run1-09b-proposed-to-approved.json), [run1-10-edit-after-approval.json](use-case-example-1/run1-10-edit-after-approval.json) |
| CTL-08 | Both ends of every approved link exist, at the stated version, of the right type | ✅ | ✅ | rejected — "target A4.Deployment INF-DOES-NOT-EXIST@1.0 not found in level model" | [run1-06-validate-proposals.json](use-case-example-1/run1-06-validate-proposals.json), [run1-14-approved-links-resolve.json](use-case-example-1/run1-14-approved-links-resolve.json) … |
| CTL-09 | The engine finds the right links: precision and recall at least the hand-executed runs' on every acceptance case | ✅ | ✅ | 2 "runs on" links found, from the deployment records; 0 wrong | [run1-03-proposals.json](use-case-example-1/run1-03-proposals.json), [run1-04-inference-log.json](use-case-example-1/run1-04-inference-log.json) … |
| CTL-10 | Engine output is always `proposed`, valid, never re-proposes an approved link, never names a record that does not exist | ✅ | ✅ | 2 "runs on" links found, from the deployment records; 0 wrong | [run1-03-proposals.json](use-case-example-1/run1-03-proposals.json), [run1-04-inference-log.json](use-case-example-1/run1-04-inference-log.json) … |
| CTL-11 | Every entity, link row, link type, rule and attribute names its source, reasoning and confidence | ✅ | ✅ | fails — AssertionError: True is not false : rule B01 | [run1-19-sources-complete.json](use-case-example-1/run1-19-sources-complete.json), [run2-7-rule-without-source.json](use-case-example-1/run2-7-rule-without-source.json) |
| CTL-12 | Every confidence rating follows the single confidence rule | ✅ | ✅ | the rule says low, not high | [run1-16-confidence-rule.json](use-case-example-1/run1-16-confidence-rule.json), [run2-11-confidence-overclaim.json](use-case-example-1/run2-11-confidence-overclaim.json) |
| CTL-13 | Every generated document, diagram and schema matches the records | ✅ | ✅ | reported stale | [run1-17-documents-current.json](use-case-example-1/run1-17-documents-current.json), [run2-12-stale-document.json](use-case-example-1/run2-12-stale-document.json) |
| CTL-14 | The owner's high-level metamodel specification is unchanged | ✅ | ✅ | fails | [run1-18-high-level-spec.json](use-case-example-1/run1-18-high-level-spec.json), [run2-13-high-level-spec-edited.json](use-case-example-1/run2-13-high-level-spec-edited.json) |
| CTL-15 | A graph store is only written from data that passes every check; a failed build keeps the last good store; every build is logged | ✅ | ✅ | load rejected; graph files unchanged; load record: accepted, rejected | [run1-02-load-record.json](use-case-example-1/run1-02-load-record.json), [run2-10-failed-load.json](use-case-example-1/run2-10-failed-load.json) … |

### 1. Tests

| # | Rule area | Data given | Should | Did | Control | Evidence | ✅/❌ |
|---|---|---|---|---|---|---|---|
| 1 | 1–3 Records, information, links inside a layer | the four datasets as they are (68 records, 69 links inside layers) | accepted | accepted — 0 errors, 6 completeness warnings | CTL-01, CTL-02, CTL-03 | [run1-01-check.json](use-case-example-1/run1-01-check.json) | ✅ |
| 2 | Knowledge graph | build the graph store with no links between layers | built; 0 links between layers | accepted; 0 links between layers | CTL-15 | [run1-02-load-record.json](use-case-example-1/run1-02-load-record.json) | ✅ |
| 3 | 5 Finding links | engine applies the 69 link-finding rules | 18 links, all correct | 18 proposed — 18 correct, 0 wrong, 0 missed | CTL-09, CTL-10 | [run1-03-proposals.json](use-case-example-1/run1-03-proposals.json), [run1-04-inference-log.json](use-case-example-1/run1-04-inference-log.json), [run1-05-score.json](use-case-example-1/run1-05-score.json) | ✅ |
| 4 | 4 Links between layers | the 18 proposed links | all valid | valid | CTL-05, CTL-08 | [run1-06-validate-proposals.json](use-case-example-1/run1-06-validate-proposals.json) | ✅ |
| 5 | 6 Approving links | approve the 18 links with no evidence attached | rejected — each link type requires evidence | rejected — 22 problems, e.g. "evidence missing required kind(s) ['deployment_design']" | CTL-06 | [run1-07-approve-without-evidence.json](use-case-example-1/run1-07-approve-without-evidence.json) | ✅ |
| 6 | 6 Approving links | approve the 18 links with the required evidence | accepted, except a link whose BIAN identifier is missing from the data (never invented) | 17 accepted; 1 blocked — bian_alignment_guidance mapping requires canonical_id on its A2 target | CTL-06 | [run1-08-approve-with-evidence.json](use-case-example-1/run1-08-approve-with-evidence.json) | ✅ |
| 7 | 6 Approving links | change 17 proposed links to approved; the blocked one stays proposed (allowed status changes) | allowed | allowed | CTL-07 | [run1-09b-proposed-to-approved.json](use-case-example-1/run1-09b-proposed-to-approved.json) | ✅ |
| 8 | 6 Approving links | edit an approved link afterwards | rejected | rejected — "P-UCE1-001: approved record is immutable but field(s) changed: ['rationale']" | CTL-07 | [run1-10-edit-after-approval.json](use-case-example-1/run1-10-edit-after-approval.json) | ✅ |
| 9 | Trace | from the production server up to the business | reaches the Payment Initiation domain, the payment processes and the Initiate Payment capability | reached: APP-PAY-HUB, CAP-PAY-010, CMP-PAY-EXEC, PRC-PAY-01, PRC-PAY-02, SD-PI | output (trace) | [run1-12-trace-and-impact.json](use-case-example-1/run1-12-trace-and-impact.json) | ✅ |
| 10 | Trace | from the Initiate Payment capability down to technology | reaches the production server | reached: APP-PAY-HUB, DEP-PAYHUB-PROD, DEP-PAYHUB-UAT, INF-K8S-PAY-PROD, INF-K8S-PAY-UAT, SD-PI | output (trace) | [run1-12-trace-and-impact.json](use-case-example-1/run1-12-trace-and-impact.json) | ✅ |
| 11 | 2 Record information (format) | every one of the 68 records against its per-entity schema | all match | 68 match, 0 fail | CTL-04 | [run1-13-schemas.json](use-case-example-1/run1-13-schemas.json) | ✅ |
| 12 | 4 Links between layers (resolution) | the 17 approved links against the datasets | every end exists | all resolve | CTL-08 | [run1-14-approved-links-resolve.json](use-case-example-1/run1-14-approved-links-resolve.json) | ✅ |
| 13 | 5 Finding links (engine discipline) | run the engine again after the 17 links are approved | never re-proposes an approved link; only ever outputs "proposed" | 1 proposals (ALIGNED_TO); 0 re-proposed approved links; 0 not "proposed" | CTL-10 | [run1-15-engine-second-run.json](use-case-example-1/run1-15-engine-second-run.json) | ✅ |
| 14 | 7 Sources | every entity, link row, link type, rule and attribute in the metamodel | all name their source | all complete | CTL-11 | [run1-19-sources-complete.json](use-case-example-1/run1-19-sources-complete.json) | ✅ |
| 15 | 7 Sources (confidence) | every confidence rating in the metamodel | all follow the single rule | 0 disagree | CTL-12 | [run1-16-confidence-rule.json](use-case-example-1/run1-16-confidence-rule.json) | ✅ |
| 16 | Platform (documents) | the governing specification against the metamodel | matches (not stale) | up to date | CTL-13 | [run1-17-documents-current.json](use-case-example-1/run1-17-documents-current.json) | ✅ |
| 17 | Platform (frozen spec) | the owner's high-level specification | unchanged | unchanged (checksum matches) | CTL-14 | [run1-18-high-level-spec.json](use-case-example-1/run1-18-high-level-spec.json) | ✅ |
| 18 | 1 Record types | a record of an unknown kind (A1.BusinessWidget) | rejected | rejected — "instance PRC-PAY-01: entity 'A1.BusinessWidget' is not in the metamodel" | CTL-01 | [run2-1-unknown-type.json](use-case-example-1/run2-1-unknown-type.json) | ✅ |
| 19 | 2 Record information | a process with criticality "urgent" | rejected | rejected — "attribute 'criticality' value 'urgent' is not one of ['high', 'medium', 'low'] (LC-06)" | CTL-02 | [run2-2-bad-value.json](use-case-example-1/run2-2-bad-value.json) | ✅ |
| 20 | 3 Links inside a layer | a process that "contains" a capability | rejected | rejected — "A1 relationship A1.BusinessProcess -composition-> A1.BusinessCapability does not match the ArchiMate 3.2 / TOG" | CTL-03 | [run2-3-disallowed-link.json](use-case-example-1/run2-3-disallowed-link.json) | ✅ |
| 21 | 4 Links between layers | a "uses domain" link from a capability (only processes may use a domain) | rejected | rejected — "relationship (A1.BusinessCapability, USES_DOMAIN, A2.ServiceDomain) is not in the registry" | CTL-05 | [run2-4-wrong-link-type.json](use-case-example-1/run2-4-wrong-link-type.json) | ✅ |
| 22 | 5 Finding links | 5a — the Payments Hub no longer names its server, but its deployment records still do | the "runs on" links still found from the deployment records; nothing invented | 2 "runs on" links found, from the deployment records; 0 wrong | CTL-09, CTL-10 | [run2-5a-application-silent.json](use-case-example-1/run2-5a-application-silent.json) | ✅ |
| 23 | 5 Finding links | 5b — nothing names the Payments Hub's server (its deployments drop it too) | no "runs on" link made; nothing invented | stricter than expected: the data is rejected before the engine runs — "required attribute 'platform_id' missing (LC-04)" | CTL-02, CTL-15 | [run2-5b-no-server.json](use-case-example-1/run2-5b-no-server.json) | ✅ |
| 24 | 7 Sources | rule B01 with its source removed | the completeness test fails | fails — AssertionError: True is not false : rule B01 | CTL-11 | [run2-7-rule-without-source.json](use-case-example-1/run2-7-rule-without-source.json) | ✅ |
| 25 | 2 Record information (format) | the "urgent" process record against its schema | fails the schema | fails — "$.attributes.criticality: must be one of ['high', 'medium', 'low']" | CTL-04 | [run2-8-schema-bad-value.json](use-case-example-1/run2-8-schema-bad-value.json) | ✅ |
| 26 | 4 Links between layers (resolution) | an approved link to a server that does not exist | rejected | rejected — "target A4.Deployment INF-DOES-NOT-EXIST@1.0 not found in level model" | CTL-08 | [run2-9-dangling-link.json](use-case-example-1/run2-9-dangling-link.json) | ✅ |
| 27 | Platform (graph store) | load bad data over a good knowledge graph | load rejected; the last good graph kept; the rejection logged | load rejected; graph files unchanged; load record: accepted, rejected | CTL-15 | [run2-10-failed-load.json](use-case-example-1/run2-10-failed-load.json) | ✅ |
| 28 | 7 Sources (confidence) | attribute A1.BusinessCapability.strategic_importance (SDEM-defined) rated high | the rule disagrees | the rule says low, not high | CTL-12 | [run2-11-confidence-overclaim.json](use-case-example-1/run2-11-confidence-overclaim.json) | ✅ |
| 29 | Platform (documents) | a governing specification that no longer matches the metamodel | reported stale | reported stale | CTL-13 | [run2-12-stale-document.json](use-case-example-1/run2-12-stale-document.json) | ✅ |
| 30 | Platform (frozen spec) | the owner's specification with one character added | the freeze test fails | fails | CTL-14 | [run2-13-high-level-spec-edited.json](use-case-example-1/run2-13-high-level-spec-edited.json) | ✅ |

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
| G-A | partly closed (CTL-22) | the engine reads only each rule's step and confidence from the metamodel; how a rule matches is in the engine's code. Since 2026-10-28 CTL-22 checks that the engine applies only metamodel rules, at their assigned steps, and implements every applicable one; the matching itself is still only in code |
| G-B | confirmed, no risk today | link-type limits are not checked, but all 9 link types are many_to_many, so there is no limit to break yet |

### 5. Findings for the owner

| ID | What we found | The control's message | Consequence |
|---|---|---|---|
| F-1 | a link that is waiting for its BIAN identifier could not be marked "needs review" | none — accepted with warnings | resolved 2026-10-28 (owner): "needs review" is allowed while the BIAN identifier and evidence are awaited; both are still required at approval |
