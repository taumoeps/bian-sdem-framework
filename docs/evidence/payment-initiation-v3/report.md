# Payment Initiation v3 — the public twin: first benchmark of SDEM against an independent reference (PT-25…PT-32)

**Run 2026-11-17 · SDEM 0.19.0 · metamodel 0.17.0 · baseline run — no thresholds (D7).** Plan: [`sdem-public-twin-benchmark-plan.md`](../../design/sdem-public-twin-benchmark-plan.md).

A made-up New Zealand retail bank's design for one scenario — a third party initiating a single domestic payment under the NZ open banking standard v2.3.3 — was written and
frozen outside SDEM by an independent author (another assistant, directed by the owner). SDEM's operator was given the design document only (`design.md`, sha256 `20199f8b…`),
built it through the CLI, froze what SDEM proposed, applied the owner's decisions, answered the reference's questions, applied its planted mistakes, and only then opened the
reference to score. The reference is the owner's and is not in this repository. **Nothing in SDEM was changed before scoring (PT-38).**

## The result in one table

| Measure | Result |
|---|---|
| **Capture** (PT-25) — of the 152 expected records the design document actually names | **141 held (93%)** — 133 as records, 8 in another form (API fields as names). 11 not held: 4 kinds SDEM has no record type for, 6 API fields with no column, 1 operation the document gives no path for |
| …of all 196 expected records | 141 (72%). **44 expected records are not in the design document at all** — a defect of the reference, below |
| **Links held** — of the 153 expected links whose two ends SDEM holds | **107 (70%)**: 79 written from the document, 15 proposed by SDEM and approved, 8 inferred by SDEM and confirmed, 5 reached by `sdem trace`. 46 missing |
| **What SDEM proposed, first run, between layers** (PT-26) — 58 links | 15 expected, 8 consistent with two expected links (component → node), **35 not expected** — 28 of them one invented table and its fields. **0 forbidden** (of the reference's 18) |
| **What SDEM inferred inside A4, first run** — 24 links | 8 expected (node runs deployment), 4 an equivalent form (path → node; the reference has path → zone), **12 wrong** (every deployment and database placed in the parent zone) |
| **Recall between layers** — of 57 expected links | 15 proposed by SDEM, 5 more reachable by trace; 20 have an end SDEM does not hold; **17 missed with both ends held** |
| **Answers** (PT-28) — 50 questions | **29 right** by a link or field SDEM holds; 5 right record but found by its description, not a link; 2 partly; 4 impact questions SDEM declined ("evidence incomplete"); 9 not held; 1 expects a record the document does not contain |
| **Planted mistakes** (PT-29) — 19 that a tool should refuse or warn about | **4 caught**, **11 accepted silently**, 4 not applicable (SDEM does not hold what was mutated). No false alarm on the unmutated design |
| **Conformance** (PT-31) | `sdem check`: 0 errors, 15 warnings |
| **Effort** (PT-27) | Operator: 126 records, 99 links, 5 requirements from the document; 9 interpretations (run log). Owner: 12 decisions, taken wholesale on the operator's recommendation and run by the operator as delegation; 0 links stated by hand |

## What this says about SDEM

**It holds a design well, reasons about it weakly, and checks it thinly.**

| # | Finding | Evidence |
|---|---|---|
| F1 | **The zone model cannot hold a valid design.** LC-17 demands cloud/on-premises → one internal zone + DMZs → private zones. Five flat zones needed two invented zones and four changed kinds | CS-003; 3 SDEM records not in the reference |
| F2 | **Required fields force values a design document does not give** — a deployment's platform and environment, an API operation's path (one operation could not be recorded) | run log 2, 3, 6; Q-08 |
| F3 | **Zone placement is wrong:** AID-Z01/Z02 put all 8 deployments and 4 system-software records in the parent internal zone, including the ingress whose node is in the DMZ | 12 of 24 in-layer inferences rejected |
| F4 | **AID invents a table for a BIAN object the design does not store** — 28 records and 28 proposed mappings for Party Authentication | 28 of 35 unexpected proposals |
| F5 | **Nothing connects a process to the application that carries it** unless a BIAN domain sits between them. 6 of 8 processes trace to nothing; all four "what process is affected" impact questions went unanswered — SDEM said *evidence incomplete* rather than *no impact*, which is the honest answer | Q-31…34; trace PROC-DEBIT, PROC-RISK, PROC-HANDOFF, PROC-CONSENT |
| F6 | **No rule reaches platform software.** Database, key custody, events and audit stayed in no zone and linked to nothing; SDEM said so (LC-16, LC-21) but proposed nothing | 4 expected links SYS → NODE missed |
| F7 | **Field types are not checked.** An amount typed as a date, a currency as a boolean, an identifier as money, a lost primary key — all accepted through a change set without a word | M-01, 02, 03, 05 |
| F8 | **A broken contract is not noticed:** an API field re-pointed at the wrong column, an operation's path changed to another product, an access link or a path's end removed | M-08, 12, 19, 21 |
| F9 | **The registry of approved links is unguarded by `sdem check`:** deleting an approved link, or adding one that contradicts the deployment's own `component_id`, passed | M-06, 07, 09 |
| F10 | **What SDEM does guard, it guards well:** every direct edit of a layer file was refused (CTL-20, 14 of 14); an agent cannot approve (CTL-21); approval without evidence is refused; a duplicate table is refused; data moved into the DMZ is flagged | M-04, 10, 11, 16; Q-41 |
| F11 | **API-level facts have no home:** request and response fields as things in their own right, their logical types and lengths, headers, scopes, security flows, a resource's permitted statuses | 18 expected records; Q-37…40, 43, 44, 46, 47; M-14, 15 |
| F12 | **SDEM never proposed a forbidden link**, and its attribute-join proposals (deployed as, deployed on, stored in, uses domain) were sound: 21 of 22 expected or consistent; the other — the status process uses Payment Order Initiation — is not in the reference but follows from the document | 0 of 18; 21 of 22 |

Operator's own limits, so they are not read as SDEM's: the permitted statuses could have been recorded as `allowed_values` on the status columns (Q-43, 44); the six API fields with no
column could have been listed in `payload_fields`; five answers were found by reading descriptions.

## What this says about the reference

It was good enough to find the twelve things above, and not good enough to be a golden set. For the next scenario:

| # | Problem | Evidence |
|---|---|---|
| R1 | **The hidden lists describe a bigger design than the design document.** 44 of 196 expected records appear nowhere in `design.md`: 8 application services, 7 functions, 4 interfaces, 3 events, 3 artifacts, 5 technology services, 5 business objects, 4 business events, 5 API-level items. 44 of the 212 expected links hang off them | `scoring.json` → records |
| R2 | **`in_design` is unreliable.** Only 18 of 212 links are marked "stated"; a table's own columns (30 links, stated by the document's tables) are marked "implied"; 11 of the 18 "stated" have an end the document does not contain | `scoring.json` → links |
| R3 | **Relationship names are loose** ("hosted by/connected to", "owns/uses"), so links were matched on their two ends only | — |
| R4 | Questions and mistakes that need a record the document does not contain | Q-35 (SVC-STATUS); M-17 (BO-PAYMENT) |
| R5 | Good: the 18 forbidden links were well chosen; the standards-derived items carried sources; the S/D split held up |  |

So the numbers above are reported two ways wherever R1 matters — against what the document names, and against everything.

## What happens next — the owner's decisions

Nothing below is done. Each SDEM change is its own change with tests first (plan phase 5); any change to the metamodel needs the owner's approval.

| # | Proposal | Kind |
|---|---|---|
| N1 | Zone placement follows the platform's zone (F3) | code (AID-Z) |
| N2 | AID infers a table for a BIAN object only when the design gives a reason to store it (F4) | code (AID-I01) |
| N3 | `sdem check` warns on field types that contradict the field's name or role, a table with no key, and an API field alias that points at a column of another meaning (F7, F8) | code — new checks, rule ids |
| N4 | `sdem check` covers the registry: an approved link removed outside `sdem`, or one that contradicts the records it joins (F9) | code |
| N5 | Propose process → application links from what the records already say (F5) — and say *evidence incomplete* everywhere SDEM now says nothing | code (AID-L) |
| N6 | Rules for platform software: on the node of its kind, in that node's zone (F6) | code (hosting inference) |
| N7 | Loosen the zone model so flat zones are valid (F1); make a deployment's platform and an operation's path optional on a *planned* record (F2) | **metamodel — owner's approval** |
| N8 | API fields, headers, scopes and statuses as first-class records (F11) | **metamodel — owner's approval; design first** |
| N9 | Reference for scenario 2: every expected record must be named in the design document; `in_design` checked by a second reader; relationship names from a fixed list (R1–R3) | the brief |

## Files

Kept outside git (`work/payment-initiation-v3/`): the workspace, `ws-initial/` (before any decision), `initial-proposals.json` (+ sha256), `review-v3.sh`, `sdem-answers.json` and
`mutation-results.json` (hashed before the reference was opened), `scoring.json`, `run-log.md`, the scripts. One slip is recorded in the run log: the first answer-key question was
seen early by a mistaken command; the design document states its answer.
