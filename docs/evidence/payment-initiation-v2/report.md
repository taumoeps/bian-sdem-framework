# Payment Initiation v2 — the test of a full design (V2-01…V2-07)

> 2026-11-16 · metamodel 0.17.0 · SDEM 0.18.0 (main, 04b953b and after) · made-up data. The test set by
> [a full design](../../design/sdem-full-design-metamodel-design.md) §7: can SDEM hold a full A1–A4 design — every kind, its
> attributes, the information chain field by field, contracts, every link type — built with the CLI only?
> Result: [`examples/payment-initiation-v2`](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/bian/sdem_bian/examples/payment-initiation-v2/). How it was built: the change sets, the AID run and
> the decisions in this folder.

## Result

| Id | Criterion | Result | Measured |
|---|---|---|---|
| V2-01 | every kind of A1–A4 used | **pass** | 46 of 46 concrete kinds |
| V2-02 | every attribute that applies is filled | **partial** | 716 of 1,444 attribute slots (50%). The empty ones are mostly optional detail BIAN does not publish (a field's ISO 20022 reference, personal-data flag) and column details a design leaves to the build (default, unique). No business object, BIAN object or data entity the design uses is thin (LC-23); the starter's two made-up BIAN objects list names without records (LC-24, advisory). |
| V2-03 | the information chain end to end, field-level lineage | **pass, with three application-only fields** | A1 object → BIAN object → table → storage → zone (`sdem trace BO-PAY-INSTR`); 27 field mappings; 8 of the payment table's 11 fields traced to a BIAN field — the other 3 (authorisation status, execution reference, channel id) are the hub's own, with no BIAN counterpart. `sdem trace` from BIAN's `PaymentTransactionAmount` reaches the `amount` column, its table, the database and the zone. |
| V2-04 | every contract points at fields | **pass, one gap** | the business service's inputs and outputs (business objects); all 6 APIs name their request and response fields; the network path names the data it carries. Gap: BIAN operations do not yet *access* the business objects (CT-02 allows it; v2 did not record it). |
| V2-05 | every link type, every link approved | **pass on types, partial on variants** | all 14 link types used, 69 approved links; 23 of the 31 type pairs. Not exercised: a deployment on a node or device, an interface exposed through a node or device, a Notify operation implemented by an event, a stage's own alignment, a business service realised by a component, data stored in an artifact. |
| V2-06 | check clean; documents; trace; impact | **pass** | `sdem check`: no errors (2 advisory LC-24); documents for A1–A4 with field tables; trace as above |
| V2-07 | what SDEM produced against what the person wrote | **reported below** | |

## What SDEM produced and what the person did (V2-07)

| | Count |
|---|---|
| Records written by change sets (drafted for the owner) | A1 18 changes, A2 84 (BIAN's objects, through `--catalogue`), A3 30, A4 13 |
| Records inferred by `sdem aid` | 86 (9 data tables with typed fields, keys and foreign keys) — **20 kept, 66 rejected** |
| Links proposed by SDEM (engine and AID) | 90 AID + 9 engine — **24 approved** |
| Links stated by the person (`sdem connect`) | **25** — 10 field-level and object mappings, the direct A1→A3 links, events, channels, platform services, storage |

**Reading it:** SDEM's inference proposed the right *shape* — a table per BIAN object, typed, keyed — but two-thirds of it duplicated
tables the design already had, or held reference data kept elsewhere. Every link of the new types was stated by the person: nothing
proposes them yet. Both are now being fixed (the owner's approvals 2, 2b, 3, 2026-11-16): AID will propose the direct A1→A3 links
from approved paths and match BIAN fields to *existing* columns, and the import will mark the fields BIAN repeats from parent objects.

**The owner's review:** the owner accepted the recommendations in [`review-v2.sh`](review-v2.sh) as the owner's decisions without reviewing
each line (2026-11-16); every approval and connection is recorded under the owner's name, with its evidence.

## Found and fixed while building it

| Finding | Fix |
|---|---|
| BIAN uses the same field name in several objects (`PaymentIdentification`) — SDEM refused it | a field is named within its object or table (identity: owner + name) |
| BIAN's data types (`Datetime`, `Identifier`, amounts) were read as business objects | read as logical types |
| `sdem bian add` could not bring business objects into a workspace | `--objects`, `--object NAME` |
| AID tried to place locations in network zones | a location is a place, never a zone's shape |
| `sdem aid` (fill, confirm, reject) changed layer files outside a change set | it records what it writes as a change set adopted by the person (AID-W10) |
| an AID proposal could not be approved (confidence written as a word) — also BUILT_AS and EXPOSED_THROUGH | confidence is a number, as the engine writes it |
| a business service's `channels` kept its old list of values | names channel records only |
| "the nine link types" in help and specs; KG-F-03 silent on D9 | worded without a number; KG-F-03 names D9 |
| a change set that raises a record's version strands the links that name the old version | by design (links name a version); a change set that only adds attributes keeps the version |

**Still open (small):** `sdem trace` lists links inside a layer as `? -?-> ?` in its "connections followed"; with `--follow-composition`,
a zone appears twice (part of, and connected to).

## Why v2 sits beside the starter

`examples/payment-initiation` is the engine's sealed evaluation set (its gold mappings and acceptance cases score the inference
against fixed answers) and about 50 tests encode its exact records. Replacing it would invalidate the benchmark, so v2 is its own
example; the owner's decision D7 ("v2 replaces v1") is revisited on that evidence.

## After the fixes (the owner's approvals 2, 2b, 3, 4 — 2026-11-16)

v2 rebuilt from the same change sets, then `sdem aid` once:

| | Before | After |
|---|---|---|
| The owner's 25 hand-stated links that SDEM now proposes | 0 | **16** in one pass — every direct A1→A3 link (SERVED_BY ×3, AUTOMATED_BY, REALIZED_BY for the business service, the event and the channel), the platform service, the BIAN alignment, both object-to-table mappings and 5 field mappings; 3 more (where the kept tables are stored) on the second pass, once the person has confirmed them |
| Inferred tables that duplicated an existing one | 2 (payment transaction, account) | **0** — an existing table is matched first (AID-K02) |
| Left to the person | — | 2 field mappings where BIAN offers two equal fields (debtor and creditor account: FinancialTransaction*From*Account or MoneyTransfer*Source*Account) — never guessed; 2 where SDEM proposed a defensible other BIAN field; 1 column already matched to the starter's own field; the payee's direct A1→A3 mapping (the chain through BIAN already holds it) |
| Proposals beyond the owner's design | — | 4, each plausible: the execution process also served by the payment initiation service, the hub served by the secrets service, the payee aligned to BIAN's payee, the starter's amount field mapped to the amount column |

Documents now mark which of a BIAN object's fields are its own and which BIAN repeats from parent objects; onboarding (`sdem transform`)
reads business events, products, channels, locations and data tables from documents and draw.io / PlantUML diagrams.
