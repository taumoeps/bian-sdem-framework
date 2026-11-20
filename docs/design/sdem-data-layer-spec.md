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
