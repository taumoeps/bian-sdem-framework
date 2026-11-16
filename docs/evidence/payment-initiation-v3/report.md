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
| **Planted mistakes** (PT-29) — 19 that a tool should refuse or warn about | **5 caught**, **10 accepted silently**, 4 not applicable (SDEM does not hold what was mutated). No false alarm on the unmutated design |
| **Conformance** (PT-31) | `sdem check`: 0 errors, 15 warnings |
| **Effort** (PT-27) | Operator: 126 records, 99 links, 5 requirements from the document; 9 interpretations (run log). Owner: 12 decisions, taken wholesale on the operator's recommendation and run by the operator as delegation; 0 links stated by hand |

## What this says about SDEM

**It holds a design well, reasons about it weakly, and checks it thinly.**

| # | Finding | Evidence |
|---|---|---|
| F1 | **The zone model cannot hold a valid design.** LC-17 demands cloud/on-premises → one internal zone + DMZs → private zones. Five flat zones needed two invented zones and four changed kinds | CS-003; 3 SDEM records not in the reference |
| F2 | ~~Required fields force values a design document does not give~~ — **withdrawn 2026-11-17: the operator's error, not SDEM's.** A record marked *planned* may leave a required field out (a warning, LC-04), and the design-from-document skill says so. The operator guessed two deployments' platforms and left the debtor-account operation unrecorded when neither was necessary | run log 2, 6; Q-08 |
| F3 | **Zone placement is wrong:** AID-Z01/Z02 put all 8 deployments and 4 system-software records in the parent internal zone, including the ingress whose node is in the DMZ | 12 of 24 in-layer inferences rejected |
| F4 | **AID invents a table for a BIAN object the design does not store** — 28 records and 28 proposed mappings for Party Authentication | 28 of 35 unexpected proposals |
| F5 | **Nothing connects a process to the application that carries it** unless a BIAN domain sits between them. 6 of 8 processes trace to nothing; all four "what process is affected" impact questions went unanswered — SDEM said *evidence incomplete* rather than *no impact*, which is the honest answer | Q-31…34; trace PROC-DEBIT, PROC-RISK, PROC-HANDOFF, PROC-CONSENT |
| F6 | **No rule reaches platform software.** Database, key custody, events and audit stayed in no zone and linked to nothing; SDEM said so (LC-16, LC-21) but proposed nothing | 4 expected links SYS → NODE missed |
| F7 | **Field types are not checked.** An amount typed as a date, a currency as a boolean, an identifier as money, a lost primary key — all accepted through a change set without a word | M-01, 02, 03, 05 |
| F8 | **A broken contract is not noticed:** an API field re-pointed at the wrong column, an operation's path changed to another product, an access link or a path's end removed | M-08, 12, 19, 21 |
| F9 | **A deleted approved link draws no warning about the design.** `sdem check` only notes that `mappings.json` changed outside `sdem` (AF-07 — an error with `--require-recorded`, which CI should use). A link added that contradicts the record's own attribute *is* caught (LC-28). *Corrected 2026-11-17: first reported as "the registry is unguarded" — the operator's harness had hidden the LC-28 warning* | M-06, 07; M-09 caught |
| F10 | **What SDEM does guard, it guards well:** every direct edit of a layer file was refused (CTL-20, 14 of 14); an agent cannot approve (CTL-21); approval without evidence is refused; a duplicate table is refused; data moved into the DMZ is flagged; an approved link that contradicts its record is flagged | M-04, 09, 10, 11, 16; Q-41 |
| F11 | **API-level facts have no home:** request and response fields as things in their own right, their logical types and lengths, headers, scopes, security flows, a resource's permitted statuses | 18 expected records; Q-37…40, 43, 44, 46, 47; M-14, 15 |
| F12 | **SDEM never proposed a forbidden link**, and its attribute-join proposals (deployed as, deployed on, stored in, uses domain) were sound: 21 of 22 expected or consistent; the other — the status process uses Payment Order Initiation — is not in the reference but follows from the document | 0 of 18; 21 of 22 |

Operator's own limits, so they are not read as SDEM's: **the debtor-account operation should have been recorded as planned, without its path (one expected record and Q-08 lost), and the platforms of the fraud and notification deployments left out, not guessed — two of the eight approved *deployed on* links rest on those guesses (F2)**; the permitted statuses could have been recorded as `allowed_values` on the status columns (Q-43, 44); the six API fields with no
column could have been listed in `payload_fields`; five answers were found by reading descriptions.

## What this says about the reference

It was good enough to find the twelve things above, and not good enough to be a golden set. For the next scenario:

| # | Problem | Evidence |
|---|---|---|
| R1 | **The hidden lists describe a bigger design than the design document.** 44 of 196 expected records are not named as elements in `design.md` (four of them appear as phrases — see the independent audit): 8 application services, 7 functions, 4 interfaces, 3 events, 3 artifacts, 5 technology services, 5 business objects, 4 business events, 5 API-level items. 44 of the 212 expected links hang off them | `scoring.json` → records |
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
| N4 | ~~`sdem check` covers the registry~~ — **withdrawn 2026-11-17:** it already does (AF-07 with `--require-recorded`; LC-28). Use `--require-recorded` in CI where agents edit | none |
| N5 | Propose process → application links from what the records already say (F5) — and say *evidence incomplete* everywhere SDEM now says nothing | code (AID-L) |
| N6 | Rules for platform software: on the node of its kind, in that node's zone (F6) | code (hosting inference) |
| N7 | Loosen the zone model so flat zones are valid (F1) — a change to the check LC-17 and its design, no metamodel file. ~~Optional platform and path on a planned record~~: already so (F2 withdrawn) | **a rule the owner decided — owner's approval** |
| N8 | API fields, headers, scopes and statuses as first-class records (F11) | **metamodel — owner's approval; design first** |
| N9 | Reference for scenario 2: every expected record must be named in the design document; `in_design` checked by a second reader; relationship names from a fixed list (R1–R3) | the brief |

## After the first score (2026-11-17) — what was changed, withdrawn and found next

The owner asked for the fixes in the order recommended. Each is its own commit, test first.

| Proposal | Outcome |
|---|---|
| N1 zone placement | **Done — AID-Z05.** Rebuilt from the same change sets: 12 wrong placements → 4 (the four system-software records, which have no host to follow) |
| N2 the invented table | **Done — AID-I08.** Rebuilt: 28 inferred records → 0; AID's proposals between layers 42 → 14; SDEM now says *no table inferred for Party Authentication — no application here realises its domain* |
| N3 field and contract checks | **Done in part — LC-29:** a column whose type cannot hold what its name says (would catch M-01, 02, 05). Not done: a table with no key is already LC-25 for a system of record; the alias mistake (M-08) rested on the operator's own use of `field_aliases`; a changed API path (M-12) gives SDEM nothing to judge it against |
| N4 guard the registry | **Withdrawn** — it is guarded (F9, corrected above) |
| N5 process → application links | **Withdrawn as code.** A process links to an application *service* or *function*, never a component — ArchiMate's rule and SDEM's. The design document named no application service, so there was nothing valid to link to. The design-from-document skill now says so, and the next brief must (N9) |
| N6 platform software | **No new rule.** A second `sdem aid` pass, after the approvals, connects the database (AID-C02 reads approved links); the first pass could not. Key custody, events and audit have nothing in the data to place them by — "a person links it" is the right answer. The skill now says to run the second pass |
| N7 flat zones | The owner agreed in principle (2026-11-17); the exact change to LC-17 is brought for approval before it is built. Its second half was dropped with F2 |
| N8 API-level records | Held until scenario 2 shows whether the gap recurs (the owner, 2026-11-17) |

Two more findings, from the second pass:

| # | Finding |
|---|---|
| F13 | **AID-C02 linked the ingress node to the database.** An API operation *accesses* a table; the ingress component composes the API's interface; so the rule counts the ingress as a user of the data and proposes its node reaches the database — in a design whose point is that it does not. For a person to reject; the rule should not climb from an API operation to the component that only exposes it |
| F14 | **A declined proposal is not remembered.** The owner left *BIAN Payment Transaction MAPPED_TO PaymentLedger* unapproved; there is no way to reject a proposed link. On the second pass SDEM, finding the object unmapped, inferred a new 30-field table for it instead. `sdem aid reject` remembers inferred *records*; proposed *links* need the same |

## Run 2 (2026-11-17) — the same benchmark after the fixes

Same frozen reference, same design document, same decisions by the owner (replayed, the two rejections now made with `sdem reject`). **Not a blind run:** the operator had seen
the reference by then, so this measures what the fixes changed, not SDEM afresh — that needs a new reference (scenario 2). The operator's own mistakes of run 1 were corrected
too: the zones recorded flat as the document has them; no deployment's platform guessed (four left out, as *planned*); the debtor-account operation, the permitted statuses
and every API field the document names recorded.

| Measure | Run 1 | Run 2 | Why |
|---|---|---|---|
| Records held, of the 152 the document names | 141 (93%) | **148 (97%)** | the operator's omissions recorded; the 4 left are kinds SDEM has no record type for |
| SDEM records not in the reference | 3 | **1** | flat zones: no invented zones |
| Links held, of those whose two ends SDEM holds | 107 of 153 (70%) | 108 of 161 (67%) | more ends held, so more links in scope; four *deployment on node* links are gone because their platform is no longer guessed |
| Proposed between layers, first pass | 58: 23 expected or consistent, 35 not | **27: 19 expected or consistent, 8 not** | AID-I08: no invented table. Precision 40% → 70% |
| Inferred inside A4, first pass | 24: 12 wrong | **8: none wrong** | AID-Z05, flat zones |
| Forbidden links proposed | 0 | 0 | |
| Questions right | 29 of 50 | **31 of 50** | +3 from what the operator now records; −1 where run 1's answer rested on a guessed platform — SDEM now says it does not know |
| Planted mistakes caught, of 19 | 5 | **8** | LC-29: the amount as a date, the currency as a boolean, the identifier as money |
| `sdem check` | 0 errors, 15 warnings | 0 errors, 29 warnings | the extra warnings are SDEM naming what is unknown: four platforms, eight shapes in no zone |
| Second pass | a 30-field table invented (F14) | **no table** — "a person rejected its mapping (RJ-04)" | `sdem reject` |

**One new finding from run 2's second pass:**

| # | Finding |
|---|---|
| F15 | **Rejecting one link led SDEM to bring in another domain.** After the owner rejected *Payment Order Initiation REALIZED_BY the API ingress*, the second `sdem aid` pass added BIAN's **Corporate Payroll Services** (21 records, inferred) and proposed it REALIZED_BY the ingress — on the word *payment* in the API's paths. On the first pass the same match was only a note ("not added — only names point to it"). A rejection must not make a weaker match look stronger. **Fixed the same day (AID-M03):** the cause was not the rejection itself — once the business links were *approved* they were no longer *proposed*, so the rule that holds a name-only match back saw no domain named on the business side; an approved link now counts. The 21 records in the run-2 workspace are unconfirmed and were left for the owner |

Still open after run 2: process ↔ application (F5 — the design names no application service); platform software with nothing to place it by (F6); API-level facts as records (F11);
a lost key, a broken API path, a removed access link or path end (M-03, 12, 19, 21); F15.

## Independent audit of run 2 (2026-11-17)

The operator had loaded the design *and* marked the result. At the owner's request the reference's author (the second assistant) was given an export of what SDEM holds and the
operator's scoring, and re-marked it against the frozen files. Its audit is the owner's, kept outside this repository. **Where it is stricter than the operator, its figure stands.**

| Measure | Operator | Independent audit | Settled |
|---|---|---|---|
| Records held, of the 152 the document names | 148 | 148 — agreed (134 as records, 14 as names only) | **148** |
| Links held or derivable, of 161 with both ends held | 108 | 98 — ten BIAN links "claimed but absent from the export" | **103, and 5 more in a different form.** The export had left out the BIAN layer's own links — the operator's omission. Checked in the workspace: 5 of the ten exist as the reference has them (domain aggregates control record ×3, control record associated with object ×2); the other 5 join the same two records the other way round — in SDEM an operation *accesses* its control record, where the reference has the control record *containing* the operation |
| Links present as stored links only (strictest) | not scored | 71 of 212 | **71 + the 5 above = 76 of 212** |
| Questions | 31 right, 5 by description, 3 partly, 11 not | 29 right, 5 by description, 4 partly, 12 not | **the audit's** — the statuses and the scheme name are held on a column or as a name, not as the standard's own API field (Q-43, 44, 46 partly); Q-49 not answered |
| Planted mistakes | 8 of 19 | 8 of 16 applicable; 7 if M-16 must prove *who* approved | **7 of 16** — see F16 |

Also taken from the audit: "44 expected records appear nowhere in the design document" was too strong — four of them (the consent, status and decision business objects, the *payment
rejected* event) are mentioned as phrases, never named as elements; the handoff path lost the reference's *mutual* TLS (recorded as `tls`); the audit log's storage is not linked;
`payload_fields` mixes request and response names.

| # | Finding |
|---|---|
| F16 | **CTL-21 knows an agent only by its name.** M-16 was refused for missing evidence, not for who approved. Given evidence, `sdem approve --reviewer automated-agent` is accepted: a reviewer is "a person" unless the name starts `sdem-` or is one of nine words (*agent*, *copilot*, *ai* …). SDEM says as much of itself — "attribution, not authentication; verified only by a signed commit" — but the control is weaker than its name. The audit's point; confirmed by the operator |

**What both markers agree on:** SDEM holds a design's records well (97% of those named), and is weak where it matters most to an architect — connecting them. Four of five impact
questions went unanswered; a third of the expected links whose ends SDEM holds are missing. The audit's recommendation, which the operator shares: strengthen links, inference,
trace and impact before adding to the metamodel.

## Files

Kept outside git (`work/payment-initiation-v3/`): the workspace, `ws-initial/` (before any decision), `initial-proposals.json` (+ sha256), `review-v3.sh`, `sdem-answers.json` and
`mutation-results.json` (hashed before the reference was opened), `scoring.json`, `run-log.md`, the scripts. One slip is recorded in the run log: the first answer-key question was
seen early by a mistaken command; the design document states its answer.
