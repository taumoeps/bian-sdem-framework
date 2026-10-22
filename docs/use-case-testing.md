# Use-case testing of the mapping plan

**Status:** planned — six use cases defined, none executed. **Purpose:** test `metamodel/new-mappings.json` (the gap-fill plan, §5 of `docs/mapping-logic-planning.md`) against concrete architectures *before* any engine code exists. Execution is by hand — the analyst (or an AI acting as the engine) performs each step of §5.2 mechanically on the level exports; the existing tooling judges the result.

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

**Given.** `examples/card-fraud-alerts/a1–a4-*.json`; `mappings.json` (FRD-001, 002, 005 approved; FRD-003 superseded; FRD-004 proposed).

**Tests.**

| # | Question | Command | Expected |
|---|---|---|---|
| E1.1 | Downstream from CAP-310 | `sdmm-graph trace CAP-310 --direction down` | CAP-310 → SD-044 → APP-FRAUD-ENGINE → INF-CLOUD-K8S-PROD, each hop with its mapping id |
| E1.2 | Upstream from INF-CLOUD-K8S-PROD | `trace … --direction up` | the same chain reversed, ending at CAP-310 |
| E1.3 | Upstream from the retired host | `trace INF-ONPREM-VM-CLUSTER-B --direction up` | nothing (exit 1): only a superseded arrow points there; with `--status approved,superseded` the old chain appears |
| E1.4 | Rehost Kubernetes | `impact INF-CLOUD-K8S-PROD --change rehost` | A4, A3 `design_change_required`; A2, A1 `no_impact`; FRD-005 to supersede |
| E1.5 | Retire the domain | `impact SD-044 --change retire` | CAP-310 `design_change_required`, APP `review_required`, INF `no_impact` |
| E1.6 | Gap honesty | trace from SO-044-07 with approved only | exit 1 — the only arrow is `proposed`; with `--status approved,proposed` it appears |

**Connections exercised.** S01 (as FRD-001), S17, S33. **Predicted:** all present and traceable; nothing to infer. **Pass:** every expected output exact. **Status:** executable now.

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

## M1 — Payment Initiation, brownfield (Medium)

**Scenario.** The business and domain architecture are mapped and approved. The payments platform exists — applications, APIs, deployments are exported from the APM and CMDB — but no A2→A3 or A3→A4 mappings have been written.

**Given.** A1: capability *Initiate Payment*, value stream *Make a Payment* with stages, two processes with activities. A2 (synthetic BIAN-style export): a Payment Initiation domain with functional pattern, asset type, control record with attributes, two service groups, six operations with action terms and behaviour qualifiers; one scenario. A3: a payments application composed of three components, one interface exposing six API operations with path, method and payload fields; four data entities with attributes. A4: two deployments in two environments, a Kubernetes platform, a managed PostgreSQL, a message broker; deployment relationships recorded. **Approved:** S01, S02, S04, S12 instances only (A1→A2). **Gold (sealed):** the A2→A3 and A3→A4 arrows an architect would approve — ~12 records.

**Execution order.** Step 1 data join on the A4 export → `DEPLOYED_AS`, `DEPLOYED_ON`, S36, S50 candidates. Step 2 REST rules → `IMPLEMENTED_BY` for each API (action term vs method, qualifier vs path, control-record attributes vs payload); mismatches reported as findings. Step 3 derivation → `REALIZED_BY` (the application hosting the implementing APIs), S25, S22/S23, S40, S47. Step 4 → `MAPPED_TO` by attribute match against the control record and BOM objects, S20.

**Connections exercised and predicted.**

| ID | Connection | Step | Predicted |
|---|---|---|---|
| S32 / S33 | component → deployment / platform | 1 | high — pure join |
| S36 | component → system software | 1 | medium — proposed, not a rule |
| S24 | operation → API | 2 | high; at least one deliberate mismatch planted (wrong method) must surface as a finding |
| S17 | domain → application | 3 | high — derived from S24 |
| S25 | operation → application service | 3 | high |
| S30 | BOM object → data entity | 4 | high |
| S20 | control record → data entity | 4 | high |
| S40, S47 | derived paths | 3 | high — must appear as *queries*, not records |

**Then.** Trace CAP → platform; rehost the Kubernetes platform. **Pass:** F1 ≥ 0.8 on step 1–3 arrows; the planted mismatch reported; no proposal for a component with no deployment record (negative test). **Status:** data to author.

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

**Scenario.** A 20-year-old core banking ledger. Its A3 (modules, interfaces, ~15 API/batch operations with reasonable banking names) and A4 (mainframe partition, DB2, MQ) are fully documented in the CMDB. **No BIAN mapping exists; no capability model exists.**

**Given.** A3 and A4 exports; A2 synthetic BIAN export for the relevant domains (e.g. position keeping, payment execution, account management); **no A1 export**; no approved mappings. **Gold (sealed):** the A3→A2 arrows an architect would approve, plus the A1 capabilities they would recognise.

**Execution order.** Step 2 *in reverse* — for each API/batch operation, find the BIAN operation whose action term, qualifier and control-record attributes it matches → `IMPLEMENTED_BY`. Step 3 — the domain whose operations a module implements → `REALIZED_BY`; the control record whose attributes a table holds → S20 / `MAPPED_TO`. Step 1 — A4 from the CMDB. Then the hard part: **A1.** BIAN's capability→domain mapping is unpublished (B01). Options in order: derive capabilities from the public BCM capability map by matching domain names to capability names (step 4); else text inference (step 5) at low confidence; else report "no proposal — requires authoring".

**Connections exercised and predicted.**

| ID | Connection | Step | Predicted |
|---|---|---|---|
| S24 | operation ← API | 2 (reverse) | high for well-named operations; medium where naming diverges |
| S17 | domain ← module | 3 | high |
| S20, S30 | control record / BOM ← tables | 4 | medium — legacy schemas rarely align attribute-for-attribute |
| S32, S33, S50 | deployment, platform, DBMS | 1 | high |
| S01 | capability ← domain | 4 then 5 | **low** — the plan's own prediction; the test is whether the executor says so |

**Pass:** F1 ≥ 0.7 on A3→A2; every A1 proposal carries low confidence and a step-5 rationale, or an explicit "no proposal"; no capability is invented that the BCM public map does not contain. **Status:** data to author.

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

**Order of execution:** E1 now; E2 after its exports are authored; M1 next (it exercises most of the plan); then H1, H2; M2 last (it tests a boundary, not the plan's core).

## Results

*To be appended per case: proposal document, `sdmm-eval` output, predicted vs observed confidence per connection, findings against the plan.*
