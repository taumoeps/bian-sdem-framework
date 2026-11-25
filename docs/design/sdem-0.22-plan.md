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
| **R-D11** | **Step 3's proof (P1) when BIAN infers as an extension** (the owner, 2026-11-24: "a") | **Identical except provenance**: every record, link, proposal, confidence, reasoning and gap byte-identical to 0.21.14's once the fields that name the inferer — `inferred.by`, `inferred.step`, a proposal's `created_by`, its evidence prefix and its number — are mapped by one published table (as the 0.20 plan's P2). Strictly byte-identical would make the extension claim SDEM inferred what BIAN did (MX-48) |

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

### Step 5 — R-D6 amended (the owner, 2026-11-25: "Stay in SDEM")

The banking examples move to `sdem-bian` (R-D6); **SDEM's tests that use them stay in SDEM**, beside the code they test, find the examples through the installed `sdem-bian`, and skip without it — SDEM's CI runs them with it installed. (R-D6 said the tests would move with the examples; most of them test SDEM's own code — trace, check, link, AID — with banking data as their input.) The core keeps `library-holds`, which `sdem new --example` now offers, and the reference structure, generated from the core with no BIAN layer.

| Stage | What | As built |
|---|---|---|
| **5a** ✅ | BIAN's documents to `sdem-bian` (R-D8); the Extensions guide | one-line pointers where they were; `docs/sdem-extensions-guide.md`; an Extensions section in the README |
| **5b-1** ✅ | the core's own example | `sdem new --example library-holds`, shipped with SDEM; the 0.20 reference structure with no BIAN file (0.19's keeps its empty one — it marks a design without BIAN) |
| **5b-2** ✅ | the banking examples to `sdem-bian` (R-D6) | the 10 designs in 0.19's form, 11 in 0.20's, `acceptance-cases.json` and `blind-cases.json` are `sdem_bian/examples` (sdem-bian 1.3.0, its manifest's `examples`); SDEM finds them through `parts.example_roots()` — `sdem new --example` offers them with sdem-bian installed, the acceptance cases, the generators and `sdem home` read them; SDEM's tests through `tests/needs.EXAMPLES` (SDEM's and sdem-bian's in one folder), skipped without it; CI and the scripts that name `examples/<design>` run `scripts/link_extension_examples.py` first; sdem-bian's proofs read its own copies. The golden set stays in SDEM (`tests/golden/`), as the tests that read it do |
| **5c** ✅ | the README for the core | install the core, `sdem-bian` in one more line for banking; the finished example is `library-holds`; a design of one's own without BIAN (room bookings: change sets for three layers, `sdem link` proposes, a person approves and connects, a trace from the runtime up to the capability) — run as written without `sdem-bian`; the BIAN walk-through in brief, `docs/sdem-quick-start.md` with `--with bian`. Found running it: `--explore` failed on a core design (the workbench listed BIAN's catalogue), and `sdem new` told a core design to add BIAN and counted its layers before 0.20's form added Data |

### Step 4 — staged (the owner, 2026-11-24: "Staged")

Outside its four modules SDEM's code names BIAN's types 63 times (12 files) and its layer by id 196 times (36 files — the A1, A2 BIAN, A3 … numbering). **4a**: BIAN's data, rules, code, patterns and the built-in fallback leave the package; a design that uses BIAN is refused without `sdem-bian` (R-D2); metamodel 0.20.0 holds no BIAN type; the core keeps only BIAN's reserved layer slot — its id and its place in the stack — as a generic place for an extension's layer. **4b**, later: that slot made fully generic. Each proved: P1 with `sdem-bian`, the core suite without it.

| Stage | What | Proof |
|---|---|---|
| **4a-1** ✅ | R-D2 (BX-15): a design that uses BIAN is refused without a usable `sdem-bian`; without it, other designs and a new design are core ones; with it, nothing changes. SDEM's CI installs `sdem-bian` (from `sdem-extensions` main) in every job, and its release smoke test in its clean environment. Running the suite with `sdem-bian` for the first time showed the dashboard numbering proposals unlike `sdem link` (`P-RUN-…` against `RUN-X…`): `sdem-bian` now gives the whole run's order and SDEM numbers in it (MX-53), every command through one function (`inference.propose`) — `sdem link`'s ids are 0.21's again | `tests/test_bian_required.py` (no `sdem-bian`); with it: the full suite, the 23 AID runs identical except `phases_by` |
| **4a-2** ✅ | BIAN's data, code, catalogue and patterns leave the package; `sdem-bian` becomes their source (BP-11's generation retired). As built: the four modules, `bian/`, the A2 metamodel file, the BIAN pack and patterns (the Payment initiation pattern too), and BIAN's rows of every core file — rules, link types, within-layer rules, attributes, official mappings, export conventions, notation, diagram templates, the viewpoint's plate, the test log — moved to sdem-bian and merged back where BIAN is on (MX-55); the base BIAN layer shipped built (`new.base_layer` reads data); `sdem aid` asks sdem-bian at every phase (its projection runs BIAN's whole engine), a core design asks nothing; `sdem link` given files gives sdem-bian a workspace of them; the engine's options reach it (acceptance case C1); SDEM's documents are the core's (BX-16) | the 23 AID runs and the link proof with sdem-bian, identical except `phases_by`, `created_by` and the version stamps; the reference-structure example (generated from the core) left out |
| **4a-3** ✅ | metamodel 0.20.0, no BIAN type in the core; frozen. As built: the 0.20.0 migration records what moved and where (`moved`), and the stability check accepts those moves (MS-06 as R-D3 amends it — said to the owner); every example migrated and its stores rebuilt; `main` is 0.22.0.dev1; 13 tests of BIAN's planning document skipped until it moves (step 5, R-D8) | the core as frozen, with and without sdem-bian; the documents current both ways; both suites green |
| **4a-4** ✅ | `sdem new` a core design unless `--with bian`; the no-BIAN gap count; the core suite without `sdem-bian`. As built: a workspace with no BIAN layer and no `ext:bian` is a core design installed or not (BX-11 as BX-15 amends it); `sdem new --with bian` (or `--bian`, or a baseline with BIAN) starts with BIAN's layer, decided before the profile is read; `sdem load --a2` and `sdem intake` (a package is written in BIAN's numbering and names its domains) need sdem-bian; a command called from Python leaves the process as it found it (`profile.kept`); the gap count was right already after 4a-2 (13 of the library example's 25 records reach every layer — 0.21.13 counted none); 169 test classes that need sdem-bian are marked (`tests/needs.py`) and CI's new `core` job runs the suite without it | without sdem-bian: the suite passes, what needs it skipped; with it: the full suite; `tests/test_bian_required.py` (R-D2, the gap count) |

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

## 8. As built

| Step | Done | Notes |
|---|---|---|
| **1** ✅ 2026-11-23 | The repository is `taumoeps/sdem`, the old address redirects; the name in every current document, the CLI and the generated documents; history records and the owner's pinned spec unchanged | SDEM CI 25 of 25 green; the extensions' CI green |
| **2** ✅ 2026-11-24 | [MX-45…MX-52](sdem-metamodel-extensions-spec.md#16-extensions-that-infer): `sdem aid` and `sdem link` run each included extension that declares `"infers"`, and check, mark and write what it gives as their own (`sdem/ext_infer.py`) | proved with a made-up extension (`tests/test_extension_inference.py`): its records in its own layer, its proposals, its mistakes refused and said, an extension not included never asked, confirm and reject as SDEM's own, no SDEM code naming it |

| **3a** ✅ (0.20) | BIAN's 17 commands were already `sdem-bian`'s own (BP-03, ST-22): its copy is identical to SDEM's apart from imports, held so by its tests, and `sdem bian …` runs it when installed | checked 2026-11-24 |
| **3b** ✅ 2026-11-24 | `sdem link`: the rules engine split — the engine and the core's 23 rules (`rules_engine.CoreRun`) apart from BIAN's 46 (`rules_bian.BianSteps`, now also `sdem-bian`'s, generated and held identical, BP-11); `sdem-bian infer --step link` runs SDEM's engine through `sdem.api` with BIAN's steps and answers with BIAN's proposals, candidates and target design whole (MX-53); SDEM runs the core's rules only when it does | **P1 (R-D11)**: 64 golden answers byte-identical after the split; `sdem link` from scratch on 13 examples — 243 proposals — identical except provenance with `sdem-bian` 1.1.0 installed, 160 of them made by it (`tests/golden/0.21-link-scratch`, held by sdem-bian's `test_infer_link.py`) |

### Step 3c — `sdem aid`: a phased contract (the owner, 2026-11-24: "A")

Unlike the rules engine, AID's core steps build on what BIAN infers in the same run — zones and connections are proposed for the deployments BIAN's container pattern just inferred, and every proposal is numbered in one sequence. So BIAN cannot answer once, at the end: SDEM calls it at the **four points** where AID goes through BIAN today, in the same order, with the state so far, and keeps everything between them (marking, naming, zones, connections, numbering) its own.

| Phase | AID's rules | What BIAN gives back |
|---|---|---|
| **projection** | F1…F3, R1…R3, M (`aid.project` with BIAN's catalogue) | the projection package: records and links by layer, links between layers, its notes |
| **patterns** | D05 | the BIAN domains a pattern names, with their parts and the uses it proposes |
| **information** | K02, I01…I04, I07 | existing tables for BIAN objects, new entities and their fields, access links |
| **direct** | L01…L05, I05 (BIAN's rules of `propose_direct`), K01 (`propose_fields`) | its links, which SDEM merges with the core's L06, I06 in the rules' order |

| Stage | What | Proof |
|---|---|---|
| **1** ✅ | `aid fill` reaches BIAN only through the four phases (`sdem/aid_bian.py`); `propose_direct` runs per rule set and is merged in its rules' order | the 23 AID runs from scratch (`tests/golden/0.21-aid-scratch`) byte-identical |
| **1b** ✅ | the code behind the phases moves into `aid_bian.py` (the projection steps out of `aid.py`; `pattern_domains`, `match_existing`, `propose_information`, `propose_access`, `propose_fields` and BIAN's sections of `propose_direct`); reading, checking and tracing a projection package stay SDEM's. As built: `propose_direct` splits by its rules — BIAN's L01, L02, I05 (`propose_direct_bian`) run first and the core's L03…L06, I06 see them as proposed links, as a later rule always saw an earlier one's; `aid.py`, `aid_info.py`, `aid_links.py` keep forwarders for the old imports | byte-identical again (23 of 23) |
| **2** ✅ | the phased contract (MX-54): `sdem-bian infer --step aid --phase <name> --state FILE`, the state as JSON; `aid_bian.py` becomes sdem-bian's (generated, BP-11); SDEM's copy steps aside when sdem-bian provides it. As built: six phases (information split into existing, information, access, as `aid fill` reaches them); the state and answers in ids (`to_wire`), since AID runs in a migrated workspace's 0.19 view and the extension in its own process; SDEM sends each mark's template, so the records are marked as before; SDEM's own copy answers through the same JSON; the run record's `phases_by` names the extension; sdem-bian 1.2.0 | the 23 runs identical except `phases_by` — both with sdem-bian installed (it answered every phase of all 23) and without |

**A correction to §3 (R-D5).** The plan said EXT-02 lets an extension use SDEM *only* through its commands and files. EXT-02 was amended in 0.20 (ST-21, approved): an extension may also use SDEM's published Python interface `sdem.api`, as `sdem-bian` already does. R-D5 stands as approved — SDEM *runs* an extension and never imports its code; inside its own program an extension may use `sdem.api`.

**Found and fixed in step 2:** `sdem aid confirm|reject` failed on any 0.20 design with approved data-access links (the Payment example): it checked against the registry as stored, not as AID's 0.19 view reads it (approved ACCESSED_BY as links inside the layer, DL-12) — it now checks as `sdem aid` itself does.
