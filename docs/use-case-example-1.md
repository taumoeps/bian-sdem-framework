# Use-case example 1 — establishing the mappings and the knowledge graph from separate architecture datasets

> **Status: PLAN — not yet executed.** Records the discussion and the agreed plan (2026-10-27). Results will be added to this document when the example is run; nothing below is a result unless marked *observed*.

## 1. Objective

**Prove that the SDEM metamodel can take four separate architecture datasets (A1 Business, A2 Service Domain, A3 Application, A4 Technology), with no links between them, and establish the mappings between them and the federated knowledge graph — so the bank's architecture becomes traceable end to end.**

The example tests the **metamodel as specified in [`architecture-metamodel-detail-level-spec.md`](architecture-metamodel-detail-level-spec.md)** (the governing specification) and the tools that implement it. Every step names the section of that specification it demonstrates; a step the specification cannot explain is a gap in the specification.

## 2. How we got here — the discussion

| Question raised | Answer agreed |
|---|---|
| What is a worked example? | A demonstration: one real case followed step by step through the specification, showing each rule applied and its result. It is not designing a new solution. |
| Is the example creating the metamodel? | **No.** The metamodel (entity types, allowed links, rules, attributes) already exists and is held fixed — it is what is being tested. The example applies it to architecture datasets. |
| What does the example produce? | The **mappings** (links between the architectures) and, from them, the **federated knowledge graph**; then proves traceability across it. |
| Start from partly-linked or separate datasets? | **Separate** — no links between architectures at the start. The use-case run M1 gave the engine 5 business-to-BIAN links; this example gives it none, which is the stronger proof. A trial run (2026-10-27, *observed*) established all 18 links of the estate from zero links: 18 proposed, 18 correct, 0 wrong, 0 missed. |
| Is clean data realistic? | **No.** The payment-initiation datasets are synthetic and consistent, so a clean run overstates what happens with real A1–A4 data. The example therefore has **two runs**: clean, and imperfect with planted defects. |
| What is the output? | A **results table** — one row per link proposed, refused or missed, with its source rule, step, evidence and reasoning, confidence, and outcome against the answer key (§6). |
| Terminology | An **architecture dataset** is one architecture's records and the links inside it, in SDEM's format (formerly called an *export*); see [`glossary.md`](glossary.md). |

## 3. The estate

The **payment-initiation** estate (`examples/payment-initiation/`), synthetic:

| Architecture dataset | Records | Links inside it |
|---|---|---|
| A1 Business — `a1-business.json` | 16 | 14 |
| A2 Service Domain (BIAN) — `a2-service-domain.json` | 24 | 33 |
| A3 Application — `a3-application.json` | 16 | 17 |
| A4 Technology — `a4-technology.json` | 12 | 5 |
| **Total** | **68** | **69** |

**Answer key:** the estate's 18 approved links (`mappings.json`) — 5 business ↔ BIAN, 7 BIAN ↔ application, 6 application ↔ technology. In run 1 it is the answer key; in run 2 a new answer key is written for the defective copy (§5).

## 4. Run 1 — clean datasets

| # | Step | Command | Detail spec | What it tests | Expected outcome |
|---|---|---|---|---|---|
| 1 | Check the four separate architecture datasets | `sdem-graph check a*.json <empty registry>` | §3, §5, §6.1, §16 | records and links inside each architecture obey the metamodel | 68 records, 69 links: **0 errors**, 6 completeness warnings (parts of BIAN's structure not in the estate) |
| 2 | Build the graph store with no links between architectures | `sdem-graph build … --out graph/` | §19 | four local knowledge graphs, built only from checked data | build accepted; federated graph holds **0** links |
| 3 | What is unlinked? | `sdem-graph query --graph graph/ --unmapped A2` (and A1, A3, A4) | §19 | the engine's work list | every record the relationship types expect to link to another architecture is listed |
| 4 | Establish the mappings | `sdem-infer rules --graph graph/ --out run1/` | §15a, §18 | the rules model applied in fill-step order | **18 proposals**: business ↔ BIAN 5, BIAN ↔ application 7, application ↔ technology 6 |
| 5 | Score against the answer key | `sdem-eval mappings.json --proposals run1/proposals.json` | §18 | the mappings are right | **18 correct, 0 wrong, 0 missed**; *Retrieve* on POST proposed at medium confidence with a method-mismatch finding; *Notify* (no REST form) correctly refused |
| 6 | Validate the proposals | `sdem-validate --strict run1/proposals.json` | §6.4 | every proposal is a valid `proposed` record | **0 errors** |
| 7 | Approve (by hand until the approve command, v0.11) | edit status, reviewer, date; `sdem-validate`, `sdem-diff` | §6.4 lifecycle | proposed → approved is allowed; a later edit to an approved link is blocked | approval passes; the edit **rejected** by `sdem-diff` |
| 8 | Rebuild — the federated graph joins all four | `sdem-graph build … approved.json --out graph/` | §19 | approved links become the federated graph | **18** links between architectures |
| 9 | Prove traceability | `sdem-graph trace INF-K8S-PAY-PROD --direction up --graph graph/` and `trace CAP-PAY-010 --direction down` | §6.3, §19 | end-to-end traceability, both directions | production cluster ← Payments Hub ← Payment Initiation domain ← both payment processes and the *Initiate Payment* capability, and the reverse; every hop shows its link ID |
| 10 | Impact | `sdem-graph impact INF-K8S-PAY-PROD --change rehost --graph graph/` | §19 | what a change affects | the dependent applications, domain, processes and capability, each classified |
| 11 | Break things on purpose | a bad attribute value; a link type A1 does not allow; a proposal to the wrong entity type | §6.1, §8, §16 | the metamodel rejects bad data | all three **rejected**, each naming the rule broken |

## 5. Run 2 — imperfect datasets

A copy of the estate with **planted, realistic defects**. Because real A1–A4 data will not be entirely correct, this run shows what the metamodel does with it: links found at lower confidence, links refused with a reason, bad data rejected before it reaches the graph — and nothing invented.

**Honest testing.** The answer key for run 2 — the expected behaviour of every defect — is **written and committed before the engine is run**, so the commit history shows it was not adjusted to fit the result.

| # | Defect planted | Where | Expected behaviour (to be fixed in the sealed answer key) |
|---|---|---|---|
| D1 | Missing join key — the application names no platform, and no platform or deployment names it | A3, A4 | that `DEPLOYED_ON` link **not proposed**; the record appears in the unmapped list |
| D2 | Typo in a reference to another architecture — a process `invokes` `SO-PI-0l` | A1 | check **warning** (LC-08, cross-architecture reference unresolved); the domain link still derived from the process's other operations, if any |
| D3 | Typo in a reference inside an architecture — a link to a record that does not exist | A3 | check **error** (LC-03 / LC-07); the dataset is **rejected** and the previous good graph kept |
| D4 | Product-style API paths (e.g. `/v2/moneyflows`) with no institution aliases | A3 | operation ↔ API **refused** (the boundary gate fails); with the alias supplied in a second pass, **found** |
| D5 | Wrong attribute value — criticality "urgent" | A1 | check **error** (LC-06); dataset rejected |
| D6 | Two APIs equally good for one operation | A3 | **no proposal**; both candidates named in the log (tie rule) |
| D7 | A business process with no `invokes` | A1 | its domain link **not derivable**; the capability link then not proposed (partial coverage is not proposed, DEC-E-09) |
| D8 | Conflicting data — an application's network zone and the network's member list disagree | A3, A4 | the application's zone wins; the disagreement reported as a finding |

Expected totals are set in the sealed answer key, not here.

## 6. Output

**`docs/use-case-example-1.md`** (this document) gains a results section per run, generated from the actual run:

**Results table** — one row per link proposed, refused or missed:

| From | Relationship | To | Rule (source) | Step | Evidence and reasoning | Confidence | Outcome |
|---|---|---|---|---|---|---|---|
| *e.g.* SO-PI-04 *Retrieve Payment Instruction* | IMPLEMENTED_BY | API-PI-04 | S24 — BIAN Semantic API guide §3.5 | 2 | Retrieve should be GET but is POST; unique best payload match → method-mismatch finding | 0.6 medium | correct, flagged |

Outcomes: **correct**, **correct — flagged** (proposed with a finding), **wrong** (proposed, not in the answer key), **missed** (in the answer key, not proposed), **refused** (attempted, not proposed, with the reason), **rejected** (the data failed a check).

**Below the table:** totals per outcome; check errors and warnings per architecture dataset; the traceability and impact results; and, for run 2, each defect against its sealed expected behaviour.

**A test** (`tests/test_use_case_example_1.py`) runs both runs on every change, so the example fails loudly if the specification, data or tools drift.

## 7. What the example proves — and what it does not

| Proves | Does not prove |
|---|---|
| the specification is complete: every step is explained by a section of the detail spec | that it works on **real** data — the estate is synthetic |
| the specification is correct: each outcome is what it says should happen | that the engine **generalises** — its rules were tuned while this estate's answers were known; a blind case written by someone else (OPEN-05) is still needed |
| the tools follow the specification, and bad data is stopped before the graph | an approve command — approval is done by hand until v0.11 |
| imperfect data degrades safely (run 2): refused or flagged, never invented | performance at scale |

## 8. Next actions

1. Owner approves this plan.
2. Build run 1 and its results table.
3. Write and commit the **sealed answer key for run 2**, then plant the defects and run it.
4. Add both results sections here; add the test to the suite.
