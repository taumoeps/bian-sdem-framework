# SDEM 0.22 — BIAN out of the core, and a new name (plan)

> **Status: approved (2026-11-23) — the owner: "approve" (R-D5…R-D10 as recommended).** The owner, 2026-11-23: *"I want BIAN separate and moved to the extensions library so it only has the base; rename this project as SDEM — Solution Domain Enterprise Model; update documentation to use extensions for expansion; documentation on BIAN moved out into the BIAN extension"*, and the decisions R-D1…R-D4 below. Backup branches `backup/before-bian-split-2026-11-23` in all three repositories. Builds on the [0.20 plan](sdem-0.20-plan.md) (BIAN an extension), [BIAN in its own package](sdem-bian-package-spec.md) (BP-…), the [extension contract](sdem-extensions-spec.md) (EXT-…), [metamodel extensions](sdem-metamodel-extensions-spec.md) (MX-…) and [metamodel stability](sdem-metamodel-stability.md) (MS-…).

## 1. Where 0.22 ends

| | 0.21 (today) | **0.22** |
|---|---|---|
| Name | Solution Domain Enterprise Model | **Solution Domain Enterprise Model** (still SDEM; the command and package stay `sdem`) |
| Repository | `taumoeps/bian-sdem-framework` | **`taumoeps/sdem`** (GitHub redirects the old address) |
| `pip install sdem` gives | the core **and** BIAN: its layer, 15 types, link types and rules, inference, `sdem bian`, the 258-domain catalogue, BIAN patterns, banking examples | **the core only**: Business, Data, Application, Technology — industry-neutral |
| BIAN | built in, with `sdem-bian` (1.0.0.dev1) as an optional copy of its data | **only** in the extension `sdem-bian` 1.0.0, in `sdem-extensions/metamodel/bian` — its data, its code, its examples and its documentation |
| A design with a BIAN layer, without `sdem-bian` | works (built-in fallback, BP-D3) | **refused**, with the message to install it (R-D2) |
| Versions | SDEM 0.21.14, metamodel 0.19.0 | **SDEM 0.22.0, metamodel 0.20.0** — a new core, frozen anew (R-D3, MS-05) |
| Documentation | BIAN throughout | the core documents describe the base and **how extensions expand it**; BIAN's own documents live with BIAN |

## 2. Decisions taken (the owner, 2026-11-23)

| Id | Decision |
|---|---|
| **R-D1** | The repository is renamed **`taumoeps/sdem`**; the project is **SDEM — Solution Domain Enterprise Model** |
| **R-D2** | A design that uses BIAN, opened without `sdem-bian` installed: **every command refuses** — *"this design uses the BIAN extension — install sdem-bian"* — no partial reading |
| **R-D3** | **SDEM 0.22.0, metamodel 0.20.0**: breaking, with a migration note; the core frozen anew |
| **R-D4** | **This plan first**, then the steps in §4, each ending with every test green and a short report to the owner |

This reverses **BP-D3** (the built-in BIAN as a fallback for all of 0.20).

## 3. Decisions approved (the owner, 2026-11-23: "approve" — each as recommended)

| Id | Question | Recommendation |
|---|---|---|
| **R-D5** | **How BIAN's code leaves SDEM.** BIAN's inference — AID choosing the service domains a process's operations belong to, BIAN's container pattern (one component per domain), the rules engine's BIAN strategies — and the `sdem bian` commands are Python inside SDEM today. EXT-02 lets an extension use SDEM only through its commands and files. | **(a) Keep EXT-02: an extension contributes through commands.** SDEM calls `sdem-bian infer --workspace … --json` and `sdem-bian link … --json` during `aid` and `link`; their answers come back as proposals and inferred records in SDEM's own formats, which SDEM checks and writes as it writes its own. `sdem bian …` becomes `sdem-bian …` (SDEM forwards `sdem bian` to it). One documented contract (new MX rules) any metamodel extension can use, not one made for BIAN. *(b) — relax EXT-02 and let SDEM import an extension's Python: faster to build, but any extension could then change SDEM's behaviour from inside it.* |
| **R-D6** | **The banking examples** (Payment v1–v4, lending, fraud, FX, trade finance, onboarding, fintech, legacy ledger — 12 of 13 0.20 examples have a BIAN layer) | **Move to `sdem-bian`'s `examples/`**, with the tests that use them, run by sdem-extensions' CI against SDEM. The core keeps the library example and gains one more non-banking design, so the core is proved on its own (the 0.20 plan's P3) |
| **R-D7** | **The 0.19-form example folders** at `examples/` (kept for migration tests) | **Move with BIAN** (they are all banking); `sdem migrate` from 0.19 keeps its own small fixture in the core's tests |
| **R-D8** | **SDEM's documents about BIAN** — design specs (`sdem-bian-*`, the BIAN inference reference, the A2 data-model draft, mapping-logic planning…), evidence that tested BIAN inference | **Move to `sdem-extensions/metamodel/bian/docs/`**, history kept: SDEM's copies become one-line pointers where other documents link to them. Records of past decisions (`docs/history/`, CHANGELOG entries) stay as written |
| **R-D9** | **DESNRE** — publishing and its in-browser SDEM bundle run SDEM on banking designs | The publisher installs `sdem-bian`; the site's bundle (`scripts/build-sdem-bundle.py`) includes it, so the agent and the workbench read the Payment example as today |
| **R-D10** | **`sdem-security`'s links into BIAN** (6 link types marked `requires: bian`, BX-50) | Unchanged — already left out, and said, when BIAN is not installed (MID-10) |

## 4. The steps — each proved before the next

| Step | What | Proof |
|---|---|---|
| **1** | **The new name.** Rename the repository to `taumoeps/sdem`; "Solution Domain Enterprise Model" in the README, the documents, `pyproject.toml`, the CLI's help, the generated documents and DESNRE's links; install URLs to `taumoeps/sdem`. The package and command stay `sdem` | every link resolves; the old address redirects; `pip install "sdem @ git+https://github.com/taumoeps/sdem@…"` works |
| **2** | **The extension contract for inference (R-D5).** SDEM's `aid` and `link` ask every installed metamodel extension that declares an inference command for its proposals, and check and write them as their own; `sdem <name> …` forwards to an extension's command. Specified as new MX rules, with a made-up extension in the tests (as the H1/H2/V1 patterns were proved) | a made-up extension's proposals arrive, checked, marked inferred, with no SDEM code naming it |
| **3** | **`sdem-bian` 1.0.0 complete.** Its data (already there), and now its code: the `sdem-bian` commands (all 17 of today's `sdem bian` commands — `search`, `add`, `list`, `select`, `update`, `import`, `custom`, `objects`, `impact`, `pack`, `inference …`), its inference behind the step-2 contract (AID's BIAN steps, BIAN's container pattern, the rules engine's BIAN strategies), its patterns (BIAN Transact, Fulfill, Payment initiation) | **P1**: SDEM 0.21.14's recorded answers on the banking examples, with `sdem-bian` installed, byte-identical (the golden set, `tests/golden/`) |
| **4** | **The core without BIAN.** Out of the `sdem` package: `bian/`, the A2 metamodel file, BIAN's link types, rules, inference rules, trace rules and patterns, every code path that names a BIAN type. `sdem new` makes a core design; `--with bian` (or `sdem profile include ext:bian`) adds it. R-D2's refusal. Metamodel **0.20.0**, frozen | the core suite green **without** `sdem-bian`; P1 again **with** it; `sdem model integrity --check` MET on the Payment example with it; the no-BIAN gap count right (the 0.21.13 known limit fixed here) |
| **5** | **Examples, tests and documents move (R-D6…R-D8).** And the core documents are rewritten for extensions: a new **Extensions** guide (what an extension is, the three patterns, how to find, install, include and write one; Security, BIAN and the DESNRE publisher as the worked cases), an *Extensions* section in the README | every link resolves in both repositories; both CIs green; the README's quick start run as written on a core install, and again with `sdem-bian` |
| **6** | **DESNRE (R-D9)** — publisher and bundle with `sdem-bian`; the Payment example republished | the site's integrity test (`tests/integrity-views.test.mjs`) green; live check in a fresh browser |
| **7** | **Release** — SDEM 0.22.0, `sdem-bian` 1.0.0, GitHub releases with the migration note: *a design that uses BIAN needs `pip install sdem-bian` after upgrading* | `sdem upgrade check` on a 0.21 banking workspace names the step; CI green on both repositories |

## 5. What does not change

- **The metamodel's meaning.** Every type, link and rule BIAN brings is the same — it moves, it is not redesigned. A banking design with `sdem-bian` installed answers exactly as today (P1).
- **The workspace files.** A 0.21 design's files are 0.22's; nothing is migrated — only `sdem-bian` must be installed.
- **The other extensions.** Security and the DESNRE publisher are unchanged, apart from installing `sdem-bian` where they meet banking designs.

## 6. Risks

| Risk | How it is met |
|---|---|
| BIAN's inference is interleaved with the core's in `aid` and the rules engine (≈280 places name BIAN types) | step 2's contract first, proved on a made-up extension; step 3 moves BIAN onto it; P1 byte-identical before anything is removed (step 4) |
| A banking user upgrades and their design stops working | R-D2's message says exactly what to install; `sdem upgrade check` says it before they upgrade; the release note leads with it |
| Links into SDEM's moved documents break (other repositories, DESNRE, bookmarks) | pointers left where documents were; the link test in both repositories |
| The golden answers depend on BIAN's examples, which move | the golden set moves with them and runs in sdem-extensions' CI against SDEM's `main` |

## 7. Size

Larger than any 0.20 step: about 280 code locations, 12 examples and the tests that use them, about 25 documents mainly about BIAN, two repositories and DESNRE. Steps 1 and 2 are independent of each other; 3 needs 2; 4 needs 3; 5–7 follow 4.
