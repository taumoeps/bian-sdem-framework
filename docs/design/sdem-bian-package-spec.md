# BIAN in its own package — step 2 of SDEM 0.20 (spec)

> **Status: proposed (2026-11-20) — for the owner's approval of BP-D1…BP-D5 (§7).** Step 2 of the [0.20 plan](sdem-0.20-plan.md)
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

| # | Decision | Recommended |
|---|---|---|
| BP-D1 | BIAN's data and its `sdem bian` commands move to `sdem-extensions/metamodel/bian` (BP-01…BP-03) | **yes** |
| BP-D2 | The core's inference steps that name A2 types stay in the core until step 3 (BP-04) | **yes** — they are rewritten by step 3 anyway |
| BP-D3 | The built-in BIAN stays as the fallback for all of 0.20 (BP-10) | **yes** — no 0.19 workspace breaks on upgrade |
| BP-D4 | A test keeps the package and the fallback identical (BP-11) | **yes** |
| BP-D5 | `bian add --dry-run` joins the golden set before the move, recaptured from `v0.19.0` | **yes** |
