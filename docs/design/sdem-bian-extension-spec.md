# BIAN as a horizontal extension — step 1 of SDEM 0.20 (spec)

> **Status: approved (2026-11-20) — the owner: "write the design spec and implement"; BX-D1…BX-D6 as recommended (§8).** Branch
> `release/0.20`; `v0.19.0` stays frozen. Step 1 of the 0.20 plan (an industry-neutral core with Business, Data, Application and Technology,
> BIAN optional): **extract the A2 Service Domain (BIAN) layer into its own extension first, change nothing else, and prove it behaves as
> 0.19** before the Data layer, renumbering or anything else begins. Builds on [metamodel extensions](sdem-metamodel-extensions-spec.md)
> (MX-…), the [layer registry](sdem-layers-spec.md) (LR-…), [metamodel stability](sdem-metamodel-stability.md) (MS-…) and the
> [extension lifecycle](sdem-extension-lifecycle-spec.md) (EL-…).

## 1. What step 1 does — and what it does not

| Changes | Stays exactly as it is |
|---|---|
| BIAN's A2 layer, its 15 types, its within-layer rules, every cross-layer link type touching A2 and every inference rule touching A2 belong to **`ext:bian`**, an extension shipped inside SDEM | the layer code **A2**, its file `a2-service-domain.json`, every type name (`A2.ServiceDomain`), every record, link, mapping id, decision and graph reference |
| SDEM's **core** is A1, A3 and A4 | A1, A3 and A4, their types and rules; numbering; the Data layer does not exist yet |
| a workspace may be **core-only** — no A2 layer at all | every existing workspace, example and published design: BIAN on, behaviour unchanged (§4) |
| security's link types to A2 types apply only where BIAN is on (§6) | DESNRE (A2 is still A2) |

No record changes identity, so **step 1 needs no workspace migration**. Renumbering, a Data layer, moving BIAN's code into its own package and an industry-neutral default are later steps, each specified and approved on its own.

## 2. The BIAN extension

| Id | Rule |
|---|---|
| **BX-01** | **`ext:bian` is a built-in metamodel extension**: shipped inside SDEM (step 1), named in `sdem extensions` with kind `metamodel` and scope `{"within": ["A2"]}` — *horizontal*: it extends the stack with a layer of its own between A1 and A3. An installed `sdem-bian` package of the same name would take its place in a later step. |
| **BX-02** | **It owns** the A2 layer (code `A2`, file `a2-service-domain.json`, agent `sdem-a2-bian`); the types in `metamodel/a2-service-domain.json` and the within-layer rules of level A2; every link type of the registry whose source or target is an A2 type; every inference rule (`metamodel/relationship-rules.json`) that names an A2 type; the BIAN catalogue and the `sdem bian` commands. |
| **BX-03** | **The core** is everything else: A1, A3, A4, the link types and inference rules among them (e.g. A1 → A3 `AUTOMATED_BY`, A3 → A4 `DEPLOYED_ON`), and every command. |
| **BX-04** | **Its position is reserved**: A2 sits between A1 and A3 whether or not BIAN is on; with BIAN off there is no A2 layer, and A1's neighbour below is A3 (LR-01, LR-06 as amended, §5). |

## 3. When BIAN is on

| Id | Rule |
|---|---|
| **BX-10** | **On** for a workspace whose profile includes `ext:bian` (`sdem profile include ext:bian`, a person's recorded decision, MX-10). |
| **BX-11** | **On** for every other workspace — every workspace made by SDEM 0.19 or earlier, **with an A2 file or without one** (a design started with `--no-bian` has no A2 file yet, and AID brings service domains in from the catalogue, as in 0.19). Checked exactly as before; `sdem extensions --workspace …` says BIAN is on implicitly and gives the command that makes it explicit. No migration is forced. *(First built as "on when the workspace holds a2-service-domain.json"; the full suite showed that changed 0.19 for designs without an A2 file yet — 11 tests — so off is now only a person's recorded choice, BX-13.)* |
| **BX-12** | **On** where there is no workspace (a command given files, `sdem types`, `sdem bian search`): 0.19's behaviour. |
| **BX-13** | **Off only where a person chose it**: `sdem new --core` (new), or `sdem profile exclude ext:bian` — recorded in `workspace.json` as `core_only: true`; `sdem profile include ext:bian` or a restore clears it. Then there is no A2 layer: `sdem types A2` names the layers there are; a record of an A2 type, a link type to one or an inference rule through one is not part of the metamodel; `sdem bian …` refuses with the command that switches it on. |
| **BX-14** | **Switching off and on** are the lifecycle's commands (EL): `sdem profile exclude ext:bian` archives the A2 layer and every connection touching it (MX-16) — a design that still needs them does not pass and nothing is written; `sdem profile restore` brings them back. |

## 4. Proof of equivalence

| Id | Rule |
|---|---|
| **BX-30** | **Golden outputs.** Before any change, SDEM 0.19's answers on its examples were recorded, normalised (no times, run ids or local paths): `check`, `comply`, `status`, `aid --dry-run`, `link`, `document` per layer and `build` on two workspaces (payment-initiation, payment-initiation-v3); `types` per layer; `trace` and `impact`; `bian search`; `check` on three dataset examples — 30 answers in `tests/golden/0.19/`, captured twice and identical (deterministic). |
| **BX-31** | **With BIAN on, every answer is the same.** A test recaptures them and compares each with its golden copy; a difference fails it, unless it is explained and approved, and the golden copy is updated in the same commit with the reason. |
| **BX-32** | **With BIAN off, the core stands alone.** A made-up non-banking workspace with only A1, A3 and A4 passes `check`, `build`, `trace`, `impact`, `link`, `aid --dry-run`, `document` and `status`; a banking workspace whose A2 is archived passes too. |
| **BX-33** | **Never silently dropped.** A workspace that includes `ext:bian` where SDEM cannot provide it is refused (MX-11a); a record of an A2 type in a workspace with BIAN off is an error naming the extension, never ignored. |

## 5. Rules this changes

| Id | Changes | Why |
|---|---|---|
| **BX-40** | **LR-01** allows one layer *between* core layers: the reserved position A2, provided by `ext:bian` only. Profiles still add layers at the ends only. | BIAN sits between Business and Application |
| **BX-41** | **LR-06** (link types to the neighbour): with BIAN off, A1's neighbour below is A3 — the link types already between them (`AUTOMATED_BY`, …) are the core's. | the core without A2 must connect business to applications |
| **BX-42** | **MS-06 does not apply to a move.** BIAN's types leave SDEM's core into `ext:bian` unchanged; with the extension on — every existing workspace — the metamodel is the same, which BX-31 proves. Nothing is deprecated or removed for anyone using it. | the owner's decision BX-D3 |
| **BX-43** | **"Horizontal" means extending the stack** — a layer of its own (BIAN) or more types inside an existing layer (a network extension, MX-30). MX Part 2's §10 table is amended to say so. | the owner's 0.20 plan |

## 6. Security, with or without BIAN

| Id | Rule |
|---|---|
| **BX-50** | **A pack's link type may require a part**: `"requires": "ext:bian"` on a link type to an A2 type. Where BIAN is off, SDEM leaves it out of the merged profile — said in `sdem profile show`, never an error — and the rest of the pack applies. Where BIAN is on, it applies as in 0.19. This is the smallest form of a bridge (MX-36), until bridges are built. |
| **BX-51** | **sdem-security marks its A2 link types** (PROTECTS and THREATENS to service domains, control records, business objects) as requiring `ext:bian`. Security then works on a core-only design (S1, S3, S4, S5; S2 empty and said so) and, with BIAN, exactly as before. |

## 7. Tests

- BX-31: the golden comparison, all 30 answers equal, with BIAN on.
- BX-32: a core-only made-up workspace through every command above; `sdem types A2` and `sdem bian search` refused there with the command that switches BIAN on.
- BX-11, BX-13: every existing workspace is on, with or without an A2 file (`--no-bian` too); `sdem new --core` is off; including `ext:bian` turns it on, excluding it turns it off.
- BX-14: exclude and restore of `ext:bian` on a copy of the example.
- BX-50, BX-51: the security extension on a core-only workspace and on the banking example.
- The full suite unchanged.

## 8. Decisions (approved 2026-11-20)

| # | Decision | Decided |
|---|---|---|
| BX-D1 | Step 1 extracts BIAN only — no renumbering, no Data layer, no type renames, no migration | **yes** |
| BX-D2 | BIAN is a built-in extension in step 1; its code stays in SDEM's package, used only where BIAN is on; its own package later | **yes** |
| BX-D3 | Moving BIAN's types into the extension is not a removal (MS-06), proven by the golden comparison | **yes** |
| BX-D4 | Existing workspaces are BIAN-on implicitly until a person makes it explicit; nothing is forced (BX-11) | **yes** |
| BX-D5 | "Horizontal" covers a layer of its own as well as types inside a layer (BX-43) | **yes** |
| BX-D6 | Security's A2 link types require `ext:bian` (BX-50, BX-51) | **yes** |

## 9. As built (2026-11-20, branch `release/0.20`)

| Rules | Where |
|---|---|
| BX-01, BX-02 | `sdem/parts.py` (on or off, and why); `metamodel/ext-bian-pack.json` and `profile.BUILTIN` (the built-in extension); the A2 file, A2 within-layer rules, A2 link types and A2 inference rules filtered by `metamodel.py`, `validate.load_registry`, `rules_engine._rules` |
| BX-04 | `layers.layers()`: no A2 where BIAN is off |
| BX-10…BX-13 | `parts.for_workspace` (off only for `core_only` in workspace.json), called by `profile.activate_from` before the profile resolves; `sdem new --core`; `sdem extensions [--workspace]` lists BIAN as built in, on or off and why, and the command that makes an implicit one explicit; `sdem bian … --workspace` refuses where it is off; `aid`'s catalogue is none where it is off; the rules engine skips a rule that is not loaded |
| BX-14 | `sdem profile exclude ext:bian` archives the A2 layer (MX-16); refused when the design still needs it — e.g. the payment example's requirement REQ-RT-01 is owned by A2 |
| BX-30, BX-31 | `scripts/golden/capture.py`, `tests/golden/0.19/` (30 answers), `tests/test_bian_extension.py` — **all 30 identical** with BIAN on. **Updated 2026-11-21 with the owner's approval of metamodel 0.18.0:** the two build answers (`payment-initiation__build.json`, `payment-initiation-v3__build.json`) record `metamodel_version` 0.18.0 and the examples' input fingerprints, which changed with their version field; nothing else in any answer changed **Updated 2026-11-22 with the owner's approval of BO-D1** (BIAN's business objects, [object index](sdem-bian-object-index-spec.md)): `payment-initiation-v3__status.json` — that design has BIAN service domains and no business object, so `sdem status` now warns of it (BO-06) and names `sdem bian objects suggest`: one warning and one next step more; nothing else changed in any of the 30 answers. **And with the owner's approval of FT-D1 (2026-11-22, [full trace](sdem-full-trace-spec.md)):** `trace__pi-A1.json` — the trace now walks part-whole links inside a layer by default: of the example's A1 records, 15 reach down the stack (5 before), 1 has no chain (11 before); upward, 15 (0 before). | **Updated 2026-11-22 under FT-08** (the owner: "continue and I agree"): `trace__pi-A1.json` — A1 connected 16 of 16 (was 15): the trace walks assignment, so the payments officer reaches below through its process. **Updated 2026-11-22 under KG-Q-09 and metamodel 0.19.0** (the owner: "ok implement", "approve and build"): `impact__pi-APP.json` — each record classified by its shortest path; `types__A3.json` — the data domain type (DAR-01); the two build answers and `payment-initiation-v3__comply.json` — the files' fingerprints only (they now say metamodel 0.19.0).
| BX-32 | the made-up core-only workspace (`sdem new --core`, card-fraud without A2) through check, status, build, trace, link, aid, document, comply |
| BX-50, BX-51 | a pack's `link_types[].requires`; `profile show` lists `left_out`; sdem-security marks its 6 A2 link types (on `release/0.20` of sdem-extensions) |

Found while building: on a core-only design `sdem link` proposes nothing new and `sdem aid` adds no layer — the core has few inference rules of its own (most go through A2). That is the 0.20 plan's later step (core inference), not a defect of this one.
