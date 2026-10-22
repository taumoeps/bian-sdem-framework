# Use-case testing of the mapping plan

**Status:** seven use cases defined; E1, M0, M1 and H1 executed 2026-10-22 (see Results); E2, M2, H2 pending. **Purpose:** test `metamodel/new-mappings.json` (the gap-fill plan, §5 of `docs/mapping-logic-planning.md`) against concrete architectures *before* any engine code exists. Execution is by hand — the analyst (or an AI session acting as the engine, following `docs/mapping-execution.md`) performs each step of §5.2 mechanically on the level exports; the existing tooling judges the result.

## Protocol

| Phase | What | Who |
|---|---|---|
| 1 Inputs | A1–A4 level exports (`schema/level-model.schema.json`); the approved mappings the use case says are *already known*; a **sealed gold set** of the mappings the test expects, written before execution and not read during it | author |
| 2 Execute | Step 0 → 5 in order, for every connection the use case lists. Each proposal shows its working: the data joined, the rule fired, or the arrows closed over. No working → it is a step-4/5 proposal at the table's lower confidence | executor |
| 3 Validate | `sdmm-validate --strict` on the proposal document; `sdmm-graph check` with the exports | tool |
| 4 Score | `sdmm-eval <gold> --proposals <proposals>` — precision / recall / F1 per arrow type; every miss and false proposal listed | tool |
| 5 Trace | the traceability questions the case poses, via `sdmm-graph trace` / `impact` over the *approved* set, then over approved + proposed | tool |
| 6 Compare | observed outcome against the confidence `new-mappings.json` predicted, per connection ID | executor, written up in the case's results section |

**Honesty rules.** The gold set is sealed in a file first. Steps 1–3 are mechanical: every proposal cites the data or arrow it came from. The table's confidence is the hypothesis under test — a *high* that misses is a finding against the plan, not against the data. All data is synthetic.

**Steps** (from §5.2): 0 BIAN export · 1 data join · 2 rule application · 3 derivation · 4 structural matching · 5 text inference.

## Tiers

| Tier | Starting point | What is tested | Tool under test |
|---|---|---|---|
| **Easy** | A1–A4 exports and approved mappings all exist | Traceability down (A1→A4) and up (A4→A1, A3→A1); impact classification for a change event; a deliberate gap reported honestly | Graph (`sdmm-graph trace`, `impact`) — exists today |
| **Medium** | A1 and A2 defined and mapped; A3/A4 either exist unmapped (brownfield) or do not exist (greenfield) | Brownfield: fill the A2→A3 and A3→A4 connections by steps 1–3. Greenfield: generate a *target* A3/A4 from BIAN's patterns, labelled as design proposals | the plan, steps 1–3; and the boundary between mapping and design |
| **Hard** | A3 and A4 exist and are documented; no A1/A2 mappings; A1 may not exist | Reverse fill: which domain does each application realise, which operation does each API implement (step 2 reversed, step 3); then the genuinely hard part — which capabilities, where BIAN's mapping is unpublished (B01) | the plan under the worst information conditions; the honesty of "no proposal" |

---

## E1 — Card Fraud Alerts (Easy)

**Scenario.** The shipped example: a capability, its Service Domain, the Fraud Engine, Kubernetes. Everything mapped and approved.

**Given.** `examples/card-fraud-alerts/a1–a4-*.json`; `mappings.json` (FRD-001, 002, 005, 006, 007 approved; FRD-003 superseded; FRD-004 proposed — FRD-006/007 and the enriched exports were added in v0.5.1, after the first run).

**Tests.**

| # | Question | Command | Expected |
|---|---|---|---|
| E1.1 | Downstream from CAP-310 | `sdmm-graph trace CAP-310 --direction down` | CAP-310 → SD-044 → APP-FRAUD-ENGINE → INF-CLOUD-K8S-PROD (FRD-005) and → DEP-FRAUD-PROD (FRD-006, since v0.5.1), each hop with its mapping id |
| E1.2 | Upstream from INF-CLOUD-K8S-PROD | `trace … --direction up` | the same chain reversed, ending at CAP-310 |
| E1.3 | Upstream from the retired host | `trace INF-ONPREM-VM-CLUSTER-B --direction up` | `(no upstream mappings)`, exit 1 (since v0.5.1 `sdmm-graph trace` exits 1 on an empty trace, like `sdmm-trace`); with `--status approved,superseded` the old chain appears |
| E1.4 | Rehost Kubernetes | `impact INF-CLOUD-K8S-PROD --change rehost` | A4, A3 `design_change_required`; A2, A1 `no_impact`; FRD-005 to supersede |
| E1.5 | Retire the domain | `impact SD-044 --change retire` | CAP-310 `design_change_required`, APP `review_required`, INF `no_impact` |
| E1.6 | Gap honesty | trace from SO-044-07 with approved only | `(no downstream mappings)`, exit 1 — the only arrow is `proposed`; with `--status approved,proposed` it appears |

**Connections exercised.** S01 (FRD-001), S17 (FRD-002), S33 (FRD-005), S32 (FRD-006), S02 (FRD-007). **Predicted:** all present and traceable; with the v0.5.1 exports, re-derivable at their assigned steps. **Pass:** every expected output exact. **Status:** executed 2026-10-22 against the pre-enrichment data — see Results; re-run pending.

## E2 — Customer Onboarding, three perspectives (Easy)

**Scenario.** The second shipped example, with process and information arrows as well as the architecture chain, a supersession, and a `DEPLOYED_AS`.

**Given.** `examples/customer-onboarding/mappings.json` (11 records) — **note:** no level exports exist yet; the case first requires authoring `a1–a4` exports for its 17 instance ids (synthetic).

**Tests.**

| # | Question | Expected |
|---|---|---|
| E2.1 | Downstream from CAP-001 | SD-001 → APP-001 → INF-001 *and* DEP-001 (two A4 arrows from the same component) |
| E2.2 | Information chain from BO-001 | BO-001 → BBO-001 → ENT-001 (`ALIGNED_TO`, `MAPPED_TO`) |
| E2.3 | Process chain | VS-001 → BS-001; PRC-001 → SD-001 |
| E2.4 | Upstream from ENT-001 | ENT-001 → BBO-001 → BO-001 — information arrows only; architecture chain must not appear |
| E2.5 | Replace APP-001 | `impact APP-001 --change replace` — SD-001 `design_change_required`, INF-001 / DEP-001 `review_required`, BBO/ENT untouched |
| E2.6 | Governance | edit an approved record's rationale → `sdmm-diff` rejects; supersede instead → accepted |

**Connections exercised.** S01, S02, S04, S12, S17, S24 (proposed), S30, S32, S33. **Pass:** chains per perspective are disjoint where they should be; impact matches the rules table. **Status:** needs level exports authored.

## M0 — Card Fraud Alerts as an inference test (Medium, on existing data)

**Scenario.** The enriched fraud exports (v0.5.1) with the approved mappings **hidden** except the capability → domain arrow. The executor must infer the rest from the exports alone. This is the first test that the data carries enough to connect the levels and that the steps are followable; it is small, so it establishes that the machinery works, not that the plan holds on a realistic estate (that is M1).

**Given.** `examples/card-fraud-alerts/a1–a4-*.json` (v0.5.2: export keys incl. `asset_type`, `stages`); `m0-mappings-given.json` — FRD-001 only (CAP-310 `SUPPORTED_BY` SD-044, approved). **Gold (sealed):** `m0-gold-mappings.json` — FRD-002, 004, 005, 006, 007, 008 approved; FRD-003 superseded; FRD-009 proposed. (First run used the v0.5.1 gold with FRD-004 proposed and no FRD-008 — see results and actions.) Do not open it until phase 5.

**Connections to attempt and what the plan predicts.**

| ID | Connection | Step | Expected from the data | Predicted |
|---|---|---|---|---|
| S33 | APP-FRAUD-ENGINE `DEPLOYED_ON` INF-CLOUD-K8S-PROD | 1 | `deployed_on` / `hosts` | high |
| S32 | APP-FRAUD-ENGINE `DEPLOYED_AS` DEP-FRAUD-PROD | 1 | `component_id` / `deployed_as` | high |
| S36 | APP-FRAUD-ENGINE → INF-CLOUD-K8S-PROD (SystemSoftware) | 1 | same key — **subsumed by S33** since v0.5.2; not a separate proposal | — |
| S24 | SO-044-07 `IMPLEMENTED_BY` POST /fraud/alerts | 2 | action term **Notify** — unused in the REST mapping, so rule 2 is untestable; rules 1 (via `asset_type`), 3, 4 testable | medium (3 of 4); the executor must say rule 2 could not be tested |
| S17 | SD-044 `REALIZED_BY` APP-FRAUD-ENGINE | 3, else 4 | derived from S24 if proposed; else asset-type name "Fraud Alert" in `/fraud/alerts` | **medium** — the derivation is capped at its S24 input (3 of 4 REST rules, medium); high only where the API arrow is approved |
| S04 | PRC-310-01 `USES_DOMAIN` SD-044 | 3 | `invokes: [SO-044-07]` → domain via B10/B09 | medium |
| S02 | VS-CARD-USE `ALIGNED_TO` BS-FRAUD-ALERT | 4 | `stages` vs `operation_sequence`, scored as **coverage of the scenario's operations** (v0.5.3 rule), not a stage count — one operation, covered by stage "Alert the cardholder" | medium |
| S01 | CAP-300 `SUPPORTED_BY` SD-044 | 5 | single candidate domain → **no proposal** (step-5 rule). The parent-capability rule is report-only since v0.5.3 and must not produce a proposal | none |

**Negative tests.** CMP-SCORING has no `deployed_on` → no `DEPLOYED_ON`; IFC-FRAUD-API is an interface, not a component → not an S17 target; no record for S50 → no proposal.

**Pass.** All six approved arrows re-derived at their assigned step (or a declared fallback / optional step with the lower band); `sdmm-eval` precision ≥ 0.8 over the IDs the gold approves; every attempted connection has a row in `m0-inference-log.json`; S01 for CAP-300 recorded as no-proposal. **Status:** executed twice — v0.5.1 gold (P 0.60 R 0.75) and v0.5.2 gold (P 0.86 R 1.00, F1 0.92); see Results. **Complete** — remaining findings applied in v0.5.3; the one false proposal (S01 parent rule) is withdrawn.

## M1 — Payment Initiation, brownfield (Medium)

**Scenario.** The business and domain architecture are mapped and approved. The payments platform exists — applications, APIs, data entities and deployments are exported from the APM and CMDB to the export conventions — but no A2→A3 or A3→A4 mappings have been written.

**Given.** `examples/payment-initiation/a1–a4-*.json` (68 instances: see that folder's README); `m1-mappings-given.json` — PAY-001…005 approved (A1→A2: `SUPPORTED_BY`, `ALIGNED_TO` ×2, `USES_DOMAIN` ×2). **Gold (sealed):** `m1-gold-mappings.json` — PAY-101…113 approved: five `IMPLEMENTED_BY`, one `REALIZED_BY`, one `MAPPED_TO`, three `DEPLOYED_ON` (PAY-113, UAT hosting, added after run 1), three `DEPLOYED_AS`. Do not open it until phase 5. `mappings.json` in that folder is the union and is **not** an input to the executor.

**Planted.** `API-PI-04` implements the *Retrieve* operation as **POST** (recorded in the gold's rationale as a legacy-channel deviation): rule 2 must fail and be reported as a finding while rules 1, 3, 4 hold, so the proposal lands one band lower. `API-PI-06` implements nothing. `SO-PI-06` is *Notify* (no REST form). `CMP-PAY-CAPTURE` / `CMP-PAY-VALIDATE` have no deployment records. `ENT-ACCOUNT-CACHE` matches no BOM object. Three Service Domains are exported, so step 5 has a real candidate set.

**Execution order.** Step 1 on the A3/A4 keys → `DEPLOYED_ON`, `DEPLOYED_AS` (five). Step 2 → `IMPLEMENTED_BY` for each API against each operation of SD-PI (rule 1 via `asset_type` "Payment Instruction" in `/payment-instructions`). Step 3 → `REALIZED_BY` from the step-2 proposals; S25 (operation → `SVC-PAY-INIT`), S22/S23, S40, S47 as derived paths. Step 4 → `MAPPED_TO` by attribute match against `BBO-PAY-INSTR` and `CR-PI`; S20.

**Connections exercised and predicted.**

| ID | Connection | Step | Predicted |
|---|---|---|---|
| S33 ×3, S32 ×3 | hub and gateway → platforms / deployments (hub → UAT platform included; `DEPLOYED_ON` is environment-agnostic since v0.5.4) | 1 | high — pure joins; **no** proposal for CMP-PAY-CAPTURE / CMP-PAY-VALIDATE |
| S24 ×5 | operations → APIs | 2 | high for 01, 02, 03, 05 (4 of 4 rules); **medium** for 04 (rule 2 fails: Retrieve on POST — must be a finding); no proposal for SO-PI-06 (Notify) or API-PI-06 |
| S17 | SD-PI → APP-PAY-HUB | 3 | high — capped at the **strongest** step-2 input (any one implemented operation suffices; v0.5.4); **no** proposal for SD-PE, SD-PA |
| S25 | operations → SVC-PAY-INIT | 3 | high (candidate-rule report) |
| S30 | BBO-PAY-INSTR → ENT-PAY-INSTR | 4 | high (8/8 attributes); no proposal for ENT-ACCOUNT-CACHE; BBO-PARTY → nothing |
| S20 | CR-PI → ENT-PAY-INSTR | 4 | high (10/11) — candidate-rule report |
| S41 | SVC-PAY-INIT → TS-SECRETS, TS-MQ | 1 | medium — conditional-rule report via `consumes` |
| S50 | entities → INF-PG-PAY-PROD | 1 | medium — institution-only report via `stored_in` |
| S40, S47 | derived paths | 3 | high — as queries |

**Then.** Trace CAP-PAY-010 → platform; `impact INF-K8S-PAY-PROD --change rehost`. **Pass.** `sdmm-eval` F1 ≥ 0.85 over the approved gold; the planted mismatch reported; every negative holds; `m1-inference-log.json` complete. **Status:** executed 2026-10-22 — see Results.

## M2 — Digital Lending, greenfield (Medium)

**Scenario.** A new product line. A1 and A2 are designed and mapped. **There is no A3 or A4** — nothing has been built.

**Given.** A1: capability, value stream, three processes. A2: two Service Domains (lending origination, credit assessment) with operations, control records, a scenario. **Approved:** A1→A2 arrows. **No A3/A4 exports.**

**What the plan can and cannot do.** No step fills A2→A3 or A3→A4 — there is nothing to join, apply rules to, or derive from. What BIAN *does* provide is a pattern: each Service Domain as a discrete deployable component exposing its operations as a REST API ([SAPG] §3.5, §4.1). The test is whether the executor produces a **target A3/A4 design proposal** from that pattern — two application components, their reference APIs from the Semantic API definitions, two deployments — and labels it unambiguously as *design*, not mapping.

**Tests.**

| # | Check | Expected |
|---|---|---|
| M2.1 | Proposals are typed as design, not mapping | records carry `status: proposed`, `created_by` naming the pattern source, confidence **low**, and `rationale` stating they are a target design derived from BIAN's container pattern |
| M2.2 | Reference APIs | each proposed API operation's path/method follows the REST mapping from the operation's action term and qualifier |
| M2.3 | Trace honesty | `sdmm-graph trace CAP --direction down` on approved only stops at A2; with proposals included it reaches the *proposed* A4 |
| M2.4 | Negative | no `DEPLOYED_ON` to any concrete platform is proposed — there is no data to name one |

**Connections exercised.** S17, S24, S32 as *design targets*; S36/S50 must not appear. **Pass:** M2.1–M2.4 hold; the write-up states where mapping ends and design begins. **Status:** data to author.

## H1 — Legacy Core Ledger, reverse mapping (Hard)

**Scenario.** A twenty-year-old core banking ledger. Its A3 (five modules, four SOAP interfaces, fourteen operations, three batch jobs, five tables) and A4 (mainframe LPAR, DB2, MQ) are fully documented in the CMDB. **No mappings exist.** A1 is only a draft capability list — six names with descriptions, no processes, no value streams.

**Given.** `examples/legacy-core-ledger/a1–a4-*.json` (87 instances; see that folder's README); `h1-mappings-given.json` — **empty**. **Gold (sealed):** `h1-gold-mappings.json` — 28 approved: 14 `IMPLEMENTED_BY`, 4 `REALIZED_BY` (module level), 4 `MAPPED_TO`, `DEPLOYED_ON`, `DEPLOYED_AS`, 4 `SUPPORTED_BY`. Do not open it, or `mappings.json`, until phase 5.

**Planted / to refuse.** Every SOAP operation is **POST**: check 2 passes only for Initiate and Register and fails for every Retrieve, Update, Control and Execute — those are proposed one band lower with a *systematic* finding ("all operations POST"), not dropped. Three batch jobs carry `method: BATCH` — not an HTTP interface; step 2 does not apply; they map to nothing. `APP-LEDGER` composes the modules that compose the interfaces — realisation is at **module** level; the ledger as a whole is a derived path, not a proposal. `ENT-AUDIT` matches no BOM object. `CAP-LENDING` and `CAP-TREASURY` match no domain: no proposal, not a low-confidence guess.

**Execution order.** Step 1 (A3/A4 keys) → `DEPLOYED_ON`, `DEPLOYED_AS`. Step 2 **in reverse** — for each SOAP operation, the decision procedure over the 14 BIAN operations of the four domains; precondition via the asset-type name in the interface's operation names and descriptions. Step 3 → `REALIZED_BY` per module from its interface's step-2 proposals (capped at the strongest input). Step 4 → `MAPPED_TO` by attribute match. Then A1: step 3 impossible (no processes); step 5 over the four domains against six capabilities — propose at most one domain per capability, low; two capabilities must get no proposal.

**Connections exercised and predicted.**

| ID | Connection | Step | Predicted |
|---|---|---|---|
| S33, S32 | ledger → LPAR, production deployment | 1 | high |
| S24 ×14 | operations ← SOAP operations | 2 reverse | high for 3 (Initiate ×2, Register); **medium** for 11 (method mismatch, unique best payload match); none for the 3 batch jobs |
| S17 ×4 | domains ← modules | 3 | high — any one implemented operation suffices; **no** proposal for APP-LEDGER (derived path) or LM-BATCH |
| S30 ×4 | BOM objects → tables | 4 | high (≥ 7/8 attributes); none for ENT-AUDIT |
| S20 ×4 | control records → tables | 4 | high — candidate-rule report |
| S01 ×4 | capabilities → domains | 5 | **low** — four-domain candidate set; two capabilities no proposal |
| S50 | tables → DB2 | 1 | medium — institution-only report via `stored_in` |

**Pass.** F1 ≥ 0.8 over the approved gold; the systematic POST finding reported once, not fourteen times; every negative held; A1 proposals all low with step-5 rationale; `h1-inference-log.json` complete. **Status:** executed 2026-10-22 — see Results.

## H2 — Acquired Fintech, hostile naming (Hard)

**Scenario.** A recently acquired fintech. A3/A4 are documented — a microservice estate with ~20 REST endpoints — but the API naming is product-specific (`/v2/moneyflows`, `/zap`), nothing resembles BIAN action terms, and there is no documentation beyond OpenAPI stubs and a deployment manifest. No A1, no A2 mappings.

**Given.** A3 export with endpoints, methods and payload field names; A4 export from the manifest; A2 synthetic BIAN export; **no A1**; no approved mappings. **Gold (sealed):** what a patient architect concluded after interviews — including several endpoints that map to *nothing* in BIAN.

**Execution order.** Step 2 fails by design (no action-term alignment). Step 1 fills A4. Step 4 — payload field names against control-record and BOM attributes; path nouns against asset types. Step 5 — only for pairs step 4 scores but cannot settle. Everything A1 is step 5 or "no proposal".

**Tests.**

| # | Check | Expected |
|---|---|---|
| H2.1 | Step 2 produces nothing and says so | no `IMPLEMENTED_BY` at step 2; the write-up records why |
| H2.2 | Step 4 proposals cite the attributes matched | every proposal names the field/attribute pairs |
| H2.3 | Endpoints with no BIAN counterpart | **no proposal** — not a forced low-confidence one; precision over recall |
| H2.4 | A1 | either low-confidence step-5 proposals with rationale, or "requires authoring" |
| H2.5 | A4 unaffected | S32/S33 still high — the hostile naming does not touch deployment data |

**Connections exercised.** S24 (expected to fail at step 2, partially recover at 4), S17, S30, S32, S33, S01. **Pass:** precision ≥ 0.8 even if recall is low; H2.3 holds; confidence bands match the table. **Status:** data to author.

---

## What the six cases cover together

| | E1 | E2 | M1 | M2 | H1 | H2 |
|---|---|---|---|---|---|---|
| Traceability down / up | ● | ● | ● | ● | ● | ● |
| Impact classification | ● | ● | ● | | | |
| Governance (diff, supersession) | ● | ● | | | | |
| Step 1 data join | | | ● | | ● | ● |
| Step 2 REST rules | | | ● | ● (as design) | ● reversed | ● must fail |
| Step 3 derivation | | | ● | | ● | |
| Step 4 structural matching | | | ● | | ● | ● |
| Step 5 text inference | | | | | ● (A1) | ● (A1) |
| Negative tests | ● | ● | ● | ● | ● | ● |
| Perspectives: architecture / process / information | A | A P I | A P I | A | A I | A I |

**Order of execution:** E1, M0, M1, H1 (done); **H2 next**; E2 after its exports are authored; M2 last (it tests a boundary, not the plan's core).

## Results

*To be appended per case: proposal document, `sdmm-eval` output, predicted vs observed confidence per connection, findings against the plan.*

### E1 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md`. The guide's template labels the engine `opus-executor`; this run is labelled `fable-executor/2026-10-22` so the record says who ran it. **Gold.** E1 has no separate `gold-mappings.json`; the gold is the three approved records in `examples/card-fraud-alerts/mappings.json`, which the case lists as *given*. The executor therefore saw the gold before executing. Mitigation: every proposal below was built from the level exports only; approved arrows were read only where a step rule permits (step 2 rule 1, step 3), and no approved arrow was used as evidence for a proposal of the same pair. **Proposal file.** `examples/card-fraud-alerts/e1-proposals.json` (2 records; overwritten by the M0 run later the same day — the E1 version is in commit fb94510).

#### Graph tests E1.1–E1.6 (phase 5, approved arrows only unless stated)

| # | Expected | Observed | Verdict |
|---|---|---|---|
| E1.0 `graph check` | — | all four levels and the mapping document OK | pass |
| E1.1 | CAP-310 → SD-044 → APP-FRAUD-ENGINE → INF-CLOUD-K8S-PROD with FRD-001, FRD-002, FRD-005 | exact; A4 node rendered as `A4.SystemSoftware` (level-model type), resolved from the mapping's `A4.InfrastructureComponent` | pass |
| E1.2 | same chain reversed, ending at CAP-310 | exact | pass |
| E1.3 | nothing, **exit 1**; with `--status approved,superseded` the old chain via FRD-003 | `INF-ONPREM-VM-CLUSTER-B  (no upstream mappings)`, **exit 0**; with the status flag the FRD-003 → FRD-002 → FRD-001 chain appears | **pass with deviation** — exit code is 0, not 1 (finding 7) |
| E1.4 | A4, A3 `design_change_required`; A2, A1 `no_impact`; FRD-005 to supersede | exact | pass |
| E1.5 | CAP-310 `design_change_required`, APP `review_required`, INF `no_impact` | exact; tool also lists FRD-001, FRD-002 to supersede | pass |
| E1.6 | **exit 1** on approved only; with `--status approved,proposed` the FRD-004 arrow appears | `SO-044-07  (no downstream mappings)`, **exit 0**; with the flag `SO-044-07 -IMPLEMENTED_BY-> POST /fraud/alerts (FRD-004)` | **pass with deviation** — exit code is 0, not 1 (finding 7) |

Verbatim output of the two deviating cases and the impact tests:

```
$ python -m sdmm.graph trace INF-ONPREM-VM-CLUSTER-B --direction up examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
UPSTREAM (depended on by):
INF-ONPREM-VM-CLUSTER-B  (no upstream mappings)
exit=0

$ python -m sdmm.trace INF-ONPREM-VM-CLUSTER-B --direction up examples/card-fraud-alerts/mappings.json
ERROR: 'INF-ONPREM-VM-CLUSTER-B' does not appear in any approved mapping
exit=1

$ python -m sdmm.graph impact INF-CLOUD-K8S-PROD --change rehost examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
IMPACT of 'rehost' on INF-CLOUD-K8S-PROD: hosting changes only; deployment records must be superseded, functional layers unaffected

  design_change_required   A4  INF-CLOUD-K8S-PROD  Managed Kubernetes (production)  via -
  design_change_required   A3  APP-FRAUD-ENGINE    Fraud Engine  via FRD-005
  no_impact                A2  SD-044              Fraud Detection (synthetic selection)  via FRD-005, FRD-002
  no_impact                A1  CAP-310             Card Fraud Alerts  via FRD-005, FRD-002, FRD-001

  mappings to supersede: FRD-005

$ python -m sdmm.graph impact SD-044 --change retire examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
IMPACT of 'retire' on SD-044: instance removed; direct dependents lose a dependency, indirect ones review

  design_change_required   A2  SD-044              Fraud Detection (synthetic selection)  via -
  design_change_required   A1  CAP-310             Card Fraud Alerts  via FRD-001
  review_required          A3  APP-FRAUD-ENGINE    Fraud Engine  via FRD-002
  no_impact                A4  INF-CLOUD-K8S-PROD  Managed Kubernetes (production)  via FRD-002, FRD-005

  mappings to supersede: FRD-001, FRD-002
```

#### Proposals

| Proposal | Plan ID | Connection | Step used (assigned / fallback) | Confidence | Working |
|---|---|---|---|---|---|
| P-E1-001 | S17 | SD-044 `REALIZED_BY` APP-FRAUD-ENGINE | 3 assigned → **4 fallback**: no approved `IMPLEMENTED_BY` exists (FRD-004 is `proposed`) and step 2 produced none, so there is nothing to close over | 0.6 (high → medium for the fallback) | functional-partition comparison of descriptions, executor convention: shared content concepts after case/plural normalisation. SD-044 vs APP-FRAUD-ENGINE share {fraud, transaction, alert} = 3/9 domain concepts; CMP-SCORING 2/9 and IFC-FRAUD-API 2/9, both parts of APP-FRAUD-ENGINE by A3 `composition`, so the whole is proposed and the parts are not |
| P-E1-002 | S01 | CAP-310 `SUPPORTED_BY` SD-044 | 3 assigned → **5 fallback**: CAP-310's only process PRC-310-01 (A1 `realization`) has no `USES_DOMAIN` arrow, no activities and no operation mapping, so S04 and hence S01 cannot be derived | 0.4 (medium → low for the fallback) | texts compared: CAP-310 "Detect suspicious card transactions in real time and alert the cardholder …" vs SD-044 "evaluates transactions and activity for indications of fraud and raises alerts"; shared concepts {fraud, transaction, alert} = 3/12 capability concepts. SD-044 is the **only** `A2.ServiceDomain` in the export, so "clearly better than the rest" is vacuous (finding 5). CAP-300 vs SD-044 shares only {fraud} — rejected |

#### Candidate-rule and institution-only proposals (not in the proposal file)

None. S36 (component → `A4.SystemSoftware`) is the pair FRD-005 actually instantiates — INF-CLOUD-K8S-PROD is `A4.SystemSoftware` in the level model — but no step-1 record supports it either (see S33 below), so no proposal.

#### sdmm-eval

```
$ python -m sdmm.evaluate examples/card-fraud-alerts/mappings.json --proposals examples/card-fraud-alerts/e1-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_ON         1    0   0   0   1   0.00  0.00  0.00
REALIZED_BY         1    1   1   0   0   1.00  1.00  1.00
SUPPORTED_BY        1    1   1   0   0   1.00  1.00  1.00
OVERALL             3    2   2   0   1   1.00  0.67  0.80

missed (approved, not proposed):
  APP-FRAUD-ENGINE -DEPLOYED_ON-> INF-CLOUD-K8S-PROD
```

Validation and trace over approved + proposed:

```
$ python -m sdmm.graph check examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json examples/card-fraud-alerts/e1-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/card-fraud-alerts/e1-proposals.json
ERROR: … (P-E1-001): proposal lacks required evidence kind(s) ['application_architecture_document']; must be supplied before approval
ERROR: … (P-E1-002): bian_alignment_guidance mapping requires bian_release; must be supplied before approval
ERROR: … (P-E1-002): proposal lacks required evidence kind(s) ['business_architecture_document', 'domain_scope_assessment']; must be supplied before approval
exit=1
$ python -m sdmm.validate examples/card-fraud-alerts/e1-proposals.json
(same three lines as WARNING)  OK: examples/card-fraud-alerts/e1-proposals.json (with warnings)
exit=0

$ python -m sdmm.graph trace CAP-310 --direction down … --status approved,proposed
CAP-310 → SD-044 (FRD-001 and P-E1-002, as two sibling branches) → APP-FRAUD-ENGINE (FRD-002 and P-E1-001, again as siblings) → INF-CLOUD-K8S-PROD (FRD-005)
```

`--strict` fails on the proposal file by construction (finding 6); the same three warnings also fail `proposals-baseline.json` under `--strict`, while `mappings.json` passes. The approved+proposed trace reaches A4 but renders each approved/proposed duplicate pair as two branches, so the subtree is printed four times (finding 8).

#### Predicted vs observed, per plan ID

| Plan ID | Predicted confidence (step) | Observed | Verdict |
|---|---|---|---|
| S01 | medium (step 3) | step 3 impossible on this data (no `USES_DOMAIN`, no activities); step-5 fallback hit the gold at low (0.4), 1/1, no false proposal | **weaker than predicted** — the plan's own fallback worked, the assigned step did not |
| S17 | high (step 3) | step 3 impossible (no approved `IMPLEMENTED_BY`; step 2 produced none); step-4 fallback hit the gold at medium (0.6), 1/1 | **weaker than predicted** |
| S33 | high (step 1) | no record in the A4 or A3 export names APP-FRAUD-ENGINE on any platform; no proposal; the approved FRD-005 **missed** | **failed on this data** |
| S24 | high (step 2) | 1 of 4 checks testable (rule 1 holds: APP-FRAUD-ENGINE is approved-realized FRD-002 and composes IFC-FRAUD-API → `POST /fraud/alerts`); rules 2–4 untestable — no action term, qualifier, control-record attributes or I/O in the A2 export, no method/path/payload fields in the A3 export. No proposal. FRD-004 (0.71) is **not** reproduced under the guide's rules | **failed on this data** (untestable, not wrong) |
| S04 | medium (step 3) | PRC-310-01 has no activities and no operation arrow; no proposal | not producible on this data |
| S02 | medium (step 4) | no `A2.BusinessScenario` instance in the export; no instance to map to | not producible on this data |
| Case prediction "all present and traceable; nothing to infer" | — | traceable: yes, every hop with its mapping id. "Nothing to infer": false — re-deriving the three approved arrows from the exports required two fallbacks and left one arrow unproducible | **holds for traceability, fails for the plan** |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide) |
|---|---|---|---|---|
| 1 | S33 (also S32, S36, S50) | step 1 found no record naming the component; the approved `DEPLOYED_ON` was missed | `level-relationships.json` policy makes `relationships` within-level only, and `attributes` is a free-form object; the E1 A4 export has no `A4.Deployment` and no attribute referencing an A3 id. The join has no key | `data_needed`: name the export-side convention the join keys on (e.g. an A4 instance attribute `hosts`/`component_id` holding the A3 id, or a `cross_level_refs` field in `level-model.schema.json`). Then either add it to the E1 A4 export or state in E1 that S33 is a trace test only |
| 2 | S24 | step 2 could test only rule 1; rules 2–4 had no data on either side | the A2 export carries name and description only; the A3 export encodes method and path in the instance id and has no payload fields. `data_needed` says what is needed but not where it lives in the export | `data_needed`: name attribute keys (`action_term`, `behaviour_qualifier`, `control_record_attributes`, `input`/`output` on A2; `method`, `path`, `payload_fields` on A3) so step 2 is mechanical. Enrich the E1 exports or declare S24 out of E1's scope. Note that FRD-004 exists at 0.71 yet cannot be reproduced by the rules — the existing proposed record is itself a name-overlap guess |
| 3 | S24, guide §3 step 2 rule 2 | the operation's verb "Notify" has no row in the action-term table | the table lists Retrieve plus twelve noun-form terms; it does not say whether an unlisted verb fails rule 2 or is untestable | guide §3: state the treatment of verbs outside the table (recommend: rule 2 untestable → counts as a miss), and verify against [SAPG] whether Notify is a published action term before adding a row |
| 4 | S17 | the plan's fallback "functional-partition comparison of descriptions (step 4)" has no row in guide §3 step 4; the executor had to define the match (shared-concept count, composition tie-break) | §5.2 defines description comparison as step 5 (text inference), not step 4 (structural). The plan labels it step 4, which keeps the confidence one band higher than a step-5 fallback would | either add an S17 row to §3 step 4 with a defined score and threshold (the convention used here is a candidate), or relabel the fallback as step 5 in `reasoning` and drop two bands. Decide which; the executor should not be choosing |
| 5 | S01, guide §3 step 5 | the "clearly better than the rest" test was vacuous: one domain in the export | step 5 is a ranking rule; with one candidate it degenerates to "does it share any concept", which is weaker than the band implies | guide §3 step 5: require the candidate set to be the full A2 landscape (or ≥ N domains) for a step-5 proposal; with fewer, mark the proposal `single-candidate` or make no proposal. `data_needed` for S01: "all exported Service Domains, not only the one mapped" |
| 6 | guide §5, §7 | `sdmm-validate --strict` fails on the proposal file; §7 says it should pass "with warnings" | `--strict` promotes every warning to an error; engine-only evidence always lacks the required evidence kinds and `bian_release`, so no proposal file can pass. `proposals-baseline.json` fails the same way | guide §5: run `sdmm-validate` without `--strict` on proposal files (keep `--strict` for `mappings.json`); §7: "passes without `--strict`; the evidence-kind and `bian_release` warnings are expected" |
| 7 | use case E1.3, E1.6 | expected exit 1; `sdmm-graph trace` exits 0 and prints `(no … mappings)` | the older `sdmm-trace` exits 1 with an ERROR; the graph command does not | `use-case-testing.md`: correct the two expected cells to "exit 0, `(no upstream/downstream mappings)`", or change `sdmm/graph.py` to exit 1 on an empty trace to match `sdmm-trace`. Not a plan finding; recorded so the case's pass criterion is exact |
| 8 | tool note | the approved+proposed trace prints the A3/A4 subtree four times | an approved and a proposed arrow on the same (source, relationship, target) are rendered as separate branches | no change to the plan; `sdmm/graph.py` trace could collapse duplicate arrows and list both mapping ids on one hop |
| 9 | S36 | the approved `DEPLOYED_ON` in E1 targets an `A4.SystemSoftware`, i.e. the S36 pair typed as S33 | supports S36's `reasoning` ("the fraud example's Kubernetes is SystemSoftware") | no change forced; evidence for promoting S36 to `enterprise_rule`. Whatever convention finding 1 adopts must cover SystemSoftware targets |
| 10 | guide §4 | `engine: opus-executor/<date>` hard-codes the model | runs by other models mislabel themselves or deviate from the template | guide §4, §6: `<model>-executor/<date>` |

#### New connection candidates (outside the plan)

| Pair | Found by step | Reasoning | Confidence | Suggested ID |
|---|---|---|---|---|
| PRC-310-01 (`A1.BusinessProcess`) → SO-044-07 (`A2.ServiceOperation`) | 4, as the S06 verb+noun rule applied to the process itself because it has no activities | process "notify the cardholder, capture their response and release or block the transaction" vs operation "Notify an interested party of a suspected fraud event and record their response": shared {notify, alert, response}; verb Notify matches, noun Alert matches. No plan ID covers process → operation (S06 is activity → operation, S04 is process → domain). If adopted, it would make S04 derivable at step 3 for processes exported without activities, and S01 in turn | medium | S06a (process → operation, `institution_only`, step 4) or an explicit note on S04 that a process with no activities may be matched directly |

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S33 | APP-FRAUD-ENGINE, CMP-SCORING × INF-CLOUD-K8S-PROD, INF-ONPREM-VM-CLUSTER-B, ENV-PROD, NET-PRIVATE | no A4 relationship or attribute, and no A3 attribute, names a component on a platform; the only A4 relationships are ENV-PROD `aggregation` INF-CLOUD-K8S-PROD and INF-CLOUD-K8S-PROD `assignment` NET-PRIVATE. No higher step covers `DEPLOYED_ON` |
| S32 | APP-FRAUD-ENGINE, CMP-SCORING | no `A4.Deployment` instance in the export — no instance to map to |
| S36 | APP-FRAUD-ENGINE × INF-CLOUD-K8S-PROD | as S33 — no record |
| S24 | SO-044-07 × `POST /fraud/alerts` | 1 of 4 rules testable (rule 1 holds); fewer than three → no proposal. Step-4 fallback (S06-style verb+noun): noun "alert" matches, verb Notify ≠ Create → fails |
| S04 | PRC-310-01 × SD-044 | no activities on the process, no `IMPLEMENTED_BY` or scenario arrow to derive from; the new-connection candidate above would supply it but is quarantined |
| S02 | VS-CARD-USE | no `A2.BusinessScenario` in the export |
| S01 | CAP-300 × SD-044 | one shared concept ({fraud}); the capability's scope (fraud, credit and operational risk) is far wider than the domain's; precision over recall |
| S17 | SD-044 × CMP-SCORING, IFC-FRAUD-API | parts of APP-FRAUD-ENGINE by composition; IFC-FRAUD-API is also an `A3.ApplicationInterface`, not the S17 target type |

**Summary.** As a graph test E1 passes: all six traces and impacts match, with two exit-code cells to correct. As a plan test it is honest rather than clean: two of three approved arrows were re-derived only by fallback steps, the deployment arrow could not be re-derived at all, and the API arrow could not be tested. Every failure is a gap in what the exports carry, not a wrong rule — which is what M1's exports must fix before it runs.

### E1 — actions taken on the findings (v0.5.1)

| Finding | Action |
|---|---|
| 1, 2, 9 — no join keys in the exports | `metamodel/export-conventions.json` defines the attribute keys steps 1–4 join on (`deployed_on`, `deployed_as`, `component_id`, `hosts`, `stored_in`, `action_term`, `behavior_qualifier`, `input/output_attributes`, `method`, `path`, `payload_fields`, `invokes`, …). The fraud exports now carry them, plus an `A4.Deployment` and an `A2.BusinessScenario`. `data_needed` in `new-mappings.json` names the keys |
| 3 — Notify | Verified in [SAPG] §3.2.5: 17 action terms, Notify among them; §3.5: not used in the REST mapping. Guide rule 2 now lists all 17 and treats Notify (or any term outside the 17) as untestable → miss |
| 4 — S17 fallback | Guide step 3 now defines a step-4 structural fallback for S17 (asset-type noun in API paths / entity names); description-only comparison is step 5, two bands lower |
| 5 — single-candidate step 5 | Guide step 5 requires the full A2 landscape or ≥ 3 candidates; otherwise *single-candidate, no proposal*. S01 `data_needed` updated |
| 6 — `--strict` | `sdmm-validate --strict` no longer promotes draft warnings on proposed records; guide §7 restated |
| 7 — exit codes | `sdmm-graph trace` exits 1 on an empty trace, consistent with `sdmm-trace`; E1.3/E1.6 expectations restated |
| 8 — duplicate branches | trace collapses an approved and a proposed record of the same arrow into one hop listing both ids |
| 10 — engine label | guide uses `<model>-executor/<date>` |
| new-connection candidate (process → operation) | recorded as a note on S04 rather than a new ID: a process exported without activities may be matched directly by the S06 rule |
| (earlier finding) four BIAN-internal constraints missing | B07, B08, B11, B12 added to `metamodel/level-relationships.json`; all 12 constraint-bearing BIAN relationships now encoded |

**E1 is re-runnable:** with the enriched exports, S33 (step 1), S32 (step 1), S24 (step 2) and S04 (step 3) now have keys. A second run should re-derive all three approved arrows at their assigned steps.

### M0 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.1. **Given.** `m0-mappings-given.json` (FRD-001 only) and the v0.5.1 exports. **Gold.** `m0-gold-mappings.json` was not opened until phase 5. Disclosure: the E1 section's v0.5.1 diff names FRD-006 as S32 and FRD-007 as S02, and the M0 section lists the gold's record ids, so the four approved gold arrows were inferable before execution; every proposal below was nonetheless produced by the step rules on the exports, and the two false proposals show the gold did not steer them. **Files.** `examples/card-fraud-alerts/m0-proposals.json` (5 records; the E1 file at the same path is in commit fb94510) and `examples/card-fraud-alerts/m0-inference-log.json` (17 attempts, 13 plan IDs).

#### Proposals

| Proposal | Plan ID | Connection | Step used (assigned / fallback) | Confidence | Working |
|---|---|---|---|---|---|
| P-M0-001 | S33 | APP-FRAUD-ENGINE `DEPLOYED_ON` INF-CLOUD-K8S-PROD | 1 / — | 0.8 | `APP-FRAUD-ENGINE.attributes.deployed_on = [INF-CLOUD-K8S-PROD]`; `INF-CLOUD-K8S-PROD.attributes.hosts = [APP-FRAUD-ENGINE]`; both sides name each other |
| P-M0-002 | S32 | APP-FRAUD-ENGINE `DEPLOYED_AS` DEP-FRAUD-PROD | 1 / — | 0.8 | `DEP-FRAUD-PROD.attributes.component_id = APP-FRAUD-ENGINE` (environment ENV-PROD, platform INF-CLOUD-K8S-PROD); `APP-FRAUD-ENGINE.attributes.deployed_as = [DEP-FRAUD-PROD]` |
| P-M0-003 | S24 | SO-044-07 `IMPLEMENTED_BY` POST /fraud/alerts | 2 / — | 0.6 (3 of 4 rules → one band lower) | rule 1 holds by the reverse test, **executor convention**: the export has no `A2.AssetType`, so the domain description's nouns {transaction, fraud, alert} were matched in the component description; API composed in IFC-FRAUD-API in APP-FRAUD-ENGINE. Rule 2 **untestable**: `action_term` Notify is not used in the BIAN REST mapping (method is POST) — counts as a miss. Rule 3 holds: qualifier `Alert` ~ path segment `alerts` after resource `fraud`. Rule 4 holds: input ∪ output = 5 attributes, 5/5 in `payload_fields` |
| P-M0-004 | S04 | PRC-310-01 `USES_DOMAIN` SD-044 | 3 / — | 0.6 | `PRC-310-01.attributes.invokes = [SO-044-07]`; A2 relationships SG-044-01 `composition` SO-044-07 (B10), SD-044 `composition` SG-044-01 (B09); no mapping arrow needed |
| P-M0-005 | S17 | SD-044 `REALIZED_BY` APP-FRAUD-ENGINE | 3 / — | 0.8 | closure over **P-M0-003 (a step-2 proposal, not an approved arrow)**: APP-FRAUD-ENGINE `composition` IFC-FRAUD-API `composition` POST /fraud/alerts, which implements SO-044-07 of SD-044. Band is the plan's for step 3 although the input is a medium proposal (finding 5) |

#### Candidate-rule and institution-only proposals (not in the proposal file)

| Proposal | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-M0-001 | S36 | APP-FRAUD-ENGINE → INF-CLOUD-K8S-PROD (`A4.SystemSoftware`) | 1 | 0.6 | the same join as P-M0-001; the target's level-model type is `A4.SystemSoftware`, so the S33 instance *is* the S36 instance |

Derived paths, reported as queries: **S23** SG-044-01 → IFC-FRAUD-API (SG-044-01 `composition` SO-044-07 → P-M0-003 → IFC-FRAUD-API `composition` POST /fraud/alerts); **S40** APP-FRAUD-ENGINE → ENV-PROD (P-M0-002 → `DEP-FRAUD-PROD.environment_id`); **S47** POST /fraud/alerts → DEP-FRAUD-PROD (A3 composition up to APP-FRAUD-ENGINE → P-M0-002).

#### sdmm-eval

```
$ python -m sdmm.graph check examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/m0-mappings-given.json examples/card-fraud-alerts/m0-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/card-fraud-alerts/m0-proposals.json
WARNING ×5: proposal lacks required evidence kind(s) [...]; must be supplied before approval
OK: examples/card-fraud-alerts/m0-proposals.json (with warnings)
exit=0

$ python -m sdmm.evaluate examples/card-fraud-alerts/m0-gold-mappings.json --proposals examples/card-fraud-alerts/m0-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
ALIGNED_TO          1    0   0   0   1   0.00  0.00  0.00
DEPLOYED_AS         1    1   1   0   0   1.00  1.00  1.00
DEPLOYED_ON         1    1   1   0   0   1.00  1.00  1.00
IMPLEMENTED_BY      0    1   0   1   0   0.00  0.00  0.00
REALIZED_BY         1    1   1   0   0   1.00  1.00  1.00
USES_DOMAIN         0    1   0   1   0   0.00  0.00  0.00
OVERALL             4    5   3   2   1   0.60  0.75  0.67

missed (approved, not proposed):
  VS-CARD-USE -ALIGNED_TO-> BS-FRAUD-ALERT

false proposals (proposed, not approved):
  PRC-310-01 -USES_DOMAIN-> SD-044  conf=0.6  The process export says the process invokes Notify Fraud Alert, which BIAN's structure places in the Fraud Detection domain
  SO-044-07 -IMPLEMENTED_BY-> POST /fraud/alerts  conf=0.6  Qualifier and all five control-record attributes match the API; the Notify action term has no REST form, so the method cannot be checked

$ python -m sdmm.graph trace CAP-310 --direction down … m0-mappings-given.json m0-proposals.json --status approved,proposed
CAP-310 -SUPPORTED_BY-> SD-044 (FRD-001) -REALIZED_BY-> APP-FRAUD-ENGINE (P-M0-005) -DEPLOYED_ON-> INF-CLOUD-K8S-PROD (P-M0-001) and -DEPLOYED_AS-> DEP-FRAUD-PROD (P-M0-002)
(approved only: stops at SD-044)
```

The two "false" proposals are both connections the M0 table told the executor to attempt and predicted at medium. The gold holds the S24 pair only as `proposed` (FRD-004, 0.71) and has no S04 record at all, and `sdmm-eval` scores against approved records only. **The case's precision ≥ 0.8 criterion is therefore unreachable by a correct execution**: five IDs are to be attempted, two of them cannot be in the approved gold, so precision tops out at 0.6. The first three pass conditions hold: all four approved arrows re-derivable at their assigned step (three were; S02 could not be, see below), every attempt logged, S01 recorded as single-candidate no-proposal.

#### Predicted vs observed, per plan ID

| Plan ID | Predicted confidence (step) | Observed | Verdict |
|---|---|---|---|
| S33 | high (1) | pure join, both keys present; hit | **holds** |
| S32 | high (1) | pure join, both keys present; hit | **holds** |
| S36 | medium (1) | same join; the pair is gold FRD-005 typed as `DEPLOYED_ON`; reported as candidate only | **holds** — and shows S33 already subsumes it (finding 6) |
| S24 | high (plan) / medium at most (case) (2) | 3 of 4 rules; rule 2 untestable (Notify), rule 1 by a declared convention because `A2.AssetType` is absent; proposed at 0.6; scored **false** because gold keeps FRD-004 `proposed` | **weaker than predicted** on the data (no asset type); scoring failure is the gold's |
| S17 | high (3) or medium (4) | step 3 over the step-2 proposal; hit at 0.8. The step-4 fallback the case names ("asset-noun alert in /fraud/alerts") was not available: no `A2.AssetType` in the export | **holds**, with a confidence-inheritance caveat (finding 5) |
| S04 | medium (3) | derived from `invokes` and the A2 composition chain; proposed at 0.6; scored **false** — no `USES_DOMAIN` in gold | **holds on the data; failed against the gold** |
| S02 | medium or none (4) | no `stages` key on VS-CARD-USE, no `A1.ValueStreamStage` instance; rule cannot fire; no proposal; gold FRD-007 **missed** | **failed on this data** — the A1 export lacks the key `export-conventions.json` defines |
| S01 (CAP-300) | none (5) | step 3: no process realises CAP-300; step 5: single candidate domain → no proposal | **holds** |
| S01 (CAP-310) | given | the step-3 rule re-derives FRD-001 from P-M0-004 (every process of CAP-310 uses SD-044) | consistent |
| S50 | medium (1) | no `A3.DataEntity` → no instance to map to | holds (negative) |
| Negatives | — | CMP-SCORING: no `deployed_on`, no proposal; IFC-FRAUD-API: interface, not an S17 target, no proposal | hold |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide / case) |
|---|---|---|---|---|
| 1 | S24, S17 | the A2 export has no `A2.AssetType` instance, so step 2 rule 1's reverse test and S17's step-4 fallback both lacked their key; the executor substituted the domain description's nouns and marked it a convention | `export-conventions.json` defines no asset-type key; the B-constraint `A2.ServiceDomain -association-> A2.AssetType` exists but the fraud export does not instantiate it | add `A2.ServiceDomain.attributes.asset_type` (or require an `A2.AssetType` instance with the association) to `export-conventions.json`; name it in S17 and S24 `data_needed`; add it to the fraud A2 export. Until then, rule 1 reverse and S17 step 4 are "untestable → no proposal", not conventions |
| 2 | S24 (case, gold) | a correct 3-of-4 step-2 proposal is scored false | the gold keeps FRD-004 as `proposed`; `sdmm-eval` gold = approved only; the M0 table nevertheless lists S24 as a connection to attempt at medium | either approve FRD-004 in `m0-gold-mappings.json` (the step-2 evidence — qualifier and 5/5 attributes — is stronger than the 0.71 name-overlap rationale it carries) or exclude S24 from the case's precision criterion. Longer term: `sdmm-eval` could score an "expected-proposed" tier so a case can assert "this should be proposed but not approved" |
| 3 | S04 (case, gold) | a pure step-3 derivation from `invokes` is scored false | the gold has no `USES_DOMAIN` record although the case predicts S04 at medium and the export was enriched with `invokes` precisely to enable it | add FRD-008 PRC-310-01 `USES_DOMAIN` SD-044 (approved, evidence `process_model`) to `m0-gold-mappings.json` and `mappings.json`; otherwise drop S04 from the M0 table. With 2 and 3 fixed, this run scores precision 1.0, recall 0.8 |
| 4 | S02 | the only approved gold arrow not re-derived | VS-CARD-USE has no `attributes.stages` and there is no `A1.ValueStreamStage` instance, although `export-conventions.json` defines the key; the step-4 rule has nothing to compare with `operation_sequence`; step 5 is not permitted for S02 | add `stages` (and the stage instances) to the A1 export, or change the case's expectation to "none". Optional rule for the plan: a step-3 derivation for S02 — value stream realises capability K (A1 `realization`), K's process invokes operation O, O ∈ scenario `operation_sequence` ⇒ candidate `ALIGNED_TO`, low. It would have produced FRD-007 here; it is not in the plan, so it was not used |
| 5 | S17, guide §2 | the derivation inherited the plan's high band although its only input was a medium step-2 proposal | the confidence rule adjusts for fallback steps but not for the status of the arrows closed over; a step-3 closure over proposals is only as good as its weakest input | guide §2 "Confidence is the plan's": a step-3 proposal derived over non-approved arrows takes min(plan band, lowest input band). Here S17 would be 0.6 |
| 6 | S36 | produced by the same key and record as S33; the gold instance of S33 targets an `A4.SystemSoftware` | S33 accepts any concrete A4 descendant, so every S36 instance is already an S33 instance; a separate institution-only ID adds a second record for one fact | either fold S36 into S33 (`reasoning`: "SystemSoftware targets are S33 instances; no separate rule") or promote S36 to `enterprise_rule` and have the validator accept it — not both |
| 7 | guide §4 | the proposal document cannot say which use case it belongs to: a top-level `use_case` key fails schema validation, and the file name is shared by every case in the same example directory (E1's file was overwritten) | `additionalProperties: false` on the mapping-document schema; §4 fixes the name `m0-proposals.json` | guide §4: name the file `<uc>-m0-proposals.json` (matching `<uc>-mappings-given.json`), or allow `use_case` in the document schema |
| 8 | case M0 pass criterion | precision ≥ 0.8 unreachable (see §sdmm-eval) | consequence of 2 and 3 | fix 2 and 3, or restate the criterion as "precision ≥ 0.8 over the IDs the gold approves" |
| 9 | S01 (step 3) | CAP-300 got no proposal though its child CAP-310 is approved-supported by SD-044 | no rule lets a parent capability inherit a child's domain | optional: add to the S01 step-3 rule "a capability whose composed child is `SUPPORTED_BY` D is a candidate for D, low". Not applied here |

#### New connection candidates (outside the plan)

| Pair | Found by step | Reasoning | Confidence | Suggested ID |
|---|---|---|---|---|
| PRC-310-01 → SO-044-07 (process → operation) | 1 (now a data fact: `invokes`) | registered in the E1 run as a step-4 candidate; the v0.5.1 export states it directly, and S04's derivation consumes it, yet no plan ID names the pair itself | high (data) | S06a, or note under S04/S06 that process-level `invokes` is read without an ID of its own |

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S33 / S32 | CMP-SCORING | no `deployed_on` / `deployed_as`; no A4 record names it (negative test) |
| S17 | SD-044 × IFC-FRAUD-API | `A3.ApplicationInterface`, not the S17 target type (negative test) |
| S17 | SD-044 × CMP-SCORING | exposes no API; covered by the proposal for its composing whole |
| S02 | VS-CARD-USE × BS-FRAUD-ALERT | no stage sequence in the A1 export; step 5 not permitted |
| S01 | CAP-300 × SD-044 | no processes (step 3); single candidate domain (step 5) |
| S50 | — | no `A3.DataEntity` instance |
| S25 / S22 | SO-044-07, SG-044-01 | no `A3.ApplicationService` instance |
| S23, S40, S47 | as listed above | derived paths — queries, not records, by plan design |

**Summary.** The machinery works: with the v0.5.1 keys, steps 1–3 are mechanical and produced four of the five connections the data supports, each traceable to a record or a composition chain. The run misses one approved arrow (S02, no stages in the export) and is scored for two false proposals that the case asked for and the gold does not hold. Those two are gold defects, not plan defects; the plan findings that matter are the missing asset-type key (1), confidence inheritance through proposed arrows (5), and S36 duplicating S33 (6).

### M0 — actions taken on the findings (v0.5.2)

| Finding | Action |
|---|---|
| 1 — no asset type | `A2.ServiceDomain.attributes.asset_type` / `functional_pattern` added to the conventions; `AT-FRAUD-ALERT` and `FP-ANALYSE` instances with their associations added to the A2 export; guide rule 1 and the S17 fallback read the asset-type name; without it they are untestable, not conventions |
| 2, 3, 8 — gold defects | FRD-004 approved (the step-2 evidence outweighs its name-overlap origin); FRD-008 `USES_DOMAIN` added approved; FRD-009 added as the new `proposed` demo record; `m0-gold-mappings.json` regenerated. The guide now states that `sdmm-eval` scores approved gold only |
| 4 — S02 | four `A1.ValueStreamStage` instances and `VS-CARD-USE.attributes.stages` added; optional step-3 derivation for S02 recorded in the plan and guide |
| 5 — derivation confidence | guide: a step-3 proposal over non-approved arrows takes min(plan band, weakest input band) |
| 6 — S36 | folded into S33: an instance of the registry rule via the entity hierarchy; `new-mappings.json` marks it `subsumed` |
| 7 — file names | `<uc>-proposals.json`, `<uc>-inference-log.json`; `use_case` allowed in the document schema; E1's overwritten file restored as `e1-proposals.json` |
| 9 — parent capability | optional step-3 rule recorded on S01 (child `SUPPORTED_BY` D ⇒ parent candidate, low) |

**M0 is re-runnable on v0.5.2.** Expected: six approved arrows re-derived; S24 at 3 of 4 rules with rule 1 now testable via the asset type; S02 at step 4 via stages; precision 1.0 over the approved gold.

### M0 — results, second run on v0.5.2 (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.2. **Given.** `m0-mappings-given.json` (FRD-001 only) and the v0.5.2 exports (asset type, functional pattern, four value-stream stages). **Gold.** `m0-gold-mappings.json` was not opened until phase 5. Disclosure: the executor saw the v0.5.1 gold in the first run's phase 5, and the changelog and the M0 section name the v0.5.2 gold's record ids and what changed; every proposal below was nonetheless produced by the step rules on the exports, and the one false proposal shows the gold did not steer them. **Files.** `examples/card-fraud-alerts/m0-proposals.json` (7 records, `use_case: M0`) and `examples/card-fraud-alerts/m0-inference-log.json` (17 attempts, 13 plan IDs).

#### Proposals

| Proposal | Plan ID | Connection | Step used (assigned / fallback) | Confidence | Working |
|---|---|---|---|---|---|
| P-M0-001 | S33 | APP-FRAUD-ENGINE `DEPLOYED_ON` INF-CLOUD-K8S-PROD | 1 / — | 0.8 | `deployed_on` and `hosts` name each other; target typed `A4.SystemSoftware` (S36 subsumed) |
| P-M0-002 | S32 | APP-FRAUD-ENGINE `DEPLOYED_AS` DEP-FRAUD-PROD | 1 / — | 0.8 | `DEP-FRAUD-PROD.component_id` and `deployed_as` name each other |
| P-M0-003 | S24 | SO-044-07 `IMPLEMENTED_BY` POST /fraud/alerts | 2 / — | 0.6 (3 of 4) | rule 1 **now data-backed**: `SD-044.asset_type` → AT-FRAUD-ALERT "Fraud Alert", both tokens in the path `/fraud/alerts`. Rule 2 **untestable**: Notify. Rule 3: `Alert` ~ `alerts`. Rule 4: 5/5 attributes in `payload_fields` |
| P-M0-004 | S04 | PRC-310-01 `USES_DOMAIN` SD-044 | 3 / — | 0.6 | `invokes = [SO-044-07]`; B10, B09 composition to SD-044 |
| P-M0-005 | S17 | SD-044 `REALIZED_BY` APP-FRAUD-ENGINE | 3 / — | **0.6** = min(high, P-M0-003 medium) | closure over the step-2 proposal via A3 composition; the v0.5.2 cap lowers it from the first run's 0.8 |
| P-M0-006 | S02 | VS-CARD-USE `ALIGNED_TO` BS-FRAUD-ALERT | 4 assigned → **optional step 3** | 0.4 | step 4 **failed**: 4 stages vs 1 operation (rule needs ± 1); ordered name match 1/4 (VSS-03 "Alert the cardholder" ~ "Notify Fraud Alert") = 25 % < 60 %. Optional derivation: VS-CARD-USE realises CAP-310; PRC-310-01 realises CAP-310 and invokes SO-044-07; SO-044-07 is the scenario's only operation |
| P-M0-007 | S01 | CAP-300 `SUPPORTED_BY` SD-044 | 3 / — (optional parent rule) | 0.4 | CAP-300 `composition` CAP-310; FRD-001 (given) CAP-310 `SUPPORTED_BY` SD-044 ⇒ parent candidate, low. Primary rule: no process of CAP-300. Step 5 not reached |

#### Candidate-rule and institution-only proposals (not in the proposal file)

None. S36 is subsumed by S33 since v0.5.2 and is logged as such. Derived paths reported as queries, unchanged from the first run: S23 SG-044-01 → IFC-FRAUD-API, S40 APP-FRAUD-ENGINE → ENV-PROD, S47 POST /fraud/alerts → DEP-FRAUD-PROD.

#### sdmm-eval

```
$ python -m sdmm.graph check examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/m0-mappings-given.json examples/card-fraud-alerts/m0-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/card-fraud-alerts/m0-proposals.json
WARNING ×10 (evidence kinds; bian_release and canonical_id on P-M0-006/007); OK: examples/card-fraud-alerts/m0-proposals.json (with warnings)
exit=0

$ python -m sdmm.evaluate examples/card-fraud-alerts/m0-gold-mappings.json --proposals examples/card-fraud-alerts/m0-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
ALIGNED_TO          1    1   1   0   0   1.00  1.00  1.00
DEPLOYED_AS         1    1   1   0   0   1.00  1.00  1.00
DEPLOYED_ON         1    1   1   0   0   1.00  1.00  1.00
IMPLEMENTED_BY      1    1   1   0   0   1.00  1.00  1.00
REALIZED_BY         1    1   1   0   0   1.00  1.00  1.00
SUPPORTED_BY        0    1   0   1   0   0.00  0.00  0.00
USES_DOMAIN         1    1   1   0   0   1.00  1.00  1.00
OVERALL             6    7   6   1   0   0.86  1.00  0.92

false proposals (proposed, not approved):
  CAP-300 -SUPPORTED_BY-> SD-044  conf=0.4  Card Risk Management contains Card Fraud Alerts, which is approved as supported by Fraud Detection, so the parent is partly supported by the same domain

$ python -m sdmm.graph trace CAP-310 --direction down … m0-mappings-given.json m0-proposals.json --status approved,proposed
CAP-310 -SUPPORTED_BY-> SD-044 (FRD-001) -REALIZED_BY-> APP-FRAUD-ENGINE (P-M0-005) -DEPLOYED_ON-> INF-CLOUD-K8S-PROD (P-M0-001) and -DEPLOYED_AS-> DEP-FRAUD-PROD (P-M0-002)
$ … trace VS-CARD-USE --direction down … --status approved,proposed
VS-CARD-USE -ALIGNED_TO-> BS-FRAUD-ALERT (P-M0-006)
```

**Pass criteria.** All six approved gold arrows re-derived (recall 1.0): four at their assigned step, S17 at its assigned step under the confidence cap, S02 by the optional step-3 derivation after step 4 failed. Precision 0.86 ≥ 0.8. Every attempt logged. S01 for CAP-300 was **not** recorded as single-candidate no-proposal: the optional parent rule fired first and produced the run's only false proposal (finding 2). The gold's `proposed` FRD-009 (SD-044 → CMP-SCORING) is matched by the executor's no-proposal for CMP-SCORING.

#### Predicted vs observed, per plan ID

| Plan ID | Predicted confidence (step) | Observed | Verdict |
|---|---|---|---|
| S33 | high (1) | pure join; hit | **holds** |
| S32 | high (1) | pure join; hit | **holds** |
| S36 | — (subsumed) | no separate record; the S33 proposal is the instance | **holds** |
| S24 | medium, 3 of 4 (2) | rule 1 testable via `asset_type`; rule 2 untestable (Notify); 3 of 4 → 0.6; hit (FRD-004 now approved) | **holds** |
| S17 | high (3) | step 3 over the step-2 proposal; cap → 0.6; hit | **holds, one band below the table** — with Notify on the only operation, a step-2 input can never be high, so S17 derived from it is medium by construction |
| S04 | medium (3) | derived from `invokes`; hit (FRD-008) | **holds** |
| S02 | medium (4) | step 4 cannot match 4 stages to a 1-operation scenario; hit at **low** via the optional step-3 derivation | **weaker than predicted** — the stage rule fails on this data; the optional rule rescues recall |
| S01 (CAP-300) | none (5) | optional step-3 parent rule fired at low; **false** | **failed** — the rule added for finding 9 costs precision here |
| S01 (CAP-310) | given | re-derived from P-M0-004; consistent | — |
| S50, S25, negatives | — | no instance / not a target / no record; no proposals | hold |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide / case) |
|---|---|---|---|---|
| 1 | S02, guide §3 step 4 | the stage-sequence rule failed on data that now has stages: 4 stages vs 1 operation is outside ± 1, and only 1/4 stage names match | the synthetic scenario has one operation; real BIAN scenarios span several operations and domains, but a stream will still usually have more stages than the scenario has operations, so an absolute count rule is the wrong shape | guide §3 step 4, S02: replace "same number of stages ± 1" with a coverage test — ≥ 60 % of the scenario's operations (or participating domains) are name-matched by stages, in order — and keep the stage-side ratio as the score. On this data that gives 1/1 operations covered, score 1/4 stages. M1's scenario must carry several operations so the rule is actually exercised |
| 2 | S01, guide §3 step 3 | the optional parent-capability rule produced the only false proposal (CAP-300 → SD-044) | "parent of a supported child is partly supported" is a scope judgement, not a derivation; the gold author did not approve it and the case table predicts none | drop the optional parent rule from S01 (revert finding 9), or keep it report-only — quarantined under *New connection candidates* like a candidate rule — so it never enters the proposal file. Recommended: drop |
| 3 | S02, guide §2 | the optional step-3 derivation for S02 is a *lower* step than the assigned 4, which the constraint "never use a lower step than assigned" forbids; the executor applied it anyway because §3 lists it, and marked it `fallback: true` in the log | the constraint and the §3 rule contradict each other; the log schema has no value for "lower-step optional rule" | guide §2: "You may use a lower-numbered step only where §3 lists it as an optional rule for that ID, after the assigned step has failed; record it as `fallback: true, direction: lower`." Or set S02 `fill_step` to 3 with step 4 as the scoring route |
| 4 | S17, case table | the case still predicts high at step 3; the v0.5.2 cap makes medium the ceiling whenever the input is a step-2 proposal, and on this domain every step-2 proposal is at most medium (Notify) | the table was not updated for the cap | case M0 table: S17 "medium (3, capped by S24) or medium (4)". Plan `confidence` for S17 stays high — the cap is per-run, not per-ID |
| 5 | case M0 | the pass text still reads "all four approved arrows"; the gold now approves six. The S01 row says step 5 while the plan's `fill_step` is 3 | not updated with the v0.5.2 gold | case M0: "all six approved arrows"; S01 row step "3 (then 5)" |
| 6 | S02 export | the validator warns that BS-FRAUD-ALERT has no `canonical_id` for a `bian_alignment_guidance` mapping | the A2 export gives a `canonical_id` to SD-044 only | `export-conventions.json`: BIAN-grounded A2 instances (scenario, operation, control record, asset type) carry `canonical_id`; add to the fraud export. Warning-level only; no change to the plan |
| 7 | S24 | holds, but the ID's plan band (high) is unreachable for any operation whose action term is Notify (rule 2 always a miss → 3 of 4 → medium) | the band is per-ID; the ceiling is per-operation | S24 `reasoning`: note that Notify operations are capped at medium by construction; an institution may treat Notify ⇔ POST as an enterprise convention to lift the cap, recorded as such |

#### New connection candidates (outside the plan)

| Pair | Found by step | Reasoning | Confidence | Suggested ID |
|---|---|---|---|---|
| PRC-310-01 → SO-044-07 (process → operation) | 1 (`invokes`) | unchanged from the first run: a data fact consumed by S04 and now by the S02 derivation, with no plan ID of its own | high (data) | S06a, or a note under S04/S06 |

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S33 / S32 | CMP-SCORING | no `deployed_on` / `deployed_as`; no A4 record names it |
| S17 | SD-044 × IFC-FRAUD-API | `A3.ApplicationInterface`, not the S17 target type |
| S17 | SD-044 × CMP-SCORING | no API, no data entity; step-4 fallback scores 0; the gold holds this pair only as the `proposed` demo FRD-009 |
| S36 | — | subsumed by S33 |
| S50 | — | no `A3.DataEntity` instance |
| S25 / S22 | SO-044-07, SG-044-01 | no `A3.ApplicationService` instance |
| S23, S40, S47 | as listed | derived paths — queries by plan design |

**Summary.** On v0.5.2 the data carries every approved arrow and the steps reach all of them: recall 1.0, precision 0.86, F1 0.92, against 0.67 on v0.5.1. Two of the v0.5.2 additions did the work (asset type for rule 1; FRD-004 and FRD-008 in the gold), one worked as intended (the confidence cap), and two optional rules cut both ways: the S02 derivation rescued an arrow the stage rule could not reach, and the S01 parent rule produced the only false proposal. Next for the plan: reshape the S02 stage rule as coverage (finding 1) and drop the S01 parent rule (finding 2). Next for the data: M1 needs multi-operation scenarios so the stage rule is actually tested.

### M0 — actions taken on the second-run findings (v0.5.3)

| Finding | Action |
|---|---|
| 1 — S02 stage rule | Guide step 4: value stream ↔ scenario is scored as **coverage of the scenario's operations** — each operation in `operation_sequence` matched, in order, by a stage whose name shares the operation's verb or asset; score = covered operations / operations; threshold ≥ 60 %. A stream with more stages than the scenario has operations is normal, not a failure |
| 2 — parent-capability rule | Withdrawn as a proposal source. It is a scope judgement; kept **report-only**: a parent whose child is `SUPPORTED_BY` D goes to *New connection candidates*, never to the proposal file. `new-mappings.json` S01 updated |
| 3 — lower-step conflict | Guide §2: an optional step the plan lists for that ID in `reasoning` may be used even when numbered lower than the assigned step; the proposal is labelled `optional-step` and takes the band the plan gives it (low for S02's step-3 derivation) |
| 4 — case text | Pass criterion says six arrows; S17 predicted medium under the cap; S02 and S01 rows restated |

**M0 is complete.** Both runs are recorded; the plan, guide, exports and gold are consistent. Next: author M1 (Payment Initiation, brownfield) to the export conventions and run it.

### M1 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.3. **Given.** `m1-mappings-given.json` (PAY-001…005) and the four v0.5.3 exports (68 instances). **Gold.** `m1-gold-mappings.json` and `mappings.json` were not opened until phase 5. The M1 case text states the gold's composition (five `IMPLEMENTED_BY`, one `REALIZED_BY`, one `MAPPED_TO`, two `DEPLOYED_ON`, three `DEPLOYED_AS`) and the planted items, so the shape of the gold was known; the instances were not. **Files.** `examples/payment-initiation/m1-proposals.json` (13 records) and `examples/payment-initiation/m1-inference-log.json` (85 attempts, 21 plan IDs, every operation × API pair included).

#### Proposals

| Proposal | Plan ID | Connection | Step (assigned / used) | Confidence | Working |
|---|---|---|---|---|---|
| P-M1-001 | S33 | APP-PAY-HUB `DEPLOYED_ON` INF-K8S-PAY-PROD | 1 / 1 | 0.8 | `deployed_on` and `hosts` name each other; `DEP-PAYHUB-PROD.platform_id` agrees |
| P-M1-002 | S33 | APP-PAY-HUB `DEPLOYED_ON` INF-K8S-PAY-UAT | 1 / 1 | 0.8 | **one-sided**: `INF-K8S-PAY-UAT.hosts` lists the hub and `DEP-PAYHUB-UAT.platform_id` agrees, but the hub's `deployed_on` omits UAT; the guide accepts either side |
| P-M1-003 | S33 | CMP-PAY-EXEC `DEPLOYED_ON` INF-K8S-PAY-PROD | 1 / 1 | 0.8 | both sides |
| P-M1-004 | S32 | APP-PAY-HUB `DEPLOYED_AS` DEP-PAYHUB-PROD | 1 / 1 | 0.8 | `component_id` and `deployed_as` name each other |
| P-M1-005 | S32 | APP-PAY-HUB `DEPLOYED_AS` DEP-PAYHUB-UAT | 1 / 1 | 0.8 | both sides |
| P-M1-006 | S32 | CMP-PAY-EXEC `DEPLOYED_AS` DEP-PAYEXEC-PROD | 1 / 1 | 0.8 | both sides |
| P-M1-007 | S24 | SO-PI-01 `IMPLEMENTED_BY` API-PI-01 | 2 / 2 | 0.8 | 4/4: asset "Payment Instruction" in `/payment-instructions`; Initiate ⇔ POST; null qualifier; 8/8 attributes |
| P-M1-008 | S24 | SO-PI-02 `IMPLEMENTED_BY` API-PI-02 | 2 / 2 | 0.8 | 4/4: Evaluate ⇔ POST; `Validation` in path; 3/3 attributes |
| P-M1-009 | S24 | SO-PI-03 `IMPLEMENTED_BY` API-PI-03 | 2 / 2 | 0.8 | 4/4: Execute ⇔ PUT; `Execution` in path; 3/3 attributes |
| P-M1-010 | S24 | SO-PI-04 `IMPLEMENTED_BY` API-PI-04 | 2 / 2 | **0.6** | 3/4: **rule 2 fails — Retrieve exposed as POST** (planted; the API's description cites a legacy-channel reason); null qualifier; 4/4 attributes. Chosen among six 3/4 pairs for SO-PI-04 by convention M1-C1c (unique top rule-4 ratio) |
| P-M1-011 | S24 | SO-PI-05 `IMPLEMENTED_BY` API-PI-05 | 2 / 2 | 0.8 | 4/4: Update ⇔ PATCH; null qualifier; 5/5 attributes |
| P-M1-012 | S17 | SD-PI `REALIZED_BY` APP-PAY-HUB | 3 / 3 | **0.6** | closure over P-M1-007…011 via SVC-PAY-INIT → IFC-PAY-API composition; cap = min(high, weakest input medium). SD-PE, SD-PA: no operations implemented, asset tokens 0/9 → no proposal |
| P-M1-013 | S30 | BBO-PAY-INSTR `MAPPED_TO` ENT-PAY-INSTR | 4 / 4 | 0.8 | 8/8 attributes = 1.00; ENT-PAY-EVENT 1/8, ENT-ACCOUNT-CACHE 1/8; BBO-PARTY 0/3 everywhere |

**Executor convention M1-C1 (step 2 disambiguation).** The rule as written ("three of four → one band lower") holds on **20** operation × API pairs of this estate besides the four 4/4 pairs (12 further pairs sit at ≤ 2/4), because rule 1 is domain-level and identical for every API under the hub, rule 3 passes vacuously for the four null-qualifier operations, and rule 4's 50 % threshold is met by any payload carrying the instruction reference and status. Applied mechanically it would have filed 19 cross-matches (Initiate → Amend, Update → Create, Retrieve → every API, Notify → every API) and one correct pair (the planted SO-PI-04). The executor therefore applied, and marks as a convention: **(a)** an operation with a 4/4 API keeps only that pair; **(b)** a 3/4 pair whose API already has a 4/4 operation is suppressed; **(c)** an operation with no 4/4 keeps the 3/4 pair with the unique highest rule-4 ratio, else none; **(d)** untestable rule 2 plus vacuous rule 3 leaves rules 1 and 4 alone, which is insufficient. Every suppressed pair is in the log with its rule values and the clause that suppressed it.

#### Candidate-rule and institution-only proposals (not in the proposal file)

| Report id | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-M1-001…005 | S25 | SO-PI-01…05 → SVC-PAY-INIT | 3 | 0.8 ×4, 0.6 (SO-PI-04) | each implementing API is composed in IFC-PAY-API in SVC-PAY-INIT; capped at the step-2 input |
| C-M1-006 | S20 | CR-PI → ENT-PAY-INSTR | 4 | 0.8 | 10/10 control-record attributes present (the case text's "10/11" is matched / entity attributes; the guide scores matched / BIAN attributes) |
| C-M1-007, 008 | S41 | SVC-PAY-INIT → TS-SECRETS, TS-MQ | 1 | 0.6 | `consumes` |
| C-M1-009…011 | S50 | ENT-PAY-INSTR, ENT-PAY-EVENT, ENT-ACCOUNT-CACHE → INF-PG-PAY-PROD | 1 | 0.6 | `stored_in` |
| C-M1-012…015 | S06 | ACT-PAY-01a/01b/02a/02b → SO-PI-01/02/03/04 | 4 assigned, **1 used** | 0.6 | `invokes` on each activity states the fact; no name match needed (finding 6) |

Derived paths as queries: **S22/S23** SG-PI-1, SG-PI-2 → SVC-PAY-INIT / IFC-PAY-API; **S40** APP-PAY-HUB → ENV-PAY-PROD, ENV-PAY-UAT and CMP-PAY-EXEC → ENV-PAY-PROD; **S47** API-PI-01…06 → DEP-PAYHUB-PROD, DEP-PAYHUB-UAT.

#### sdmm-eval

```
$ python -m sdmm.graph check examples/payment-initiation/a*.json examples/payment-initiation/m1-mappings-given.json examples/payment-initiation/m1-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/payment-initiation/m1-proposals.json
WARNING ×13 (required evidence kinds on proposals); OK: examples/payment-initiation/m1-proposals.json (with warnings)
exit=0

$ python -m sdmm.evaluate examples/payment-initiation/m1-gold-mappings.json --proposals examples/payment-initiation/m1-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_AS         3    3   3   0   0   1.00  1.00  1.00
DEPLOYED_ON         2    3   2   1   0   0.67  1.00  0.80
IMPLEMENTED_BY      5    5   5   0   0   1.00  1.00  1.00
MAPPED_TO           1    1   1   0   0   1.00  1.00  1.00
REALIZED_BY         1    1   1   0   0   1.00  1.00  1.00
OVERALL            12   13  12   1   0   0.92  1.00  0.96

false proposals (proposed, not approved):
  APP-PAY-HUB -DEPLOYED_ON-> INF-K8S-PAY-UAT  conf=0.8  The CMDB says the UAT cluster hosts the hub and the UAT deployment record agrees; the APM export omits it

$ python -m sdmm.graph trace CAP-PAY-010 --direction down … m1-mappings-given.json m1-proposals.json --status approved,proposed
CAP-PAY-010 -SUPPORTED_BY-> SD-PI (PAY-001) -REALIZED_BY-> APP-PAY-HUB (P-M1-012)
  -DEPLOYED_ON-> INF-K8S-PAY-PROD (P-M1-001); -DEPLOYED_ON-> INF-K8S-PAY-UAT (P-M1-002)
  -DEPLOYED_AS-> DEP-PAYHUB-PROD (P-M1-004); -DEPLOYED_AS-> DEP-PAYHUB-UAT (P-M1-005)

$ python -m sdmm.graph impact INF-K8S-PAY-PROD --change rehost … --status approved,proposed
design_change_required  A4 INF-K8S-PAY-PROD; A3 APP-PAY-HUB (via P-M1-001); A3 CMP-PAY-EXEC (via P-M1-003)
no_impact               A2 SD-PI; A1 CAP-PAY-010, PRC-PAY-01, PRC-PAY-02
mappings to supersede: P-M1-001, P-M1-003
```

**Pass criteria.** F1 0.96 ≥ 0.85. The planted mismatch is reported (P-M1-010, finding 5). Every negative holds: no `DEPLOYED_ON`/`DEPLOYED_AS` for CMP-PAY-CAPTURE or CMP-PAY-VALIDATE, nothing for API-PI-06, nothing for SO-PI-06, nothing for ENT-ACCOUNT-CACHE, nothing for SD-PE or SD-PA. The log is complete. **Caveat:** the clean `IMPLEMENTED_BY` row depends on convention M1-C1; under the step-2 rule as written it would read 24 proposals, 5 tp, 19 fp, precision 0.21, and overall precision 0.38.

#### Predicted vs observed, per plan ID

| Plan ID | Predicted | Observed | Verdict |
|---|---|---|---|
| S33 ×2 | high (1) | both hits; **a third, one-sided record (hub → UAT) proposed and false** | **holds for the two; the UAT record is a data/gold question (finding 2)** |
| S32 ×3 | high (1) | 3/3 hits, all two-sided | **holds** |
| S36 | subsumed | no separate record | holds |
| S24 ×5 | high for 01, 02, 03, 05; medium for 04 | exactly that — **but only after disambiguation**; the rule alone yields 24 proposals (4 at 4/4, 20 at 3/4) | **holds with convention; fails as written (finding 1)** |
| S24 negatives | none for SO-PI-06, API-PI-06 | none filed; the rule alone would file Notify → all six APIs and Retrieve → API-PI-06 | as above |
| S17 | medium (capped) | 0.6; hit; SD-PE / SD-PA none | **holds** — though the cap bites on the one medium input while four inputs are high (finding 3) |
| S25 ×5 | high (report) | reported, capped per input | holds |
| S30 | high, 8/8 | 8/8 hit; negatives hold | **holds** |
| S20 | high, "10/11" | 10/10 by the guide's score; reported | holds (finding 8 on the score's denominator) |
| S41 ×2, S50 ×3 | medium (report) | reported from `consumes` / `stored_in` | hold |
| S40, S47 | high (queries) | queries | hold |
| S06 ×4 | — (not listed) | `invokes` states activity → operation at step 1; plan assigns step 4 | finding 6 |
| S01, S02, S04 (given) | — | re-derivations agree with PAY-001…004; CAP-PAY-000: three-domain step 5, two domains tie → no proposal | hold |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide / case) |
|---|---|---|---|---|
| 1 | S24, guide §3 step 2 | the "three of four" clause admits **19 cross-matches** on a six-operation domain (Initiate → Amend, Update → Create, Retrieve → all six APIs, Notify → all six) | rule 1 is domain-level, so it is identical for every API of one component; rule 3 passes vacuously for null-qualifier operations (4 of 6 here); rule 4's 50 % bar is met by any payload carrying the reference and status; the rule has no per-operation or per-API exclusivity | guide §3 step 2: (i) count only *evidential* passes — a vacuous rule 3 and an untestable rule 2 are neither pass nor fail — and require three evidential passes, or two with rule 4 at 100 %; (ii) adopt M1-C1 (a)–(c) as the disambiguation rule: an operation's 4/4 pair excludes its 3/4 pairs, an API's 4/4 operation excludes other 3/4 pairs on it, remaining operations take the unique best rule-4 ratio or nothing; (iii) raise rule 4's threshold or weight it by attribute specificity (an attribute shared by every operation of the control record, like `payment_instruction_reference`, discriminates nothing). `S24.reasoning`: state that the four rules are necessary conditions, not a scoring function, and that exclusivity is part of the fill |
| 2 | S33 (case, gold, data) | APP-PAY-HUB → INF-K8S-PAY-UAT proposed at high and scored false | the A4 export (`hosts`) and the UAT deployment record (`platform_id`) both state it; the A3 export's `deployed_on` omits it; the gold approves the UAT `DEPLOYED_AS` (PAY-110) but not the UAT `DEPLOYED_ON`; the guide accepts a one-sided record | decide the modelling question in the plan: either `DEPLOYED_ON` covers every environment (add PAY-113 to the gold — the data supports it as firmly as PAY-110) or `DEPLOYED_ON` is production hosting only (say so in `S33.reasoning`, and the gold's omission is right). Independently: guide step 1 — a two-sided record keeps the plan's band, a one-sided record drops one band; `sdmm-graph check` could warn when `hosts` / `platform_id` / `deployed_on` disagree |
| 3 | S17, guide §2 | the derivation was capped at 0.6 because one of five inputs is medium, although four are high and one high arrow suffices for the rule | the cap takes the minimum over all inputs regardless of whether the rule needs all of them or any of them | guide §2: for a closure that needs **any one** input arrow (S17, S25), cap at the band of the **strongest** input; for a closure that needs **all** inputs (S01 "every process"), cap at the weakest. Here S17 would be 0.8 |
| 4 | S02, guide §3 step 4 | the coverage rule's "verb **or** asset-type noun" clause is trivial when every operation of a domain carries the asset name — all four operations of SD-PI contain "Payment Instruction", so stage VSS-P1 alone covers all of them | asset-type noun is the resource, not the behaviour; only the verb or qualifier distinguishes operations | guide: match on the operation's action term (or qualifier) first; use the asset noun only to confirm the domain. Checked here against the given PAY-002: 3/4 by verb/qualifier, 4/4 trivially by noun |
| 5 | S24 (planted) | API-PI-04 implements Retrieve as POST; rule 2 failed, proposal filed at medium with the finding; the gold approves it citing an architecture decision record | the plan has no way to lift a documented, approved deviation back to high; the executor can only report the mismatch | S24 `reasoning` / registry: allow an `architecture_decision_record` evidence kind on `IMPLEMENTED_BY`; when present, a rule-2 deviation is recorded as `deviation` on the mapping and the band is not reduced. The gold's PAY-105 rationale says "4/4 attributes" where the data gives 5/5 — text fix |
| 6 | S06 | activity → operation is stated directly by `invokes` on each activity, yet the plan assigns step 4 (name match) | `export-conventions.json` already defines `A1.BusinessActivity.invokes`; the plan was not updated when the key was added | S06 `fill_step` 1 where `invokes` is present, 4 otherwise; same for the process-level `invokes` already consumed by S04 (E1/M0 candidate S06a) |
| 7 | S24, new pair | SO-PI-06 (Notify) has no REST form; the A3 export has `EVT-PAY-STATUS` "Published when an instruction changes state", triggered by APP-PAY-HUB — the natural implementation of a Notify operation is an event, not an API | the plan has no `A2.ServiceOperation → A3.Event` connection | quarantined below; if adopted, a Notify-specific rule: action term Notify ⇔ an `A3.Event` whose description names the operation's asset and a state change, step 4 (structural: asset noun in event name/description), medium |
| 8 | S20, case text | the case predicts "10/11"; the guide's score is matched / BIAN attributes = 10/10 | two denominators in use | case M1 table: 10/10; keep the guide's definition (coverage of the BIAN object), and report the entity-side extension count separately |
| 9 | S01 step 5 | with three exported domains the step-5 ranking finally had a real candidate set, and it correctly produced **no proposal** for CAP-PAY-000 (SD-PI and SD-PE tie) | — | no change; record that the "clearly better" test worked as intended on a parent capability spanning two domains |

#### New connection candidates (outside the plan)

| Pair | Found by step | Reasoning | Confidence | Suggested ID |
|---|---|---|---|---|
| SO-PI-06 (Notify) → EVT-PAY-STATUS (`A3.Event`) | 4/5 | "Notify an interested party of a change in the instruction's state" vs "Published when an instruction changes state"; the event is triggered by APP-PAY-HUB, which realises SD-PI; Notify has no REST form, so no API can implement it | medium | S24e — operation (Notify) → event |
| CAP-PAY-000 → SD-PI (parent of CAP-PAY-010) | 3, report-only | child approved as PAY-001; parent spans SD-PI and SD-PE | low | S01 report-only rule, as the guide now specifies |
| PRC-PAY-01/02 → SO-PI-01…04 (process → operation) | 1 (`invokes`) | as in E1/M0: a data fact with no ID of its own | high (data) | S06a |

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S33 / S32 | CMP-PAY-CAPTURE, CMP-PAY-VALIDATE | no `deployed_on` / `deployed_as`; no `hosts` / `component_id` names them |
| S24 | 31 operation × API pairs (all in the log) | 12 pairs at ≤ 2/4; 19 pairs at 3/4 suppressed by M1-C1 — (a) 8, (b) 8, (c) 1, (d) 2; the twentieth 3/4 pair, SO-PI-04 × API-PI-04, was selected by (c) and filed |
| S24 | SO-PI-06 × API-PI-01…06 | Notify: rule 2 untestable; with null qualifier only rules 1 and 4 remain → M1-C1 (d) |
| S24 | SO-PI-01…05 × API-PI-06 | List events: ≤ 2/4 for all but Retrieve (3/4: GET matches, payload 1/4), suppressed by (c) in favour of API-PI-04 |
| S17 | SD-PE, SD-PA | no operations implemented; asset tokens 0/9 in paths and entity names |
| S17 | SD-PI × CMP-PAY-CAPTURE / VALIDATE / EXEC | the APIs are composed under SVC-PAY-INIT in the hub, not under the sub-components |
| S30 | BBO-PAY-INSTR × ENT-PAY-EVENT, ENT-ACCOUNT-CACHE; BBO-PARTY × all three | 1/8, 1/8; 0/3 |
| S12 | BO-PAYEE × BBO-PARTY | 0/3 attribute names match |
| S01 | CAP-PAY-000 | no processes; step 5 with three domains: SD-PI and SD-PE tie |
| S49 / S45 | — | no `stored_in` naming an artifact; no `A3.ApplicationFunction` |
| S01, S02, S04, S12 | the five given arrows | given; re-derivations agree |

**Summary.** The plan reaches every approved arrow of a 68-instance brownfield estate: steps 1, 3 and 4 are mechanical and precise, and the planted REST deviation surfaces exactly where the case put it. The one false proposal is a modelling question the plan has not answered (does `DEPLOYED_ON` cover non-production hosting?), not an inference error. The finding that matters is step 2: the four REST rules are sound as *necessary conditions* but the "three of four" clause is not a usable fill rule — on this estate it admits nineteen wrong pairs for one right one. The executor's disambiguation convention recovers the correct five; it should be written into the guide, together with evidential-only counting of the rules. Next for the data: H1 and H2 will exercise step 2 in reverse and under hostile naming, where this weakness will matter more.

### M1 — actions taken on the findings (v0.5.4)

| Finding | Action |
|---|---|
| 1 — "3 of 4" is not a fill rule | Guide step 2 rewritten as a **decision procedure**: boundary precondition (a gate, never a vote); checks 2–4 as pass / fail / neutral (null qualifier is neutral, not a pass); propose at band only on 2+4 pass; one band lower with a finding only for a method mismatch that is the unique best payload match; one-to-one disambiguation per operation and API; ties are no proposal. The disambiguation Opus applied by convention is now the rule |
| 2 — UAT hosting | `DEPLOYED_ON` is environment-agnostic; the environment lives on the Deployment. PAY-113 (hub `DEPLOYED_ON` UAT platform) added to the gold; the A3 export's `deployed_on` lists both platforms. Run 1's one false proposal is correct under the restated gold → precision 1.0 |
| 3 — confidence cap | A derivation is capped at the **strongest** input where any one input suffices (S17, S25, S22, S23) and at the weakest only where all are needed (S01) |
| 4 — stage matching | Stages match on the operation's **action term**, never the asset noun |
| 5 — Notify → event | Recorded as a structured new-connection candidate in `new-mappings.json` (`new_connection_candidates`); reported, never proposed, until it has an ID |

**M1 is complete** on the plan's core: F1 0.96 on run 1, 1.0 under the restated gold. The step-2 rewrite is the significant improvement to carry into H1 and H2, where step 2 runs in reverse and under hostile naming.

### H1 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.4. **Given.** `h1-mappings-given.json` — empty; the four v0.5.4 exports (87 instances). **Gold.** `h1-gold-mappings.json` and `mappings.json` were not opened until phase 5. The H1 case text states the gold's composition and the planted items, so the shape was known; the instances were not. **Baseline.** The case defines none; proposals carry the executor-assigned `H1-BASE-2026-Q4` (finding 8). **Files.** `examples/legacy-core-ledger/h1-proposals.json` (28 records) and `examples/legacy-core-ledger/h1-inference-log.json` (190 attempts, 21 plan IDs; every gated operation × API pair, failed gates summarised per domain and module).

**Executor conventions, marked.** The guide left three gaps on this estate and the executor filled each with a stated rule, recorded in the log and in findings 1, 2 and 5: **H1-C1** — the boundary gate at token level with an abbreviation/synonym table (the literal asset-type phrase occurs for only two of the four modules); **H1-C2** — iterative one-to-one exclusion in step-2 disambiguation (the clause as written leaves two ties); **H1-C3** — "clearly better" in step 5 means at least two shared concepts and strictly more than every other domain. Check 3 on SOAP paths, which have no resource structure, was tested on the camel-split operation name by stem (Closure ~ Close, Posting ~ Post, Reversal ~ Reverse).

#### Proposals

| Proposal | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| P-H1-001 | S33 | APP-LEDGER `DEPLOYED_ON` INF-MF-LPAR-PROD (`A4.Node`) | 1 | 0.8 | `deployed_on`, `hosts` and `DEP-LM-PROD.platform_id` — three records |
| P-H1-002 | S32 | APP-LEDGER `DEPLOYED_AS` DEP-LM-PROD | 1 | 0.8 | `component_id` and `deployed_as` name each other |
| P-H1-003 | S24 | SO-CA-01 Initiate `IMPLEMENTED_BY` OP-OpenAccount | 2 rev | 0.8 | decision 1: Initiate ⇔ POST; no qualifier, path clean (neutral); 6/6 attributes |
| P-H1-004 | S24 | SO-CA-02 Retrieve ← OP-GetAccount | 2 rev | 0.6 | decision 2: **F-SOAP** (Retrieve on POST); neutral; 6/6, unique best |
| P-H1-005 | S24 | SO-CA-03 Control ← OP-BlockAccount | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 2/2 — **tie with AmendOverdraft at 2/2 under the clause as written**, resolved in round 2 when AmendOverdraft went to SO-CA-04 (H1-C2) |
| P-H1-006 | S24 | SO-CA-04 Update ← OP-AmendOverdraft | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 3/3 unique (GetAccount excluded, taken by SO-CA-02) |
| P-H1-007 | S24 | SO-CA-05 Execute/Closure ← OP-CloseAccount | 2 rev | 0.6 | decision 2: F-SOAP; check 3 **pass** (Closure ~ Close); 3/3 unique |
| P-H1-008 | S24 | SO-PK-01 Update/Posting ← OP-PostEntry | 2 rev | 0.6 | decision 2: F-SOAP; check 3 pass (Posting ~ Post); 7/7 |
| P-H1-009 | S24 | SO-PK-02 Retrieve ← OP-GetBalance | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 4/4 unique (PostEntry 3/4 and check-3 fail: carries the Posting stem) |
| P-H1-010 | S24 | SO-PK-03 Execute/Reversal ← OP-ReverseEntry | 2 rev | 0.6 | decision 2: F-SOAP; check 3 pass; 2/2 — tie with PostEntry at 2/2 broken by the qualifier in the name (guide clause 4) |
| P-H1-011 | S24 | SO-PE-01 Initiate ← OP-SubmitPayment | 2 rev | 0.8 | decision 1: Initiate ⇔ POST; neutral; 6/6 |
| P-H1-012 | S24 | SO-PE-02 Retrieve ← OP-PaymentStatus | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 4/4 unique |
| P-H1-013 | S24 | SO-PE-03 Control ← OP-CancelPayment | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 2/2 unique after SubmitPayment (decision 1) and PaymentStatus were taken |
| P-H1-014 | S24 | SO-PRD-01 Register ← OP-CreateCustomer | 2 rev | 0.8 | decision 1: Register ⇔ POST; neutral; 4/4 — **tie with GetCustomer at 4/4 under the clause as written**, resolved in round 2 after GetCustomer went to SO-PRD-02 (5/5 unique) |
| P-H1-015 | S24 | SO-PRD-02 Retrieve ← OP-GetCustomer | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 5/5 unique |
| P-H1-016 | S24 | SO-PRD-03 Update ← OP-UpdateCustomer | 2 rev | 0.6 | decision 2: F-SOAP; neutral; 3/3 unique |
| P-H1-017 | S17 | SD-CA `REALIZED_BY` LM-ACCT | 3 | 0.8 | over P-H1-003…007; cap = strongest input (P-H1-003 high) |
| P-H1-018 | S17 | SD-PK `REALIZED_BY` LM-POST | 3 | **0.6** | over P-H1-008…010; all three inputs medium (every PK operation is a POST deviation), so the cap gives medium (finding 6) |
| P-H1-019 | S17 | SD-PE `REALIZED_BY` LM-PAY | 3 | 0.8 | over P-H1-011…013; strongest input high |
| P-H1-020 | S17 | SD-PRD `REALIZED_BY` LM-PARTY | 3 | 0.8 | over P-H1-014…016; strongest input high |
| P-H1-021 | S30 | BBO-ACCOUNT `MAPPED_TO` ENT-ACCOUNT | 4 | 0.8 | 8/8; extension `branch_code` |
| P-H1-022 | S30 | BBO-POSTING `MAPPED_TO` ENT-POSTING | 4 | 0.8 | 7/7; extension `operator_id` |
| P-H1-023 | S30 | BBO-PAYMENT-TXN `MAPPED_TO` ENT-PAYMENT | 4 | 0.8 | 8/8 |
| P-H1-024 | S30 | BBO-PARTY `MAPPED_TO` ENT-PARTY | 4 | 0.8 | 6/6; extension `created_by` |
| P-H1-025 | S01 | CAP-ACCT-SVC `SUPPORTED_BY` SD-CA | 3 → **5** | 0.4 | step 3 impossible (no processes); four-domain set; shared {account, block, close, current, maintain, open, term} = 7, runner-up 1 |
| P-H1-026 | S01 | CAP-POSITION `SUPPORTED_BY` SD-PK | 3 → 5 | 0.4 | shared {balance, financial, maintain, movement, position, record} = 6, runner-up 2 |
| P-H1-027 | S01 | CAP-PAY-EXEC `SUPPORTED_BY` SD-PE | 3 → 5 | 0.4 | shared {authorised, execute, execution, payment, scheme} = 5, runner-up 0 |
| P-H1-028 | S01 | CAP-PARTY-DATA `SUPPORTED_BY` SD-PRD | 3 → 5 | 0.4 | shared {data, master, record, reference} = 4, runner-up 1 |

**Systematic finding F-SOAP** (reported once, referenced by eleven proposals): every operation of the four LedgerMaster SOAP interfaces is exposed as POST, so check 2 fails for all Retrieve, Update, Control and Execute operations; they are proposed one band lower. The gold approves all eleven with "deviation recorded".

#### Candidate-rule and institution-only proposals (not in the proposal file)

| Report id | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-H1-001…005 | S50 | ENT-ACCOUNT, ENT-POSTING, ENT-PAYMENT, ENT-PARTY, ENT-AUDIT → INF-DB2-PROD | 1 | 0.6 | `stored_in` |
| C-H1-006…009 | S20 | CR-CA → ENT-ACCOUNT 8/8; CR-PK → ENT-POSTING **7/8** (`position_reference` absent); CR-PE → ENT-PAYMENT 8/8; CR-PRD → ENT-PARTY 6/6 | 4 | 0.8 | attribute match |

Derived paths as queries: **S23** SG-CA/PK/PE/PRD → IFC-ACCT/POST/PAY/PARTY; **S40** APP-LEDGER → ENV-PROD; **S47** the 17 operations and jobs → DEP-LM-PROD; and **the ledger as a whole**: SD-CA, SD-PK, SD-PE, SD-PRD → APP-LEDGER → INF-MF-LPAR-PROD through module composition — a query, not a stored `REALIZED_BY`, as the case requires.

#### sdmm-eval

```
$ python -m sdmm.graph check examples/legacy-core-ledger/a*.json examples/legacy-core-ledger/h1-mappings-given.json examples/legacy-core-ledger/h1-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/legacy-core-ledger/h1-proposals.json
WARNING ×28 (required evidence kinds on proposals); WARNING ×4 (P-H1-025…028: bian_alignment_guidance mapping requires bian_release)
OK: examples/legacy-core-ledger/h1-proposals.json (with warnings)
exit=0

$ python -m sdmm.evaluate examples/legacy-core-ledger/h1-gold-mappings.json --proposals examples/legacy-core-ledger/h1-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_AS         1    1   1   0   0   1.00  1.00  1.00
DEPLOYED_ON         1    1   1   0   0   1.00  1.00  1.00
IMPLEMENTED_BY     14   14  14   0   0   1.00  1.00  1.00
MAPPED_TO           4    4   4   0   0   1.00  1.00  1.00
REALIZED_BY         4    4   4   0   0   1.00  1.00  1.00
SUPPORTED_BY        4    4   4   0   0   1.00  1.00  1.00
OVERALL            28   28  28   0   0   1.00  1.00  1.00

$ python -m sdmm.graph trace CAP-ACCT-SVC --direction down … h1-proposals.json --status approved,proposed
CAP-ACCT-SVC -SUPPORTED_BY-> SD-CA (P-H1-025) -REALIZED_BY-> LM-ACCT (P-H1-017)
(approved only: "(no downstream mappings)", exit 1 — nothing is approved in H1)
$ … trace INF-MF-LPAR-PROD --direction up … --status approved,proposed
INF-MF-LPAR-PROD <-DEPLOYED_ON- APP-LEDGER (P-H1-001)
```

The downstream trace from a capability stops at the module: `LM-ACCT` has no deployment record of its own, and the ledger's hosting is reached only through A3 composition (`APP-LEDGER` composes the modules), which the mapping graph does not follow. The chain capability → domain → module → platform exists in the data but is a derived path, not a trace (finding 7).

**Pass criteria.** F1 1.00 ≥ 0.8. F-SOAP reported once. Every negative held: no deployment arrows for the five modules; nothing for the three BATCH jobs; nothing for ENT-AUDIT; no `REALIZED_BY` for APP-LEDGER or LM-BATCH; **no proposal for CAP-LENDING (0 shared concepts) or CAP-TREASURY (1, "position")**. All four A1 proposals low with a step-5 rationale naming both texts and the runner-up. Log complete. **Caveat:** under the guide's text as written — strict gate and non-iterative disambiguation — the run would have filed 8 of 14 `IMPLEMENTED_BY` (the posting and party gates fail literally; two ties remain), recall 0.79 overall.

#### Predicted vs observed, per plan ID

| Plan ID | Predicted | Observed | Verdict |
|---|---|---|---|
| S33, S32 | high (1) | hits, three and two records | **holds** |
| S24 ×14 | high ×3 (Initiate ×2, Register), medium ×11, none for BATCH | exactly that; 14/14 hit | **holds — with H1-C1 and H1-C2**; as written 8/14 (findings 1, 2) |
| S17 ×4 | high — any one implemented operation suffices | 4/4 hit; three at 0.8, **SD-PK at 0.6** because all its inputs carry the POST deviation | **holds, one band below the table for SD-PK** (finding 6) |
| S30 ×4 | high (≥ 7/8) | 8/8, 7/7, 8/8, 6/6; ENT-AUDIT nothing | **holds** |
| S20 ×4 | high (report) | 8/8, 7/8, 8/8, 6/6 reported | holds |
| S01 ×4 | low; two capabilities none | 4/4 hit at 0.4; CAP-LENDING and CAP-TREASURY refused | **holds** — with H1-C3 (finding 5) |
| S50 ×5 | medium (report) | reported | holds |
| S36 | subsumed | the LPAR is an `A4.Node`; S33 covers it through the hierarchy | holds |
| Negatives | APP-LEDGER, LM-BATCH, BATCH jobs, ENT-AUDIT | all no-proposal | hold |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide / case) |
|---|---|---|---|---|
| 1 | S24 precondition, guide §3 step 2 | the boundary gate as written (literal asset-type name in paths, entity names or description) passes for only two of four modules: "current account" occurs in one operation description of LM-ACCT and "payment transactions" in ENT-PAYMENT's description; "Financial Position" and "Party Reference" occur nowhere in LM-POST's or LM-PARTY's texts | legacy estates name things `POSTING_JRNL`, `CUST_MASTER`, `GetBalance`, `CreateCustomer`; BIAN names them Position, Party. A literal gate blocks exactly the reverse-mapping case it exists for; strictly, six of fourteen operations are never considered | guide: the gate reads the module's camel-split operation names, its paths, its entity names, and the descriptions of module, operations and entities; it passes when at least half the asset-type tokens, or a listed synonym or abbreviation, occur. `export-conventions.json`: an optional institution glossary (`aliases`: acct→account, txn→transaction, customer→party …) that steps 2 and 4 consult. The gate's looseness is acceptable because it is a filter, not evidence — here it also admitted SD-CA × LM-POST and SD-CA/SD-PK × LM-BATCH without harm |
| 2 | S24 disambiguation, guide clause 4 | two ties the clause cannot break: SO-CA-03 Control (2 attributes) matches BlockAccount and AmendOverdraft at 2/2; SO-PRD-01 Register matches CreateCustomer and GetCustomer at 4/4. Neither operation has a qualifier, so the tie-break does not apply; the clause says "no proposal" | the clause excludes only pairs sharing an API or operation with a **decision-1** pair; it does not propagate uniquely resolved decision-2 pairs. GetCustomer is SO-PRD-02's unique best (5/5) and AmendOverdraft is SO-CA-04's unique best (3/3); once those are taken, each tie has one candidate left | guide clause 4: "Resolution is iterative: a pair that is its operation's unique candidate is assigned; its API and operation leave every other candidate set; repeat until nothing changes. Only ties that survive the fixpoint are no proposal." Two rounds sufficed here |
| 3 | S24 check 3 | SOAP paths have no resource/sub-resource structure (`/ledger/svc/CloseAccount`); the qualifier was sought in the camel-split operation name by stem (Closure ~ Close, Posting ~ Post, Reversal ~ Reverse) | the check's text presumes REST paths. The fail clause (a null-qualifier operation against a path carrying another operation's qualifier) was the discriminator in three pairs (SO-CA-02 × CloseAccount, SO-PK-02 × PostEntry, SO-PK-03 × PostEntry resolved by the tie-break) | guide check 3: "For RPC-style paths the qualifier is sought in the operation name (camel-split); a clear synonym is a shared stem of ≥ 4 letters." Keep the fail clause — it carried the discrimination the method could not provide |
| 4 | S24, F-SOAP | the systematic finding worked as specified: one finding, eleven references; the gold approves all eleven as recorded deviations | — | a `deviation` field on the mapping record (M1 finding 5) so the architect sees "method: POST for Retrieve, SOAP convention" without reading the evidence string; the proposal keeps the lower band until approved |
| 5 | S01, guide §3 step 5 | "no domain clearly better than the rest" has no threshold; CAP-TREASURY shares one generic token ("position") with SD-PK and nothing with the others — a strict reading of "better than the rest" would have proposed it | one shared word is not a scope match; the case requires a refusal here | guide step 5: "clearly better = at least two shared concepts after stop-words, and strictly more than every other domain" (H1-C3). On this run it separated the four true pairs (4–7 shared, runner-up ≤ 2) from the two refusals (0 and 1) with margin |
| 6 | S17, guide §2 cap | SD-PK → LM-POST derived at 0.6 while the other three modules got 0.8: every Position Keeping operation is a POST deviation, so its strongest input is medium | the cap propagates a documented, systematic method deviation into the realisation band, although the realisation is as certain as the others — the APIs do implement the operations | guide §2: a decision-2 input whose only failed check is a systematic deviation (one F-finding covering the interface) counts as high for the purpose of the S17 cap; or, with finding 4, the band is not reduced once the deviation is recorded |
| 7 | S17 / S33 trace | `sdmm-graph trace CAP-ACCT-SVC --direction down` stops at LM-ACCT: the module has no deployment arrow and the trace does not follow A3 composition to APP-LEDGER | realisation at module level (correct) plus hosting at ledger level (correct) leaves a composition hop the mapping graph does not traverse | `sdmm/graph.py`: optionally follow within-level `composition` upward from a traced component to its whole when the whole carries the A4 arrows (flag `--through-composition`), reporting the hop as derived. Not a plan change; recorded so the case's "capability → platform" expectation is exact |
| 8 | guide §4 | no baseline exists for H1 (nothing is approved); the executor assigned `H1-BASE-2026-Q4` | the template requires `baseline_id` but the case does not define one | case H1 / guide §4: name the baseline the proposals belong to, or allow `baseline_id` to be omitted on a proposal document for an unbaselined estate |
| 9 | S01 validator | `bian_release` is required on `bian_alignment_guidance` mappings; the A2 export carries no release identifier | the A2 export has `model_version` but no BIAN release field | `export-conventions.json`: a model-level `bian_release` on the A2 export that step-5 proposals copy; warning-level only |

#### New connection candidates (outside the plan)

None. The three BATCH jobs overlap no control record at ≥ 50 % (JOB-INTEREST vs CR-PK is the best at 2/8), so there is no non-REST realisation to report. The A2 export has no Notify operation. LM-BATCH and TS-SCHED (the scheduler) are plausibly related but no export key links them, so nothing is recorded.

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S33 / S32 | LM-ACCT, LM-POST, LM-PAY, LM-PARTY, LM-BATCH | no deployment record of their own; hosting is the ledger's (derived path) |
| S24 | 67 gated operation × SOAP-operation pairs (all in the log) | 14 proposed; 45 at decision 3 (check 4 below 50 % or not the best match, or check 3 fail); 8 decision-1/2 candidates excluded by one-to-one resolution |
| S24 | 13 of 20 domain × module gates | gate fails: no asset-type token or synonym in the module's texts; one summary record each |
| S24 | JOB-EOD, JOB-INTEREST, JOB-AUDIT | `method: BATCH` — not an HTTP interface; step 2 not applicable; best control-record overlap 2/8 |
| S17 | APP-LEDGER × four domains | composes the modules; realisation is at module level; the whole is a query |
| S17 | LM-BATCH × four domains | exposes only BATCH jobs; no implemented operation; asset tokens absent |
| S30 / S20 | ENT-AUDIT × every BOM object and control record | 0/n |
| S01 | CAP-LENDING | 0 shared concepts with any domain |
| S01 | CAP-TREASURY | 1 shared concept ("position") with SD-PK only — below the H1-C3 threshold; refused rather than guessed |
| S25, S41, S49 | — | no `A3.ApplicationService`, no `consumes`, no artifact |
| S02, S04, S06, S12 | — | the A1 draft has no value streams, processes, activities or business objects |

**Summary.** Reverse mapping under the worst information conditions the suite defines — nothing approved, a draft capability list, SOAP-era naming — reached every one of the 28 approved arrows with no false proposal, and refused the two capabilities and the three batch jobs it was meant to refuse. The honest caveat is that three gaps in the guide had to be filled by stated conventions: the boundary gate must read operation names and descriptions through an alias table (as written it blocks half the estate), disambiguation must iterate (as written it leaves two ties), and step 5 needs a numeric "clearly better". None of the three is inference; each is a rule the guide should state. The method deviation (all POST) was carried as one finding and should stop depressing the realisation band once recorded. H2's hostile naming will press on finding 1 hardest.

### H1 — actions taken on the findings (v0.5.5)

| Finding | Action |
|---|---|
| 1 — literal boundary gate | Guide step 2: **token gate** — asset-type name *and aliases* (`A2.AssetType.attributes.aliases`, new export convention) against camel/snake-split operation names, paths, descriptions and accessed entity names. Aliases added to all three examples' asset types |
| 2 — disambiguation ties | Disambiguation iterates to a fixpoint (decision-1 pairs first, then unique best payload matches, repeat) |
| 3 — step 5 threshold | Propose only when the best domain shares ≥ 2 non-generic concepts and leads the runner-up by ≥ 1; generic banking words are not evidence |
| 4 — systematic deviation depressing S17 | A derivation is not lowered by inputs whose only deficit is a recorded systematic interface deviation |
| 5 — trace stops at the module | `sdmm-graph trace --follow-composition` continues a chain through within-level composition (module → its whole downstream; whole → parts upstream), rendered as `PART_OF` / `COMPOSES` structural hops |

**H1 is complete:** 28 of 28 from nothing approved, no false proposal, every refusal held. Under the guide as it stood, recall would have been 0.79; the three conventions the executor had to invent are now rules.
