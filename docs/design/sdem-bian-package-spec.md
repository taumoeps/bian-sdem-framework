# BIAN in its own package — step 2 of SDEM 0.20 (spec)

> **Status: approved (2026-11-20) — the owner: "agree with recommendations" (BP-D1…BP-D5, §7); built (§8); BP-03 as built approved by the owner ("accept recommendation", decision BP-D6).** Step 2 of the [0.20 plan](sdem-0.20-plan.md)
> (approved). Builds on step 1, [BIAN as a horizontal extension](sdem-bian-extension-spec.md) (BX-…), and the
> [metamodel extensions](sdem-metamodel-extensions-spec.md) (MX-…). Proof: **P1** — the 30 golden answers byte-identical with the package
> installed — and the core-only tests (BX-32) without it.

## 1. What BIAN is in SDEM today (surveyed 2026-11-20)

| Part | Where | Size |
|---|---|---|
| the A2 metamodel | `metamodel/a2-service-domain.json` | 15 types |
| link types touching A2 | `schema/relationship-types.json` | 10 of 31 |
| inference rules touching A2 | `metamodel/relationship-rules.json` | 46 of 69 |
| the BIAN catalogue, its inferences, its licence | `bian/base-14.0.0.json`, `bian/inferences-14.0.0.json`, `bian/LICENSE` | 3.4 MB |
| the `sdem bian` commands; import, search, add | `sdem/bian.py`, `sdem/inferences.py` | 1,166 lines |
| **code in the core that names A2 types** | 35 modules — most in `rules_engine.py` (46 places: the inference steps that go through service domains) and `aid.py` (46), then `containment`, `aid_fill`, `diagram`, `intake`, `relationships`, `aid_info`, `new` … | — |

The first four are **data**, and move cleanly. The fifth and sixth are **code**: the core *calls* BIAN's, and BIAN's inference steps are
written inside the core's engine.

## 2. What moves in step 2

| Id | Rule |
|---|---|
| **BP-01** | **A package `sdem-bian`** in `sdem-extensions/metamodel/bian/`, installed like security (`pip install …`), kind `metamodel`, scope `{"within": ["A2"]}`: a program `sdem-bian` with a manifest (EXT-15). `sdem bian …` keeps working, run as the extension (`sdem <name>` runs an installed extension). |
| **BP-02** | **It carries BIAN's data**: the A2 metamodel, its 10 link types, its 46 inference rules, the catalogue with its inferences and licence. SDEM reads them **as data** — from the folder the manifest names — never by importing the package's code (the privacy and no-dependency rules hold). |
| **BP-03** | **It carries the `sdem bian` commands** (`bian.py`, `inferences.py`), moved as they are. What the core calls of them today (`base_layer`, reading a catalogue, `natural_keys` for WS-07) becomes reading the catalogue file the package names. |
| **BP-04** | **The inference steps that name A2 types stay in the core's engine in step 2**, gated as in step 1 (they skip when BIAN is off). They move behind an interface in step 3, which rewrites every type name anyway (stable identity) — moving them twice is what PL-D1 avoids. |
| **BP-05** | **An installed `sdem-bian` takes the built-in's place** (BX-01); its version is the one `sdem extensions` and the profile name. |

## 3. Without the package installed

| Id | Rule |
|---|---|
| **BP-10** | **For 0.20, SDEM keeps its built-in BIAN as the fallback** — a workspace on BIAN (every 0.19 workspace) keeps working on a plain `pip install sdem`, and `sdem extensions` says *built in — install sdem-bian for its own updates*. Removing the fallback is a later, separate decision with a deprecation notice (MS-06). |
| **BP-11** | Where both exist, they must agree: the package's data is checked against the built-in copy by a test until the fallback goes — a difference fails it. |

## 4. Proof

- **P1** with `sdem-bian` installed: the 30 golden answers byte-identical (BX-31).
- **P1** without it (the fallback): the same.
- The core-only tests (BX-32) with and without the package.
- `sdem bian search`, `add`, `import` from the package give the same answers as from the core (they are in the golden set).
- The package's own tests; the full suite; CI on both repositories' `release/0.20`.

## 5. What step 2 does not do

No renumbering, no type renames, no Data layer, no change to any workspace file, DESNRE unchanged. The core's A2-naming code (BP-04) waits
for step 3.

## 6. Risks

| Risk | Answer |
|---|---|
| two copies of BIAN drift | BP-11's test |
| a user installs an old `sdem-bian` | its manifest names the SDEM versions it supports (`sdem`); outside them, SDEM uses the built-in and says why |
| `sdem bian` behaves differently run as an extension (separate process: exit codes, `--json` header) | the golden set already holds `bian search`; add `bian add --dry-run` to it before moving |

## 7. Decisions for the owner

| # | Decision | Decided |
|---|---|---|
| BP-D1 | BIAN's data and its `sdem bian` commands move to `sdem-extensions/metamodel/bian` (BP-01…BP-03) | **yes** |
| BP-D2 | The core's inference steps that name A2 types stay in the core until step 3 (BP-04) | **yes** — they are rewritten by step 3 anyway |
| BP-D3 | The built-in BIAN stays as the fallback for all of 0.20 (BP-10) | **yes** — no 0.19 workspace breaks on upgrade |
| BP-D4 | A test keeps the package and the fallback identical (BP-11) | **yes** |
| BP-D5 | `bian add --dry-run` joins the golden set before the move, recaptured from `v0.19.0` | **yes** |
| BP-D6 | BP-03 as built: the `sdem bian` code stays in SDEM and reads the package's data; it moves through step 3's interface, never by an exception to EXT-02 (§8) | **yes** (2026-11-20) |

## 8. As built (2026-11-20, branch `release/0.20`)

| Rules | Where |
|---|---|
| BP-01 | `sdem-extensions/metamodel/bian/` — `sdem-bian` 1.0.0.dev1: a manifest naming its data folder (`bian_data`) and its pack; CI `bian.yml` against SDEM `release/0.20` |
| BP-02 | its data folder: `a2-service-domain.json` (15 types), `within-layer-rules.json` (23), `link-types.json` (10), `inference-rules.json` (46), `catalogue/` (BIAN 14, its inferences, licence). SDEM reads it in `parts.py` — `splice` puts each BIAN row from the package in SDEM's order (replaced by key; a new one after; a dropped one gone), `metamodel_doc`, `catalogue_dir` — used by the metamodel, the link registry, the rule set, `sdem bian`, the inference record and the workbench |
| BP-05 | `parts.package()`: the installed `sdem-bian`, if it names a complete data folder and supports this SDEM |
| BP-10 | not installed, or refused: SDEM's own copy; `sdem extensions` says *used instead of the installed sdem-bian: …*; `sdem profile include ext:bian` works either way |
| BP-11 | `scripts/bian_package.py` writes the package's data from SDEM's; the package's test fails if they differ |
| proof | **P1 with the package**: the 32 recorded answers identical to `v0.19.0` (a real install in a clean environment, and a stand-in package in SDEM's own tests); SDEM reads the package's data — a marked copy shows in the metamodel, the registry, the rules and `sdem types`; a package for another SDEM is not used and is said not to be |
| BP-D5 | `bian add --dry-run` (two cases) joined the golden set, **captured from a `v0.19.0` checkout** — which also reproduced the 30 earlier answers byte for byte |

### BP-03 — built differently, for the owner

BP-03 said the `sdem bian` code (`bian.py`, `inferences.py`) moves into the package "as it is". It **was not moved**: the extension
contract (**EXT-02**) lets an extension use SDEM only through its commands and documented files, and that code is built on SDEM's
internals (the metamodel, conformance, the change-set writer). Moving it would make the package import SDEM's code, or copy it.

As built: **the commands stay in SDEM and read the package's data**; `sdem-bian <command>` runs SDEM's `sdem bian <command>`. Everything
BIAN *is* — its metamodel, rules and catalogue — lives in and versions with the package; what *runs* it is SDEM's, like the A2 inference
steps (BP-04). Both get one interface in step 3, which renames every type anyway. **Approved by the owner (2026-11-20), BP-D6.**
