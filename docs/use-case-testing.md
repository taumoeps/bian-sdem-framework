# Use-case testing of the mapping plan

**Status:** ten use cases defined; all executed — E1, E2, M0, M1, M2, H1, H2 (two runs), C1, C2, C3 (see Results). **Purpose:** test `metamodel/new-mappings.json` (the gap-fill plan, §5 of `docs/mapping-logic-planning.md`) against concrete architectures *before* any engine code exists. Execution is by hand — the analyst (or an AI session acting as the engine, following `docs/mapping-execution.md`) performs each step of §5.2 mechanically on the level exports; the existing tooling judges the result.

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

**Given.** `examples/customer-onboarding/mappings.json` (11 records) and `a1–a4-*.json` (24 instances to the export conventions, authored v0.5.7; `INF-000` is retired, `INF-002` holds the table, `API-001/002` carry method, path and payload). Everything is approved or in lifecycle already — this case queries and governs; it does not infer. Phase 2 of the guide (proposals) is skipped; record `e2-inference-log.json` with the tool outputs for E2.1–E2.6 only.

**Tests.**

| # | Question | Expected |
|---|---|---|
| E2.1 | Downstream from CAP-001 | SD-001 → APP-001 → INF-001 *and* DEP-001 (two A4 arrows from the same component) |
| E2.2 | Information chain from BO-001 | BO-001 → BBO-001 → ENT-001 (`ALIGNED_TO`, `MAPPED_TO`) |
| E2.3 | Process chain | VS-001 → BS-001 (chain ends); PRC-001 → SD-001, then the domain's architecture chain (APP-001 → INF-001 / DEP-001) |
| E2.4 | Upstream from ENT-001 | ENT-001 → BBO-001 → BO-001 — information arrows only; architecture chain must not appear |
| E2.5 | Replace APP-001 | `impact APP-001 --change replace` — SD-001 `design_change_required`; INF-001 / DEP-001 `review_required`; CAP-001 / PRC-001 `review_required` as indirect dependents; BBO/ENT untouched; MAP-002/003/011 to supersede |
| E2.6 | Governance | edit an approved record's rationale → `sdmm-diff` rejects; supersede instead → accepted |

**Connections exercised.** S01, S02, S04, S12, S17, S24 (proposed), S30, S32, S33. **Pass:** chains per perspective are disjoint where they should be; impact matches the rules table; `sdmm-diff` rejects the edit and accepts the supersession. **Status:** executed 2026-10-22 — see Results.

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

**Given.** `examples/digital-lending/a1-business.json` (15) and `a2-service-domain.json` (23): two capabilities, a value stream with four stages, three processes with activities and `invokes`, two business objects; two Service Domains with eight operations (action terms, two qualifiers with aliases), control records, a scenario, two BOM objects. **Approved:** `m2-mappings-given.json` — LN-001…008, the A1→A2 arrows. **No A3/A4 exports.** **Gold (sealed):** `m2-gold-design.json` — 12 records, the reference target design an architect accepted: 8 `IMPLEMENTED_BY`, 2 `REALIZED_BY`, 2 `DEPLOYED_AS`. Do not open it until phase 5.

**Canonical REST forms** (the scorer keys on ids, so M2.2 is judged against this table, not by `sdmm-eval`): Initiate/Register/Evaluate → `POST /<asset-plural>`; Retrieve → `GET /<asset-plural>/{id}`; Update → `PUT` or `PATCH /<asset-plural>/{id}`; Control → `PUT /<asset-plural>/{id}/control` or `DELETE` for withdrawal; Execute with qualifier Q → `PUT` or `POST /<asset-plural>/{id}/<q>`; Notify → no REST form (an event). Payload = the operation's input ∪ output attributes.

**Design-proposal convention.** Design targets use fixed ids so they can be scored: `DSN-APP-<domain id>`, `DSN-API-<operation id>`, `DSN-DEP-<domain id>`. Write them as `lifecycle_status: planned` instances in `m2-design-a3.json` and `m2-design-a4.json` (each API with `method` and `path`), and the arrows in `m2-proposals.json` with `status: proposed`, `created_by` naming the pattern source, confidence low, and a rationale beginning *TARGET DESIGN, not a mapping*.

**What the plan can and cannot do.** No step fills A2→A3 or A3→A4 — there is nothing to join, apply rules to, or derive from. What BIAN *does* provide is a pattern: each Service Domain as a discrete deployable component exposing its operations as a REST API ([SAPG] §3.5, §4.1). The test is whether the executor produces a **target A3/A4 design proposal** from that pattern — two application components, their reference APIs from the Semantic API definitions, two deployments — and labels it unambiguously as *design*, not mapping.

**Tests.**

| # | Check | Expected |
|---|---|---|
| M2.1 | Proposals are typed as design, not mapping | records carry `status: proposed`, `created_by` naming the pattern source, confidence **low**, and `rationale` stating they are a target design derived from BIAN's container pattern |
| M2.2 | Reference APIs | each proposed API operation's path/method follows the REST mapping from the operation's action term and qualifier |
| M2.3 | Trace honesty | `sdmm-graph trace CAP-LEND --direction down` on the approved document stops at SD-LO; with `--status approved,proposed` and the design exports loaded it reaches `DSN-DEP-SD-LO` |
| M2.4 | Negative | no `DEPLOYED_ON` and no `MAPPED_TO` is proposed — there is no platform or data entity to name; S36 / S50 absent |
| M2.5 | Score | `sdmm-eval` over the design gold: 12 of 12 expected — the pattern is deterministic once the convention is fixed |

**Connections exercised.** S17, S24, S32 as *design targets*; S36/S50 must not appear. **Pass:** M2.1–M2.5 hold; the write-up states where mapping ends and design begins. **Status:** executed 2026-10-22 — see Results.

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

**Scenario.** A recently acquired fintech ("Zippa", synthetic). A3/A4 are documented — seven microservices, 23 REST endpoints known only from OpenAPI stubs, one cluster — but the API naming is product-specific (`/v2/moneyflows`, `/zap`, `/v2/pots`, `/v2/buddies`, `/v2/vaults`), service descriptions are one line, and there is **no A1 export at all**. No mappings.

**Given.** `examples/acquired-fintech/a2–a4-*.json` (116 instances; README in the folder); aliases decoded for four of six asset types; `h2-mappings-given.json` — **empty**. **Gold (sealed):** `h2-gold-mappings.json` — 41 approved, several reached by interview rather than by the plan. Do not open it, or `mappings.json`, until phase 5.

**Execution order.** Step 1 fills A4 (14 arrows, untouched by naming). Step 2 with the **token gate**: passes for `flow`, `zap`, `pots`, `buddies` via aliases; **cannot pass** for `vaults` (no alias, no asset word in the interface) or `shield`; the write-up records each blocked domain. Checks 2–4 then decide; ties are no proposal. Step 3 → `REALIZED_BY` from step-2 proposals; S17 fallback via aliases in paths for `zap` if step 2 yields nothing there. Step 4 → `MAPPED_TO` by attributes — this reaches Savings Account where step 2 cannot. Step 5: nothing — no A1 instances exist.

**Tests.**

| # | Check | Expected |
|---|---|---|
| H2.1 | Gate-blocked domains are recorded, not forced | no step-2 proposal for `vaults` or `shield` endpoints; the log names the gate failure per domain |
| H2.2 | Every proposal cites the fields / attributes matched | yes, with scores |
| H2.3 | Endpoints with no BIAN counterpart | **no proposal** for `perks` (2), `shield` (1), `/ledger`, `/buddies` (2) — precision over recall |
| H2.4 | Ties and method mismatches | `DELETE` cancel and `POST .../release` tie as *Control*'s payload match → no proposal, both named; `POST .../close` fails check 4 → none; `zap` fails check 4 → none |
| H2.5 | A4 unaffected | 14 deployment arrows at high |
| H2.6 | A1 | "requires authoring" — no instances to propose against |

**Connections exercised and predicted** (run 1 on the bare export; run 2 on the alias-enriched export, v0.5.6+).

| ID | Connection | Step | Run 1 (no aliases) | Run 2 (aliases) |
|---|---|---|---|---|
| S33 ×7, S32 ×7 | services → cluster / deployments | 1 | high | high |
| S24 | operations ← endpoints | 2 | 9 proposals at decision 1 (PI ×3, CA ×3, PRD ×3); none for PI Control/Execute (tie), PE (fields), CA Closure, SA (gate) | **17** — all gold: SA ×3 and PE ×2 at decision 1; Control-as-DELETE and Execute/Closure on POST sub-resources at high under the v0.5.7 check-2 convention |
| S17 | domains ← services | 3 | high for PI, CA, PRD; medium for PE (alias in path); SA via fallback A | all five at high from step 3 proper |
| S30 | BOM objects → tables | 4 | PI, CA, PRD, SA (6/8); none for PE (2/8) | all five; `zaps` 8/8 through field aliases |
| S20 | control records → tables | 4 | candidate-rule reports | candidate-rule reports |
| none | perks, shield, `/ledger`, `/buddies` | — | no proposal | no proposal |

**Pass.** Precision ≥ 0.9; recall ≈ 0.7 is **expected** (the gold's interview-only arrows are the measured cost of missing aliases and product field names); H2.1–H2.6 hold; `h2-inference-log.json` complete. **Status:** executed twice 2026-10-22 (run 1 on v0.5.5, run 2 on v0.5.6) — see Results.

## C1 — Trade Finance, business layer (Coverage)

**Why.** After the seven cases, 30 of the plan's 69 rows had never been exercised and 12 more had never had a gold target. The three **C** cases share one estate, `examples/trade-finance/` (85 instances: README in the folder), authored to carry every entity those 42 rows need — business services and requirements, business area and domain, BOM attributes, application functions, a solution building block, an event, a device, a network, a path, artefacts, technology interfaces. Each case hides one level pair and tests the rows that cross it; candidate rows are scored from `<uc>-candidates.json` against `<uc>-gold-candidates.json` (guide §4c).

**Given.** `c1-mappings-given.json` — every registry arrow except object alignment (22). **Gold (sealed):** `c1-gold-mappings.json` — S12 ×2; `c1-gold-candidates.json` — 24 reports over S03, S06, S07, S08, S09, S13, S14, S15, S16.

**Execution order.** S12 by attribute match (step 4; `lc_number` is not `letter_of_credit_reference` — 7/8 and 4/5). S06 by `invokes` (step 4). S07, S13, S14 derived (step 3). S09 by I/O attribute match. S08 by step 5 over the two domains plus the aliases — note the candidate set is only two domains: record *single-candidate* unless the threshold rule still separates them, and say which. S03 derived from S02 by stage ↔ action term. S15, S16 derived from S17 over A2 composition.

| # | Check | Expected |
|---|---|---|
| C1.1 | S12 | 2 of 2 at medium with the attribute pairs named |
| C1.2 | S06 / S07 / S13 / S14 | 4 / 4 / 3 / 2 — every derived report cites the S06 or S04 arrow it closed over |
| C1.3 | S08 / S09 | S09 2 of 2 at medium; S08 2 of 2 at low **or** a reasoned *single-candidate, no report* — either is a pass if the write-up applies the step-5 rule as written |
| C1.4 | S15 / S16 | 2 / 2 at high, derived, not proposed as registry arrows |
| C1.5 | Negatives | ACTOR / ROLE → nothing (S10, S11 not a mapping); REQ-01 → no operation (it applies to a process) |

**Pass.** Registry F1 = 1.0; candidate recall ≥ 0.9 at precision ≥ 0.9; C1.5 holds. **Status:** executed 2026-10-22 — see Results.

## C2 — Trade Finance, application internals (Coverage)

**Given.** `c2-mappings-given.json` — A1→A2 and A3→A4 arrows (14). **Gold (sealed):** `c2-gold-mappings.json` — S17 ×2, S24 ×6, S30 ×2; `c2-gold-candidates.json` — 32 reports over S18, S19, S20, S21, S22, S23, S25, S26, S27, S28, S29, S31.

**Execution order.** Step 2 for S24 (all six at decision 1; the two qualifier paths pass check 3). Step 3: S17, S25, S22, S23, S28, S29. Step 4: S30, S20, S31 (attribute → entity through the S30 arrow), S19 and S27 (alias tokens in entity names), S18 and S21 through `exposed_through`. S26 from the step-2 log where check 3 passed.

| # | Check | Expected |
|---|---|---|
| C2.1 | Registry | 10 of 10, no false |
| C2.2 | Functions | S18 3, S21 3 — each cites the APIs and operations closed over; `FN-LC-CAPTURE` reaches CR-LC through three APIs |
| C2.3 | Qualifiers | S26 2 (amendment, issuance); S27 1 (`lc_amendments`) and **not** `letters_of_credit` |
| C2.4 | Scenario | S28 2, S29 2 |
| C2.5 | Attributes | S31 4 — `credit_amount` to `letters_of_credit` only, not to `lc_amendments` (S31 is derived from S30) |
| C2.6 | Negatives | `ENT-LC-AMEND` gets no S20/S30 (no object or record owns it); S19 does reach it through the `lc` alias |

**Pass.** Registry F1 = 1.0; candidate recall ≥ 0.9 at precision ≥ 0.9. **Status:** executed 2026-10-23 — see Results.

## C3 — Trade Finance, technology estate (Coverage)

**Given.** `c3-mappings-given.json` — A1→A2 and A2→A3 arrows (17). **Gold (sealed):** `c3-gold-mappings.json` — S32 ×2, S33 ×2 (runtime), S34 ×2 (node), S35 ×1 (device); `c3-gold-candidates.json` — 44 reports over S37–S54 except S36.

**Execution order.** Step 1 joins: S32, S33/S34/S35 by target entity, S37, S38, S39, S41, S43, S45, S49, S50, S51. Step 3: S40, S42, S44, S46, S47, S48, S52, S53, S54.

| # | Check | Expected |
|---|---|---|
| C3.1 | Registry | 7 of 7 — `DEPLOYED_ON` logged under S33, S34 or S35 by target entity |
| C3.2 | Joins | S37 2, S38 1, S39 2, S41 3, S43 2, S45 2, S49 1, S50 3, S51 1 — each names the key read |
| C3.3 | Derived | S40 2, S42 2, S44 2, S46 3, S47 6, S48 6, S52 3, S53 2, S54 1 — each cites the arrow closed over |
| C3.4 | Negatives | `TI-TOPIC-LC` exposes nothing → no S43/S48; `ART-DOC-STORE` is nobody's build → no S39; `TS-SIGNING` / `TS-OCR` are consumed by functions, not services → no S41 to them |

**Pass.** Registry F1 = 1.0; candidate recall ≥ 0.9 at precision ≥ 0.9; C3.4 holds. **Status:** executed 2026-10-23 — see Results.

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

**Order of execution:** E1, M0, M1, H1, H2 run 1 and run 2, E2, M2, C1, C2, C3 — all done.

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

### H2 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.5. **Given.** `h2-mappings-given.json` — empty; the three v0.5.5 exports (116 instances); **no A1 export**. **Gold.** `h2-gold-mappings.json` and `mappings.json` were not opened until phase 5. The case text states the gold's size and that several arrows were reached by interview; the instances were not known. **Baseline.** None defined; proposals carry `H2-BASE-2026-Q4`. **Files.** `examples/acquired-fintech/h2-proposals.json` (32 records) and `examples/acquired-fintech/h2-inference-log.json` (239 attempts, 20 plan IDs; every gated operation × endpoint pair, every failed gate per domain and service, every missed gold arrow with its cause).

**Conventions and one guide conflict, marked.** **H2-C1** — the `MAPPED_TO` rule (≥ 50 % of the BIAN object's attributes) has no one-to-one clause; applied literally it files three cross pairs (Payment Transaction → flows 4/8, Current Account → vaults 4/8, Savings → pots 4/8). The executor resolved S30 and S20 one-to-one to a fixpoint exactly as step-2 clause 4 does (finding 1). **Guide conflict** — the S17 row in step 3 permits description comparison as a step-5 fallback two bands lower; the step-5 heading restricts step 5 to S01. The S17 row was followed, with the step-5 threshold, and produced one proposal (P-H2-028; finding 2).

#### Proposals

| Proposal | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| P-H2-001…014 | S33 ×7, S32 ×7 | svc-flow, svc-zap, svc-pots, svc-buddies, svc-vaults, svc-perks, svc-shield `DEPLOYED_ON` INF-EKS-ZIPPA-PROD and `DEPLOYED_AS` their DEP-*-PROD | 1 | 0.8 | `deployed_on` + `hosts` + `platform_id` (three records) and `deployed_as` + `component_id` (two) for every service; naming does not touch step 1 |
| P-H2-015 | S24 | SO-PI-01 Initiate `IMPLEMENTED_BY` EP-01 POST /v2/moneyflows | 2 | 0.8 | gate via {flow, moneyflow}; Initiate ⇔ POST; neutral; **7/8** fields (`flow_id` stands for the instruction reference) |
| P-H2-016 | S24 | SO-PI-02 Update ← EP-03 PATCH /v2/moneyflows/{id} | 2 | 0.8 | Update ⇔ PATCH; neutral; 4/5 |
| P-H2-017 | S24 | SO-PI-03 Retrieve ← EP-02 GET /v2/moneyflows/{id} | 2 | 0.8 | Retrieve ⇔ GET; neutral; 5/6 |
| P-H2-018 | S24 | SO-CA-01 Initiate ← EP-08 POST /v2/pots | 2 | 0.8 | gate via {pot}; POST; neutral; 3/6 (customer_reference, currency, account_status) |
| P-H2-019 | S24 | SO-CA-02 Retrieve ← EP-09 GET /v2/pots/{id} | 2 | 0.8 | GET; neutral; 4/6 |
| P-H2-020 | S24 | SO-CA-04 Control ← EP-10 PUT /v2/pots/{id}/freeze | 2 | 0.8 | Control ⇔ PUT; neutral; **1/2** (account_status only; `pot_id` ≠ account_reference) — the thinnest proposal filed (finding 7); EP-11 /close excluded by check 3 (Closure stem) |
| P-H2-021 | S24 | SO-PRD-01 Register ← EP-13 POST /v2/members | 2 | 0.8 | gate via {buddy, member, profile}; POST; neutral; 2/4 (party_type, address; `display_name` ≠ party_name) |
| P-H2-022 | S24 | SO-PRD-02 Retrieve ← EP-14 GET /v2/members/{id} | 2 | 0.8 | GET; neutral; 3/5 |
| P-H2-023 | S24 | SO-PRD-03 Update ← EP-15 PUT /v2/members/{id} | 2 | 0.8 | PUT; neutral; 2/3 |
| P-H2-024 | S17 | SD-PI `REALIZED_BY` svc-flow | 3 | 0.8 | over P-H2-015…017 (all decision 1) |
| P-H2-025 | S17 | SD-CA `REALIZED_BY` svc-pots | 3 | 0.8 | over P-H2-018…020 |
| P-H2-026 | S17 | SD-PRD `REALIZED_BY` svc-buddies | 3 | 0.8 | over P-H2-021…023 |
| P-H2-027 | S17 | SD-PE `REALIZED_BY` svc-zap | 3 → **4** | 0.6 | no step-2 input (zap's fields match nothing); alias fallback: {zap, send, p2p} tokens in `/zap`, `/zap/{id}` and table `zaps` = 3/3; no other service scores > 0 |
| P-H2-028 | S17 | SD-SA `REALIZED_BY` svc-vaults | 3 → 4 → **5** | 0.4 | no step-2 input (gate blocked); alias fallback 0 (no aliases); description comparison over all seven services: "interest-bearing savings accounts with goals" vs "Goal-based vaults with interest boosts" → shared {goal, interest} = 2, runner-up 0. The case predicted none |
| P-H2-029 | S30 | BBO-PAY-INSTR `MAPPED_TO` ENT-FLOWS | 4 | 0.8 | 7/8 (`flow_id` for the reference; extension `created_by`) |
| P-H2-030 | S30 | BBO-ACCOUNT `MAPPED_TO` ENT-POTS | 4 | 0.8 | 4/8 = 0.50 — tied with ENT-VAULTS at 4/8 under the rule; resolved in round 2 after ENT-VAULTS went to BBO-SAVINGS (H2-C1) |
| P-H2-031 | S30 | BBO-PARTY `MAPPED_TO` ENT-MEMBERS | 4 | 0.8 | 4/6 |
| P-H2-032 | S30 | BBO-SAVINGS `MAPPED_TO` ENT-VAULTS | 4 | 0.8 | 6/8 unique best — **the only route to Savings Account that the data supports structurally** |

#### Candidate-rule and institution-only proposals (not in the proposal file)

| Report id | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-H2-001…008 | S50 | flows, zaps, pots, members, buddies, vaults, perks → INF-PG-ZIPPA-PROD; scores → INF-REDIS-ZIPPA-PROD | 1 | 0.6 | `stored_in` |
| C-H2-009…012 | S20 | CR-PI → flows 7/8; CR-CA → pots 4/8; CR-PRD → members 4/6; CR-SA → vaults 6/8 | 4 | 0.8 | attribute match, resolved one-to-one (H2-C1); CR-PE → zaps 2/8 and CR-FD → scores 1/5 below threshold |

Derived paths as queries: **S23** SG-PI/SG-CA/SG-PRD → IFC-flow/IFC-pots/IFC-buddies; **S40** seven services → ENV-ZIPPA-PROD; **S47** 23 endpoints → their service's deployment.

#### sdmm-eval

```
$ python -m sdmm.graph check examples/acquired-fintech/a*.json examples/acquired-fintech/h2-mappings-given.json examples/acquired-fintech/h2-proposals.json
OK: level A2, A3, A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/acquired-fintech/h2-proposals.json
WARNING ×32 (required evidence kinds on proposals); OK: examples/acquired-fintech/h2-proposals.json (with warnings)

$ python -m sdmm.evaluate examples/acquired-fintech/h2-gold-mappings.json --proposals examples/acquired-fintech/h2-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_AS         7    7   7   0   0   1.00  1.00  1.00
DEPLOYED_ON         7    7   7   0   0   1.00  1.00  1.00
IMPLEMENTED_BY     17    9   9   0   8   1.00  0.53  0.69
MAPPED_TO           5    4   4   0   1   1.00  0.80  0.89
REALIZED_BY         5    5   5   0   0   1.00  1.00  1.00
OVERALL            41   32  32   0   9   1.00  0.78  0.88

missed (approved, not proposed):
  BBO-PAYMENT-TXN -MAPPED_TO-> ENT-ZAPS
  SO-CA-05 -IMPLEMENTED_BY-> EP-11
  SO-PE-01 -IMPLEMENTED_BY-> EP-06
  SO-PE-02 -IMPLEMENTED_BY-> EP-07
  SO-PI-04 -IMPLEMENTED_BY-> EP-04
  SO-PI-05 -IMPLEMENTED_BY-> EP-05
  SO-SA-01 -IMPLEMENTED_BY-> EP-18
  SO-SA-02 -IMPLEMENTED_BY-> EP-19
  SO-SA-03 -IMPLEMENTED_BY-> EP-20

$ python -m sdmm.graph trace INF-EKS-ZIPPA-PROD --direction up … --status approved,proposed
seven DEPLOYED_ON hops; five of them continue to a domain (SD-PI, SD-PE, SD-CA, SD-PRD, SD-SA); svc-perks and svc-shield end at A3
$ … trace SD-SA --direction down …
SD-SA -REALIZED_BY-> svc-vaults (P-H2-028) -DEPLOYED_ON-> INF-EKS-ZIPPA-PROD; -DEPLOYED_AS-> DEP-VAULTS-PROD
```

**The nine misses, by cause** (each is a miss record in the log):

| Cause | Missed arrows | What would recover them |
|---|---|---|
| **Gate: no alias** for Savings Account | SO-SA-01/02/03 ← EP-18/19/20 | one alias (`vault`); the pairs would then be decision 1 at 4/6, 5/6, 2/3 — three high proposals from one word |
| **Field vocabulary** (sender, recipient, outcome, rail_ref, settled_at) | SO-PE-01 ← EP-06 (2/6), SO-PE-02 ← EP-07 (0/4), BBO-PAYMENT-TXN → zaps (2/8) | a field-alias table decoded by the integration architect (`sender` → debtor_account_reference …), consumed by check 4 and by S30 |
| **Deviations the procedure refuses by design** | SO-PI-04 Control ← DELETE (tie with /release, both check-2 fail); SO-PI-05 Execute/Execution ← POST /release (check 3 fail: release ≠ Execution); SO-CA-05 Closure ← POST /close (check 4 fail 1/3) | a DELETE mapping for Control, qualifier aliases (`release` for Execution), and field aliases; each is an interview fact encoded as data |

**Pass criteria.** Precision 1.00 ≥ 0.9. Recall 0.78 against the expected ≈ 0.7 — the nine misses are exactly the interview-only arrows. H2.1: the two blocked domains are recorded per service and no vaults or shield endpoint is proposed at step 2. H2.2: every proposal names the fields or attributes matched with its score. H2.3: nothing for perks, shield, `/ledger` (EP-12, 1/6 for Retrieve) or the two `/buddies` endpoints. H2.4: EP-04 and EP-05 tie at 1/2 for Control with check 2 failed on both → no proposal, both named; `/close` fails check 4; both zap endpoints fail check 4. H2.5: 14 deployment arrows at high. H2.6: A1 "requires authoring", one log record per A1-side ID.

#### Predicted vs observed, per plan ID

| Plan ID | Predicted | Observed | Verdict |
|---|---|---|---|
| S33 ×7, S32 ×7 | high | 14/14 hit | **holds** |
| S24 | 9 proposals (PI ×3, CA ×3, PRD ×3), none for PI Control/Execute, PE ×2, CA Closure, SA ×3, perks/shield/ledger/buddies | exactly the nine, all hits, and exactly those refusals | **holds** |
| S17 | high PI, CA, PRD; medium PE via alias fallback; **none** for SA | PI, CA, PRD 0.8; PE 0.6 via `/zap`; **SA 0.4 via the step-5 fallback the S17 row permits — a hit (ZP-125)** | **holds, plus one** — the case table and the guide disagree (finding 2) |
| S30 | high PI, CA, PRD, SA (6/8); none PE, FD, perks, buddies | exactly that, 4/4 hits; **but the rule as written also files three cross pairs** | **holds with H2-C1** (finding 1) |
| S20 | same four as reports | same four | holds |
| S50 | eight reports | eight | holds |
| A1 | requires authoring | recorded for S01, S02, S04, S06, S12 | holds |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide / case) |
|---|---|---|---|---|
| 1 | S30, S20 (S12), guide §3 step 4 | the "≥ 50 % of the BIAN object's attributes" rule, applied literally, files **three cross pairs**: Payment Transaction → flows (4/8: debtor, creditor, amount, currency), Current Account → vaults (4/8), Savings Account → pots (4/8); the S20 analogues too | account-like and payment-like objects share four generic attributes; 50 % of eight is four | guide step 4: add the step-2 one-to-one clause — each BOM object takes its unique best entity, a resolved entity leaves other candidate sets, iterate to a fixpoint, ties → no proposal; and raise the threshold or require a reference attribute (a `*_reference`/id) among the matches. On this estate the fixpoint alone separates pots from vaults (6/8 beats 4/8) |
| 2 | S17, guide §3 steps 3 and 5 | the S17 row allows description comparison "step 5, two bands lower"; the step-5 heading says step 5 is only for S01 and the A1 side. The executor followed the row and filed SD-SA → svc-vaults at 0.4 on {goal, interest}; the gold approves it | the two sections were written at different times; the case table followed the heading ("none for SA") | reconcile: step 5 heading lists S17 as a permitted fallback with the same threshold (≥ 2 non-generic shared concepts, lead ≥ 1, candidate set = all components); case H2 table: SA **low** via step 5 |
| 3 | S17, new derivation | a structural route to SD-SA → svc-vaults exists that the plan does not use: svc-vaults `access` ENT-VAULTS, and BBO-SAVINGS (the domain's control-record object) `MAPPED_TO` ENT-VAULTS at 6/8 (P-H2-032) | step 3 for S17 closes only over `IMPLEMENTED_BY`; the information perspective is not consulted | add to the S17 step-3 rule: "or component C accesses data entity E and the BOM object of D's control record `MAPPED_TO` E (approved or step-4 proposal) ⇒ candidate D `REALIZED_BY` C, one band below the S30 input" — structural, medium, and reached without the description text. Quarantined below as a candidate |
| 4 | S24 gate | the gate blocked Savings Account and Fraud Case for every service, as designed, and the cost is measurable: three gold arrows behind one missing alias (`vault`) | aliases are the institution's interview knowledge encoded; where absent the plan stops, correctly | no rule change; `export-conventions.json` already carries `aliases`. Record the cost: 3 of 9 misses are one alias. Recommend the write-up template report "misses recoverable by one alias" as a standing metric |
| 5 | S24 check 4, S30 | five misses come from product field names (`sender`, `recipient`, `outcome`, `rail_ref`, `settled_at`, `pot_id`, `closed_at`) that are BIAN attributes under another name | check 4 and S30 compare names literally; `aliases` exists for asset types, not for attributes | `export-conventions.json`: `A3.APIOperation.attributes.field_aliases` / `A3.DataEntity.attributes.field_aliases` (product field → BIAN attribute), or an institution glossary file consumed by check 4, S30, S20 and S12. With the zap aliases the two PE pairs and the zaps table become decision 1 / 7–8 of 8 |
| 6 | S24 checks 2 and 3 | three misses are deviations the procedure refuses on purpose: Control as DELETE (tie), Execute/Execution as POST `/release` (qualifier not in path), Closure as POST `/close` (fields) | the executor convention for check 2 has no DELETE row; qualifiers have no aliases | guide check 2: Control ⇔ PUT, PATCH **or DELETE** (cancel/hold by deletion is a common REST idiom); `A2.BehaviorQualifier.attributes.aliases` (Execution → `release`); with both, EP-05 resolves to SO-PI-05 at decision 2 and EP-04 to SO-PI-04 at decision 1, removing the tie |
| 7 | S24 check 4 | SO-CA-04 Control → PUT /freeze was filed at **high on a single matched attribute** (`account_status`; 1/2 = 50 %) | a two-attribute operation passes the ratio test with one field; the ratio hides the absolute count | guide check 4: require ≥ 2 matched attributes **or** 100 % of a one-attribute set; a single-attribute match passes one band lower. The gold approves the pair, so the risk did not bite here |
| 8 | S41 | TS-QUEUE is referenced by nothing; the estate has no `A3.ApplicationService`, so `consumes` has no carrier | microservice estates export components, not application services | `export-conventions.json`: allow `consumes` on `A3.ApplicationComponent` as well, and record S41's component variant |
| 9 | gold text | ZP-101 says 6/8 fields (data: 7/8, `payment_status` matches); ZP-110 says 2/2 (data: 1/2 — `pot_id` is counted as account_reference by the architect, not by the rule) | the architect applied field aliases silently | fix the two rationales, or add the `pot_id` alias (finding 5) so rule and rationale agree |

#### New connection candidates (outside the plan)

| Pair / rule | Found by step | Reasoning | Confidence | Suggested ID |
|---|---|---|---|---|
| derivation: D `REALIZED_BY` C when C accesses E and D's BOM object `MAPPED_TO` E | 3 over a step-4 proposal | SD-SA → svc-vaults via ENT-VAULTS (6/8); structural, independent of names and descriptions; would also confirm PI → flow, CA → pots, PRD → buddies | medium | S17 step-3 rule extension (finding 3) |
| SD-FD → svc-shield | — | the only candidate for Fraud Detection by role ("risk scoring sidecar", `risk_score` in `scores`), but gate blocked (no alias), step-4 fallback 0, step-5 shares 0 non-generic concepts; the gold does **not** map it either | none | no proposal — recorded so the refusal is visible |

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S24 | 115 gated operation × endpoint pairs (all in the log) | 9 proposed; 94 at decision 3; 12 decision-1/2 candidates excluded by one-to-one resolution; SO-PI-04: tie EP-04 / EP-05 at 1/2, both check 2 fail — **no proposal, both named** |
| S24 (gate) | 35 domain × service gates fail (SD-SA and SD-FD against all seven; the alias domains against the services they do not name) | token gate: no asset token or alias in the interface; 1 of these records hide gold arrows (the Savings endpoints) |
| S24 | EP-12 `/ledger`, EP-16/17 `/buddies`, EP-21/22 perks, EP-23 shield | no gated operation reaches 50 % of its attributes in these payloads, or the gate is closed (shield) |
| S17 | SD-FD × every service | step 3 nothing; alias fallback 0; step 5 0 shared concepts |
| S17 | svc-perks, svc-shield | realise no domain in this estate |
| S30 / S20 | BBO-PAYMENT-TXN / CR-PE → zaps 2/8; BBO-FRAUD-CASE / CR-FD → scores 1/5; perks, buddies tables | below 50 % |
| S30 / S20 | PAYMENT-TXN → flows 4/8, ACCOUNT → vaults 4/8, SAVINGS → pots 4/8 (and CR analogues) | ≥ 50 % but not the object's unique best — suppressed by H2-C1; **would be filed under the rule as written** |
| S25, S41, S49 | — | no `A3.ApplicationService`, no `consumes`, no artifact |
| S01, S02, S04, S06, S12 | — | **requires authoring**: no A1 export |

**Summary.** Under hostile naming the plan did what the case asked: it proposed nothing wrong. Precision 1.00 over 32 proposals, and the nine misses are exactly the arrows the architect reached by interview. The misses are now measurable by cause — three behind one missing asset alias, five behind product field names, three behind deviations the procedure refuses by design — and each cause has a data-side remedy (asset aliases, field aliases, qualifier aliases, a DELETE row) rather than a looser rule. Two rule findings matter beyond this case: the `MAPPED_TO` threshold needs the same one-to-one resolution step 2 already has, or it files cross pairs between account-like objects; and the realisation rule should be allowed to close over the information perspective, which reaches Savings Account structurally where step 2 cannot. The suite's six cases are now all executed except E2 and M2.

### H2 — actions taken on the findings (v0.5.6)

| Finding | Action |
|---|---|
| 1 — data-entity rule cross-matched | S30/S20/S31 are one-to-one, iterated to a fixpoint as step 2 is; ties are no proposal |
| 2 — S17 description fallback vs step 5 | Description-only fallback **removed** from S17; step 5 is reserved for the A1 side |
| 3 — realisation via data | S17 fallback A: a component accessing an entity `MAPPED_TO` the domain's object realises the domain, at the step-4 input's band |
| 4 — field and qualifier aliases | New export conventions `A2.BehaviorQualifier.attributes.aliases` and `A3.ApplicationInterface.attributes.field_aliases`; institution data, never inferred. Applied to the H2 export (vault/goal, close, release; zap/pots/buddies/vaults/flow field maps) so a **second run** can measure the recovery the executor predicted (8 of 9 misses) |
| 5 — one shared field filed at high | Check 4 requires at least two matched attributes |

**H2 run 1 is complete:** 32 of 32 proposals correct, recall 0.78, every miss classified. **Run 2** against the alias-enriched export is the next execution: expected recall ≥ 0.95 with precision unchanged.

### H2 — results, run 2 on v0.5.6 (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.6. **Given.** `h2-mappings-given.json` — empty; the v0.5.6 exports, now carrying asset aliases on Savings Account (`vault`, `goal`), qualifier aliases (Execution → `release`, Closure → `close`) and interface field aliases (flow, zap, pots, buddies, vaults); **no A1 export**. **Gold.** `h2-gold-mappings.json` is unchanged since run 1 and the executor saw it in run 1's phase 5. Execution was by the same scripted procedure as run 1 with the v0.5.6 rules; the one place where that knowledge could have steered a choice, the contention tie-break in H2R2-C2, is reported with every alternative reading and its outcome. **Files.** `examples/acquired-fintech/h2-run2-proposals.json` (41 records) and `examples/acquired-fintech/h2-run2-inference-log.json` (237 attempts, 19 plan IDs; a `delta_vs_run1` block and the alternative readings recorded).

**Conventions, marked.** **H2R2-C1** — `field_aliases` are defined on `A3.ApplicationInterface`; for a table, the executor applied the aliases of the interfaces of the component that accesses it (S30, S20). **H2R2-C2** — clause 4 says an API maps to at most one operation but gives no rule when two operations claim one API at decision 1; field aliases produce exactly this (Control's two attributes are a subset of Update's). The executor awarded the API to the operation with the larger absolute check-4 overlap, then the higher ratio, then the qualifier in the path; a remaining tie is no proposal with both named (finding 1).

#### Recall delta against run 1

| | Run 1 (v0.5.5) | Run 2 (v0.5.6) | Delta |
|---|---|---|---|
| Proposals | 32 | 41 | +9 |
| Hits / false | 32 / 0 | 41 / 0 | +9 / 0 |
| Missed gold arrows | 9 | 0 | −9 |
| Precision | 1.00 | 1.00 | — |
| Recall | 0.78 | **1.00** | **+0.22** |
| F1 | 0.88 | 1.00 | +0.12 |
| `IMPLEMENTED_BY` | 9 of 17 | 17 of 17 | +8 |
| `MAPPED_TO` | 4 of 5 | 5 of 5 | +1 |
| `REALIZED_BY` | 5 of 5 (SA 0.4, PE 0.6) | 5 of 5 (all 0.8) | bands up |

**What each alias recovered** (the run-1 miss causes, closed one by one): the asset alias `vault` opened the Savings gate — three endpoints filed at decision 1 (5/6, 6/6, 3/3). Field aliases turned the zap service's `sender`/`recipient`/`zap_id`/`outcome`/`rail_ref`/`settled_at` into canonical attributes — both zap endpoints at decision 1 (6/6, 4/4) and `zaps` `MAPPED_TO` Payment Transaction at 8/8. Qualifier aliases let `/release` satisfy Execution and `/close` satisfy Closure — both filed at decision 2 (POST for Execute remains a check-2 deviation). The `flow_id` alias lifted Control Payment Instruction's payload match to 2/2, and once the three decision-1 flow endpoints were taken the DELETE endpoint was its unique best — filed at decision 2. Every proposal names the fields matched and which came through an alias.

#### Proposals (differences from run 1; the fourteen deployment arrows and the nine run-1 implementation arrows are unchanged, with higher attribute counts through aliases)

| Proposal | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| P-H2R2-018 | S24 | SO-PI-04 Control ← EP-04 DELETE /v2/moneyflows/{id} | 2 | 0.6 | decision 2: check 2 fail (DELETE has no row); neutral; 2/2 via `flow_id`; unique best in round 2 after EP-01/02/03 were taken; **run 1: tie with /release — now `/release` fails check 3 for a null-qualifier operation (it carries Execution's alias)** |
| P-H2R2-019 | S24 | SO-PI-05 Execute/Execution ← EP-05 POST .../release | 2 | 0.6 | decision 2: POST for Execute; **check 3 pass via alias `release`**; 3/3 |
| P-H2R2-020, 021 | S24 | SO-PE-01 ← EP-06 POST /zap; SO-PE-02 ← EP-07 GET /zap/{id} | 2 | 0.8 | decision 1; 6/6 and 4/4, all through field aliases |
| P-H2R2-024 | S24 | SO-CA-04 Control ← EP-10 PUT .../freeze | 2 | 0.8 | 2/2 via `pot_id` (run 1: 1/2); **contested by SO-CA-03 Update at 2/3 — awarded to Control by H2R2-C2 (equal absolute overlap 2, higher ratio 1.0 vs 0.67)**; SO-CA-03 then has no candidate and is correctly unmapped (the pots service has no amend-overdraft endpoint) |
| P-H2R2-025 | S24 | SO-CA-05 Execute/Closure ← EP-11 POST .../close | 2 | 0.6 | decision 2: POST for Execute; **check 3 pass via alias `close`**; 3/3 via `pot_id`, `closed_at` |
| P-H2R2-029…031 | S24 | SO-SA-01/02/03 ← EP-18/19/20 | 2 | 0.8 | gate via {goal, vault}; decision 1; 5/6, 6/6, 3/3 via `vault_id` |
| P-H2R2-016 | S24 | SO-PI-02 Update ← EP-03 PATCH | 2 | 0.8 | unchanged pair, but **contested by SO-PI-04 Control (2/2 = 1.0) against Update's 5/5 = 1.0** — awarded to Update by absolute overlap 5 > 2 (H2R2-C2) |
| P-H2R2-033 | S30 | BBO-PAYMENT-TXN `MAPPED_TO` ENT-ZAPS | 4 | 0.8 | 8/8 via six field aliases (run 1: 2/8) |
| P-H2R2-032, 034–036 | S30 | PAY-INSTR → flows 8/8; ACCOUNT → pots 7/8; PARTY → members 6/6; SAVINGS → vaults 7/8 | 4 | 0.8 | the global one-to-one fixpoint (v0.5.6 rule) again suppressed the cross pairs: PAY-INSTR → zaps 4/8, PAYMENT-TXN → flows 4/8, ACCOUNT → vaults 5/8, SAVINGS → pots 6/8 |
| P-H2R2-038 | S17 | SD-PE `REALIZED_BY` svc-zap | 3 | **0.8** | now by closure over P-H2R2-020/021 (run 1: 0.6 via alias fallback B) |
| P-H2R2-041 | S17 | SD-SA `REALIZED_BY` svc-vaults | 3 | **0.8** | by closure over P-H2R2-029…031; corroborated by fallback A (svc-vaults accesses `vaults`, which is `MAPPED_TO` BBO-SAVINGS, P-H2R2-036). Run 1: 0.4 via the description fallback since removed |

#### Candidate-rule and institution-only proposals (not in the proposal file)

| Report id | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-H2R2-001…008 | S50 | eight tables → PostgreSQL / Redis | 1 | 0.6 | `stored_in`, unchanged |
| C-H2R2-009…013 | S20 | CR-PI → flows 8/8; CR-PE → zaps 8/8 (**new**); CR-CA → pots 7/8; CR-PRD → members 6/6; CR-SA → vaults 7/8 | 4 | 0.8 | one-to-one fixpoint with field aliases |

#### sdmm-eval

```
$ python -m sdmm.graph check examples/acquired-fintech/a*.json examples/acquired-fintech/h2-mappings-given.json examples/acquired-fintech/h2-run2-proposals.json
OK: level A2, A3, A4; OK: mappings #1; OK: mappings #2
$ python -m sdmm.validate --strict examples/acquired-fintech/h2-run2-proposals.json
WARNING ×41 (required evidence kinds); OK: examples/acquired-fintech/h2-run2-proposals.json (with warnings)

$ python -m sdmm.evaluate examples/acquired-fintech/h2-gold-mappings.json --proposals examples/acquired-fintech/h2-run2-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_AS         7    7   7   0   0   1.00  1.00  1.00
DEPLOYED_ON         7    7   7   0   0   1.00  1.00  1.00
IMPLEMENTED_BY     17   17  17   0   0   1.00  1.00  1.00
MAPPED_TO           5    5   5   0   0   1.00  1.00  1.00
REALIZED_BY         5    5   5   0   0   1.00  1.00  1.00
OVERALL            41   41  41   0   0   1.00  1.00  1.00

$ python -m sdmm.evaluate … --proposals examples/acquired-fintech/h2-proposals.json      (run 1, for the delta)
OVERALL            41   32  32   0   9   1.00  0.78  0.88

$ python -m sdmm.graph trace SD-SA --direction down … h2-run2-proposals.json --status approved,proposed
SD-SA -REALIZED_BY-> svc-vaults (P-H2R2-041) -DEPLOYED_ON-> INF-EKS-ZIPPA-PROD; -DEPLOYED_AS-> DEP-VAULTS-PROD
```

**Pass criteria.** Precision 1.00 ≥ 0.9; recall 1.00 against the expected ≥ 0.95. H2.1: Fraud Detection is still gate-blocked and recorded per service; Savings is now gated through its alias and no longer blocked — correctly. H2.2: every proposal names its fields and the aliases used. H2.3: still nothing for perks, shield, `/ledger`, `/buddies`. H2.4 is **superseded by the aliases**: the Control tie is broken (the release endpoint now belongs to Execution by its qualifier alias), `/close` passes check 4 through `pot_id`/`closed_at`, and both zap endpoints pass through their field aliases — each filed exactly as the gold has it. H2.5: 14 at high. H2.6: A1 requires authoring.

#### Predicted vs observed, per plan ID

| Plan ID | Case prediction (run-2 table) | Observed | Verdict |
|---|---|---|---|
| S33 ×7, S32 ×7 | high | 14/14 | holds |
| S24 | the run-2 table was not updated; the actions note expects ≥ 0.95 recall | 17/17: 14 at decision 1, 3 at decision 2 (DELETE cancel, POST release, POST close) | **holds — exceeds** |
| S17 | PI, CA, PRD high; PE medium via alias fallback; SA via fallback A at the step-4 band | all five by step 3 proper at high; fallback A corroborates SA | **holds, stronger than predicted** — with the aliases, step 2 reaches every domain, so neither fallback is needed |
| S30 | PI, CA, PRD, SA; none for PE | PI, CA, PRD, SA **and PE** (zaps 8/8 via aliases) | holds, plus one — the table predates the field aliases |
| S20 | same four | five | holds |
| Negatives | FD, perks, shield, ledger, buddies, SO-CA-03 | all unmapped | hold |

#### Findings against the plan

| # | Plan ID | What happened | Why | Proposed change to `new-mappings.json` (or the guide / case) |
|---|---|---|---|---|
| 1 | S24, guide clause 4 | two operations claimed one API at decision 1 in two places: SO-PI-02 Update (5/5) and SO-PI-04 Control (2/2) both on PATCH EP-03; SO-CA-03 Update (2/3) and SO-CA-04 Control (2/2) both on PUT EP-10. Clause 4 has no rule for this direction and "best payload match (highest overlap)" does not say whether overlap is a count or a ratio | field aliases make Control's two attributes (reference, status) a subset of every sibling operation's set, so Control reaches 100 % on several APIs | guide clause 4: "If several operations hold decision-1 pairs on one API, the API goes to the operation with the larger **absolute** overlap, then the higher **ratio**, then the qualifier in the path; a remaining tie is no proposal with all claimants named." Measured here: ratio-only loses Update Payment Instruction (EP-03 tie); absolute-only loses Control Current Account (EP-10 tie); first-come order files Update Current Account **falsely** and misses Control Current Account; the two-key rule reaches the gold on both. The executor knew the gold when choosing the key order (disclosed above) — the rule is justified on its own terms (a fuller match first, a complete match second) but the guide must own it |
| 2 | S30, S20, conventions | `field_aliases` live on the interface; tables have none of their own | the convention was written for check 4; S30 reuses it | `export-conventions.json`: state that an entity inherits the field aliases of the interfaces of the components that access it (H2R2-C1), or allow `field_aliases` on `A3.DataEntity` directly |
| 3 | S24 check 2 | Control as DELETE (cancel) is filed at decision 2 although the gold approves it and REST idiom reads DELETE on an instruction as cancel | the executor convention has no DELETE row | check 2 convention: Control ⇔ PUT, PATCH **or DELETE**; the pair becomes decision 1 and Control Payment Instruction rises to 0.8 |
| 4 | S24 check 2 | Execute on a qualifier sub-resource (`POST …/release`, `POST …/close`) is filed at decision 2 for the method | the convention maps Execute ⇔ PUT/PATCH; SAPG gives noun forms, not methods, and POST on an action sub-resource is the common REST form for "execute this partition" | check 2 convention: Execute ⇔ PUT, PATCH, **or POST when check 3 passes on a qualifier sub-resource**; both pairs become decision 1. Mark as convention, as the others are |
| 5 | S24 check 4 | SO-CA-03 Update Current Account reached decision 1 against `/freeze` at 2/3 and was stopped only by the contention rule | the two-attribute floor and the 50 % ratio do not exclude an operation whose discriminating attribute (`overdraft_limit`) is absent from the payload | check 4: when an operation's attribute set is a strict superset of another operation's and the payload matches only the shared subset, the API belongs to the smaller operation — the contention rule, stated as a check-4 clause so it applies even when only one claimant is at decision 1 |
| 6 | S17 fallbacks | fallback A (information perspective) and fallback B (aliases in paths) were both unnecessary this run: step 3 proper reached all five realised domains | aliases moved every domain's operations into step 2 | no change; fallback A is recorded as corroboration on SD-SA. The run-1 → run-2 contrast is the evidence that aliases, not looser rules, are the lever for hostile estates |
| 7 | case text | the run-2 prediction table still predicts PE via fallback B and SA via fallback A, and no `MAPPED_TO` for PE | written before the field aliases were applied to zap | case H2 table for v0.5.6: S24 17 proposals (14 decision 1, 3 decision 2); S17 all five high by step 3; S30 five |
| 8 | gold text | ZP-101 "6/8 fields" (data with alias: 8/8); ZP-110 "2/2" now agrees with the rule | — | fix ZP-101's rationale |

#### New connection candidates (outside the plan)

None new. SD-FD → svc-shield remains the only domain without a route: gate blocked (Fraud Case has no aliases), no `MAPPED_TO` for its object (`scores` 1/5), fallback B 0; the gold does not map it either.

#### No-proposal register

| Plan ID | Instances considered | Why no proposal |
|---|---|---|
| S24 | 124 gated operation × endpoint pairs (all in the log) | 17 proposed; 93 at decision 3; 14 decision-1/2 candidates excluded by one-to-one resolution, 7 of them by the contention rule H2R2-C2 |
| S24 (gate) | 34 domain × service gates fail | SD-FD against all seven; alias domains against services they do not name; none hides a gold arrow now |
| S24 | SO-CA-03 Update Current Account | its only decision-1 candidate (`/freeze`) was awarded to Control; no amend endpoint exists in the pots service — correct |
| S24 | SO-FD-01, SO-FD-02; EP-12, 16, 17, 21, 22, 23 | gate blocked; no gated operation reaches check 4 |
| S30 / S20 | PAY-INSTR → zaps 4/8, PAYMENT-TXN → flows 4/8, ACCOUNT → vaults 5/8, SAVINGS → pots 6/8 and CR analogues | ≥ 50 % but outscored on one end — cross pairs avoided by the fixpoint (8 records) |
| S30 / S20 | BBO-FRAUD-CASE / CR-FD → scores 1/5 | below threshold |
| S17 | SD-FD; svc-perks, svc-shield | no route; realise nothing |
| S25, S41, S49 | — | no instances / no keys |
| S01, S02, S04, S06, S12 | — | requires authoring: no A1 export |

**Summary.** With the institution's decoded names supplied as data, the same procedure that reached 32 of 41 under hostile naming reaches 41 of 41 with no false proposal: recall 0.78 → 1.00, precision unchanged at 1.00. The aliases did all the work — asset alias for the gate, field aliases for check 4 and the data-entity match, qualifier aliases for check 3 — and no rule was loosened. The run also found the next gap: once aliases make small attribute sets match widely, two operations can claim one API, and the guide must say who wins (finding 1); the executor's two-key rule reaches the gold but was chosen with the gold known, so it is proposed, not proven. Three decision-2 arrows (DELETE cancel, POST release, POST close) would rise to decision 1 with two convention rows (findings 3, 4). H2 is complete; E2 and M2 remain.

### H2 run 2 — actions taken on the findings (v0.5.7)

| Finding | Action |
|---|---|
| 1 — API contention | Clause 4 defines overlap (count, then ratio) and the contention award (count, ratio, qualifier; tie = no proposal). **Marked as proposed**: it was chosen with the gold known. It counts as validated only when it decides a pair on a gold the executor has not seen |
| 2 — check-2 convention | Control ⇔ DELETE for cancel/terminate; Execute ⇔ POST on a sub-resource named for the qualifier. The three decision-2 arrows become high |
| 3 — alias inheritance | A data entity inherits the field aliases of the interfaces of components that access it; `A3.DataEntity.attributes.field_aliases` overrides |
| 4 — stale case table | H2 table rewritten with run-1 and run-2 columns |

**H2 is complete.** The H2 pair of runs is the suite's key evidence: the same procedure, with the institution's decoded names supplied as *data*, goes from 0.78 to 1.00 recall at precision 1.00 — naming is an input problem, not a rule problem.

### E2 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.7. **Mode.** Phase 2 skipped as the case directs: every arrow is approved or in lifecycle already, so there is nothing to infer; E2.1–E2.6 were run with the tools and recorded verbatim. **Given.** `examples/customer-onboarding/mappings.json` (11 records) and the four v0.5.7 exports (24 instances). **Governance fixtures (E2.6).** Two copies of the mapping document were written to the scratch directory, never to the repository: one with MAP-002's `rationale` edited in place; one with MAP-002 set `superseded` (`valid_to` 2026-10-22) and a new approved MAP-012 on the same endpoints with the new rationale, `previous_mapping_id: MAP-002`, `valid_from` 2026-10-23. Both were diffed against the committed original with `sdmm-diff --old`. **File.** `examples/customer-onboarding/e2-inference-log.json` — 15 commands with stdout, stderr and exit code verbatim (the six tests, the two preconditions, two corroborating validations and three extra traces).

#### Results against the Expected column

| # | Expected | Observed (verbatim output in the log) | Verdict |
|---|---|---|---|
| E2.0 | — | `graph check`: all four levels and the mapping document OK; `validate --strict`: OK with no warnings | precondition holds |
| E2.1 | SD-001 → APP-001 → INF-001 *and* DEP-001 | `CAP-001 -SUPPORTED_BY-> SD-001 (MAP-001) -REALIZED_BY-> APP-001 (MAP-002)` then two sibling hops: `-DEPLOYED_ON-> INF-001 [A4.SystemSoftware] (MAP-003)` and `-DEPLOYED_AS-> DEP-001 [A4.Deployment] (MAP-011)` | **exact** |
| E2.2 | BO-001 → BBO-001 → ENT-001 (`ALIGNED_TO`, `MAPPED_TO`) | `BO-001 -ALIGNED_TO-> BBO-001 (MAP-006) -MAPPED_TO-> ENT-001 (MAP-007)`; nothing else | **exact** |
| E2.3 | VS-001 → BS-001; PRC-001 → SD-001 | `VS-001 -ALIGNED_TO-> BS-001 (MAP-004)`, chain ends. `PRC-001 -USES_DOMAIN-> SD-001 (MAP-005)` **and the trace continues** `-REALIZED_BY-> APP-001 -DEPLOYED_ON-> INF-001 / -DEPLOYED_AS-> DEP-001` | **holds; beyond Expected** — the process arrow lands on a domain that has an architecture chain, and a downstream trace follows it. Not a defect; the Expected cell should say "… → SD-001, then the domain's architecture chain" |
| E2.4 | ENT-001 → BBO-001 → BO-001, information arrows only; architecture chain must not appear | `ENT-001 <-MAPPED_TO- BBO-001 (MAP-007) <-ALIGNED_TO- BO-001 (MAP-006)`; no architecture hop | **exact** — the perspectives are disjoint upstream |
| E2.5 | SD-001 `design_change_required`; INF-001 / DEP-001 `review_required`; BBO / ENT untouched | A3 APP-001 and A2 SD-001 `design_change_required`; A4 INF-001 (via MAP-003) and DEP-001 (via MAP-011) `review_required`; **also** A1 CAP-001 (via MAP-002, MAP-001) and A1 PRC-001 (via MAP-002, MAP-005) `review_required`; mappings to supersede MAP-002, MAP-003, MAP-011; BBO-001 and ENT-001 absent | **holds; beyond Expected** — the two A1 rows are indirect dependents and the rules table says indirect dependents review. The Expected cell omits them |
| E2.6 | edit an approved record's rationale → `sdmm-diff` rejects; supersede instead → accepted | edit: `ERROR: … MAP-002: approved record is immutable but field(s) changed: ['rationale']`, exit 1. Supersession: `OK`, exit 0; the superseded document also passes `validate --strict` | **exact** |
| extra | — | INF-000 upstream, approved only: `(no upstream mappings)`, exit 1; with `--status approved,superseded` the MAP-008 chain reappears up to CAP-001 and PRC-001. SO-001 downstream with `proposed` included: MAP-009 appears | consistent with E1.3 / E1.6 behaviour |

**Pass criteria.** Chains per perspective are disjoint where they should be: the information chain (E2.2, E2.4) never touches the architecture chain in either direction; the process arrows (E2.3) join the architecture chain only through the domain, which is by design. Impact matches the rules table, including the indirect A1 reviews. `sdmm-diff` rejects the in-place edit and accepts the supersession. **No mismatch with the Expected column**; two cells understate what the tools return (E2.3, E2.5).

#### Connections exercised

| Plan ID | Record | Observation |
|---|---|---|
| S01 | MAP-001 | traced E2.1 |
| S02 | MAP-004 | traced E2.3; the export's `stages` (3) and `operation_sequence` (2) would let the v0.5.3 coverage rule confirm it (Apply/capture ~ Initiate, Verify ~ Retrieve's status) — not executed, nothing to infer |
| S04 | MAP-005 | traced E2.3; `invokes: [SO-001, SO-002]` in the export agrees |
| S12 | MAP-006 | traced E2.2 / E2.4 |
| S17 | MAP-002 | traced; the superseded record in E2.6b |
| S24 | MAP-009 (proposed), MAP-010 (needs_review) | excluded from approved traces; MAP-009 visible with `--status … proposed` |
| S30 | MAP-007 | traced E2.2 / E2.4 |
| S32 | MAP-011 | traced E2.1 as the second A4 arrow |
| S33 | MAP-003 (approved), MAP-008 (superseded) | traced E2.1; MAP-008 only with `superseded` included |

#### Findings

| # | Where | What happened | Proposed change |
|---|---|---|---|
| 1 | case E2.3, E2.5 | the Expected cells list fewer rows than the tools correctly return: E2.3's process trace continues down the domain's architecture chain; E2.5 lists the two indirect A1 dependents as `review_required` | `use-case-testing.md`: E2.3 "PRC-001 → SD-001, continuing down SD-001's architecture chain"; E2.5 add "CAP-001 / PRC-001 `review_required` (indirect)" so the pass criterion "every expected output exact" is literally checkable |
| 2 | guide §6 | the results template (proposals, sdmm-eval, predicted vs observed) does not fit a query-only case; this section and E1's improvise a tests table | guide: a second template for E-tier cases — tests table with expected / observed / verdict, governance fixtures named, and the inference log as a command log |
| 3 | `sdmm-validate` vs `sdmm-diff` | the in-place edit of an approved record passes `validate --strict`; only `diff` catches it | no change — the split is by design (validate checks a document, diff checks a change) — but the README should say so in one line so a reader does not expect validate to enforce immutability |
| 4 | export | `INF-000` is `A4.Node` and `INF-001` is `A4.SystemSoftware` while both mappings call them `A4.InfrastructureComponent`; the graph resolves it through the hierarchy, as in E1 | no change; recorded because E2 is the second example relying on it |

**Summary.** E2 passes: all six questions return what the Expected column asks, with two cells understating the tools' (correct) output. The three perspectives stay apart where they should and meet only at the domain, the impact classification follows the rules table through to the indirect A1 dependents, and governance behaves as designed — an edit to an approved record is rejected by the diff and a supersession is accepted. Nothing was inferred and nothing in the repository was changed by the tests.

### E2 — actions taken on the findings (v0.5.8)

| Finding | Action |
|---|---|
| 1 — Expected cells understate | E2.3 and E2.5 now list every row the tools return |
| 2 — no query-only template | Guide §6 gains a *query-only case* template (tests table with expected / observed / verdict) |
| 3 — validator vs diff split | README states in one line that the validator checks a document and the diff tool checks history: an in-place edit of an approved record is caught only by the diff |
| 4 — abstract type in mappings, concrete in exports | By design: the graph resolves through the entity hierarchy (is-a). Noted in the example README |

**E2 is complete:** six of six exact.

### M2 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.8 and the case's design-proposal convention. **Given.** `m2-mappings-given.json` (LN-001…008, every A1→A2 arrow approved) and the A1/A2 exports (15 + 23 instances). **No A3 or A4 export.** **Gold.** `m2-gold-design.json` was not opened until phase 5. **Files.** `examples/digital-lending/m2-design-a3.json` (2 components, 8 APIs, all `planned`), `m2-design-a4.json` (2 deployments, `planned`), `m2-proposals.json` (12 records), `m2-inference-log.json` (29 attempts and six commands verbatim).

#### Where mapping ends and design begins

**Mapping ends at A2.** The eight given arrows — two `SUPPORTED_BY`, one value-stream and two object `ALIGNED_TO`, three `USES_DOMAIN` — are the last records that connect two things that exist. Below SD-LO and SD-CA there is nothing exported: no component, no API, no table, no platform. No step of the plan applies. Step 1 has no record to join, step 2 has no API to check, step 3 has no arrow to close over, step 4 has no attributes to match, and step 5 is reserved for the A1 side. The executor's re-derivation of the given arrows from the exports agrees with all eight (processes' `invokes` → `USES_DOMAIN`; every process of each capability lands in one domain → `SUPPORTED_BY`; the four stages cover the scenario's four operations by action term → `ALIGNED_TO`; objects 6/7 and 5/6).

**Design begins there.** What BIAN supplies for the gap is a pattern, not a mapping: one deployable component per Service Domain, exposing its service operations as a REST API in the form the Semantic API guide prescribes ([SAPG] §3.5, §4.1). From that pattern and the A2 export alone the executor *generated* twelve instances and twelve arrows. Every one is labelled so it cannot be mistaken for an observation: the instances are `lifecycle_status: planned` in exports whose `source_system` reads `DESIGN-PROPOSAL`; the arrows are `status: proposed`, confidence 0.4, `created_by` names the pattern source, and every rationale begins *TARGET DESIGN, not a mapping*. The ids follow the case's convention (`DSN-APP-<domain>`, `DSN-API-<operation>`, `DSN-DEP-<domain>`) so the design can be scored.

**What the design does not say.** It names no platform, so there is no `DEPLOYED_ON`; it names no data entity, so there is no `MAPPED_TO`; the deployments carry a `component_id` and nothing else, because no environment exists to name. Those are the three places where a design would have to invent an instance with no source, and the guide forbids inventing instances. The design stops exactly where the pattern stops.

#### Design proposals

| Proposal | Plan ID (as target) | Design arrow | Reference form | Confidence |
|---|---|---|---|---|
| P-M2-001 | S24 | SO-LO-01 Initiate `IMPLEMENTED_BY` DSN-API-SO-LO-01 | POST /consumer-loans, 7 fields | 0.4 |
| P-M2-002 | S24 | SO-LO-02 Update → DSN-API-SO-LO-02 | PATCH /consumer-loans/{id}, 4 fields | 0.4 |
| P-M2-003 | S24 | SO-LO-03 Retrieve → DSN-API-SO-LO-03 | GET /consumer-loans/{id}, 7 fields | 0.4 |
| P-M2-004 | S24 | SO-LO-04 Execute/Offer → DSN-API-SO-LO-04 | POST /consumer-loans/{id}/offer, 3 fields | 0.4 |
| P-M2-005 | S24 | SO-LO-05 Execute/Agreement → DSN-API-SO-LO-05 | POST /consumer-loans/{id}/agreement, 4 fields | 0.4 |
| P-M2-006 | S24 | SO-LO-06 Control → DSN-API-SO-LO-06 | PUT /consumer-loans/{id}/control, 2 fields | 0.4 |
| P-M2-007 | S17 | SD-LO `REALIZED_BY` DSN-APP-SD-LO | one component per domain, composing the six APIs | 0.4 |
| P-M2-008 | S32 | DSN-APP-SD-LO `DEPLOYED_AS` DSN-DEP-SD-LO | one deployment, environment and platform undecided | 0.4 |
| P-M2-009 | S24 | SO-CA-01 Evaluate → DSN-API-SO-CA-01 | POST /credit-assessments, 6 fields | 0.4 |
| P-M2-010 | S24 | SO-CA-02 Retrieve → DSN-API-SO-CA-02 | GET /credit-assessments/{id}, 5 fields | 0.4 |
| P-M2-011 | S17 | SD-CA `REALIZED_BY` DSN-APP-SD-CA | one component per domain, composing the two APIs | 0.4 |
| P-M2-012 | S32 | DSN-APP-SD-CA `DEPLOYED_AS` DSN-DEP-SD-CA | one deployment | 0.4 |

**Conventions, marked.** **M2-C1** — reference paths: resource is the kebab-case plural of the asset-type name; Initiate/Evaluate → POST on the collection; Retrieve → GET on the instance; Update → PATCH on the instance; Execute with a qualifier → POST on the qualifier sub-resource (guide check 2, v0.5.7); Control → PUT on the instance's `control` action; payload = input ∪ output attributes. **M2-C2** — the id convention has no interface, so APIs are composed directly under the component. **M2-C3** — a target deployment carries `component_id` only.

**M2.2 self-check.** The step-2 decision procedure, run over the design as if it were an export, finds every reference API at decision 1 for its own operation: check 2 passes by construction, check 3 passes for the two qualifier operations (`/offer`, `/agreement`) and is neutral for the rest, check 4 is 100 % for all eight. Two cross candidates appear — Update against the control API (2/4) and Control against the PATCH API (2/2) — and lose to the own API on overlap and ratio under the v0.5.7 contention rule; they are the same Control-is-a-subset-of-Update shape H2 run 2 found in real data.

#### Tests

| # | Expected | Observed | Verdict |
|---|---|---|---|
| M2.1 | records typed as design: `status: proposed`, `created_by` names the pattern source, confidence low, rationale states a target design from BIAN's container pattern | all twelve: `proposed`, 0.4, `created_by` = "bian-container-pattern [SAPG] §3.5 (REST mapping) + §4.1 … executor fable-executor/2026-10-22", rationale begins "TARGET DESIGN, not a mapping:"; design instances `planned` in exports marked `DESIGN-PROPOSAL` | **holds** |
| M2.2 | each API's path/method follows the REST mapping from action term and qualifier | table above; self-check decision 1 for all eight | **holds** |
| M2.3 | trace CAP-LEND down on the approved document stops at SD-LO; with `--status approved,proposed` and the design exports it reaches DSN-DEP-SD-LO | approved only: `CAP-LEND -SUPPORTED_BY-> SD-LO (LN-001)`, chain ends. With design: `… -REALIZED_BY-> DSN-APP-SD-LO 'Consumer Loan service (target)' (P-M2-007) -DEPLOYED_AS-> DSN-DEP-SD-LO (P-M2-008)` | **exact** |
| M2.4 | no `DEPLOYED_ON`, no `MAPPED_TO`; S36 / S50 absent | none of the four relationships appears; the log records each as "no proposal — nothing to name" | **holds** |
| M2.5 | `sdmm-eval` over the design gold: 12 of 12 | `OVERALL 12 12 12 0 0 1.00 1.00 1.00` | **holds** |

```
$ python -m sdmm.graph check a1 a2 m2-design-a3.json m2-design-a4.json m2-mappings-given.json m2-proposals.json
OK: level A1; OK: level A2; OK: level A3 (synthetic-bank-lending-a3-TARGET-DESIGN); OK: level A4 (…-a4-TARGET-DESIGN); OK: mappings #1; OK: mappings #2
$ python -m sdmm.validate --strict m2-proposals.json
WARNING ×12 (required evidence kinds); OK (with warnings)
$ python -m sdmm.evaluate examples/digital-lending/m2-gold-design.json --proposals examples/digital-lending/m2-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_AS         2    2   2   0   0   1.00  1.00  1.00
IMPLEMENTED_BY      8    8   8   0   0   1.00  1.00  1.00
REALIZED_BY         2    2   2   0   0   1.00  1.00  1.00
OVERALL            12   12  12   0   0   1.00  1.00  1.00
```

#### Findings

| # | Where | What happened | Proposed change |
|---|---|---|---|
| 1 | case convention, `sdmm-eval` | the scorer keys on ids, so M2.5 scores the *shape* of the design (one component, one API per operation, one deployment) and not the REST forms; the gold's rationales allow alternatives ("PUT or PATCH", "PUT …/offer (or POST on the sub-resource)") that an id-based score never tests | either put `method` and `path` into the design gold as attributes of the DSN-API records and have the case check them (M2.2 by equality), or state in the convention which form is canonical. As it stands M2.2 is checked by rule (the self-check), not by the gold |
| 2 | design gold vs README | `m2-gold-design.json` records are `status: approved` (so `sdmm-eval` can score them) while the README and case say "all `proposed`, confidence low" | README/case: "approved in the gold so the scorer counts them; the executor's copies are `proposed`". One line |
| 3 | guide §3–§4 | the guide has no design mode: §2 forbids inventing instances, which is right for mapping, yet M2 requires generating them; the executor relied on the case text alone | guide: a short *Design targets* section — when a level has no export, the executor may generate `planned` instances from a named pattern under a fixed id convention, in a separate export marked as design, with every arrow `proposed` at low and labelled; never a `DEPLOYED_ON` or `MAPPED_TO` without an observed target |
| 4 | S24 reference form | Control's payload (reference + status) is a subset of Update's; in the design the two are told apart only by path (`/control` vs the instance). Built estates will reproduce the H2 contention case | the design should give Control a distinguishing field (e.g. `control_action`) — a design finding, recorded for the architect rather than a plan change |
| 5 | case M2.3 | the test loads the design exports to trace into A3/A4; a reader could take the trace as evidence that the chain exists | `sdmm-graph trace` could print the source-system label of a level export whose `source_system` starts with `DESIGN-PROPOSAL`, or mark `planned` instances in the tree, so a design hop is visibly not an observed one |

#### No-proposal register

| Plan ID | Why no proposal |
|---|---|
| S33 `DEPLOYED_ON` | no platform instance exists; naming one would invent an instance with no source |
| S30 `MAPPED_TO`, S20 | no data entity exists; a target entity from the control record's attributes would be a further design step the convention does not define |
| S36, S50 | no platform, no DBMS |
| S25, S41 | no application service, no technology service |
| S01, S02, S04, S12 | given (LN-001…008); re-derivations agree |

**Summary.** M2 passes all five checks, and it does so by not pretending: the plan maps nothing below A2 here because nothing exists, and the executor says so. What it delivers instead is a target design generated from BIAN's container pattern, scored 12 of 12 against the architect's reference, and labelled at every point — in the exports, the records, the confidence and the rationale — as design rather than mapping. The boundary is a single sentence: a mapping connects two things that were observed; everything in `m2-design-*.json` was derived, so the arrows to it are proposals about what to build, not statements about what is. The suite's seven cases are now all executed.

### M2 — actions taken on the findings (v0.5.9)

| Finding | Action |
|---|---|
| 1 — scorer tests shape, not REST form | The case names the canonical REST forms; M2.2 is judged against that table (a record-level `method`/`path` would need a schema change — not made) |
| 2 — guide has no design mode | Guide §3 gains *Design targets* — the one situation in which the executor may create instances, and the labelling that makes them unmistakable |
| 3 — gold status | Example README states why the design gold is `approved` |
| 4 — Control payload a subset of Update's | `SO-LO-06` gains `control_action` / `control_reason`; the same shape in H2 is left as run data |
| 5 — design hops invisible in traces | `sdmm-graph trace` marks any `planned` instance `[DESIGN — planned, not observed]` |

**M2 is complete and the suite is closed:** seven cases, eight runs.

## Plan coverage after the suite — all 69 entries

Built from `metamodel/new-mappings.json` and the eight inference logs; counts are attempts logged under each plan ID across all runs (E1 and E2 are query-only and log commands, not plan IDs). *n/a* rows were never candidates for a proposal by the plan's own decision. *Not exercised* rows need a case whose exports carry their entities — **C1, C2 and C3 (`examples/trade-finance/`) were authored for exactly these 42 rows**; this table is regenerated after they run.

| Verdict | Entries |
|---|---|
| not exercised | 30 |
| n/a | 19 |
| report-only by rule | 7 |
| refusals only | 5 |
| validated with findings | 4 |
| validated | 4 |

| ID | Connection | Decision | Step | Plan conf. | Exercised in | hit / false / miss / no-proposal | Verdict |
|---|---|---|---|---|---|---|---|
| B01 | BusinessCapability → ServiceDomain (aligns to) | not encodable | 3 | low | — | — | n/a — not encodable |
| B02 | BusinessArea → BusinessDomain (contains) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B03 | BusinessDomain → ServiceDomain (contains) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B04 | ServiceDomain → FunctionalPattern (applies) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B05 | ServiceDomain → AssetType (manages) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B06 | ServiceDomain → ControlRecord (governs) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B07 | ControlRecord → BehaviorQualifier (is partitioned by) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B08 | ControlRecord → BusinessObject (attributes typed by) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B09 | ServiceDomain → ServiceGroup (offers) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B10 | ServiceGroup → ServiceOperation (contains) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B11 | ServiceOperation → ControlRecord (acts on) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B12 | ServiceDomain → ServiceDomain (connects to) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B13 | BusinessScenario → ServiceOperation (sequences) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B14 | Wireframe → ServiceDomain (depicts) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| B15 | SemanticAPI → ServiceDomain (derived from) | bian internal | 0 | high | — | — | n/a — inside A2; encoded as an A2 relationship constraint and checked by `sdmm-graph check` on every A2 export |
| S01 | BusinessCapability → ServiceDomain (SUPPORTED_BY) | registry rule | 3 | medium | H1, H2, H2 r2, M0, M1, M2 | 4 / 1 / 0 / 9 | **validated with findings** — 1 false / 0 missed, each with a named cause, fixed in the guide or data |
| S02 | ValueStream → BusinessScenario (ALIGNED_TO) | registry rule | 4 | medium | H1, H2, H2 r2, M0, M1, M2 | 1 / 0 / 0 / 7 | **validated** — every gold arrow hit, no false |
| S03 | ValueStreamStage → BusinessScenario (candidate) | derived path | 4 | low | — | — | **not exercised** — no case carried the data |
| S04 | BusinessProcess → ServiceDomain (USES_DOMAIN) | registry rule | 3 | medium | H1, H2, H2 r2, M0, M1, M2 | 1 / 0 / 0 / 8 | **validated** — every gold arrow hit, no false |
| S05 | BusinessProcess → BusinessScenario (candidate) | historical method | 4 | low | — | — | n/a — historical method |
| S06 | BusinessActivity → ServiceOperation (candidate) | institution only | 4 | medium | H1, H2, H2 r2, M1 | 0 / 0 / 0 / 7 | report-only by rule — reported as a candidate, never proposed |
| S07 | BusinessActivity → ServiceDomain (candidate) | derived path | 3 | medium | — | — | **not exercised** — no case carried the data |
| S08 | BusinessService → ServiceDomain (candidate) | institution only | 5 | low | — | — | **not exercised** — no case carried the data |
| S09 | BusinessService → ServiceOperation (candidate) | institution only | 4 | low | — | — | **not exercised** — no case carried the data |
| S10 | BusinessActor → BusinessScenario (candidate) | not a mapping |  | low | — | — | n/a — not a mapping |
| S11 | BusinessRole → BusinessScenario (candidate) | not a mapping |  | low | — | — | n/a — not a mapping |
| S12 | BusinessObject → BusinessObject (ALIGNED_TO) | registry rule | 4 | medium | H1, H2, H2 r2, M1 | 0 / 0 / 0 / 5 | refusals only — no gold arrow to reach in those cases |
| S13 | BusinessRequirement → ServiceDomain (candidate) | institution only | 3 | low | — | — | **not exercised** — no case carried the data |
| S14 | BusinessRequirement → ServiceOperation (candidate) | institution only | 3 | low | — | — | **not exercised** — no case carried the data |
| S15 | BusinessArea → ApplicationComponent (candidate) | derived path | 3 | high | — | — | **not exercised** — no case carried the data |
| S16 | BusinessDomain → ApplicationComponent (candidate) | derived path | 3 | high | — | — | **not exercised** — no case carried the data |
| S17 | ServiceDomain → ApplicationComponent (REALIZED_BY) | registry rule | 3 | high | H1, H2, H2 r2, M0, M1, M2 | 18 / 0 / 0 / 28 | **validated** — every gold arrow hit, no false |
| S18 | FunctionalPattern → ApplicationFunction (candidate) | institution only | 4 | low | — | — | **not exercised** — no case carried the data |
| S19 | AssetType → DataEntity (candidate) | institution only | 4 | low | — | — | **not exercised** — no case carried the data |
| S20 | ControlRecord → DataEntity (candidate) | candidate rule | 4 | high | H1, H2, H2 r2, M1, M2 | 0 / 0 / 0 / 62 | report-only by rule — reported as a candidate, never proposed |
| S21 | ControlRecord → ApplicationFunction (candidate) | candidate rule | 4 | medium | — | — | **not exercised** — no case carried the data |
| S22 | ServiceGroup → ApplicationService (candidate) | derived path | 3 | medium | M1 | 0 / 0 / 0 / 1 | refusals only — no gold arrow to reach in those cases |
| S23 | ServiceGroup → ApplicationInterface (candidate) | derived path | 3 | medium | H1, H2, H2 r2, M0, M1 | 0 / 0 / 0 / 8 | refusals only — no gold arrow to reach in those cases |
| S24 | ServiceOperation → APIOperation (IMPLEMENTED_BY) | registry rule | 2 | high | H1, H2, H2 r2, M0, M1, M2 | 54 / 0 / 8 / 387 | **validated with findings** — 0 false / 8 missed, each with a named cause, fixed in the guide or data |
| S25 | ServiceOperation → ApplicationService (candidate) | candidate rule | 3 | high | H1, H2, H2 r2, M0, M1, M2 | 0 / 0 / 0 / 10 | report-only by rule — reported as a candidate, never proposed |
| S26 | BehaviorQualifier → APIOperation (candidate) | derived path | 2 | high | — | — | **not exercised** — no case carried the data |
| S27 | BehaviorQualifier → DataEntity (candidate) | derived path | 4 | medium | — | — | **not exercised** — no case carried the data |
| S28 | BusinessScenario → ApplicationService (candidate) | candidate rule | 3 | medium | — | — | **not exercised** — no case carried the data |
| S29 | BusinessScenario → ApplicationComponent (candidate) | candidate rule | 3 | medium | — | — | **not exercised** — no case carried the data |
| S30 | BusinessObject → DataEntity (MAPPED_TO) | registry rule | 4 | high | H1, H2, H2 r2, M1, M2 | 14 / 0 / 1 / 54 | **validated with findings** — 0 false / 1 missed, each with a named cause, fixed in the guide or data |
| S31 | BusinessObjectAttribute → DataEntity (candidate) | derived path | 4 | high | — | — | **not exercised** — no case carried the data |
| S32 | ApplicationComponent → Deployment (DEPLOYED_AS) | registry rule | 1 | high | H1, H2, H2 r2, M0, M1, M2 | 21 / 0 / 0 / 7 | **validated** — every gold arrow hit, no false |
| S33 | ApplicationComponent → InfrastructureComponent (DEPLOYED_ON) | registry rule | 1 | high | H1, H2, H2 r2, M0, M1, M2 | 18 / 1 / 0 / 10 | **validated with findings** — 1 false / 0 missed, each with a named cause, fixed in the guide or data |
| S34 | ApplicationComponent → Node (candidate) | conditional rule | 1 | low | — | — | **not exercised** — no case carried the data |
| S35 | ApplicationComponent → Device (candidate) | institution only | 1 | low | — | — | **not exercised** — no case carried the data |
| S36 | ApplicationComponent → SystemSoftware (candidate) | subsumed | 1 | high | H1, H2, H2 r2, M0, M1, M2 | 0 / 0 / 0 / 6 | n/a — subsumed |
| S37 | ApplicationComponent → CommunicationNetwork (candidate) | institution only | 1 | low | — | — | **not exercised** — no case carried the data |
| S38 | ApplicationComponent → Path (candidate) | institution only | 1 | low | — | — | **not exercised** — no case carried the data |
| S39 | ApplicationComponent → Artifact (candidate) | conditional rule | 1 | medium | — | — | **not exercised** — no case carried the data |
| S40 | ApplicationComponent → DeploymentEnvironment (candidate) | derived path | 3 | high | H1, H2, H2 r2, M0, M1 | 0 / 0 / 0 / 5 | refusals only — no gold arrow to reach in those cases |
| S41 | ApplicationService → TechnologyService (candidate) | conditional rule | 1 | medium | H1, H2, H2 r2, M1, M2 | 0 / 0 / 0 / 6 | report-only by rule — reported as a candidate, never proposed |
| S42 | ApplicationService → TechnologyInterface (candidate) | derived path | 3 | low | — | — | **not exercised** — no case carried the data |
| S43 | ApplicationInterface → TechnologyInterface (candidate) | institution only | 1 | low | — | — | **not exercised** — no case carried the data |
| S44 | ApplicationInterface → TechnologyService (candidate) | institution only | 1 | low | — | — | **not exercised** — no case carried the data |
| S45 | ApplicationFunction → TechnologyService (candidate) | conditional rule | 1 | medium | M1 | 0 / 0 / 0 / 1 | report-only by rule — reported as a candidate, never proposed |
| S46 | ApplicationFunction → SystemSoftware (candidate) | derived path | 3 | low | — | — | **not exercised** — no case carried the data |
| S47 | APIOperation → Deployment (candidate) | derived path | 3 | high | H1, H2, H2 r2, M0, M1 | 0 / 0 / 0 / 5 | refusals only — no gold arrow to reach in those cases |
| S48 | APIOperation → TechnologyInterface (candidate) | derived path | 3 | medium | — | — | **not exercised** — no case carried the data |
| S49 | DataEntity → Artifact (candidate) | conditional rule | 1 | medium | H1, H2, M1 | 0 / 0 / 0 / 3 | report-only by rule — reported as a candidate, never proposed |
| S50 | DataEntity → SystemSoftware (candidate) | institution only | 1 | medium | H1, H2, H2 r2, M0, M1, M2 | 0 / 0 / 0 / 26 | report-only by rule — reported as a candidate, never proposed |
| S51 | Event → TechnologyService (candidate) | institution only | 1 | low | — | — | **not exercised** — no case carried the data |
| S52 | SolutionBuildingBlock → InfrastructureComponent (candidate) | derived path | 3 | medium | — | — | **not exercised** — no case carried the data |
| S53 | SolutionBuildingBlock → Deployment (candidate) | derived path | 3 | medium | — | — | **not exercised** — no case carried the data |
| S54 | SolutionBuildingBlock → Node (candidate) | derived path | 3 | low | — | — | **not exercised** — no case carried the data |

### C1 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.10 including §4c. **Given.** `c1-mappings-given.json` — 22 approved registry arrows, everything except object alignment; the four trade-finance exports. **Gold.** `c1-gold-mappings.json` and `c1-gold-candidates.json` (and `mappings.json`, `candidates.json`) were not opened until phase 5. **Files.** `examples/trade-finance/c1-proposals.json` (2 registry records), `c1-candidates.json` (24 candidate reports, `relationship` = plan ID, `created_by: candidate_rule:<ID>`), `c1-inference-log.json` (57 attempts, 21 plan IDs).

**Readings and conventions, marked.** **C1-R1 (S13)** — a requirement whose `applies_to` names an *activity* closes over that activity's S06/S07 chain, not over the parent process's S04 arrows; the parent of ACT-T3 and ACT-T4 (PRC-LC-ISSUE) uses two domains, so the process route would give REQ-02 and REQ-03 two domains each. **C1-C1 (S09)** — the plan's threshold (≥ 50 %, ≥ 2) alone admits five service → operation pairs; only each service's unique best is reported, as the step-2 and S30 rules already do. **S08** — two domains are the full exported A2 landscape, so the step-5 rule's first condition holds and the ranking is not vacuous; the threshold (≥ 2 non-generic shared concepts, lead ≥ 1) was applied and met for both services. **S03** — `apply ≈ initiate` was used for the first stage (not in the guide's synonym list).

#### Registry proposals (`c1-proposals.json`)

| Proposal | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| P-C1-001 | S12 | BO-LC `ALIGNED_TO` BBO-LC | 4 | 0.6 | 7/8 BIAN attributes matched by name (applicant_reference, beneficiary_reference, credit_amount, currency, expiry_date, application_status, issuance_reference); `letter_of_credit_reference` unmatched — the bank's `lc_number` has no alias in the export; one-to-one fixpoint |
| P-C1-002 | S12 | BO-DOCSET `ALIGNED_TO` BBO-DOCSET | 4 | 0.6 | **3/5** (document_set_reference, compliance_outcome, discrepancies); `letter_of_credit_reference` (bank: `lc_number`) and `checked_at` (bank: `presented_at`) unmatched; cross pairs 0/8 and 0/5 |

#### Candidate-rule reports (`c1-candidates.json`)

| Reports | Plan ID | Connections | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-C1-001…004 | S06 | ACT-T1→SO-LC-01, ACT-T2→SO-LC-02, ACT-T3→SO-DC-01, ACT-T4→SO-LC-03 | 4 assigned, **1 used** | 0.6 | `invokes` on each activity states the pair; the activity name agrees with the action term |
| C-C1-005…008 | S07 | ACT-T1→SD-LC, ACT-T2→SD-LC, ACT-T3→SD-DC, ACT-T4→SD-LC | 3 | 0.6 | each cites its S06 report and the B10/B09 composition |
| C-C1-009, 011, 013 | S13 | REQ-01→SD-LC (over given S04 TF-103); REQ-02→SD-DC and REQ-03→SD-LC (over S06 C-C1-003/004 and S07, reading C1-R1) | 3 | 0.4 | `applies_to` → S04 for the process-level requirement; → S06/S07 for the two activity-level ones |
| C-C1-010, 012 | S14 | REQ-02→SO-DC-01, REQ-03→SO-LC-03 | 3 | 0.4 | `applies_to` → S06 reports; **REQ-01 gets no S14** — it applies to a process (C1.5) |
| C-C1-014, 015 | S09 | BSV-LC-APP→SO-LC-01 (7/7), BSV-DOC-CHECK→SO-DC-01 (4/4) | 4 | 0.4 | inputs ∪ outputs vs the operation's I/O; unique best. Suppressed above threshold (C1-C1): BSV-LC-APP→SO-LC-04 5/7, →SO-LC-02 4/7; BSV-DOC-CHECK→SO-DC-02 3/4 |
| C-C1-016, 017 | S08 | BSV-LC-APP→SD-LC, BSV-DOC-CHECK→SD-DC | 5 | 0.4 | shared non-generic concepts with the asset type and aliases; runner-up at least one behind, both services |
| C-C1-018…020 | S03 | VSS-T1, VSS-T2, VSS-T3 → BS-LC | 3 (from approved S02 TF-102) | 0.4 | stage verb ↔ operation action term in sequence: apply ≈ Initiate (marked), check ≈ Evaluate, issue = Issuance alias |
| C-C1-021…024 | S15, S16 | BA-TRADE→APP-LC/APP-DOC; BD-TRADE→APP-LC/APP-DOC | 3 | 0.8 | A2 composition area → domain → service domain (B02, B03) over the given S17 arrows TF-108/109; derived paths reported as candidates, never as registry arrows |

#### sdmm-eval (both files)

```
$ python -m sdmm.graph check examples/trade-finance/a*.json examples/trade-finance/c1-mappings-given.json examples/trade-finance/c1-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2
$ python -m sdmm.validate --strict examples/trade-finance/c1-proposals.json
WARNING ×2 (bian_release required; evidence kinds); OK (with warnings)

$ python -m sdmm.evaluate examples/trade-finance/c1-gold-mappings.json --proposals examples/trade-finance/c1-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
ALIGNED_TO          2    2   2   0   0   1.00  1.00  1.00
OVERALL             2    2   2   0   0   1.00  1.00  1.00

$ python -m sdmm.evaluate examples/trade-finance/c1-gold-candidates.json --proposals examples/trade-finance/c1-candidates.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
S03                 3    3   3   0   0   1.00  1.00  1.00
S06                 4    4   4   0   0   1.00  1.00  1.00
S07                 4    4   4   0   0   1.00  1.00  1.00
S08                 2    2   2   0   0   1.00  1.00  1.00
S09                 2    2   2   0   0   1.00  1.00  1.00
S13                 3    3   3   0   0   1.00  1.00  1.00
S14                 2    2   2   0   0   1.00  1.00  1.00
S15                 2    2   2   0   0   1.00  1.00  1.00
S16                 2    2   2   0   0   1.00  1.00  1.00
OVERALL            24   24  24   0   0   1.00  1.00  1.00
```

#### Tests

| # | Expected | Observed | Verdict |
|---|---|---|---|
| C1.1 | S12 2 of 2 at medium, attribute pairs named | 2 of 2 at 0.6; pairs named; scores 7/8 and **3/5** (the case text says 4/5 — finding 1) | **holds** |
| C1.2 | S06 / S07 / S13 / S14 = 4 / 4 / 3 / 2, each derived report citing its S06 or S04 arrow | 4 / 4 / 3 / 2; every S07, S13, S14 report names the C-C1 or TF record it closed over | **holds** |
| C1.3 | S09 2 of 2 at medium; S08 2 of 2 at low **or** a reasoned single-candidate refusal | S09 2 of 2 at **low** (the plan's band; the case says medium — finding 2); S08 2 of 2 at low with the full-landscape reading stated | **holds** |
| C1.4 | S15 / S16 2 / 2 at high, derived, not registry | 2 / 2 at 0.8 in the candidates file only | **holds** |
| C1.5 | ACTOR / ROLE nothing; REQ-01 no operation | S10, S11 logged as not-a-mapping, no report; REQ-01 → no S14, its S13 only | **holds** |

**Pass criteria.** Registry F1 1.00; candidate precision 1.00, recall 1.00 (≥ 0.9 required); C1.5 holds.

#### Findings

| # | Plan ID | What happened | Why | Proposed change |
|---|---|---|---|---|
| 1 | S12, case, gold | the executor scores BO-DOCSET → BBO-DOCSET at 3/5; the case says 4/5 and the gold TF-106 rationale reads "lc_number = letter_of_credit_reference" | the architect applied a glossary alias the export does not carry; the case text itself says lc_number is *not* the reference, which is consistent with 7/8 but gives 3/5, not 4/5, for the document set | `export-conventions.json`: `A1.BusinessObject.attributes.field_aliases` (glossary term → BOM attribute), the A1 counterpart of the interface field aliases; S12 reads it. Fix the case cell to 3/5 or add the alias and make it 8/8 and 4/5 |
| 2 | S03, S09, S13, S14 (gold bands) | the gold reports carry 0.6 where the plan says low (0.4); the case text also says "S09 at medium" | the gold was authored at medium for derivations whose inputs are medium or approved; the plan's bands for institution-only rows are low by default | decide per row: either raise the plan bands for S09 (a structural match at 100 % is not low evidence) and for S13/S14/S03 when derived over approved inputs, or correct the gold to the plan. The scorer ignores confidence, so this is a consistency fix, not a score change |
| 3 | S13 | `data_needed` says "applies_to → S04 instances"; the gold's REQ-02 and REQ-03 targets follow the activity's own operation (one domain each), which the S04 route cannot produce when the parent process uses two domains | requirements on activities are finer than S04 | S13 `data_needed`: "process-level `applies_to` → S04; activity-level `applies_to` → S06/S07 (the activity's operation's domain)" — reading C1-R1 |
| 4 | S09 | the threshold alone admits five pairs; three would have been false | small I/O sets overlap generic attributes (reference, status, amount) across sibling operations | S09 `data_needed`: add "unique best match per service, one-to-one as S30" (C1-C1); same clause as every other attribute-overlap rule now has |
| 5 | S06 | filed by the `invokes` key at step 1 grade while the plan still assigns step 4 | the plan's `data_needed` already names `invokes` first | S06 `fill_step` 1 with step 4 as the fallback when `invokes` is absent (M1 finding 6, still open) |
| 6 | S03, guide step 4 synonyms | `apply ≈ initiate` was needed for the first stage and is not in the guide's list | the list has capture, validate, execute, confirm | add apply/submit/request ≈ initiate/create to the S02/S03 synonym list |
| 7 | S08, guide step 5 | the rule's two conditions ("full exported landscape" **or** "≥ 3 domains") disagree when the landscape has two domains; the case flagged exactly this | the first condition was written for the A1 side where the export may be partial | state the precedence: a complete landscape qualifies at any size; the ≥ 3 floor applies only when the export is known to be a selection |

#### No-proposal register

| Plan ID | Instances | Why |
|---|---|---|
| S09 | BSV-LC-APP → SO-LC-04 (5/7), SO-LC-02 (4/7); BSV-DOC-CHECK → SO-DC-02 (3/4) | above threshold but not the service's best — suppressed by C1-C1; would be reported under the rule as written |
| S14 | REQ-01 | applies to a process; S14 closes over activity-level S06 only |
| S12 | BO-LC → BBO-DOCSET, BO-DOCSET → BBO-LC | 0/5, 0/8 |
| S10, S11 | ACTOR-TRADE-OPS, ROLE-TRADE-OFFICER | not a mapping (plan) |
| S05 | — | historical method; not in C1's rows |
| S01, S02, S04, S17, S24, S30, S32, S33/S34/S35 | the 22 given arrows | given |

**Summary.** The first coverage case puts nine previously untested candidate rows and the one untested registry row through the steps, and all 26 targets are reached with nothing false: registry 2 of 2, candidates 24 of 24. Three readings had to be stated where the plan or guide is loose — activity-level requirements close through their own operation, service-to-operation matching must be one-to-one, two domains are a full landscape — and each is a one-line fix to `data_needed` or the guide. The one data gap is the A1 side's missing glossary alias, which is why the document-set alignment scores 3 of 5 rather than the architect's 4 of 5.

### C1 — actions taken on the findings (v0.5.11)

| Finding | Action |
|---|---|
| 1 — glossary aliases | `A1.BusinessObject.attributes.field_aliases` convention; applied to the estate (`lc_number → letter_of_credit_reference`) |
| 2 — gold bands | Every candidate gold confidence set to the plan's band for its ID |
| 3 — plan data | S13 activity route and S09 one-to-one written into `data_needed`; S06 moved to step 1 when `invokes` is present |
| 4 — synonyms / precedence | apply, submit, check, issue, release added; full landscape takes precedence over the three-domain floor |

### C2 — results (2026-10-23, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.11 including §4c. **Given.** `c2-mappings-given.json` — 14 approved arrows (A1→A2 and A3→A4); the four trade-finance exports. **Gold.** `c2-gold-mappings.json` and `c2-gold-candidates.json` (and `mappings.json`, `candidates.json`) were not opened until phase 5. **Files.** `examples/trade-finance/c2-proposals.json` (10 registry records), `c2-candidates.json` (32 candidate reports over twelve plan IDs, `relationship` = plan ID), `c2-inference-log.json` (90 attempts, 21 plan IDs).

#### Registry proposals (`c2-proposals.json`)

| Proposal | Plan ID | Connection | Step | Confidence | Working |
|---|---|---|---|---|---|
| P-C2-001…004 | S24 | SO-LC-01 Initiate → API-LC-01 POST /letters-of-credit (7/7); SO-LC-02 Update/Amendment → API-LC-02 PATCH …/amendment (check 3 **pass** via alias, 5/5); SO-LC-03 Execute/Issuance → API-LC-03 PUT …/issuance (pass, 3/3); SO-LC-04 Retrieve → API-LC-04 GET (6/6) | 2 | 0.8 | gate via {credit, lc, letter}; all decision 1 |
| P-C2-005, 006 | S24 | SO-DC-01 Evaluate → API-DC-01 POST /document-sets/{id}/check (4/4; `check` is no qualifier, so check 3 neutral); SO-DC-02 Retrieve → API-DC-02 GET (4/4) | 2 | 0.8 | gate via {doc, document, set}; decision 1 |
| P-C2-007, 008 | S17 | SD-LC `REALIZED_BY` APP-LC; SD-DC `REALIZED_BY` APP-DOC | 3 | 0.8 | closure over the step-2 proposals; strongest input high |
| P-C2-009, 010 | S30 | BBO-LC `MAPPED_TO` ENT-LC 8/8; BBO-DOCSET `MAPPED_TO` ENT-DOCSET 5/5 | 4 | 0.8 | one-to-one fixpoint; BBO-LC → ENT-LC-AMEND 3/8 below threshold |

#### Candidate-rule reports (`c2-candidates.json`)

| Reports | Plan ID | Connections | Step | Confidence | Working |
|---|---|---|---|---|---|
| C-C2-003…008 | S25 | SO-LC-01…04 → SVC-LC; SO-DC-01, 02 → SVC-DOC | 3 | 0.8 | each step-2 proposal's API is composed in the interface of that service |
| C-C2-009…012 | S22, S23 | SG-LC → SVC-LC / IFC-LC; SG-DC → SVC-DOC / IFC-DOC | 3 | 0.6 | derived paths over the group's operations' APIs |
| C-C2-013, 014 | S20 | CR-LC → ENT-LC **8/9** (`amendment_reference` absent); CR-DC → ENT-DOCSET 5/5 | 4 | 0.8 | one-to-one; **CR-LC → ENT-LC-AMEND 4/9 = 0.44, below threshold (C2.6)** |
| C-C2-015…018 | S31 | BBOA-CREDIT-AMOUNT, BBOA-EXPIRY → ENT-LC; BBOA-COMPLIANCE, BBOA-DISCREPANCIES → ENT-DOCSET | 4 | 0.8 | through the object's S30 arrow only; **`credit_amount` is also a column of `lc_amendments` and is not reported there (C2.5)** |
| C-C2-019…021 | S19 | AT-LC → ENT-LC ({credit, letter}), AT-LC → **ENT-LC-AMEND** ({lc}), AT-DOCSET → ENT-DOCSET ({document, set}) | 4 | 0.4 | asset tokens and aliases in entity names (C2.6: the `lc` alias reaches the amendment table) |
| C-C2-022 | S27 | BQ-AMENDMENT → ENT-LC-AMEND | 4 | 0.6 | alias `amendment` in `lc_amendments`; **not `letters_of_credit`** (C2.3); BQ-ISSUANCE names no table |
| C-C2-001, 002 | S26 | BQ-AMENDMENT → API-LC-02; BQ-ISSUANCE → API-LC-03 | 2 | 0.8 | the two step-2 pairs where check 3 passed (C2.3) |
| C-C2-023, 025, 027 | S18 | FP-FULFIL → FN-LC-CAPTURE, FN-LC-ISSUE; FP-ASSESS → FN-DOC-CHECK | 4 assigned, **3 used** | 0.4 | `exposed_through` → step-2 proposals → operations → domain → `functional_pattern` |
| C-C2-024, 026, 028 | S21 | CR-LC → FN-LC-CAPTURE (**through three APIs**, C2.2), CR-LC → FN-LC-ISSUE, CR-DC → FN-DOC-CHECK | 4 assigned, **3 used** | 0.6 | `exposed_through` → step-2 proposals → operations `access` the control record (B11) |
| C-C2-029…032 | S28, S29 | BS-LC → SVC-LC, SVC-DOC; BS-LC → APP-LC, APP-DOC | 3 | 0.6 | the scenario's three operations through S25 / through S17 over their domains (C2.4) |

#### sdmm-eval (both files)

```
$ python -m sdmm.graph check examples/trade-finance/a*.json examples/trade-finance/c2-mappings-given.json examples/trade-finance/c2-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2
$ python -m sdmm.validate --strict examples/trade-finance/c2-proposals.json
WARNING ×10 (required evidence kinds); OK (with warnings)

$ python -m sdmm.evaluate examples/trade-finance/c2-gold-mappings.json --proposals examples/trade-finance/c2-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
IMPLEMENTED_BY      6    6   6   0   0   1.00  1.00  1.00
MAPPED_TO           2    2   2   0   0   1.00  1.00  1.00
REALIZED_BY         2    2   2   0   0   1.00  1.00  1.00
OVERALL            10   10  10   0   0   1.00  1.00  1.00

$ python -m sdmm.evaluate examples/trade-finance/c2-gold-candidates.json --proposals examples/trade-finance/c2-candidates.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
S18 3 3 3 0 0 1.00 1.00 1.00   S19 3 3 3 0 0   S20 2 2 2 0 0   S21 3 3 3 0 0   S22 2 2 2 0 0   S23 2 2 2 0 0
S25 6 6 6 0 0 1.00 1.00 1.00   S26 2 2 2 0 0   S27 1 1 1 0 0   S28 2 2 2 0 0   S29 2 2 2 0 0   S31 4 4 4 0 0
OVERALL            32   32  32   0   0   1.00  1.00  1.00
```

#### Tests

| # | Expected | Observed | Verdict |
|---|---|---|---|
| C2.1 | registry 10 of 10, no false | 10 of 10, none false; all six S24 at decision 1 | **holds** |
| C2.2 | S18 3, S21 3, each citing the APIs and operations closed over; FN-LC-CAPTURE reaches CR-LC through three APIs | 3 and 3; each report lists `exposed_through` and the P-C2 ids; FN-LC-CAPTURE via API-LC-01/02/04 | **holds** |
| C2.3 | S26 2 (amendment, issuance); S27 1 (`lc_amendments`), not `letters_of_credit` | S26 2; S27 1 on ENT-LC-AMEND only | **holds** |
| C2.4 | S28 2, S29 2 | 2 and 2 | **holds** |
| C2.5 | S31 4; `credit_amount` to `letters_of_credit` only | 4; the `lc_amendments` column logged as not reported | **holds** |
| C2.6 | ENT-LC-AMEND no S20/S30; S19 reaches it through `lc` | CR-LC → ENT-LC-AMEND 4/9 and BBO-LC → ENT-LC-AMEND 3/8 below threshold; S19 AT-LC → ENT-LC-AMEND via `lc` | **holds** |

**Pass criteria.** Registry F1 1.00; candidate precision 1.00, recall 1.00 (≥ 0.9 required). The gold's bands equal the plan's bands on every report, unlike C1.

#### Findings

| # | Plan ID | What happened | Proposed change |
|---|---|---|---|
| 1 | S18, S21 | both are filled by derivation — function → `exposed_through` APIs → step-2 proposals → operations → pattern / control record — yet the plan assigns step 4 | `fill_step` 3 for both; `data_needed` already describes the derivation. Step 4 (description match) remains the fallback when `exposed_through` is absent |
| 2 | S20 | CR-LC → ENT-LC-AMEND scored 4/9 = 0.44, close to the 50 % threshold; a control record with one more shared attribute would cross it, and only the one-to-one fixpoint would then keep the amendment table out | no change to the threshold; record that the fixpoint, not the threshold, is what separates a partition table from the main table — S27 is the rule that claims partitions (it did) |
| 3 | S24 gate | the asset-type name "Document Set" yields the token `set`, which is generic; it matched `document_sets` here but would match any `*_sets` table elsewhere | add common structural nouns (`set`, `record`, `item`, `list`) to the gate's stop list, or gate on the asset name's head noun and aliases only |
| 4 | S24 check 3 | `POST /document-sets/{id}/check` is an action sub-resource on a null-qualifier operation; check 3 is neutral because `check` is no qualifier, which is right, but the guide does not say that non-qualifier action segments are tolerated | guide check 3: "a path segment that is neither a qualifier nor a qualifier alias is ignored" |

#### No-proposal register

| Plan ID | Instances | Why |
|---|---|---|
| S24 | 14 gated pairs not filed (all in the log) | decision 3 (method or payload) or excluded one-to-one; the two cross-domain gates (SD-LC × APP-DOC, SD-DC × APP-LC) fail |
| S20, S30 | CR-LC / BBO-LC → ENT-LC-AMEND | 4/9, 3/8 below threshold |
| S31 | BBOA-CREDIT-AMOUNT → ENT-LC-AMEND | column present but not the object's S30 entity |
| S27 | BQ-ISSUANCE → any; BQ-AMENDMENT → ENT-LC | no alias token in the name |
| S19 | AT-DOCSET → ENT-LC, ENT-LC-AMEND; AT-LC → ENT-DOCSET | no token |
| S01, S02, S04, S12, S32, S33/S34/S35 | the 14 given arrows | given |

**Summary.** The application-internals case reaches every one of its 42 targets with nothing false and every band equal to the plan's. Twelve candidate rows that had never run now have working behind them, and the two negatives the case planted on the amendment table came out right for the right reasons: the attribute rules keep it out, the asset-alias and qualifier rules bring it in as a partition. The only plan corrections are two step labels and a stop-word.

### C2 — actions taken on the findings (v0.5.12)

| Finding | Action |
|---|---|
| 1 — S18 / S21 fill step | Moved to step 3 (derivation through `exposed_through` and S24) |
| 2 — partition tables | S20 reasoning states the fixpoint-not-threshold behaviour and the S27 claim |
| 3 — generic gate token | Structural nouns added to the gate's stop list |
| 4 — check 3 | A path segment that is neither a qualifier nor an alias is ignored |

### C3 — results (2026-10-23, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md` v0.5.12 including §4c. **Given.** `c3-mappings-given.json` — 17 approved arrows (A1→A2 and A2→A3); the four trade-finance exports. **Gold.** `c3-gold-mappings.json` and `c3-gold-candidates.json` (and `mappings.json`, `candidates.json`) were not opened until phase 5. **Files.** `examples/trade-finance/c3-proposals.json` (7 registry records), `c3-candidates.json` (45 candidate reports over eighteen plan IDs, `relationship` = plan ID), `c3-inference-log.json` (75 attempts, 29 plan IDs).

#### Registry proposals (`c3-proposals.json`) — `DEPLOYED_ON` logged by target entity

| Proposal | Plan row | Connection | Target entity | Records read | Confidence |
|---|---|---|---|---|---|
| P-C3-001, 004 | S32 | APP-LC `DEPLOYED_AS` DEP-LC-PROD; APP-DOC `DEPLOYED_AS` DEP-DOC-PROD | `A4.Deployment` | `deployed_as` + `component_id` | 0.8 |
| P-C3-003, 007 | **S33** | APP-LC, APP-DOC `DEPLOYED_ON` SYS-RUNTIME-TF | `A4.SystemSoftware` (S36 subsumed) | `deployed_on` + `hosts` | 0.8 |
| P-C3-002, 006 | **S34** | APP-LC, APP-DOC `DEPLOYED_ON` NODE-TF-PROD | `A4.Node` | `deployed_on` + `hosts` + `platform_id` | 0.8 |
| P-C3-005 | **S35** | APP-DOC `DEPLOYED_ON` DEV-SCAN-01 | `A4.Device` | `deployed_on` + `hosts` | 0.8 |

#### Candidate-rule reports (`c3-candidates.json`)

| Reports | Plan ID | Connections | Step | Confidence | Key or arrow read |
|---|---|---|---|---|---|
| 2 | S37 | APP-LC, APP-DOC → NET-TF | 1 | 0.4 | `network_zone`; corroborated by `NET-TF.connects` naming the hosting node and device |
| 1 | S38 | APP-DOC → PATH-TF-01 | 1 | 0.4 | `PATH-TF-01.carries` |
| 2 | S39 | APP-LC → ART-LC-IMG; APP-DOC → ART-DOC-IMG | 1 | 0.6 | `built_as` + `of_component`; **ART-DOC-STORE is nobody's build — no report (C3.4)** |
| 3 | S41 | SVC-LC → TS-QUEUE, TS-GATEWAY; SVC-DOC → TS-GATEWAY | 1 | 0.6 | `consumes`; **TS-SIGNING / TS-OCR are consumed by functions, not services — no S41 (C3.4)** |
| 2 | S43 | IFC-LC, IFC-DOC → TI-INGRESS | 1 | 0.4 | `exposed_through` + `exposes`; **TI-TOPIC-LC exposes nothing — no S43, hence no S48 (C3.4)** |
| 2 | S45 | FN-LC-ISSUE → TS-SIGNING; FN-DOC-CHECK → TS-OCR | 1 | 0.6 | `consumes` on the function; FN-LC-CAPTURE consumes nothing |
| 1 | S49 | ENT-DOCSET → ART-DOC-STORE | 1 | 0.6 | `stored_in` naming an `A4.Artifact` |
| 3 | S50 | ENT-LC, ENT-LC-AMEND, ENT-DOCSET → SYS-DB-TF | 1 | 0.6 | `stored_in` naming an `A4.SystemSoftware` |
| 1 | S51 | EVT-LC-ISSUED → TS-QUEUE | 1 | 0.4 | `published_to` |
| 2 | S40 | APP-LC, APP-DOC → ENV-TF-PROD | 3 | 0.8 | over P-C3-001/004 and `environment_id` |
| **3** | S42 | SVC-LC → TI-INGRESS, **SVC-LC → TI-TOPIC-LC**, SVC-DOC → TI-INGRESS | 3 | 0.4 | over S41 and `TechnologyService → TechnologyInterface` composition, mechanically; the topic report is the run's one false (finding 1) |
| 2 | S44 | IFC-LC, IFC-DOC → TS-GATEWAY | 3 | 0.4 | over S43 and `of_service` |
| 3 | S46 | FN-LC-CAPTURE, FN-LC-ISSUE, FN-DOC-CHECK → SYS-RUNTIME-TF | 3 | 0.4 | the function's component `DEPLOYED_ON` a SystemSoftware (P-C3-003/007) |
| 6 | S47 | API-LC-01…04 → DEP-LC-PROD; API-DC-01, 02 → DEP-DOC-PROD | 3 | 0.8 | A3 composition up to the component + P-C3-001/004 |
| 6 | S48 | the six APIs → TI-INGRESS | 3 | 0.6 | over S43 for the API's interface |
| 3 | S52 | SBB-TRADE → NODE-TF-PROD, SYS-RUNTIME-TF, DEV-SCAN-01 | 3 | 0.6 | `components` + the five `DEPLOYED_ON` proposals |
| 2 | S53 | SBB-TRADE → DEP-LC-PROD, DEP-DOC-PROD | 3 | 0.6 | `components` + P-C3-001/004 |
| 1 | S54 | SBB-TRADE → NODE-TF-PROD | 3 | 0.4 | `components` + the S34 proposals |

#### sdmm-eval (both files)

```
$ python -m sdmm.graph check examples/trade-finance/a*.json examples/trade-finance/c3-mappings-given.json examples/trade-finance/c3-proposals.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2
$ python -m sdmm.validate --strict examples/trade-finance/c3-proposals.json
WARNING ×7 (required evidence kinds); OK (with warnings)

$ python -m sdmm.evaluate examples/trade-finance/c3-gold-mappings.json --proposals examples/trade-finance/c3-proposals.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
DEPLOYED_AS         2    2   2   0   0   1.00  1.00  1.00
DEPLOYED_ON         5    5   5   0   0   1.00  1.00  1.00
OVERALL             7    7   7   0   0   1.00  1.00  1.00

$ python -m sdmm.evaluate examples/trade-finance/c3-gold-candidates.json --proposals examples/trade-finance/c3-candidates.json
relationship     gold prop  tp  fp  fn   prec   rec    f1
S37 2 2 2 0 0   S38 1 1 1 0 0   S39 2 2 2 0 0   S40 2 2 2 0 0   S41 3 3 3 0 0   S43 2 2 2 0 0   S44 2 2 2 0 0   S45 2 2 2 0 0   S46 3 3 3 0 0
S47 6 6 6 0 0   S48 6 6 6 0 0   S49 1 1 1 0 0   S50 3 3 3 0 0   S51 1 1 1 0 0   S52 3 3 3 0 0   S53 2 2 2 0 0   S54 1 1 1 0 0   (all 1.00)
S42                 2    3   2   1   0   0.67  1.00  0.80
OVERALL            44   45  44   1   0   0.98  1.00  0.99

false proposals (proposed, not approved):
  SVC-LC -S42-> TI-TOPIC-LC  conf=0.4  … the rule as written (S41 + TechnologyService -> TechnologyInterface composition) is applied mechanically — note TI-TOPIC-LC.exposes = []

$ python -m sdmm.graph impact NODE-TF-PROD --change rehost --status approved,proposed …
design_change_required  A4 NODE-TF-PROD; A3 APP-LC (via P-C3-002); A3 APP-DOC (via P-C3-006)
no_impact               A2 SD-LC, SD-DC; A1 CAP-TF, PRC-LC-APPLY, PRC-LC-ISSUE
mappings to supersede: P-C3-002, P-C3-006
```

#### Tests

| # | Expected | Observed | Verdict |
|---|---|---|---|
| C3.1 | registry 7 of 7; `DEPLOYED_ON` logged under S33, S34 or S35 by target | 7 of 7; two S33 (SystemSoftware), two S34 (Node), one S35 (Device); S36 logged as subsumed | **holds** |
| C3.2 | S37 2, S38 1, S39 2, S41 3, S43 2, S45 2, S49 1, S50 3, S51 1 — each names the key read | exactly those counts; every report quotes its export key | **holds** |
| C3.3 | S40 2, S42 2, S44 2, S46 3, S47 6, S48 6, S52 3, S53 2, S54 1 — each cites the arrow closed over | all as expected **except S42 = 3**: the derivation as written also reaches TI-TOPIC-LC via TS-QUEUE | **holds except S42** (one false; finding 1) |
| C3.4 | TI-TOPIC-LC → no S43 / S48; ART-DOC-STORE → no S39; TS-SIGNING / TS-OCR → no S41 | all three negatives hold and are logged with the key that is empty or absent | **holds** |

**Pass criteria.** Registry F1 1.00; candidate precision 0.98 and recall 1.00 (≥ 0.9 required); C3.4 holds.

#### Findings

| # | Plan ID | What happened | Why | Proposed change |
|---|---|---|---|---|
| 1 | S42 | one false report: SVC-LC → TI-TOPIC-LC. The plan's `data_needed` ("S41 instances + A4 composition TechnologyService → TechnologyInterface") was applied mechanically; SVC-LC consumes TS-QUEUE, whose interface is the topic | the rule conflates two relations: the interfaces of the technology services a service *consumes*, and the interface through which the service is *exposed*. The gold means the second (TI-INGRESS, which `exposes` the service's interfaces) | S42 `data_needed`: "derived over S43 + S44 — the technology interface that exposes one of the application service's interfaces", or at minimum "interfaces with a non-empty `exposes`". Under either reading the run files 2 and the row scores 1.00 |
| 2 | S33 / S34 / S35 | one registry rule, three plan rows, now logged by target entity as §4c requires; the component with three hosts (APP-DOC: node, runtime, device) produced three `DEPLOYED_ON` arrows at the same band | the data states all three; the plan has no notion of "primary" host | no change to the plan; note for the architect that `DEPLOYED_ON` fans out per host layer (node pool, runtime on the pool, appliance) and the environment is carried by `DEPLOYED_AS` |
| 3 | S52 | the derived path's target type is the abstract `A4.InfrastructureComponent`; the three reports target a Node, a SystemSoftware and a Device, which the hierarchy accepts | — | no change; record that S52 is the union of S33/S34/S35 at block grain, as S54 is the S34 slice |
| 4 | S37 | both `network_zone` on the component and `connects` on the network named the same segment; the rule accepts either | — | no change; when the two disagree the guide should say which wins (the component's own attribute) |

#### No-proposal register

| Plan ID | Instances | Why |
|---|---|---|
| S39 | → ART-DOC-STORE | nobody's build: no `of_component`, no `built_as` names it (C3.4); reached by S49 instead |
| S41 | → TS-SIGNING, TS-OCR | consumed by functions (S45), not by application services (C3.4) |
| S43, S48 | → TI-TOPIC-LC | `exposes` empty (C3.4); the topic is reached only by S51 (event published to its service) and, wrongly, by S42 |
| S45 | FN-LC-CAPTURE | `consumes` empty |
| S36 | — | subsumed; logged under S33 |
| S01, S02, S04, S12, S17, S24, S30 | the 17 given arrows | given |

**Summary.** The technology estate is the most mechanical of the three coverage cases and it behaves that way: eleven of the eighteen rows are pure joins on the new export keys and nine are closures over this run's own step-1 proposals, and all 51 targets are reached. The one false report is instructive rather than accidental: S42's rule text derives "the interfaces of the services I consume", while the architect meant "the interface I am exposed through", and the broker topic is exactly where the two readings part. The three coverage cases together put every one of the 42 previously unexercised plan rows through the steps; across C1–C3 the registry files score 19 of 19 and the candidate files 100 of 101, with the one false pointing at a one-line fix to S42.
