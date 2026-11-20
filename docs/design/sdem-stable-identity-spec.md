# Stable identity for layers and types — step 3 of SDEM 0.20 (spec)

> **Status: approved (2026-11-20) — the owner: "yes to all, go ahead" (ST-D1…ST-D6, §8).** Step 3 of the [0.20 plan](sdem-0.20-plan.md)
> (approved, PL-D1: before the Data layer). Builds on steps 1 and 2 ([BIAN extension](sdem-bian-extension-spec.md),
> [BIAN package](sdem-bian-package-spec.md)), the [layer registry](sdem-layers-spec.md) (LR-…) and
> [metamodel stability](sdem-metamodel-stability.md) (MS-…).

## 1. The problem, measured (2026-11-20)

A type's name carries its layer's position: `A3.ApplicationComponent` means "the third layer". In 0.20 the position moves — Application is
A3 in the default and A4 with BIAN — so the name of the same thing would change when a person switches an extension on. Today the
position is written:

| Where | How often |
|---|---|
| SDEM's code — type names (`'A3.ApplicationComponent'`) | ~570, in 26 modules |
| SDEM's code — layer codes (`'A3'`) | ~520 |
| the metamodel | 50 types |
| the examples' records and links | ~2,800 type names |
| skills, templates, docs | ~155 files |

## 2. The rule

| Id | Rule |
|---|---|
| **ST-01** | **Every layer has an id that never changes**: `business`, `data`, `application`, `technology` — and an extension's: `bian` (BIAN's Service Domain layer), `security`. |
| **ST-02** | **Every type has an id that never changes**: `<layer id>.<TypeName>` — `application.ApplicationComponent`, `bian.ServiceDomain`. A type that moves layer (`A3.DataEntity` → the Data layer, step 4) gets its new id once, with its old one kept as an alias (ST-05). |
| **ST-03** | **The A-number is computed, never stored as identity**: the layers in use, in their order, numbered from A1 (Business). It is what a person reads — `A3`, `A3.ApplicationComponent` — and SDEM shows it everywhere it does now. |
| **ST-04** | **One table**, `metamodel/identity.json`: each layer id with its order and the extension that provides it; each type id with its 0.19 name. SDEM reads every name through it; a name the table does not know is an error, never guessed. |
| **ST-05** | **Old names keep working**: `A3.ApplicationComponent` in a file, a command or a link is read as `application.ApplicationComponent` for as long as 0.20 lasts — so no workspace, script or published design breaks. |

## 3. What step 3 changes — and what it does not

In step 3 the stack is still 0.19's (Business, BIAN, Application with its data, Technology), so **every computed A-number is the same as
0.19's** — `application` is A3, BIAN is A2. Step 3 therefore changes how SDEM *knows* a layer and a type, not what anyone *sees*:

| Changes | Stays |
|---|---|
| SDEM's code asks the table for a layer or type by id, instead of writing `'A3.…'` | every answer, every file, every command — **P1: the 32 recorded answers byte-identical** |
| `sdem types --ids` shows each type's id beside its name | workspace files keep 0.19's names (no migration; ST-05) |
| an extension may name types by id | DESNRE, the examples, the skills and docs |

The A-numbers start to move only in step 4 (the Data layer) and step 5 (BIAN on the default); that is where P2 (identical after
translation) is needed.

## 4. Files, from step 4

| Id | Rule |
|---|---|
| **ST-10** | **From step 4, workspace files store type ids**, not A-names — so a record's identity does not change when BIAN is switched on or off. Step 4's migration rewrites them (preview, backup, rollback); a file with 0.19's names is still read (ST-05). |
| **ST-11** | What a person reads stays the A-name (ST-03): `sdem check`, `document`, the workbench, DESNRE. |

## 5. The code interface for extensions (BP-D6)

| Id | Rule |
|---|---|
| **ST-20** | **`sdem.api`, a published, versioned Python interface** — the metamodel by type id, a workspace's records and links, the catalogue folder, writing a change set, registering an inference step. Its version is in the manifest (`"api": ">=1,<2"`); SDEM keeps it stable within a major version. |
| **ST-21** | **EXT-02 is amended**: an extension may use SDEM through its commands *or* through `sdem.api` — never through any other module. A test fails if a package imports anything else of SDEM's. |
| **ST-22** | **BIAN's code moves through it**: the `sdem bian` commands and the inference steps that go through service domains (BP-03, BP-04) move to `sdem-bian`, written against `sdem.api` and type ids. SDEM keeps its built-in copy as the fallback for all of 0.20 (BP-10), held identical by test. |

## 6. Order inside step 3 — each part proved by P1 before the next

| Part | What | Size |
|---|---|---|
| 3a | `metamodel/identity.json`, the lookup (`sdem/identity.py`), the computed A-number; `sdem types --ids` | small |
| 3b | the core's code moves from written names to ids, **module by module** — the layer registry, metamodel, validation and conformance first; the rules engine and AID last | ~1,100 places, 26 modules |
| 3c | `sdem.api` (ST-20, ST-21) | medium |
| 3d | BIAN's code into `sdem-bian` through it (ST-22) | ~1,200 lines and the A2 inference steps |

A part is committed only with the 32 answers byte-identical and the full suite green.

## 7. Risks

| Risk | Answer |
|---|---|
| a missed `'A3.'` in the code keeps the old position | after 3b, a test fails on any type name or layer code written in SDEM's code outside `identity.json` |
| the computed A-number differs from 0.19's | P1 — any difference fails |
| `sdem.api` frozen too early | it starts at `0.x` (unstable) through 0.20; `1.0` when 0.20 is released |

## 8. Decisions for the owner

| # | Decision | Decided |
|---|---|---|
| ST-D1 | Layer and type ids as in ST-01, ST-02 (`application.ApplicationComponent`, `bian.ServiceDomain`) | **yes** |
| ST-D2 | Step 3 changes nothing a person sees; proved byte-identical (P1), not just after translation | **yes** |
| ST-D3 | Old names are read for all of 0.20 (ST-05) | **yes** |
| ST-D4 | Workspace files store type ids from step 4's migration (ST-10) | **yes** — identity must not change when BIAN is switched |
| ST-D5 | `sdem.api` as the one code interface for extensions; EXT-02 amended (ST-20, ST-21) | **yes** |
| ST-D6 | BIAN's code and inference steps move to `sdem-bian` in step 3 through it (ST-22) | **yes** |
| ST-D7 | **ST-22 split** (2026-11-20, the owner: "split it"): in step 3, `sdem.api` and the `sdem bian` commands (`bian.py`, `inferences.py`) move to `sdem-bian`; the engines' BIAN inference steps — woven through 27 functions of the rules engine, AID, its fill and link steps and containment — are extracted in **step 5**, through a plug-in point designed with the service domain → data → application paths (PL-D4). Until then they stay in SDEM, off where BIAN is off | **yes** |

## 9. As built (2026-11-20, branch `release/0.20`)

| Part | Where | Proof |
|---|---|---|
| **3a** | `metamodel/identity.json` (4 layers, 50 types, each with its 0.19 name); `sdem/identity.py` — `T`, `layer`, `type_id`, `layer_id`, cached; `sdem types --ids`; `sdem types <type id>` | 32 answers identical; `tests/test_identity.py` |
| **3b** | 1,073 names written in 46 modules — every string that was exactly a type name or layer code is `_T('<type id>')` / `_L('<layer id>')`; the 8 `'A2.'` prefix checks `_L('bian') + '.'` | 32 answers identical after each of three batches; the rules engine as fast (3,000 records in 0.6 s) |
| **3c** | `sdem/api.py`, version **0.1**: the metamodel and identity, a workspace, the graph, SDEM's writer, `is_person`, and `run(command, main, argv)` — an extension's code for one of SDEM's commands, run through SDEM's own command line; EXT-02 amended (ST-21) | `sdem.api` loads lazily; anything else refused by name |
| **3d-1** | `sdem-bian` 1.0.0.dev2 carries the `sdem bian` commands (`bian.py`, `inferences.py`), generated from SDEM's by `scripts/bian_package.py` with every import of SDEM's code turned into `sdem.api`; its manifest names `commands` and `api`; `sdem bian …` runs the package's code when it is installed and supports this `sdem.api`, SDEM's own otherwise (BP-10) | 32 answers identical through the package's code (a real install, and a stand-in in SDEM's tests); the package imports only `sdem.api`; package and SDEM's copy identical (BP-11) |
| **3d-2** | the engines' BIAN inference steps — **step 5** (ST-D7) | — |

**Not yet as the spec said (§7):** 271 labels and messages still carry an A-number written as text ("A1 Business", "not an A2 dataset"). They are right while the stack is 0.19's; a test lets their count only go down (`tests/data/identity-text-baseline.json`), and step 4, where the numbers move, computes them.
