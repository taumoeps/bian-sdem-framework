# The public twin — a benchmark for SDEM that uses no real organisation's designs (PT-01…PT-39)

> **Status: approved — the owner agreed D1 in conversation and D2–D9 as recommended (2026-11-17). Phase 0 is done; phase 1 (sources) has begun.** No design has been built. The brief for the reference's author is [`sdem-public-twin-reference-brief.md`](sdem-public-twin-reference-brief.md).

## 1. Why

SDEM's examples are made up, and Payment Initiation v2 was built *with* SDEM and checked *by* SDEM. That shows SDEM is consistent with itself; it does not show that a design SDEM holds is right, or that what SDEM proposes and answers is right. The owner cannot share their employer's designs, so the test must come from somewhere else.

**The question this benchmark answers (PT-01):** given a realistic design that was written and frozen *outside* SDEM, from public sources —

1. does SDEM hold it without losing anything;
2. are the links SDEM proposes the right ones, and does it leave out the wrong ones;
3. are SDEM's answers (trace, impact, lineage) right;
4. does SDEM catch mistakes planted in it?

**What it does not test (PT-02):** SDEM does not design — the architect does, and `sdem aid` only proposes for a person to approve (CTL-21). So the benchmark never asks SDEM to invent an architecture from requirements. It also does not test the made-up bank's software: there is no running system, no fault injection, no load test.

## 2. Rules for the whole benchmark

| Id | Rule |
|---|---|
| PT-03 | **Public sources only.** Every fact in the twin cites a published source in the source register (section 4), or is marked a design decision. Nothing from the owner's employer: no names, patterns, diagrams, configurations or decisions. The owner reviews as an architect, and records findings only as general statements. |
| PT-04 | **Made-up data** (AGENTS.md rule 3). The bank, its systems, people, addresses and account numbers are invented; the standards it follows are real and cited. |
| PT-05 | **Cite, never copy.** Payments NZ's API standards are public to read, but "no other right or licence is granted" (their copyright notice, read 2026-11-17). The twin names a resource or field and cites where it is defined; it does not reproduce specification text, schemas or diagrams. The same holds for BIAN and ISO 20022. See risk R1. |
| PT-06 | **Two kinds of statement, scored apart.** *Standards-derived* (S): can be checked against a source — a BIAN service domain, a field of the API standard. *Design decision* (D): the made-up bank's own choice — its components, its zones. S items have a right answer; D items are right only in the sense "as the reference design says". |
| PT-07 | **The reference is frozen before SDEM runs**, and kept outside this repository until scoring. A change to it after the freeze is recorded with its reason and who made it; a change made *because* SDEM disagreed is reviewed against the source, never just accepted. |
| PT-08 | **No metamodel change is expected.** If the benchmark shows the metamodel cannot hold something, that is a finding for the owner's approval (AGENTS.md rule 2), not something changed during the run. |
| PT-09 | **An agent never approves a link** (CTL-21). Approvals in the SDEM run are the owner's, or the owner's explicit delegation, recorded as such. |

## 3. The twin

**A made-up New Zealand retail bank** ("the twin bank"; a name is chosen at build time and checked not to be a real organisation's).

| | |
|---|---|
| Market | New Zealand, retail banking, NZD |
| First scenario (S1) | A customer pays a merchant through a third party (an accredited requestor): the third party asks for consent, the customer authorises it with the bank (the standard's redirect flow), the third party initiates a single domestic payment, the bank validates and executes it, the third party reads its status |
| Why this path first | Its standard — the API Centre's Payment Initiation API — is the best-documented public source in the NZ market, so the largest share of the design is S (checkable), not D |
| The bank's existing systems (D) | Invented, but ordinary: online-banking identity, an account ledger, a payments hub, fraud screening, notifications, an API gateway |
| Out of scope for S1 | The decoupled authorisation flow (another device, or later) — scenario S1b, so S1 is never read as the whole of payment initiation; enduring (repeated) payment consents, bulk files, direct debits, high-value and cross-border payments, cards |

**Later scenarios, one at a time, each with its own frozen reference (PT-10):** S2 the customer initiates the same payment in online banking; S3 validation and authorisation failures; S4 execution, clearing and settlement with other banks; S5 status, returns and reconciliation.

## 4. Source register

Confidence is **high** only where the public source itself was read in this session (2026-11-17); **medium** where a search result summarised it; **low** where it is from memory.

| # | Layer | Source | What it is used for | What was checked | Confidence |
|---|---|---|---|---|---|
| SR-01 | A3, information | Payments NZ API Centre (closed 30 September 2026; MBIE now manages the standards, which remain on the Payments NZ site) — Payment Initiation API and Security Profile. Versions listed on the standards home: 2.0.2 … 2.3.5, **3.0.3** (highest). | Resources, fields, statuses, consent and authorisation flow, security profile | Standards home page read: "read-only and publicly available"; versions as listed; copyright notice as in PT-05 | high (that it exists, is public, its versions); **not yet read: the specification pages themselves** |
| SR-02 | A3 | Which version banks run, and the law names | Choosing the version to freeze | News: the four largest banks implemented v2.3 (May 2025); one bank's developer page recommends 3.0. A search summary of MBIE's *Customer and Product Data (Banking and Other Deposit Taking) Standards 2025* says they incorporate NZ Banking Data API Specification v2.3.3 and its security profile, in force 1 December 2025 — the document itself not opened. Specification pages: Payment Initiation v2.3.5 `…/PaymentsNZAPIStandards/pages/3000402649`, Security Profile v2.3.5 `…/pages/3000403202` (links read from the standards home) | medium |
| SR-03 | Regulation | Customer and Product Data Act 2025; banking designation regulations; the Banking and Other Deposit Taking Standards 2025 | Why the bank must offer the API; consent; who may ask | Search summaries: Royal Assent 29 March 2025; in force from 1 December 2025 for the four largest banks; amendments planned for 2026. MBIE's own pages did not load | medium |
| SR-04 | A2 | BIAN 14.0.0 semantic APIs (Payment Order Initiation, Party Authentication, others the scenario needs) | Service domains, operations, business objects and fields | Files already held and imported for v2 | high |
| SR-05 | A1 (scheme) | Payments NZ — Bulk Electronic Clearing System (BECS) and Settlement Before Interchange (SBI) | Scenario S4: how a payment clears and settles between banks | Both pages read: BECS covers direct credits, bill payments, automatic payments, direct debits; SBI is SWIFT-based, settles then interchanges several times a business day. **The file format and detailed rules are not on these pages**; a rules PDF ("Rules Part 2 v64") appeared in search but was not opened | high (what the pages say); low (formats and rules) |
| SR-06 | A1 (settlement) | Reserve Bank of New Zealand — ESAS | S4: where settlement happens | Search summary: ESAS moved to ISO 20022 in November 2025 | medium |
| SR-07 | A4 | Reserve Bank — BS11 Outsourcing Policy (September 2022); Guidance on Cyber Resilience (2021) | Expectations a deployment design should meet | Search summaries; the Reserve Bank's pages not opened | medium |
| SR-08 | A4 | PCI DSS | Zones, key management | Not checked this session | low |
| SR-09 | Information | ISO 20022 (`pain.001`, `pain.002`, `pacs.008`) | Only where NZ uses it — high-value payments, S4/S5 | Not checked; for S1 the API standard's own data model is the reference | low |
| SR-10 | Notation | ArchiMate 3.2 | Whether each link is one ArchiMate defines | The specification is behind an Open Group sign-in (as noted in the containment design, C7) | medium |
| SR-11 | Second test | An open-source payments or core-banking system (candidates: Mojaloop, Apache Fineract) | Section 9 | Not checked | low |

**PT-11:** before the reference is written, every source it will cite is opened, its exact version and date recorded, and its confidence raised to high or the item marked "not verifiable — design decision". SR-01's specification pages come first.

## 5. The two models

| | Model A — the reference | Model B — SDEM's |
|---|---|---|
| What | The design as an architect would write it, plus what is expected of a tool that holds it | The same design held in SDEM |
| Made by | **Not this SDEM session** (D2): the owner, or another assistant the owner directs | SDEM's CLI, run by this session, approvals by the owner (PT-09) |
| Made from | The source register and the scenario | Model A's **design document only** — never its expected lists or answer key |
| Where | Outside this repository until scoring (PT-07) | `examples/payment-initiation-v3/`, evidence in `docs/evidence/payment-initiation-v3/` |

**Model A's files (PT-12…PT-17):**

| Id | File | Content |
|---|---|---|
| PT-12 | `design.md` | The solution design in prose, by layer, as an architect writes one: scenario, actors, requirements (with measurable targets, marked D), business process, BIAN alignment, applications and interfaces, data and fields, deployment and zones. Every statement marked S (with its SR-number and location) or D |
| PT-13 | `expected-records.json` | Every record the design implies, by layer and kind, with the fields that matter |
| PT-14 | `expected-links.json` | Every link inside a layer and between layers, each S or D — and a list of **links that must not exist** (for example, a BIAN operation implemented by an API that does something else) |
| PT-15 | `answer-key.json` | 30–50 questions with the expected answer and its source: lineage ("which column stores the instructed amount, and which field of the standard is it?"), trace ("what does the payment consent depend on, down to its zone?"), impact ("what is affected if the fraud screening service is retired?"), governance ("can an agent approve its own proposed link?" — no) |
| PT-16 | `mutations.json` | 15–25 planted mistakes, each with what it changes and how SDEM should respond: *refuse* (a check fails), *warn*, or *cannot know* (a matter of judgement SDEM is not expected to catch — stated honestly up front) |
| PT-39 | `coverage.json` | One row per requirement: what carries it through the four layers, and whether it is met by the design, by a procedure, or not at all. Hidden, like the lists above |
| PT-17 | `SOURCES.md`, `FROZEN.txt` | Every source the author opened (URL, version, date read) and everything they could not verify; then the date, who froze it, and a hash of the files |

**PT-18 — review of the reference before the freeze:** every S item is checked against its source by someone other than its author (the owner, or this session reading *only* the S items of `design.md` against the sources — never the expected lists). A wrong reference would make every score meaningless.

## 6. The SDEM run

Done as an architect would, through the CLI, following the `sdem-design-from-document` and `sdem-scenarios` skills. Everything SDEM is given and everything a person does is logged.

| Step | What | Logged |
|---|---|---|
| PT-19 | A new workspace; `sdem bian import` for only the BIAN objects the design names | The command lines |
| PT-20 | `design.md` → one change set per layer, each record citing the section it came from | Statements that could not be turned into a record, and why |
| PT-21 | `sdem aid` — SDEM infers and proposes. **Its first output is frozen as `initial-proposals.json` before anyone approves, rejects or corrects anything** | Every proposal with its rule and confidence |
| PT-22 | The owner approves or rejects each proposed link (PT-09) | Each decision; each link the owner had to state by hand |
| PT-23 | `sdem check`, documents, `sdem trace`, `sdem impact` for the answer key's questions — the questions are revealed only now | Raw output |
| PT-24 | Each mutation applied to a copy; `sdem check` and the relevant command run | Raw output |

## 7. Scoring

Reported as measured numbers, S and D apart (PT-06). **No overall score and no "maturity" figure** — nothing defines one. The first run is the baseline; whether a number is good enough is the owner's judgement, and thresholds can be set from the second run on (D7).

| Id | Measure | How |
|---|---|---|
| PT-25 | **Capture** | Of the expected records, how many SDEM holds with the right kind and fields — a modelling the reference lists as an acceptable alternative counts; statements SDEM had no place for (a finding about the metamodel) |
| PT-37 | **Coverage** | Of the reference's requirements (`coverage.json`), for how many SDEM's design shows the same chain through the four layers |
| PT-26 | **Links proposed — precision and recall** | Of the links SDEM proposed, how many are in the expected list (precision); of the expected links, how many SDEM proposed without being told (recall); how many forbidden links it proposed (must be none). **Scored twice:** on `initial-proposals.json` — what SDEM did unaided — and on the final approved design. **And in two groups:** links the design document *states* (holding a design) and links it only *implies* (reasoning) — the reference marks each (`in_design`) |
| PT-27 | **Effort** | Links the owner stated by hand; proposals rejected |
| PT-28 | **Answers** | Of the answer key's questions, how many SDEM answered exactly, partly, wrongly, or could not answer |
| PT-29 | **Mutations** | Of the planted mistakes marked *refuse* or *warn*, how many were caught; false alarms on the unmutated design |
| PT-30 | **Standards** | Of the S statements, how many SDEM's data agrees with — checked against the source, not against SDEM's own check |
| PT-31 | **Conformance** | `sdem check` clean; reported, but it is the least informative measure |

**PT-38:** SDEM's code is not changed to suit the reference before the first run is scored (phase 5 comes after phase 4) — the uncorrected result is the finding.

**PT-32:** every disagreement between the models is classified — SDEM wrong, the reference wrong (PT-07), the design document ambiguous, or the metamodel unable to say it — and listed in the report. The findings are the benchmark's product; the numbers summarise them.

## 8. Order of work — one scenario through all four layers, then the next

Not A1 complete, then A2, then A3, then A4: a layer cannot be verified alone, because the mistakes are in the links between layers.

For each scenario: fix the two points that are public first (BIAN for A2; the API standard's data model for the information), write A1 and A3 between them, then A4 under A3; go back up when a lower layer shows a missing requirement, and record the change.

## 9. The second test — a real open-source system (PT-33)

The twin's applications and deployment are invented, so nothing outside the reference says they are right. An open-source payments or banking system has what the twin lacks: API definitions, data schemas and deployment files that nobody invented for the test. After S1: onboard one such system with SDEM (`sdem transform`, change sets) and compare SDEM's records with the repository's own files, the same measures applying. The system is chosen then (D8), after checking its licence and documentation.

## 10. Out of scope

| Id | Not done | Why |
|---|---|---|
| PT-34 | A running reference system (containers, executable contract tests, fault injection) | It would test the made-up bank's software, not SDEM, at many times the cost. Section 9 gets implementation facts from a system that already exists |
| PT-35 | A maturity score | Undefined; the measures in section 7 are reported as they are |
| PT-36 | Other domains (lending, cards, treasury) | One scenario cannot show SDEM is right everywhere. They follow only if this benchmark proves useful |

## 11. Risks

| Id | Risk | Handling |
|---|---|---|
| R1 | **Copyright** — the API standards grant no licence beyond reading | PT-05: names and citations only. The owner decides (D5) whether naming the standard's resources and fields in a public example is acceptable, or the twin stays in a private repository, or Payments NZ is asked |
| R2 | **The reference is wrong** — written by an assistant, it may state things the standards do not say | PT-11 (sources opened, versions recorded) and PT-18 (S items checked by someone other than the author) |
| R3 | **The answer leaks** — this session can read any file in this repository | PT-07: the reference stays outside the repository; the session is given `design.md` only, then the questions at PT-23 |
| R4 | **Scheme detail is not public** — BECS file formats and rules were not found on Payments NZ's pages | S1 does not need them. For S4, what cannot be cited is a design decision (D), or the scenario is cut back to what is public |
| R5 | **The owner's time** — approvals are the owner's (PT-09) | S1 is kept small: an estimated 60–90 records and 30–50 links between layers. The owner may delegate, recorded as delegation |
| R6 | **The employer's confidentiality** | PT-03. The owner checks their employment obligations before reviewing; nothing is recalled from work into the twin |

## 12. Decisions for the owner

| # | Decision | Decided (the owner, 2026-11-17 — each as recommended) |
|---|---|---|
| D1 | The market and first scenario | New Zealand; S1 — a third party initiates a single domestic payment (section 3). *The owner agreed this in conversation, 2026-11-17* |
| D2 | Who writes Model A | Another assistant the owner directs, from this plan and the source register; the owner reviews. Not this session |
| D3 | Where Model A is kept until scoring | A private folder or repository this session is not pointed at |
| D4 | Which version of the API standard to freeze | **v2.3.3** — the version MBIE's regulated Standards incorporate by reference (a search summary of MBIE's document, and the second assistant's own check, 2026-11-17). Not a later patch, not 3.0 |
| D5 | Copyright (R1) | Build v3 in this public repository with names and citations only; no specification text. Ask Payments NZ if in doubt |
| D6 | Who approves links in the SDEM run | The owner, in one sitting on one consolidated page |
| D7 | Thresholds | None for the first run — it is the baseline |
| D8 | The second test (section 9) | Yes, after S1; system chosen then |
| D9 | Keep Payment Initiation v2 | Yes — unchanged, as the regression example; v3 sits beside it |

## 13. Phases — each ends at a stop for the owner

| Phase | Work | Output | Stop |
|---|---|---|---|
| 0 | The owner reviews this plan; decides D1–D9 | This document, approved or changed | ✔ |
| 1 | Sources opened and recorded (PT-11) | The source register, every row high or marked D | ✔ the owner confirms the version to freeze |
| 2 | Model A written and reviewed (PT-12…PT-18), then frozen | Six files, outside this repository | ✔ the owner freezes |
| 3 | The SDEM run (PT-19…PT-24) | `examples/payment-initiation-v3/`, the log | ✔ the owner's approvals |
| 4 | Scoring and the report (PT-25…PT-32) | `docs/evidence/payment-initiation-v3/report.md` | ✔ the owner reads the findings |
| 5 | Fixes to SDEM that the findings justify — each its own change, tests first | Changes with rule ids, CHANGELOG | per change |
| 6 | The next scenario, or the second test | — | ✔ |

## 14. Where this plan came from

The owner's question (2026-11-17): how to build a full design and know it is correct without sharing an employer's designs. This session proposed a public twin with an answer key written first. A second assistant's review, which the owner shared, added the point this plan is built on — a reference made independently of SDEM, frozen before SDEM runs — and the negative assertions, the precision and recall measures, and keeping v2. Not taken from that review: SEPA (the wrong market), a running reference system (PT-34), and a maturity score (PT-35).

The same assistant then reviewed this plan and the brief (2026-11-17). Taken: v2.3.3 confirmed (D4); the decoupled flow named as its own scenario; stated and implied links scored apart, and SDEM's first proposals frozen and scored before any approval (PT-21, PT-26); acceptable alternatives (PT-25); a coverage file in place of record counts (PT-37); no change to SDEM before the first score (PT-38). Changed in taking: the coverage table is a hidden file, not part of the design document — it is a list of the links between layers; and nothing is left out of the design document to manufacture inference tests — the reference classifies each link honestly instead. Reported there and confirmed by search: Payments NZ's API Centre closed on 30 September 2026 and MBIE now manages the standards. Reported there and **not** confirmed: that a regulated bank must support both authorisation flows — the author checks.
