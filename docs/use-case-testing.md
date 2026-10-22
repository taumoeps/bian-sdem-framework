# Use-case testing of the mapping plan

**Status:** six use cases defined; E1 executed 2026-10-22 (see Results), E2–H2 pending. **Purpose:** test `metamodel/new-mappings.json` (the gap-fill plan, §5 of `docs/mapping-logic-planning.md`) against concrete architectures *before* any engine code exists. Execution is by hand — the analyst (or an AI session acting as the engine, following `docs/mapping-execution.md`) performs each step of §5.2 mechanically on the level exports; the existing tooling judges the result.

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

**Connections exercised.** S01 (as FRD-001), S17, S33. **Predicted:** all present and traceable; nothing to infer. **Pass:** every expected output exact. **Status:** executed 2026-10-22 — see Results.

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

### E1 — results (2026-10-22, fable-executor)

**Executor.** Claude Fable 5.1, following `docs/mapping-execution.md`. The guide's template labels the engine `opus-executor`; this run is labelled `fable-executor/2026-10-22` so the record says who ran it. **Gold.** E1 has no separate `gold-mappings.json`; the gold is the three approved records in `examples/card-fraud-alerts/mappings.json`, which the case lists as *given*. The executor therefore saw the gold before executing. Mitigation: every proposal below was built from the level exports only; approved arrows were read only where a step rule permits (step 2 rule 1, step 3), and no approved arrow was used as evidence for a proposal of the same pair. **Proposal file.** `examples/card-fraud-alerts/proposals-executor.json` (2 records).

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
$ python -m sdmm.evaluate examples/card-fraud-alerts/mappings.json --proposals examples/card-fraud-alerts/proposals-executor.json
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
$ python -m sdmm.graph check examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json examples/card-fraud-alerts/proposals-executor.json
OK: level A1 … A4; OK: mappings #1; OK: mappings #2

$ python -m sdmm.validate --strict examples/card-fraud-alerts/proposals-executor.json
ERROR: … (P-E1-001): proposal lacks required evidence kind(s) ['application_architecture_document']; must be supplied before approval
ERROR: … (P-E1-002): bian_alignment_guidance mapping requires bian_release; must be supplied before approval
ERROR: … (P-E1-002): proposal lacks required evidence kind(s) ['business_architecture_document', 'domain_scope_assessment']; must be supplied before approval
exit=1
$ python -m sdmm.validate examples/card-fraud-alerts/proposals-executor.json
(same three lines as WARNING)  OK: examples/card-fraud-alerts/proposals-executor.json (with warnings)
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
