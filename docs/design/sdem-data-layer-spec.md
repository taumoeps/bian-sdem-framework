# The Data layer — step 4 of SDEM 0.20 (spec)

> **Status: approved (2026-11-21) — the owner: "go ahead" (DL-D1…DL-D8 as recommended, §9).** Step 4 of the [0.20 plan](sdem-0.20-plan.md)
> (approved). Builds on [stable identity](sdem-stable-identity-spec.md) (ST-…, step 3), the [BIAN extension](sdem-bian-extension-spec.md)
> and [package](sdem-bian-package-spec.md) (steps 1, 2), the [layer registry](sdem-layers-spec.md) (LR-…) and the
> [Architecture viewpoint](sdem-architecture-viewpoint-spec.md) (ARV-…), which already draws data as a plate of its own.

## 1. Where it ends

| | 0.19 | **0.20 default** | **0.20 + BIAN** |
|---|---|---|---|
| Business | A1 | A1 | A1 |
| Service Domain (BIAN) | A2 | — | A2 |
| **Data** | inside A3 | **A2** | **A3** |
| Application | A3 | A3 | A4 |
| Technology | A4 | A4 | A5 |

## 2. What data is in SDEM today (surveyed 2026-11-20)

| | |
|---|---|
| types | `A3.DataEntity`, `A3.DataAttribute` |
| within-A3 rules that touch them | 11 — 5 are *access* (component, function, service, event, API operation → data entity); 6 are data's own structure (composition, aggregation, specialization, association, entity → attribute) |
| link types to other layers | 5 — business object → entity (A1, A2: `MAPPED_TO`), BIAN attribute → data attribute (`FIELD_MAPPED_TO`), entity → artifact / system software (A4: `STORED_IN`) |
| inference rules | 7 |
| records in the examples | 88 entities, 140 attributes |

## 3. The layer

| Id | Rule |
|---|---|
| **DL-01** | **A core layer `data`** between Business (and BIAN, when on) and Application — the Data Architecture of TOGAF's four domains. Its agent `sdem-data`; its file `data.json` (DL-10). |
| **DL-02** | **Its types move from Application unchanged**: `data.DataEntity`, `data.DataAttribute` — same fields, same rules. `application.DataEntity` and `A3.DataEntity` are read as their aliases (ST-05). New data types (domain, model, contract, store, classification) each come with their own spec, later (PL-D3). |
| **DL-03** | **Data's own structure stays inside its layer**: the 6 within-layer rules (composition, aggregation, specialization, association, entity → attribute) become level `data`. |
| **DL-04** | **Access becomes a link between layers**: application component, function, service, event and API operation → data entity, link type `ACCESSES` (ArchiMate's *access*), Application → Data. |
| **DL-05** | **The links to other layers keep their meaning, with new ends**: `MAPPED_TO` from business object (and BIAN's), `FIELD_MAPPED_TO` from BIAN's attribute, `STORED_IN` to technology — now from or to the Data layer. Whether a link between non-neighbours is allowed is LR-06's question, answered for each in step 5 (PL-D4); in step 4 each of these is allowed as it was. |

## 4. Numbering

| Id | Rule |
|---|---|
| **DL-06** | **The A-number is computed from the layers in use** (ST-03) — no position is held for a layer that is off: default A1–A4, with BIAN A1–A5. BX-04's reserved A2 ends. |
| **DL-07** | **Every label and message carries the computed number** — the 271 texts still written with an A-number in step 3 (the ratchet, `tests/data/identity-text-baseline.json`) are computed; the ratchet's count ends at 0. |

## 5. Files and migration

| Id | Rule |
|---|---|
| **DL-10** | **Layer files are named by layer id**: `business.json`, `bian.json`, `data.json`, `application.json`, `technology.json` — a number in a file name would change with BIAN (ST-10). 0.19's names (`a1-business.json` …) are still read. |
| **DL-11** | **Records store type ids** (ST-10): `"type": "data.DataEntity"`. What a person reads is the computed name (`A2.DataEntity`, or `A3.DataEntity` with BIAN). |
| **DL-12** | **`sdem migrate --to 0.20`** moves a workspace: data records out of the application file into `data.json`; type names to ids; files renamed; access links to `ACCESSES` mappings (DL-13). **Only on a person's command**; `--dry-run` shows every change; a backup is written first; `sdem migrate --rollback` restores it exactly. A workspace not migrated is still read (ST-05) and says it can be migrated. |
| **DL-13** | **An access link that was within A3 becomes an approved link between layers**, recorded as approved *by the migration* — by the person who ran it, evidence `migration:0.19-within-layer-access`, with the original link's own source kept. Nothing is lost and nobody has to re-approve what their design already said; `sdem status` lists them, so a person can review them. |

## 6. Everything that reads a layer

| Id | Rule |
|---|---|
| **DL-20** | The examples are migrated in the repository (the synthetic data only); the golden answers are re-recorded **only through translation** (P2): the 32 answers of 0.19, translated by `identity.json`, must equal the new ones; every other difference is named here and approved. |
| **DL-21** | A made-up **non-banking** example in four layers (default) runs every command end to end (P3). |
| **DL-22** | **Security** (`sdem-security`): S3 *Data security* attaches to the Data layer; its link types to `A3.DataEntity`/`A3.DataAttribute` name the data ids. **BIAN** (`sdem-bian`): its `MAPPED_TO` and `FIELD_MAPPED_TO` name the data ids. Each package gets a release for 0.20. |
| **DL-23** | **The Architecture viewpoint** draws Data from the Data layer — the plate it already draws; **DESNRE** receives the same plates (its layout is decided in the DESNRE project, not here). The DESNRE publisher sends the computed numbers. |
| **DL-24** | **Skills, agent instructions and docs** name layers by name and the computed number (the agents' `sdem-data`). |
| **DL-25** | **A layer named in what a person or agent writes means one layer, in either form.** A change set (`"layer"`) may name its layer by **id** (`application`), which means the same layer in either form, or by its code as this workspace numbers it; a code is never re-read as 0.19's (ST-04: never guessed) — when an agent's 0.19 number is another layer's here, CTL-19's refusal says which layer that number is now and how to name its own. **An organisation profile** names layers in 0.19's numbering (A1 Business, A2 BIAN, A3 Application, A4 Technology, its own layers by its own codes) — one profile serves workspaces in both forms; in a workspace numbered otherwise its core codes are read as the layers they name, and an own layer whose code is now a core layer's takes the next free A-number (its type names, e.g. `BANK.A5.Facility`, are ids and do not change). |
| **DL-26** | **What comes from outside a workspace is read in its own form.** An intake package (`sdem intake`, written to the authoring guide) and `sdem transform`'s candidates are in 0.19's form — Data's records in the application file. `sdem intake` checks and takes a package in that form, then migrates the new workspace when 0.20 is the default; the accesses it moves become **proposed** `ACCESSED_BY` links (nobody has reviewed a design just taken in) — **approved** only with `--accept`, where the person takes the design as authored. `sdem load` into a migrated workspace runs in its 0.19 view, as `sdem aid` does: Data's records go to `data.json`, an access the past design states becomes a proposed `ACCESSED_BY` in `loads/LOAD-…-proposals.json`. An existing workspace in 0.20's form is not a target for `sdem intake` (it starts a design). |

## 7. Order inside step 4

| Part | What | Proof |
|---|---|---|
| 4a | numbering from layers in use (DL-06); every label computed (DL-07) | with BIAN on, the 32 answers byte-identical (nothing moves yet) |
| 4b | layer files by id and records by type id, read both ways (DL-10, DL-11) — reading only | the 32 answers byte-identical |
| 4c | the Data layer: types, rules, `ACCESSES`, links to other layers, inference rules (DL-01…DL-05) | **P2**: the 32 answers translated |
| 4d | `sdem migrate --to 0.20`, backup, rollback (DL-12, DL-13); the examples migrated (DL-20) | migrate → rollback restores every byte; P2 on the migrated examples |
| 4e | the non-banking example (DL-21) | **P3** |
| 4f | security and BIAN packages, the viewpoint, DESNRE publisher, skills and docs (DL-22…DL-24) | their tests; CI on both repositories |

## 8. Risks

| Risk | Answer |
|---|---|
| the access links' governance changes (within-layer needed no approval) | DL-13: approved by the migration, listed for review — never silently, never re-asked |
| a published design (DESNRE) shows old numbers | the publisher sends computed numbers; a design not re-published keeps showing what it showed (EL-04) |
| data's inference rules weaken when data is no longer inside Application | P2 on `aid` and `link` answers: every proposal must survive, translated |
| BIAN's service domain → application links now pass the Data layer | allowed as in 0.19 in step 4 (DL-05); designed in step 5 (PL-D4) |

## 9. Decisions for the owner

| # | Decision | Decided |
|---|---|---|
| DL-D1 | A core layer `data` between Business (and BIAN) and Application (DL-01) | **yes** |
| DL-D2 | Its types move unchanged; new data types each have their own spec later (DL-02) | **yes** |
| DL-D3 | Access becomes a link between layers, `ACCESSES` (DL-04) | **yes** — the layer boundary is what makes Data a layer |
| DL-D4 | Migrated access links are approved by the migration and listed for review (DL-13) | **yes** — alternative: mark them *proposed* and have a person approve each |
| DL-D5 | Numbering from the layers in use; BIAN's reserved A2 ends (DL-06) | **yes** |
| DL-D6 | Layer files named by layer id; records store type ids; old names read (DL-10, DL-11) | **yes** |
| DL-D7 | Migration only on a person's command, with dry run, backup and rollback (DL-12) | **yes** |
| DL-D8 | Security and BIAN packages each get a 0.20 release naming the data ids (DL-22) | **yes** |

## 10. As built so far (2026-11-21, branch `release/0.20`)

| Part | Where | Proof |
|---|---|---|
| **4b** | one boundary for a design's files — `sdem/identity.py` `load`, `loads`, `for_file`: reading accepts an id, a name as read now or a 0.19 name, **by the file's form** (an unmigrated file holds 0.19's names and codes; a migrated one ids); writing gives the file's own form; 194 reads and 31 direct writes routed through it; graph stores are derived and not translated | P1 |
| **4a** | the A-number from the layers in use (DL-06): `identity.stack()`; BIAN's reserved A2 ends; a layer not in use has a code nothing matches (`(bian)`); 46 module tables live (`identity.live`), recomputed when the stack changes; 266 labels and messages computed (DL-07) — 26 texts left name no layer of the stack (record and dataset ids, an organisation's types, page templates, history), held by a ratchet | P1; a core-only design reads A1–A3 |
| **4c-1** | the workspace's **form** (migrated or not), set when it is opened (`parts.migrated()`), decides its files' names (DL-10): `identity.F(layer id)` — 70 file names in the code; graph files too | P1 |
| **4c** | the Data layer (DL-01…DL-05): `data` in `metamodel/identity.json`; `data.DataEntity`, `data.DataAttribute` (their step-3 ids kept as aliases); a type's layer from its id; the 5 within-Application access rules become **`ACCESSED_BY`** link types (Data → Application); adjacency judged with Data counted as part of Application, so every link type of 0.19 is as valid as it was (DL-05); SDEM's standards read through `sdem/form020.py` | **P2** (`tests/test_data_layer.py`): the 32 answers of 0.19, translated, against the golden workspaces migrated — every difference named, with its reason |
| **4d (part)** | `sdem migrate --to 0.20` (`sdem/migrate20.py`): backup, ids, files renamed, data records to `data.json`, access links to approved `ACCESSED_BY` links, checked in the new form — restored if it does not pass; `sdem migrate --rollback` | migrate → rollback restores every byte |

**Built differently from the text above, for the owner:**

| Rule | As built | Why |
|---|---|---|
| DL-01, DL-12 | **The Data layer is in use only in a migrated workspace.** An unmigrated workspace keeps 0.19's stack — its data records in the Application file — and is read and answered exactly as before (P1). Without a workspace (`sdem types`, files given directly), 0.19's form too, until 0.20 is released (DL-D9, below). | DL-12's "a workspace not migrated is still read" — byte for byte |
| DL-04 | the link type is **`ACCESSED_BY`** (data entity → application element), not `ACCESSES` | every link between layers points down the stack (KG-F-03); the meaning is ArchiMate's access, unchanged |
| DL-13 | the migrated access links carry the evidence kind the link type requires — `application_architecture_document:sdem-migrate-0.20#within-layer-access` — and say in their rationale that the migration approved them, by whom and when | the registry's required evidence holds for every approved link |
| — | SDEM's inference engine AID runs on a migrated workspace in its **0.19 view** (`identity.view_019`) — Data's records in Application, approved `ACCESSED_BY` as access — and its results go back through ids, Data's records into `data.json`; an access it newly infers becomes a *proposed* `ACCESSED_BY` link | the engine proven on 0.19's stack runs unchanged; a link between layers is a person's to approve |
| — | a graph store records the layers it was built with (`load-record.json`, when not 0.19's); `--graph` reads it | trace and impact on a migrated workspace's store |

**Every feature in the 0.20 form (2026-11-21).** The full suite runs in both forms — as it is (0.19) and with new workspaces in 0.20's form — now the default (DL-D9a). What that found, fixed: each layer agent's scope (CTL-19) read by layer id, with a refusal that names a 0.19 number's layer now (DL-25); organisation profiles in either form (DL-25); every table of layers with Data (about fifty — in 0.19's form Data shares Application's code, so nothing there changes); a change set's fingerprint taken from what its file stores; AID's change sets recorded in the workspace's numbering; a coordination record's layer stored as an id and read by the file's form; `sdem migrate --to 0.20` keeps a workspace's chain of change sets whole (its rewrite of each layer recorded as a change set the person adopts) and always writes `data.json`; `sdem home`, the dashboard and the workbench open each workspace in its own form; `sdem query --type` takes a 0.19 name (ST-05); link checks read a type id; intake, load and transform (DL-26); the acceptance harness grades a 0.20 workspace as 0.19 held it (`to_019`, P2).

**The examples in the 0.20 form (DL-20, DL-21; 2026-11-21).** Every example is in `examples/0.20/`, beside its 0.19 original — migrated by SDEM's own migration (`scripts/migrate_example_020.py`; payment-initiation-v3's workspace with `sdem migrate --to 0.20`, its authored package kept as written, DL-26), its graph store rebuilt, and reconciled with the original record by record (`tests/test_data_layer.py`, Reconciled: every record, field and link; each access an approved `ACCESSED_BY`). The 0.19 originals stay: `sdem new --example` starts from them, and P1's golden answers are proven on them. **P3:** `examples/0.20/library-holds` — a made-up municipal library's holds, SDEM's default four layers with no BIAN (A1 Business, A2 Data, A3 Application, A4 Technology) — runs every command that applies to it end to end (`tests/test_non_banking_example.py`). It found three gaps, fixed: the workbench and `sdem home` read the BIAN layer where it is not in use; `sdem new --from` reported its records in the numbering from before its migration; the copy in 0.19's form (`export_019`) carried the change sets, whose fingerprints are of the 0.20 files — it is now the design without its history (checked in the workspace), its files recorded as the export's.

**Still to do in step 4:** every feature in the 0.20 form, then the default switched on (DL-D9a) — agents' layer scope, layout and zones, load, intake, the acceptance harness; the examples migrated (DL-20); the made-up non-banking example (DL-21, P3); security and BIAN packages naming the data ids (DL-22); the viewpoint, DESNRE publisher, skills and docs (DL-23, DL-24).

| # | Decision | Decided |
|---|---|---|
| DL-D9 | In 0.20, `sdem new` creates a workspace in the 0.20 form (Data layer, files by id), and SDEM without a workspace shows the 0.20 stack; an existing workspace stays in 0.19's form until a person migrates it | **yes** — approved 2026-11-21 ("yes continue"), with the payment-initiation example migrated to 0.20 |
| DL-D9a | **Opt-in until every feature works in the 0.20 form** (the owner, 2026-11-21: "opt-in for now"). Switching the default on broke a large part of the full suite — real gaps: each layer agent's scope for change sets (CTL-19), the layout and zone commands, load and intake, the acceptance harness. So `sdem new --form 0.20` (or `SDEM_FORM=0.20`) opts in; the payment example in the 0.20 form is `examples/0.20/payment-initiation`, beside the 0.19 one, reconciled with it record by record. The default switches on when the suite is green in both forms | **yes** — **switched on 2026-11-21** (the owner: "yes"), with the suite green in both forms: `sdem new` makes the 0.20 form; `--form 0.19` or `SDEM_FORM=0.19` keeps 0.19's |
