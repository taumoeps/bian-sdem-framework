# Mapping execution guide — for the executor

**Who this is for.** A model session (or an analyst) acting as the mapping engine for one use case in `docs/use-case-testing.md`. You are executing a **plan**, not designing one. The plan is `metamodel/new-mappings.json`; the data is the use case's level exports. Your job is to produce the connections the plan says can be produced, show the working for each, and report precisely where the plan did not work.

**Objective.** Test whether the connections in `new-mappings.json` are correct and producible from the data. Every miss, false proposal or forced guess is a finding that improves the plan. A clean run with no findings is less useful than an honest one.

---

## 1. Before you start

Read, in this order:

1. `metamodel/new-mappings.json` — every connection, its `rule_decision`, `fill_step`, `data_needed`, `reasoning`, `confidence`. This is your instruction set per connection.
2. `docs/mapping-logic-planning.md` §5.2 — the five steps and the direction of fill.
3. The use case's section in `docs/use-case-testing.md` — the scenario, what is *given*, the connections it exercises, the expected outcomes.
4. `schema/relationship-types.json` — the nine registry rules and their required evidence kinds.
5. `metamodel/level-relationships.json` — the within-level relationship kinds you may read from the exports.
6. `metamodel/export-conventions.json` — the attribute keys on export instances that steps 1–4 join on. **If an export lacks the key a step needs, that is a finding about the export, and the step produces no proposal.**

Do **not** read the use case's gold set (`<uc>-gold-mappings.json` or `gold-mappings.json`) until phase 5. The mappings you may treat as already approved are only those in the case's *given* file (`<uc>-mappings-given.json`) — not the example's full `mappings.json`. If you have already seen the gold set, say so in the report.

## 2. Constraints — read these twice

| Rule | Meaning |
|---|---|
| **Use only the connections in the plan.** | A proposal must correspond to an ID in `new-mappings.json`. The `source`/`target` entity types of your proposal must be the ID's `source`/`target` (or, for A4, a concrete descendant of `A4.InfrastructureComponent`). |
| **New connections are allowed but quarantined.** | If the data clearly supports a connection that no ID covers, record it in the **New connection candidates** section of the report, not in the proposal document. Give its entity pair, the step that found it, reasoning and confidence. It is a proposed addition to the plan, not a result. |
| **Follow the step the plan assigns.** | Use the ID's `fill_step`. You may fall back to a *higher-numbered* step only if the assigned step cannot produce the connection from the data, and you must say so in the working. Never use a lower step than assigned (e.g. do not "derive" what the plan says must come from data) — **except** an optional step the plan's `reasoning` for that ID explicitly lists (e.g. S02's step-3 derivation); use it only after the assigned step has failed, label the proposal `optional-step`, and give it the band the plan states for that option. |
| **Show the working for every proposal.** | Step 1: the export record(s) joined. Step 2: the rule(s) fired and the values compared. Step 3: the approved arrows closed over, by `mapping_id`. Step 4: the attributes/paths/positions matched and the score. Step 5: the texts compared and why. No working → no proposal. |
| **Never approve.** | Every record is `status: proposed`. You do not set `reviewer_id` or `approved_at`. |
| **Never invent instances.** | Every `source.id` and `target.id` must exist in a level export. If the connection needs an instance that is not there, that is a finding ("no instance to map to"), not a proposal. |
| **No proposal is a valid answer.** | Where the data does not support any candidate at the assigned step or a permitted fallback, record *no proposal* with the reason. Precision over recall. |
| **Confidence is the plan's, not yours.** | Set `confidence` to the band the plan predicts for that ID (high 0.8, medium 0.6, low 0.4), adjusted down one band if you used a fallback step. **A step-3 derivation over non-approved arrows is capped by its inputs:** where the rule needs *all* its inputs (S01: every process of the capability), the cap is the weakest input's band; where *any one* input suffices (S17: one implemented operation realises the domain; S25, S22, S23), the cap is the strongest input's band (M1 finding 3). **An input lowered only by a recorded systematic interface deviation** (e.g. every SOAP operation is POST) does not lower the derivation: the deviation is about the API's form, not about which component implements the domain (H1 finding 4). If you believe the plan's band is wrong, say so in findings — do not silently change it. |

## 3. The steps, as rules

### Step 0 — BIAN export
Not executed by you. The A2 export is given. Read from it: domains, functional pattern, asset type, control record and its attributes, behaviour qualifiers, service groups, operations with action term and input/output, scenarios with their operation sequences.

### Step 1 — Data join
Read the A4 export's `relationships` and `attributes`, and the A3 export's `attributes`. Produce a proposal where a record states the fact directly:

| Connection | Join on |
|---|---|
| S32 `DEPLOYED_AS` | `A4.Deployment.attributes.component_id` = the component's id (or `A3.ApplicationComponent.attributes.deployed_as` lists the deployment id) |
| S33 `DEPLOYED_ON` | `A3.ApplicationComponent.attributes.deployed_on` lists the A4 id, or the A4 instance's `attributes.hosts` lists the component, **or** an `A4.Deployment` with `component_id` = the component names the platform in `platform_id`. `DEPLOYED_ON` is environment-agnostic — a component hosted in UAT is `DEPLOYED_ON` the UAT platform; the environment is carried by the `A4.Deployment` (S32) (M1 finding 2) |
| S36 component → system software | as S33 where the A4 target is `A4.SystemSoftware` |
| S50 data entity → database platform | `A3.DataEntity.attributes.stored_in` lists an `A4.SystemSoftware` id |
| S41 / S45 | `A3.ApplicationService.attributes.consumes` (or the function's) lists `A4.TechnologyService` ids |
| S49 | `A3.DataEntity.attributes.stored_in` lists an `A4.Artifact` id |

Relationships in exports are within-level only (policy); cross-level facts live in these attributes. Keys are defined in `metamodel/export-conventions.json`.

Working: quote the record. If no record names the component, **no proposal**.

### Step 2 — BIAN REST rule application (operation ↔ API)

Rewritten after M1: a tally of "3 of 4 rules" is not a fill rule — on a six-operation domain it admits nineteen wrong pairs (M1 finding 1). Step 2 is a **decision procedure** with one precondition, three evidential checks and a disambiguation.

**Precondition — boundary** ([SAPG] §3.5 p. 52: the Service Domain matches the application boundary of the API). Pass when **either**:

- the API's component is `REALIZED_BY` the domain (approved), **or**
- **token gate (reverse cases):** tokenise the domain's asset-type name *and its aliases* (`A2.AssetType.attributes.aliases`, supplied by the institution — e.g. "Financial Position" → `balance, position, posting, ledger`) and tokenise the component's interface: operation names (camel-case and snake-case split), paths, descriptions, and the names of the data entities it accesses. Lower-case, singularise, drop stop words. Pass if any asset token appears in the interface tokens.

Legacy names rarely contain the literal BIAN asset name ("POSTING_JRNL" does not say "Financial Position"); a literal gate blocks half of a legacy estate (H1 finding 1). No asset type and no aliases in the export → the gate is untestable for that domain; record it. The gate is the same for every API of one component and must never count as evidence.

**Checks** — each is *pass*, *fail* or *neutral*; only pass and fail are evidence:

| # | Check | Source | Pass | Fail | Neutral |
|---|---|---|---|---|---|
| 2 | Action term ↔ HTTP method | [SAPG] §3.2.5 (17 action terms), §3.5 (Retrieve → GET; Notify unused in the REST mapping) | Retrieve ⇔ GET (verified). **Executor convention, marked:** Create/Initiate/Register/Evaluate/Provide/Request ⇔ POST; Update/Control/Exchange/Capture/Grant/Execute ⇔ PUT or PATCH; Activate/Configure/Feedback ⇔ PUT or POST | any other combination | — (Notify or a term outside the 17: **fail** — no REST form) |
| 3 | Behaviour qualifier ↔ path | [SAPG] §3.5 p. 55 | the operation has a qualifier and its name (or clear synonym) is a path segment after the resource | the operation has a qualifier and the path lacks it; **or** the operation has no qualifier and the path carries a segment that is another operation's qualifier | the operation has no qualifier and the path has no qualifier segment |
| 4 | Attributes ↔ payload | [SAPG] §3.5 (attributes filtered by action term) | ≥ 50 % of `input_attributes` ∪ `output_attributes` appear in `payload_fields` **and** this API is the operation's best payload match (highest overlap) | < 50 % | — |

**Decision, per operation, over the APIs that passed the precondition:**

1. **Propose at the plan's band (high)** when checks 2 and 4 pass and check 3 is pass or neutral.
2. **Propose one band lower, with a finding on the API** when check 2 fails but checks 3 (pass or neutral) and 4 pass and the API is the operation's unique best payload match — e.g. a Retrieve implemented as POST. The finding states the method mismatch.
3. **Otherwise no proposal.** Two passes with a failed check 3, or check 4 failed, is not a mapping.
4. **Disambiguation, iterated to a fixpoint:** an operation maps to at most one API and an API to at most one operation in step 2. Round 1: file every decision-1 pair; remove any other pair sharing its operation or API. Round 2: among the remaining decision-2 pairs, file each operation's unique best payload match; remove pairs sharing its operation or API. Repeat until no pair is filed in a round (H1 needed two rounds). If two APIs tie as an operation's best payload match, the one whose path or name contains the operation's qualifier wins; a remaining tie is **no proposal** with both candidates named in the log.

**Non-HTTP interfaces.** If `attributes.method` is not an HTTP method (e.g. `BATCH`, `MQ`, `FILE`), the BIAN REST mapping does not apply: step 2 is **not applicable** for that operation — record it in the no-proposal register and, if the payload overlaps a control record ≥ 50 %, report the pair under *New connection candidates* as a non-REST realisation. Never force it through check 2.

**Systematic deviations.** When every operation of an interface fails check 2 the same way (e.g. a SOAP interface where all operations are POST), report **one** finding naming the interface and the convention, and reference it from each affected proposal — not fourteen separate findings.

**Notify operations.** A *Notify* operation has no REST form; if the A3 export carries an `A3.Event` whose name matches the operation's asset and state change, report it under *New connection candidates* as `A2.ServiceOperation → A3.Event` (no plan ID yet; M1 finding 5). Never as a proposal.

Working: for every operation × API pair that passed the precondition, log the three check results and the decision reached, including suppressed pairs and the clause that suppressed them (M1 logged 36 pairs this way; that is the standard).

### Step 3 — Derivation over approved arrows
Closure rules. Cite the `mapping_id` of every arrow used.

| Connection | Rule |
|---|---|
| S17 `REALIZED_BY` | if component C exposes API operations that `IMPLEMENTED_BY` (approved, or your step-2 proposals — say which) operations of domain D, then D `REALIZED_BY` C. **Fallback (step 4, one band lower):** a token of the domain's asset-type name **or its aliases** (`A2.ServiceDomain.attributes.asset_type` → `A2.AssetType.name`, `.attributes.aliases`) appears in the component's API paths or data entity names — a structural match, scored as matches / APIs+entities, threshold ≥ 1 match. Description-only comparison is **step 5**, two bands lower |
| S25 | operation O `IMPLEMENTED_BY` API a; a exposed by application service S (A3 composition) ⇒ O → S |
| S22 / S23 | the service/interface exposing the APIs of a group's operations |
| S04 `USES_DOMAIN` | process P (or one of its activities) has `attributes.invokes` naming operation O, or an S06 proposal; O in domain D (B09/B10) ⇒ P `USES_DOMAIN` D. A process exported without activities may be matched directly to operations by the S06 verb+noun rule (step 4) |
| S01 `SUPPORTED_BY` (candidate) | every process of capability K (A1 relationship) `USES_DOMAIN` D ⇒ candidate K `SUPPORTED_BY` D, confidence medium; if only some processes, low. **Report-only:** a parent capability whose composed child is `SUPPORTED_BY` D is listed under *New connection candidates*, never proposed — whether a parent's scope is covered by a child's domain is a judgement, not a derivation (M0 run 2) |
| S02 `ALIGNED_TO` (optional step 3) | value stream V realises capability K (A1 `realization`); a process of K invokes operation O; O in scenario S's `operation_sequence` ⇒ candidate V `ALIGNED_TO` S, low. Step 4 (stages vs sequence) remains the primary route |
| S07, S15, S16, S40, S42, S46, S47, S48, S52–S54 | derived paths — report as **queries** (the chain of arrows), not as proposal records |

### Step 4 — Structural matching
Only for the IDs the plan assigns to step 4, or as a declared fallback.

| Connection | Match on | Propose when |
|---|---|---|
| S30 `MAPPED_TO`, S20, S31 | BOM / control-record attribute names vs data entity attribute names (normalise case, underscores, plural) | ≥ 50 % of the BIAN object's attributes matched; score = matched / BIAN attributes |
| S12 `ALIGNED_TO` (object) | bank glossary attributes vs BOM attributes | as above |
| S02 `ALIGNED_TO` (value stream) | **coverage of the scenario's operations**: each operation in `operation_sequence`, in order, is matched by a stage whose name shares the operation's **action term** (verb or a clear synonym: capture ≈ initiate/create, validate ≈ evaluate, execute, confirm ≈ retrieve/notify). The asset noun is **not** evidence — every operation of a domain shares it (M1 finding 4). A stream may have more stages than the scenario has operations | score = covered operations / operations in the scenario; propose when ≥ 60 % |
| S06 | activity name vs operation name (action verb + asset noun) | both verb and noun match |
| S18, S19, S21, S27 | as the plan's `data_needed` states | state the score |

Working: the attribute/stage pairs matched and the score.

### Step 5 — Text inference
Only for S01 when step 3 produced nothing (capability with no mapped processes), and for the A1 side of hard cases. Compare the capability description with each candidate domain's description (name, description, asset type and aliases). Count **shared concepts**: content words after stop-word removal, excluding generic banking words (`bank, customer, manage, account, service, process, record, data`) — these appear everywhere and are not evidence. Propose at most **one** domain per capability, low confidence, with the two texts quoted and the shared concepts named, **only when** the best domain shares **≥ 2 concepts** and leads the runner-up by **≥ 1** (H1 finding 3). **The candidate set must be the full exported A2 landscape, or at least three domains**; with fewer, record *single-candidate, no proposal*. Otherwise **no proposal**.

## 4. Output — the proposal document

One file per use case: `examples/<example>/<uc>-proposals.json` (e.g. `m0-proposals.json`), in the mapping-document shape; `use_case` is an allowed top-level key:

```json
{
  "registry_version": "0.4.0",
  "metamodel_version": "0.4.0",
  "engine": "<model>-executor/<date>",
  "use_case": "<uc>",
  "mappings": [
    {
      "mapping_id": "P-M1-001",
      "source": {"id": "<instance id>", "type": "<entity>", "version": "<version>"},
      "relationship": "<registry relationship>",
      "target": {"id": "<instance id>", "type": "<entity>", "version": "<version>", "canonical_id": "<if the A2 export has one>"},
      "status": "proposed",
      "confidence": 0.8,
      "evidence": ["engine_rationale:S24 step2 rules 1-4 passed; action term Retrieve ↔ GET; qualifier 'Instruction' in path; 6/8 attributes in payload"],
      "rationale": "<one sentence>",
      "baseline_id": "<use case baseline>",
      "created_by": "<model>-executor/<date>"
    }
  ]
}
```

Rules: `evidence[0]` starts with `engine_rationale:` and names the plan ID and step. Only registry relationships may be used (the nine); candidate-rule connections (S20, S21, S25, S28, S29) and institution-only ones (S36, S50) are reported in the **Candidate-rule proposals** section of the report in the same record shape, not in this file, because the validator will reject their relationship.

## 4b. Output — the inference log

Alongside the proposal file, write `examples/<example>/<uc>-inference-log.json`: **one record per connection attempted**, including those that produced no proposal. This is the file the next optimisation step is planned from.

```json
{
  "use_case": "M0", "executor": "<model>-executor/<date>",
  "attempts": [
    {
      "plan_id": "S33", "connection": "APP-FRAUD-ENGINE DEPLOYED_ON INF-CLOUD-K8S-PROD",
      "step_assigned": 1, "step_used": 1, "fallback": false,
      "data_read": ["a3-application.json: APP-FRAUD-ENGINE.attributes.deployed_on", "a4-technology.json: INF-CLOUD-K8S-PROD.attributes.hosts"],
      "reasoning": "both sides name each other; direct join, no inference",
      "confidence_predicted": "high", "confidence_given": 0.8,
      "proposal_id": "P-M0-001",
      "outcome": "hit | miss | false | no_proposal",
      "outcome_note": "filled in phase 6 after sdmm-eval"
    }
  ]
}
```

`outcome` is set after scoring: **hit** (proposal matches gold), **false** (proposal not in gold), **miss** (gold connection with no proposal — one record per missed gold arrow), **no_proposal** (attempted, nothing proposed, with the reason in `reasoning`). Every plan ID the use case lists must appear at least once.

`sdmm-eval` scores proposals against **approved** gold only. If a case lists a connection whose gold record is `proposed`, it will be scored false — the case must either approve it in the gold or exclude it from the precision criterion (M0 finding 2).

## 5. Judge, then score

```bash
python -m sdmm.graph check  examples/<example>/a*.json examples/<example>/<uc>-mappings-given.json examples/<example>/<uc>-proposals.json
python -m sdmm.validate --strict examples/<example>/<uc>-proposals.json
python -m sdmm.evaluate examples/<example>/<uc>-gold-mappings.json --proposals examples/<example>/<uc>-proposals.json
python -m sdmm.graph trace <id> --direction down examples/<example>/a*.json examples/<example>/<uc>-mappings-given.json examples/<example>/<uc>-proposals.json --status approved,proposed
```

Only now open `gold-mappings.json`. Paste the `sdmm-eval` output verbatim into the report.

## 6. Report — append to `docs/use-case-testing.md` under *Results*

```
### <Case id> — results (<date>, <model>-executor)

#### Proposals
<table: proposal id | plan ID | connection | step used (assigned / fallback) | confidence | working (one line)>

#### Candidate-rule and institution-only proposals (not in the proposal file)
<same table>

#### sdmm-eval
<verbatim output>

#### Predicted vs observed, per plan ID
| Plan ID | Predicted confidence | Observed | Verdict |
| S24 | high | 5/6 hit, 1 false | holds / weaker than predicted / failed |

#### Findings against the plan
| # | Plan ID | What happened | Why | Proposed change to new-mappings.json |
| 1 | S36 | data had it; plan says institution-only | ... | promote to enterprise_rule? |

#### New connection candidates (outside the plan)
| Pair | Found by step | Reasoning | Confidence | Suggested ID |

#### No-proposal register
| Plan ID | Instances considered | Why no proposal |
```

Every row in *Findings* must say what to change: the ID's `fill_step`, `confidence`, `data_needed`, `rule_decision`, or the step rules in §3 of this guide. That table is the output that matters.

## 7. What a good run looks like

- Every proposal traceable to a record, a rule, an arrow or a scored match.
- At least one *no proposal* with a reason.
- The planted mismatch (where the case has one) surfaced as a finding.
- `sdmm-validate --strict` passes on the proposal file: draft warnings (missing evidence kinds, `bian_release`, `canonical_id` on proposed records) are reported but not promoted to errors under `--strict`.
- Predicted-vs-observed filled for every ID the case exercises, including the ones that failed.
- `inference-log.json` written, with an `outcome` on every attempt.
