# SDEM 0.20 — the plan: an industry-neutral core, BIAN as an extension (proposed)

> **Status: approved (2026-11-20) — the owner: "approved recommendations" (PL-D1…PL-D4, §5).** Step 1 is built and approved
> ([BIAN extension](sdem-bian-extension-spec.md), BX-…). Each later step gets its own spec, its own approval and its own proof before it
> begins; this page fixes only the order and how each step is proved. Branch `release/0.20`; `v0.19.0` stays frozen and is the rollback.

## 1. Where 0.20 ends

| | 0.19 | **0.20 default** | **0.20 + BIAN** |
|---|---|---|---|
| Business | A1 | A1 | A1 |
| Service Domain (BIAN) | A2 | — | A2 |
| Data | inside A3 (`A3.DataEntity`, `A3.DataAttribute`) | **A2** | **A3** |
| Application | A3 | A3 | A4 |
| Technology | A4 | A4 | A5 |

The default is any organisation's design — Business, Data, Application, Technology. A bank adds BIAN and gets five layers. The Architecture
view already draws data as a plate of its own (A3-1 Data, A3-2 Application); 0.20 makes the metamodel say what the view already shows.

## 2. The order — each step proved before the next

| Step | What | Proof (§3) | Migrates workspaces? |
|---|---|---|---|
| **1** ✅ | BIAN is a built-in extension `ext:bian`; the core is A1, A3, A4; off only by a person's choice (`sdem new --core`) | **P1**: the 30 golden answers byte-identical | no |
| **2** | BIAN's files and code move into their own package, `sdem-extensions/metamodel/bian` (`sdem-bian`): the A2 metamodel, its link types and rules, the catalogue, the `sdem bian` commands. SDEM without it installed is the core; with it, as step 1 | **P1** again, with `sdem-bian` installed; the core-only tests without it | no |
| **3** | **Stable identity.** Each layer and type gets an id that never changes (`business`, `bian.service-domain`, `data`, `application`, `technology`; `application.ApplicationComponent`); the A-number is computed from the layers in use and shown, never stored as identity. Old names (`A3.ApplicationComponent`) are read through a translation table, and every answer can be given in either | **P2**: the 30 answers identical after translation | records keep their files; names read through the table |
| **4** | **The default four layers.** Data leaves A3 for a layer of its own: `A3.DataEntity` and `A3.DataAttribute` move; the new data types (domain, model, contract, store, classification — each in its own spec); application → data `access` becomes a link between layers; the inference rules and the registry follow. Workspaces migrate with a preview, a backup and a rollback | **P3**: a made-up non-banking design end to end; **P2** on the examples with the Data layer | **yes** — preview, backup, rollback |
| **5** | **BIAN on the default — five layers.** `ext:bian` sits between Business and Data. Which of 0.19's service domain → application links and rules stay valid across the Data layer between them, and how they are written, is its spec's main question | **P4**: 0.19's 30 answers, translated, all match — "operates the same as 0.19" | the examples, through step 4's migration |

Each step ends with the full suite green, `sdem model check` current and CI green on `release/0.20`, then a short report to the owner
before the next step starts. Later in 0.20 and not ordered here: core inference rules (so `link` and `aid` propose more without BIAN), security
on the Data layer, DESNRE's five-plate view.

## 3. The proofs

| Id | Proof | How |
|---|---|---|
| **P1** | **Identical.** Every recorded answer is byte-for-byte 0.19's | `scripts/golden/capture.py` against `tests/golden/0.19/` (BX-30, BX-31) |
| **P2** | **Identical after translation.** The same answers once each name is translated by one published table (old layer and type name → stable id → the new A-number) — nothing else may differ | a translation table in the metamodel; the golden test translates 0.19's answers and compares |
| **P3** | **The default stands alone.** A made-up design of another industry passes check, status, build, trace, impact, link, aid, document and comply in four layers | a synthetic example, added in step 4 |
| **P4** | **BIAN on the default is 0.19.** P2 on the five-layer stack: the same records, links, checks, proposals, traces and impacts as 0.19, translated | the golden test with BIAN on the default |

Where an answer **must** change — a link that 0.19 drew straight from a service domain to an application now crosses the Data layer — the
step's spec names each one and why, the owner approves it, and the golden copy is updated in the same commit with that reason (BX-31). An
unexplained difference fails.

## 4. Rollback

- `v0.19.0` is frozen; `main` stays at it until 0.20 is released.
- Steps 1–3 change no workspace file. Step 4's migration writes a backup and has `sdem migrate --rollback`; it runs only when a person asks.
- DESNRE's live site stays on 0.19's data until 0.20 is released; previews only before then.

## 5. Decisions for the owner

| # | Decision | Decided |
|---|---|---|
| PL-D1 | The order of §2 — stable identity (3) **before** the Data layer (4) | **yes** — without it, every type name changes twice |
| PL-D2 | The proofs of §3 — byte-identical for 1–2, identical after translation for 3–5 | **yes** |
| PL-D3 | Data's types move from A3 unchanged in step 4; new data types each have their own spec | **yes** |
| PL-D4 | Step 5's spec decides, link by link, how service domain → application connections cross the Data layer | **yes** |
