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

For each row, read the source and target entity's `reference.concept` in the catalogue. The row's `reference_source` must be the reference architecture that **both** concepts derive from (A2: BIAN; A1/A3/A4: ArchiMate, or TOGAF for `A3.SolutionBuildingBlock`, or an SDMM extension row when either end is an SDMM extension entity). A row that relates an ArchiMate concept to a BIAN concept inside one level, or cites a source neither entity derives from, **fails**.

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

For each row, count the relationship instances across all example exports that match it (directly or through inheritance). Produce the table *row → count → estates*. Rows with zero instances are **not tested by data**; list them. (Baseline at authoring: 42 of 131 rows are exercised. The gap is expected — many ArchiMate rows are legitimate but unused — and is reported, not failed.)

### T6 — Dependency: the mapping rules find the rows they walk

Every cross-level rule that derives over within-level structure depends on specific rows. For each dependency below, confirm (a) the row exists, (b) at least one example estate carries an instance of it, (c) the guide or plan text names the same kind as the row. A mismatch between the guide's wording and the row's kind is a **fail** on the guide, not the row.

| Rule | Walks | Row(s) expected |
|---|---|---|
| S15, S16 (area / domain → component) | A2 composition area → domain → Service Domain | RA2 rows for B02, B03 |
| S17 fallback, S22, S23, S25, S28, S47, S48 | A3: component composes interface; interface composes API operations; interface assigned to service | the A3 rows for those three pairs |
| S18, S21 (function rows) | A3: component assigned to function; function exposed through APIs (`exposed_through` key, not a relationship) | component → function row; note that `exposed_through` is an attribute |
| S40 | A4: environment aggregates deployment | the A4 environment row |
| S42, S44 | A4: technology interface assigned to technology service | the A4 interface → service row |
| S46 | A4: node / device assigned system software | the A4 assignment rows |
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
