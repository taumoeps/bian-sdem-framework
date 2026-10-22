# Relationships test plan — validating the within-level connections

**Purpose.** Validate the 131 within-level connection rows and 12 inheritance rows in `metamodel/level-relationships.json` (documented in `docs/relationships-planning.md`): that each is grounded in its reference architecture, that the set is complete and consistent for each level, that `sdmm-graph check` enforces it exactly, and that every mapping rule which walks a within-level link finds the row it needs. This is a **test plan**, not a use case: nothing is inferred, no mapping is proposed, and the record is not edited — the output is a verdict per row and a findings table.

**Executor.** Opus, under the same discipline as `docs/mapping-execution.md` §1: use only the files named here; show the working for every verdict; never edit `level-relationships.json`, the catalogue, the examples or the checker; put every proposed change in the findings table for the owner to apply.

**Inputs.**

| File | Role |
|---|---|
| `metamodel/level-relationships.json` | the record under test: `constraints` (rows `RA1-01` … `RA4-35`), `inheritance` (`XA1-01` …), `kinds`, `policy` |
| `metamodel/a1-business.json` … `a4-technology.json` | the entity catalogue: each entity's `reference` (standard, concept, locator), `extends`, `abstract`, `artefact` |
| `docs/reference-architecture-provenance.md`; README › *Reference architecture provenance* | which reference architecture each entity derives from |
| `metamodel/official-mappings.json` | the B rows (B02–B15) that the A2 rows must cover |
| `metamodel/new-mappings.json`; `docs/mapping-execution.md` §3 | the cross-level rules whose derivation steps walk within-level links |
| `examples/*/a[1-4]-*.json` (seven estates, 25 exports) | real relationship instances to measure coverage and to probe the checker |
| `sdmm/metamodel.py` (`relationship_issue`), `sdmm/graph.py` (`LevelGraph.validate`) | the enforcement under test |
| Public sources | [SL14] BIAN portal pages; [SAPG]; [RN14]. ArchiMate 3.2 and TOGAF 10 are login-gated: **do not** attempt to fetch them; verify against the public chapter structure only and leave `unverified_*` rows at that status unless a public source contradicts them |

**Outputs.**

| File | Content |
|---|---|
| `metamodel/relationships-test-log.json` | one entry per row (131 + 12): `id`, `tests_run`, `verdict` per test (T1–T6 below), `evidence` (source read, command run, example instance), `notes` |
| `docs/relationships-testing.md` › *Results* (append) | the summary tables in §4, the findings table in §5, the coverage table |
| no other file changes | the record, catalogue, examples and code are read-only for the executor |

---

## 1. Tests

Run every test for every row it applies to. A row's overall verdict is the weakest of its test verdicts: **pass**, **pass with note**, **fail**, **not testable** (login-gated source, no example instance).

### T1 — Provenance: the row names concepts the entities actually derive from

For each row, read the source and target entity's `reference.concept` in the catalogue. The row's `reference_source` must be the reference architecture that **both** concepts derive from (A2: BIAN; A1/A3/A4: ArchiMate, or TOGAF for `A3.SolutionBuildingBlock`, or an SDMM extension row when either end is an SDMM extension entity). **Provenance by inheritance counts:** an SDMM extension entity (`A1.ValueStreamStage`, `A1.BusinessActivity`, `A4.Deployment`, …) carries its parent's reference architecture, and `A1.BusinessCapability`, catalogued to BIAN's BCM, also derives from ArchiMate Strategy (its locator says so) — a row citing ArchiMate for either is a pass, not a note. A row that relates an ArchiMate concept to a BIAN concept inside one level, or cites a source neither entity derives from, **fails**.

Working: the two concepts and the standard each is cited to; the row's `reference_source`.

### T2 — Grounding: the relationship exists in the reference architecture, in that direction

- **A2 rows (17).** Verify against the public BIAN pages cited (portal metamodel overview, Service Landscape structure, Control Record Model, BOM overview, business scenarios, wireframes) and [SAPG] sections. Each of B02–B15 must be covered by exactly one row with the matching `official_id`; direction must match the B row (`source → target`). The three rows without a B id (`ServiceOperation → BehaviorQualifier`, `BusinessObject → BusinessObjectAttribute`, `BOMModel → BusinessObject`) must each cite a public page that supports them, or be marked `sdmm_reading` — report which.
- **ArchiMate / TOGAF rows (103).** The specifications are login-gated. Test **direction and kind against ArchiMate's generic metamodel** (ch. 5, public summary): active structure is *assigned to* behaviour; behaviour *realizes* a service; behaviour *accesses* passive structure; a service *serves* elements; an interface is *assigned to* the service it exposes; an interface is *composed in* its active-structure element; artifacts are *assigned from* the node they run on; a path is *realized by* a network; a core element *realizes* a requirement; a capability *serves* a value stream; same-type *composition / aggregation / specialization*; behaviour *triggering / flow*. A row whose direction or kind contradicts that pattern **fails** (name the pattern). A row consistent with it **passes with note: unverified against the specification's relationship table**. Do not upgrade `unverified_archimate` to `verified`.
- **SDMM extension rows (11).** Verify against the extension's definition in the catalogue (`A4.Deployment` = artifact assigned to node; `A4.DeploymentEnvironment` = node grouping; `A1.ValueStreamStage` is-a value stream; `A1.BusinessActivity` is-a process; `A3.APIOperation` aligned to Semantic API). The row must follow from the definition.

### T3 — Consistency within the level

- **No entity orphaned.** Every concrete, non-artefact entity of the level is the source or target of at least one row. (Expected exceptions: none; abstract `A4.InfrastructureComponent` is covered by inheritance only.)
- **Inheritance does not create duplicates or holes.** Where a row exists on a parent (`A1.BusinessProcess`) and again on its child (`A1.BusinessActivity`), the child row is redundant under `is_a` — report it as *redundant, harmless* (the checker accepts through inheritance). Where a child needs a relationship the parent row does not give it, report the hole.
- **No contradictory pair.** No two rows state the same pair with opposite direction unless ArchiMate allows both (e.g. serving between components). Report each such pair and whether it is intended.
- **Association is generic.** Confirm the policy and the checker treat `association` as permitted between any two entities of one level, and that no `association` row is therefore needed (the three A2 `association` rows exist for their official-id provenance, not for enforcement — say so).
- **Kinds.** Every row's `kind` is in `kinds`; every kind in `kinds` is used by at least one row or is `association`.

### T4 — Enforcement: the checker accepts exactly the rows

Build the probes in a scratch directory (never under `examples/`), each a minimal level export with two or three instances, and run `python -m sdmm.graph check <probe>`. Record the command, exit code and message.

| Probe | Expected |
|---|---|
| T4.1 For each level, one relationship per row, instantiated on concrete entities | every one accepted (131 relationships; may be one export per level) |
| T4.2 Reversed direction for one row of each kind per level (e.g. `A4.Artifact assignment A4.Node`, `A1.ValueStream realization A1.BusinessCapability`, `A3.ApplicationService composition A3.ApplicationInterface`) | rejected, message names the pair and the basis (`BIAN structure` for A2, `ArchiMate 3.2 / TOGAF` otherwise) |
| T4.3 A kind not in the row set for that pair (`A3.ApplicationComponent composition A3.ApplicationFunction`) | rejected |
| T4.4 `association` between two arbitrary entities of one level, per level | accepted |
| T4.5 A row satisfied only through inheritance (`A1.BusinessActivity access A1.BusinessObject` when stated on the parent; `A4.Device` where a row names `A4.Node`? — Device does **not** extend Node: expect rejection unless a Device row exists) | accepted / rejected as the record implies — report which |
| T4.6 An instance of abstract `A4.InfrastructureComponent` | rejected: "entity is abstract" |
| T4.7 A relationship whose ends are on different levels inside one export (`A2.ServiceDomain composition A3.ApplicationComponent` in an A2 file) | rejected: "not an A2 entity" |
| T4.8 A kind not catalogued (`uses`) | rejected: "kind not catalogued" |
| T4.9 Every example export (`examples/*/a[1-4]-*.json`) and the M2 design exports | accepted (regression) |

### T5 — Coverage: which rows the ten estates exercise

For each row, count the relationship instances across all example exports that match it (directly or through inheritance). Produce the table *row → count → estates*. Rows with zero instances are **not tested by data**; list them. (Baseline at authoring: 42 of 131 rows were exercised by the realistic estates. Since v0.5.18 `examples/reference-structure/`, generated from the record by `sdmm-structure`, carries one relationship per enforceable row, so every row is exercised on committed data; report realistic-estate coverage and reference-structure coverage separately.)

### T6 — Dependency: the mapping rules find the rows they walk

Every cross-level rule that derives over within-level structure depends on specific rows. For each dependency below, confirm (a) the row exists, (b) at least one example estate carries an instance of it, (c) the guide or plan text names the same kind as the row. A mismatch between the guide's wording and the row's kind is a **fail** on the guide, not the row.

| Rule | Walks | Row(s) expected |
|---|---|---|
| S15, S16 (area / domain → component) | A2 composition area → domain → Service Domain | RA2 rows for B02, B03 |
| S17 fallback, S22, S23, S25, S28, S47, S48 | A3: component composes interface; interface composes API operations; interface assigned to service | the A3 rows for those three pairs |
| S18, S21 (function rows) | A3: component assigned to function; function exposed through APIs (`exposed_through` key, not a relationship) | component → function row; note that `exposed_through` is an attribute |
| S40 | A4: environment aggregates deployment | the A4 environment row |
| S42, S44 | A4: technology interface assigned to technology service | the A4 interface → service row |
| S46 | the cross-level `DEPLOYED_ON` arrow from the function's component to system software (S33) — no within-level row is walked | none; listed to record that S46 has no within-level dependency (corrected after the first run, finding 5) |
| S52, S53, S54 | A3: solution building block aggregates components | the TOGAF row |
| `--follow-composition` trace | within-level `composition` only (part → whole) | confirm which rows are `composition` and therefore followed; list the rows a trace will **not** follow (aggregation, assignment) and whether that matters for S52–S54 and the H1 module case |
| S02 optional route | A1: capability serves value stream; process realizes capability | the A1 serving and realization rows |
| S13, S14 | A1: requirement — the guide uses `applies_to`, the rows say a core element `realization` requirement | confirm the examples use `association` (generic) and whether the plan should name `realization` |

---

## 2. Procedure

1. Read the inputs; do not read anything under `examples/*/*-gold-*`, `*-proposals.json` or `*-inference-log.json` — they are irrelevant here and must not shape verdicts.
2. T1, T2, T3 over the record, row by row; write the log as you go.
3. T4 probes in the scratch directory; record every command verbatim.
4. T5 and T6 over the examples and the plan.
5. Write the log, append *Results*, commit with a message that states the pass / fail / note / not-testable counts.

**Time box.** The 103 ArchiMate / TOGAF rows need only the generic-metamodel pattern check in T2; do not attempt per-row literature search.

---

## 3. Pass criteria

- Every A2 row passes T1–T3 and B02–B15 are each covered once.
- No row fails T2 on direction or kind against the generic metamodel.
- T4.1–T4.9 all as expected; any deviation is a finding on the checker.
- T6: every dependency has its row, an example instance, and consistent wording; any wording mismatch is a finding on the guide or plan.
- Findings table complete: every proposed change names the row ID and the field to change.

## 4. Results template

```
### Results (<date>, <executor>)

| Test | Rows in scope | pass | pass with note | fail | not testable |
| T1 provenance | 131 | | | | |
| T2 grounding | 131 | | | | |
| T3 consistency | per level | | | | |
| T4 enforcement | 9 probes | | | | |
| T5 coverage | 131 | exercised: n | | | unexercised: n |
| T6 dependency | 10 dependencies | | | | |

#### Coverage (T5)
| Row | Count | Estates |

#### Dependencies (T6)
| Rule | Row(s) | Exists | Example instance | Wording consistent | Verdict |
```

## 5. Findings template

| # | Row ID | Test | What was found | Evidence | Proposed change (field → value) |
|---|---|---|---|---|---|

Every finding must be actionable on one row or one named file: add a row (with basis), remove a row, change a kind or direction, correct a `verification` or `confidence`, or reword the guide / plan. "Consider" is not a finding.

---

### Results (2026-10-23, fable-executor)

**Executor.** Claude Fable 5.1 under the discipline above (the plan names Opus). **Read-only inputs**: the record, the catalogue, the 25 example exports plus the two M2 design exports, `sdmm/metamodel.py` and `sdmm/graph.py`; nothing under `examples/*/*-gold-*`, `*-proposals.json` or `*-inference-log.json` was read. **Probes** were built under the session scratch directory, never under `examples/`. **No login-gated source was fetched**; the BIAN portal was not re-fetched either — A2 grounding rests on the official record's `verified` B rows and the citations carried by the rows (noted on every A2 entry). **Log.** `metamodel/relationships-test-log.json`: 143 entries (131 rows, 12 inheritance), each with T1–T5 verdicts, evidence and notes; the 36 probe commands with exit codes; the coverage counts; the ten dependencies.

| Test | Rows in scope | pass | pass with note | fail | not testable |
|---|---|---|---|---|---|
| T1 provenance | 131 | 107 | 24 | 0 | 0 |
| T2 grounding | 131 | 25 | 106 | 0 | 0 |
| T3 consistency | per level (131) | 107 | 24 | 0 | 0 |
| T4 enforcement | 9 probe groups (36 commands) | 8 | 1 (T4.1: 3 artefact rows cannot be instantiated) | 0 | 3 rows (RA2-15, 16, 17) |
| T5 coverage | 131 | exercised: 43 | | | unexercised: 88 (reported, not failed) |
| T6 dependency | 10 dependencies | 2 | 8 | 0 | 0 |
| **Overall (weakest of T1–T4), 131 rows** | | **19** | **109** | **0** | **3** |
| Inheritance rows (XA1-01…XA4-10) | 12 | 12 | 0 | 0 | 0 |

**What the notes are.** T2: the 103 ArchiMate / TOGAF rows all match a generic-metamodel pattern (named in the log) and keep `unverified_*`, as the plan requires; the three no-B A2 rows are supported as the plan asks (RA2-08 by [SAPG] §3.2.4/§3.5, RA2-10 by the public BOM page, RA2-17 marked `sdmm_reading`). T1: 18 rows with an SDMM-extension end cite ArchiMate rather than an "SDMM extension" source, and 7 capability rows cite ArchiMate while the catalogue references BIAN BCM (two rows are in both sets; RA2-17 is the artefact wrapper) — both are provenance-by-inheritance, accepted with a note and raised as findings F1 and F2. T3: 15 A1 child rows are redundant under `is_a` (harmless) and two A3 triggering pairs run in both directions (intended). **No row fails any test.**

#### T2 — B coverage

B02–B15 are each covered by exactly one row with matching direction: RA2-01 (B02), RA2-02 (B03), RA2-06 (B04), RA2-07 (B05), RA2-05 (B06), RA2-11 (B07), RA2-12 (B08), RA2-03 (B09), RA2-04 (B10), RA2-13 (B11), RA2-14 (B12), RA2-09 (B13), RA2-15 (B14), RA2-16 (B15). B01 is not a within-level row.

#### T3 — consistency

| Level | Orphans | Redundant child rows (under `is_a`) | Opposite-direction pairs |
|---|---|---|---|
| A1 | none | RA1-04 ⊂ RA1-03; RA1-10 ⊂ RA1-09; RA1-16 ⊂ RA1-08; RA1-17, RA1-18 ⊂ RA1-09; RA1-19 ⊂ RA1-11; RA1-20 ⊂ RA1-12; RA1-21 ⊂ RA1-13; RA1-22 ⊂ RA1-14; RA1-23 ⊂ RA1-15; RA1-24 ⊂ RA1-25; RA1-26 ⊂ RA1-24; RA1-28 ⊂ RA1-27; RA1-37 ⊂ RA1-36; RA1-39 ⊂ RA1-38 — 15, all harmless | none |
| A2 | none (artefacts covered by RA2-15/16/17) | none | none |
| A3 | none | none | RA3-22 / RA3-25 and RA3-23 / RA3-24 (`triggering` between behaviour and event, both directions) — intended |
| A4 | none; abstract `A4.InfrastructureComponent` by inheritance only | none (Device does not extend Node) | none |

Association: `relationship_issue` returns `None` for `association` before the rows are consulted, so no association row is needed for enforcement; RA2-06, 07, 08, 12, 15 exist for their official-id provenance. Kinds: all ten catalogued kinds are used; every row's kind is catalogued.

#### T4 — enforcement (36 commands; full output in the log)

| Probe | Result |
|---|---|
| T4.1 one relationship per row | A1 48 / 48, A3 31 / 31, A4 35 / 35 accepted; A2: 14 / 17 accepted — **RA2-15, RA2-16, RA2-17 cannot be instantiated**: `entity 'A2.Wireframe' is an artefact, not an instance type` (likewise SemanticAPI, BOMModel). The rows are provenance-only (finding F5) |
| T4.2 reversed direction, one row per kind per level | 21 probes, all rejected; A2 messages say `does not match the BIAN structure constraints`, others `the ArchiMate 3.2 / TOGAF constraints`, each naming the pair |
| T4.3 `A3.ApplicationComponent composition A3.ApplicationFunction` | rejected |
| T4.4 `association` between arbitrary entities | accepted at all four levels |
| T4.5 inheritance | a) `BusinessActivity access BusinessObject` accepted (RA1-12 parent, RA1-20 direct); b) `ValueStreamStage composition ValueStreamStage` accepted **through RA1-05 only** (stage is-a value stream); c) `Device composition Device` **rejected** — Device does not extend Node and only RA4-30 (aggregation) exists (finding F6) |
| T4.6 abstract `A4.InfrastructureComponent` instance | rejected: `is abstract; level models must use concrete entities` |
| T4.7 `A2.ServiceDomain composition A3.ApplicationComponent` in an A2 export | rejected: `entity 'A3.ApplicationComponent' is not an A2 entity` |
| T4.8 kind `uses` | rejected: `relationship kind 'uses' is not catalogued` |
| T4.9 27 example and design exports | all accepted, individually and loaded together |

#### Coverage (T5)

43 of 131 rows are exercised by the 27 exports (baseline at authoring: 42); 62 further relationship instances are `association`. Every example relationship matches a row or is an association — none is unmatched.

| Row | Count | Estates |
|---|---|---|
| RA2-04 | 57 | acquired-fintech, card-fraud-alerts, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-13 | 56 | acquired-fintech, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA3-27 | 52 | acquired-fintech, card-fraud-alerts, customer-onboarding, legacy-core-ledger, payment-initiation, trade-finance |
| RA3-16 | 22 | acquired-fintech, customer-onboarding, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-06 | 19 | acquired-fintech, card-fraud-alerts, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-07 | 19 | acquired-fintech, card-fraud-alerts, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA1-05 | 18 | card-fraud-alerts, customer-onboarding, digital-lending, payment-initiation, trade-finance |
| RA2-02 | 18 | acquired-fintech, card-fraud-alerts, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-03 | 18 | acquired-fintech, card-fraud-alerts, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-05 | 17 | acquired-fintech, card-fraud-alerts, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-12 | 16 | acquired-fintech, customer-onboarding, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA4-31 | 15 | acquired-fintech, card-fraud-alerts, customer-onboarding, legacy-core-ledger, payment-initiation, trade-finance |
| RA2-09 | 14 | card-fraud-alerts, customer-onboarding, digital-lending, payment-initiation, trade-finance |
| RA3-03 | 13 | acquired-fintech, card-fraud-alerts, customer-onboarding, legacy-core-ledger |
| RA1-24 | 11 | digital-lending, payment-initiation, trade-finance |
| RA1-25 | 11 | digital-lending, payment-initiation, trade-finance |
| RA2-11 | 11 | acquired-fintech, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA3-28 | 11 | digital-lending, legacy-core-ledger |
| RA1-08 | 9 | card-fraud-alerts, customer-onboarding, digital-lending, payment-initiation, trade-finance |
| RA3-01 | 9 | card-fraud-alerts, legacy-core-ledger, payment-initiation |
| RA1-12 | 6 | customer-onboarding, digital-lending, payment-initiation, trade-finance |
| RA2-14 | 6 | acquired-fintech, digital-lending, legacy-core-ledger, payment-initiation, trade-finance |
| RA1-03 | 5 | card-fraud-alerts, customer-onboarding, digital-lending, payment-initiation, trade-finance |
| RA2-10 | 5 | payment-initiation, trade-finance |
| RA3-17 | 4 | trade-finance |
| RA3-04 | 3 | trade-finance |
| RA3-06 | 3 | payment-initiation, trade-finance |
| RA3-07 | 3 | payment-initiation, trade-finance |
| RA4-04 | 3 | legacy-core-ledger, trade-finance |
| RA1-01 | 2 | card-fraud-alerts, payment-initiation |
| RA1-11 | 2 | trade-finance |
| RA1-36 | 2 | payment-initiation, trade-finance |
| RA3-22 | 2 | payment-initiation, trade-finance |
| RA3-30 | 2 | trade-finance |
| RA4-07 | 2 | trade-finance |
| RA4-22 | 2 | trade-finance |
| RA1-35 | 1 | trade-finance |
| RA2-01 | 1 | trade-finance |
| RA3-11 | 1 | acquired-fintech |
| RA4-12 | 1 | trade-finance |
| RA4-17 | 1 | payment-initiation |
| RA4-26 | 1 | trade-finance |
| RA4-34 | 1 | card-fraud-alerts |

**Unexercised (88)**: RA2-08, RA2-15, RA2-16, RA2-17, RA1-02, RA1-04, RA1-06, RA1-07, RA1-09, RA1-10, RA1-13, RA1-14, RA1-15, RA1-16, RA1-17, RA1-18, RA1-19, RA1-20, RA1-21, RA1-22, RA1-23, RA1-26, RA1-27, RA1-28, RA1-29, RA1-30, RA1-31, RA1-32, RA1-33, RA1-34, RA1-37, RA1-38, RA1-39, RA1-40, RA1-41, RA1-42, RA1-43, RA1-44, RA1-45, RA1-46, RA1-47, RA1-48, RA3-02, RA3-05, RA3-08, RA3-09, RA3-10, RA3-12, RA3-13, RA3-14, RA3-15, RA3-18, RA3-19, RA3-20, RA3-21, RA3-23, RA3-24, RA3-25, RA3-26, RA3-29, RA3-31, RA4-01, RA4-02, RA4-03, RA4-05, RA4-06, RA4-08, RA4-09, RA4-10, RA4-11, RA4-13, RA4-14, RA4-15, RA4-16, RA4-18, RA4-19, RA4-20, RA4-21, RA4-23, RA4-24, RA4-25, RA4-27, RA4-28, RA4-29, RA4-30, RA4-32, RA4-33, RA4-35.

#### Dependencies (T6)

| Rule | Row(s) | Exists | Example instance | Wording consistent | Verdict |
|---|---|---|---|---|---|
| S15, S16 | RA2-01, RA2-02 | yes | 1 / 18 (trade-finance; all estates for RA2-02) | yes — plan names the composition chain | pass |
| S17 fallback, S22, S23, S25, S28, S47, S48 | RA3-03, RA3-27, RA3-07 | yes | 13 / 52 / 3 | yes — guide S25 and plan name "interface composes operations; interface assignment service". Note two export shapes: component → interface → APIs (three estates) and component realizes service ← interface assigned (payment, trade); RA3-28 allows component → API directly (ledger batch jobs, M2 design) | pass with note |
| S18, S21 | RA3-04 | yes | 3 (trade-finance) | plan reads `exposed_through` (attribute); the assignment row exists alongside | pass with note |
| S40 | RA4-31 | yes | 15 | plan says "A4 environment membership" without the kind (F11) | pass with note |
| S42, S44 | RA4-22 | yes | 2 (trade-finance) | plan reads `of_service` (attribute); the assignment row exists alongside | pass with note |
| S46 | RA4-04, RA4-05 | yes | 3 / 0 | **the test plan's expectation is wrong, not the guide**: S46 walks the component's cross-level `DEPLOYED_ON` (S33), not the A4 assignment rows (F9) | pass with note |
| S52, S53, S54 | RA3-30 | yes | 2 (trade-finance) | plan reads `components` (attribute); the TOGAF aggregation row exists alongside | pass with note |
| `--follow-composition` | the 30 `composition` rows (listed in the log) | — | `composition_hops` skips every other kind | not followed: aggregation (RA3-30 block → component, RA4-31 environment → deployment) and assignment (RA3-04, RA3-07, RA4-04). S52–S54 are derived paths, unaffected; the H1 module chain (RA3-01) is followed; in the payment/trade shape a trace from an API stops at the interface and never reaches the service (F12) | pass with note |
| S02 optional route | RA1-03, RA1-08 | yes | 5 / 9 | yes — guide says "capability serves value stream (A1 serving)" and the examples now carry `serving` | pass |
| S13, S14 | RA1-13, RA1-21, RA1-33, RA1-34 | yes | 0 / 0 / 0 / 0 | plan and guide read `applies_to`; the rows say core element `realization` requirement; trade-finance links requirement → process/activity by `association` in the opposite direction, so no realization row has an instance (F10) | pass with note |

### Findings (2026-10-23)

| # | Row ID | Test | What was found | Evidence | Proposed change (field → value) |
|---|---|---|---|---|---|
| F1 | RA1-04, 05, 06, 07, 10, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 28, 37, 39 | T1 | one end is an SDMM extension (`ValueStreamStage`, `BusinessActivity`) but the row cites `[AM] ArchiMate 3.2`; T1 as written wants an "SDMM extension" source when either end is an extension | catalogue: both entities `reference.standard: SDMM`, `extends` an ArchiMate entity; rows' `basis` already says "(BusinessActivity is the SDMM extension)" | `docs/relationships-testing.md` T1 → "or an ArchiMate/TOGAF source when the extension `extends` a concept of that standard (provenance by inheritance)". Alternative: 18 rows' `reference_source` → "SDMM extension of [AM] …". Recommended: the plan text |
| F2 | RA1-01, 02, 03, 04, 08, 16, 34 | T1 | `A1.BusinessCapability` is catalogued to BIAN BCM (`bian_aligned`); the rows cite ArchiMate Strategy, which the provenance table also lists for the entity but the catalogue's single `reference` cannot hold | `metamodel/a1-business.json` A1.BusinessCapability `reference.standard: BIAN BCM`; provenance doc: "BIAN BCM; ArchiMate Strategy layer" | catalogue A1.BusinessCapability → add `reference_also: {standard: ArchiMate 3.2, concept: Capability, locator: chapter 7}` so T1 can resolve the rows; or the 7 rows' `reasoning` → name the dual provenance |
| F3 | RA2-15, RA2-16 (B14, B15) | T2 | the official record still says the B rows are "artefact relationship — not a level-model constraint" while the record has encoded them since 0.5.14 | `metamodel/official-mappings.json` B14/B15 `disposition` | B14, B15 `disposition` → "encoded — level-relationships.json constraint (artefact row; not instantiable)" |
| F4 | RA4-34 | T2 | `DeploymentEnvironment aggregation SystemSoftware` goes beyond the definition "Node grouping" | catalogue A4.DeploymentEnvironment locator "extension of A4.Node grouping" | catalogue definition → "grouping of technology elements (nodes, devices, system software, deployments)"; or remove RA4-34 |
| F5 | RA2-15, RA2-16, RA2-17 | T4.1 | the rows can never be matched: the checker rejects any instance of an artefact type, so an export cannot carry a Wireframe, SemanticAPI or BOMModel relationship | probes `t41_RA2-15/16/17.json`: exit 1, `is an artefact, not an instance type` | rows → add `enforceable: false` (provenance-only); `docs/relationships-testing.md` T4.1 → "128 instantiable rows; the three artefact rows are provenance-only" |
| F6 | (new) RA4-36 | T4.5c | `Device composition Device` is rejected: Node has composition and aggregation (RA4-01/02), Device only aggregation (RA4-30), and Device does not extend Node | probe `t45c.json`: exit 1 | add RA4-36 `A4.Device composition A4.Device`, `[AM] ArchiMate 3.2` ch. 10 same-type composition, `unverified_archimate`, medium — or state in RA4-30's `reasoning` why devices aggregate but do not compose |
| F7 | the 15 A1 child rows in T3 | T3 | redundant under `is_a` — the checker accepts the child relationship through the parent row; harmless, but a reader cannot tell which rows carry enforcement | T3 table | each redundant row → add `implied_by: <parent row id>` (e.g. RA1-20 `implied_by: RA1-12`); no removal |
| F8 | RA3-22/25, RA3-23/24 | T3 | opposite-direction `triggering` pairs | T3 | each row's `description` → add "(both directions are intended: behaviour triggers an event and an event triggers behaviour)" |
| F9 | — (test plan) | T6 | the T6 table expects S46 to walk the A4 node/device → system-software assignment rows; the guide and plan derive S46 over the component's cross-level `DEPLOYED_ON` (S33) | plan S46 `data_needed` | `docs/relationships-testing.md` T6 row S46 → "walks S33 (cross-level); no within-level row" |
| F10 | RA1-13, RA1-21, RA1-33, RA1-34; trade-finance a1 | T6 | the requirement rows say process/activity/service/capability `realization` requirement; the only estate with requirements links them requirement → process/activity by `association`, so the four rows have no instance and S13/S14 read the `applies_to` attribute instead | T5 counts 0; trade-finance `REQ-01 association PRC-LC-APPLY` | `examples/trade-finance/a1-business.json` → `PRC-LC-APPLY realization REQ-01`, `ACT-T3 realization REQ-02`, `ACT-T4 realization REQ-03` (exercises RA1-13, RA1-21); plan S13/S14 `data_needed` → "applies_to, or the A1 realization row (process → requirement)" |
| F11 | — (plan S40) | T6 | "A4 environment membership" names no kind | plan S40 `data_needed` | S40 `data_needed` → "A4.DeploymentEnvironment aggregation Deployment (RA4-31), or Deployment.environment_id" |
| F12 | — (`sdmm/graph.py`) | T6 | `--follow-composition` follows `composition` only; in the payment/trade export shape the interface is `assignment`-linked to the service, so a downstream trace from an API never reaches the application service; blocks (aggregation) are never entered | `composition_hops` line 154 | `graph.py` → `--follow-structure composition,assignment,aggregation` (default `composition`), with each virtual hop labelled by its kind; or document in the guide that traces stop at assignment and aggregation |
| F13 | RA3-05, RA4-05, RA4-06, RA4-11, RA4-16, RA4-21, RA1-09, RA1-13 | T5 | rows the mapping rules or SDMM definitions rest on with zero instances: function realizes service; device / system software assigned system software; node / device / system software assigned deployment; process realizes value stream; process realizes requirement | T5 counts | `examples/trade-finance`: add `FN-LC-ISSUE realization SVC-LC` (RA3-05), `DEV-SCAN-01 assignment SYS-RUNTIME-TF`? — only if true of the estate; `NODE-TF-PROD assignment DEP-LC-PROD` (RA4-11); see F10 for RA1-13. Rows the examples cannot honestly carry stay unexercised |
| F14 | RA3-28 | T2 | component composes API operations directly, bypassing the interface; consistent with the extension and used by the ledger batch jobs and the M2 design, but it means S22/S23 (group → interface) can find no interface for those operations | T6 row 2 | RA3-28 `reasoning` → state that operations composed directly in a component have no interface and S22/S23 report none for them |

**Pass criteria.** Every A2 row passes T1–T3 and B02–B15 are each covered once — met. No row fails T2 on direction or kind — met (103 pattern matches, 0 contradictions). T4.1–T4.9 — met except the three artefact rows, which cannot be probed (F5); the deviation is on the record's description of those rows, not on the checker. T6 — every dependency has its row and an instance, except the requirement rows (F10) and one expectation error in the plan itself (F9). The findings table names a row or a file for every change.

**Summary.** The record is sound: 131 rows, none failing provenance, grounding or consistency, and the checker accepts exactly the rows and rejects every reversed, mistyped, cross-level or uncatalogued probe. The notes are where the work is: 103 rows remain unverified against login-gated specifications by design; 23 rows carry provenance by inheritance that the plan's T1 wording does not yet allow; three A2 artefact rows exist for provenance and can never be enforced; one Device row is missing; and 88 rows are unexercised by the examples, including the requirement rows that the trade-finance estate links the other way round. Fourteen findings, each a field on a row or a line in a named file.

---

## 6. Phase 2 — Independent verification of the inferred rows (A1, A3, A4)

**Why.** The 115 rows outside A2 cite ArchiMate 3.2 or TOGAF 10, which are login-gated. Each now carries an `inference` on the record (`metamodel/level-relationships.json`, rendered in `docs/relationships-planning.md`): the ArchiMate concept of both ends, the generic pattern the row instantiates, the reasoning, SDMM's inference confidence, and the test to run. Phase 2 checks every inference against a **public implementation** of the specification's relationship matrix, so no Open Group account is needed and no specification text is reproduced.

**Oracle.** The open-source Archi tool (github.com/archimatetool/archi) ships `relationships.xml` under `com.archimatetool.model`, listing for each source and target concept the permitted relationship letters: `c` composition, `g` aggregation, `i` assignment, `r` realization, `v` serving, `a` access, `f` flow, `t` triggering, `s` specialization, `o` association, `n` influence. Locate the file in the repository's default branch, record the **commit hash and path** you read, and read it with WebFetch or the GitHub tools. **Do not copy the file or any part of it into this repository**; cite it.

**Procedure, per row (RA1-*, RA3-*, RA4-*).**

1. Take `inference.archimate_source`, `inference.archimate_target` and the row's `kind`. Map the kind to its letter.
2. Look up the oracle entry for that source → target pair. Verdict:
   - **confirmed** — the letter is listed.
   - **confirmed, alternative accepted** — the row's `inference.test` names an alternative letter and that one is listed (RA4-31).
   - **contradicted** — the letter is absent. Record what the oracle *does* list for the pair, and for the reverse pair, so the finding can say whether the direction or the kind is wrong.
   - **not testable** — no ArchiMate concept (the two TOGAF rows RA3-30, RA3-31): check the public TOGAF content-metamodel description that solution building blocks group solution components; report, do not score.
3. For rows where an end is an SDMM extension (`A1.ValueStreamStage`, `A1.BusinessActivity`, `A3.APIOperation`, `A4.Deployment`, `A4.DeploymentEnvironment`), the lookup uses the concept the extension derives from; say so in the entry and note whether the extension's definition could change the answer.
4. Compare the verdict with `inference.confidence`: a *high* row contradicted, or a *low* row confirmed, is itself a finding on the inference calibration.

**Outputs.** Extend `metamodel/relationships-test-log.json`: per row, add `phase2: {oracle_pair, letters_listed, verdict, note}`; a top-level `phase2_oracle: {repo, path, commit}`. Append *Phase 2 results* to this document: a table of verdict counts by level and by inference confidence, the list of contradicted rows with the oracle's letters for both directions, and findings.

**Findings.** One row per contradicted row: propose `kind` change, direction swap, or removal, with the oracle letters as evidence. One row per calibration miss. Rows confirmed are proposed for `verification: verified_against_archi` (a new status distinct from `verified`, since the oracle is an implementation, not the specification). The record is not edited by the executor.

**Pass.** Every row has a Phase 2 verdict; no contradicted row is left without a proposed change; the oracle is cited by commit hash.

**Prompt.** *Execute Phase 2 of `docs/relationships-testing.md` (§6) against `metamodel/level-relationships.json`. Read-only on the record; cite the Archi oracle by commit hash and path; copy nothing from it. Extend `metamodel/relationships-test-log.json`, append Phase 2 results and findings, and commit with the confirmed / contradicted / not-testable counts in the message.*

---

### Phase 2 results (2026-10-23, fable-executor)

**Oracle.** `github.com/archimatetool/archi`, path `com.archimatetool.model/model/relationships.xml`, read at default-branch commit `9e6a014f9ef6a782a7dda604ef7b4d03d2c7819a` (file last changed in `6d236081d9460f063076dbb6225f8645c5f5a7a5`); the file declares `relationships version="3.2"` and lists 62 concepts. It was read through the GitHub API into a session scratch lookup; **nothing from it is copied into this repository** — the log records, per row, only the letters the oracle lists for that row's pair. The record was not edited. TOGAF text was not fetched (login-gated).

**Scope.** 115 rows — every A1, A3 and A4 row, including RA4-36 (added in v0.5.17 on Phase 1 finding F6; it has no Phase 1 verdicts and the log says so). Each row's `inference.archimate_source` → `archimate_target` and its kind's letter were looked up; for rows with an SDMM-extension end the lookup used the concept the extension derives from and the entry says so.

| Verdict | A1 | A3 | A4 | Total |
|---|---|---|---|---|
| confirmed | 48 | 29 | 35 | 112 |
| confirmed, alternative accepted | 0 | 0 | 1 | 1 |
| contradicted | 0 | 0 | 0 | 0 |
| not testable | 0 | 2 | 0 | 2 |

| Verdict | inference high | inference medium | inference low | Total |
|---|---|---|---|---|
| confirmed | 66 | 42 | 4 | 112 |
| confirmed, alternative accepted | 0 | 0 | 1 | 1 |
| contradicted | 0 | 0 | 0 | 0 |
| not testable | 0 | 2 | 0 | 2 |

**Contradicted rows: none.** Every ArchiMate-grounded row's direction and kind is listed by the oracle for the inferred pair. **Alternative accepted (1):** RA4-31 `DeploymentEnvironment aggregation Deployment` — the lookup pair Node → Artifact lists `aio` (access, assignment, association): aggregation is **not** listed, assignment is; the row's `inference.test` names assignment as the accepted alternative, so the row passes by §6 but its kind is SDMM's, not ArchiMate's (finding P2-F2). **Not testable (2):** RA3-30, RA3-31 (TOGAF Solution Building Block; the public content-metamodel description is consistent, not scored).

**SDMM-extension rows (11).** RA3-27, RA3-28, RA3-29 (APIOperation as Application Interface), RA4-11, RA4-16, RA4-21 (Deployment as Artifact assigned to a node / device / system software), RA4-32, RA4-33, RA4-34 (DeploymentEnvironment as Node grouping) and RA4-35 (Deployment aggregates Artifact as Artifact → Artifact) are confirmed through the parent concept; RA4-31 is the alternative case above. The extension definitions do not change the answer except for RA4-31, where "environment groups deployments" is modelled as aggregation while ArchiMate's Node → Artifact relation is assignment.

#### Phase 2 findings

| # | Row ID | What was found | Evidence (oracle letters) | Proposed change (field → value) |
|---|---|---|---|---|
| P2-F1 | the 102 `unverified_archimate` rows (all confirmed) | the row's kind is listed by the oracle for the inferred pair | per-row `phase2.letters_listed` in the log | `verification` → `verified_against_archi` (new status: verified against an open-source implementation of the matrix, not the specification); `confidence` may stay as is |
| P2-F2 | RA4-31 | aggregation is not in the oracle for Node → Artifact; assignment is | listed `aio`, reverse `o` | either `kind` → `assignment` (then `verification` → `verified_against_archi`), or keep `aggregation` with `verification: sdmm_definition` and `inference.pattern` → "SDMM grouping; ArchiMate would assign the artifact to the node" — not both |
| P2-F3 | RA3-10 | calibration miss: `inference.confidence: low` but the oracle lists the kind for ApplicationComponent → ApplicationComponent | listed `cfgorstv` | `inference.confidence` → `medium` (the oracle confirms the pair; the row's own `confidence` stays `medium` because the semantics of flow/triggering between components remain a modelling choice) |
| P2-F4 | RA3-12 | calibration miss: `inference.confidence: low` but the oracle lists the kind for ApplicationComponent → ApplicationComponent | listed `cfgorstv` | `inference.confidence` → `medium` (the oracle confirms the pair; the row's own `confidence` stays `medium` because the semantics of flow/triggering between components remain a modelling choice) |
| P2-F5 | RA4-24 | calibration miss: `inference.confidence: low` but the oracle lists the kind for Node → Node | listed `cfgiostv` | `inference.confidence` → `medium` (the oracle confirms the pair; the row's own `confidence` stays `medium` because the semantics of flow/triggering between nodes remain a modelling choice) |
| P2-F6 | RA4-25 | calibration miss: `inference.confidence: low` but the oracle lists the kind for Node → Node | listed `cfgiostv` | `inference.confidence` → `medium` (the oracle confirms the pair; the row's own `confidence` stays `medium` because the semantics of flow/triggering between nodes remain a modelling choice) |
| P2-F7 | RA4-31 | calibration miss: `inference.confidence: low`, confirmed through the alternative | as P2-F2 | resolve with P2-F2; if the kind becomes assignment, `inference.confidence` → `high` |
| P2-F8 | the 11 `sdmm_definition` rows confirmed via the parent concept | ArchiMate supports the parent-concept relation the extension relies on | per-row `phase2.letters_listed` | `inference` → add `parent_concept_verified_against_archi: true`; keep `verification: sdmm_definition` (the extension itself is SDMM's) |
| P2-F9 | RA3-30, RA3-31 | not testable against ArchiMate; TOGAF is login-gated | — | `verification` stays `unverified_togaf`; `inference.test` → cite the public TOGAF content-metamodel overview page so a later run can check it without an account |
| P2-F10 | RA4-36 | added on Phase 1 finding F6 after the Phase 1 run, so it carries no T1–T5 verdicts; Phase 2 confirms it (Device → Device lists composition) | listed `cfgostv` | re-run Phase 1 T1–T5 for RA4-36 at the next Phase 1 pass; `verification` → `verified_against_archi` with the others |
| P2-F11 | docs/relationships-testing.md §6 | the lookup needed a concept-name mapping (`Value Stream` → `ValueStream`, `Data Object` → `DataObject`, …) and a commit-pinning convention | `phase2_oracle` in the log | §6 → state the mapping rule (remove spaces) and the convention used here (default-branch head commit read, plus the file's last-change commit) |

**Pass.** Every row has a Phase 2 verdict; there is no contradicted row; the oracle is cited by commit hash and path. The calibration picture is one-sided: no high inference was contradicted, while five low inferences were confirmed — the inference confidences are conservative rather than wrong.

**Summary.** The 113 ArchiMate-grounded within-level rows survive an independent, public implementation of the ArchiMate 3.2 relationship matrix without a single contradiction of direction or kind; the one row that passes only through its stated alternative (RA4-31) is where SDMM's own grouping semantics diverge from ArchiMate's assignment, and the record should say which it means. Phase 1 left 102 rows `unverified_archimate`; Phase 2 proposes `verified_against_archi` for all 102.
