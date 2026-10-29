# SDEM Workbench — Specification

> **Status: approved by the owner and built (2026-10-28)** (SDEM-D01 and the CLI-only interface of SDEM-D07). Requirements for the design in [`sdem-workbench-design.md`](sdem-workbench-design.md). Each requirement has an ID (WB-*), a status, and how it is accepted. The CLI — one `sdem` command — the controls and the Copilot set-up (`.github/`) are built.

## 1. Purpose and boundary

The workbench is how architects use SDEM: they open the **SDEM project in VS Code**, run SDEM from the **terminal pane (the CLI)**, and use the **GitHub Copilot Chat window** for AI support. **Git** holds history and the approval trail.

**Out of scope:** a new application, server or VS Code extension (WB-Q01); MCP; an AI API, model or key inside SDEM; drawing tools.

## 2. Environment and workflow

| ID | Requirement | Status |
|---|---|---|
| WB-E01 | The architect opens the SDEM project (the repository folder) in VS Code; Explorer and editor show the metamodel, datasets, registry, stores, projections and documents as files. No server is needed. | built |
| WB-E02 | The terminal pane runs SDEM: Python 3.10 or later, SDEM installed from the project (`pip install -e .`), giving the `sdem` command — or `python -m sdem …` without installing. | built |
| WB-E03 | The chat window is GitHub Copilot Chat, for AI support (§4). **Optional**: every journey is a CLI command the architect can run without it. | built — CLI and Copilot set-up (`.github/copilot-instructions.md`, agents, prompts, skills) |
| WB-E04 | Git for history; pull requests on the organisation's Git host for review and approval. | built (Git); approval flow WB-A01 not documented in the project |
| WB-E05 | The project recommends its VS Code extensions (`.vscode/extensions.json`): Python, Copilot Chat, Mermaid preview. | built |
| WB-E06 | A getting-started page: install, open the project in VS Code, open the terminal pane and run the first check, open the chat and ask Copilot to explain the result. | built — [`sdem-workbench-user-guide.md`](../sdem-workbench-user-guide.md) §3–5 |

## 3. The CLI — SDEM's only interface (SDEM-D07)

| ID | Requirement | Status |
|---|---|---|
| WB-K01 | **Every engine and function is a CLI command.** Nothing an architect needs is reachable only from Python code or a script. | built — the journeys, plus `sdem model examples` and `sdem model baseline-pack` for the scripts |
| WB-K02 | **One `sdem` command** with a subcommand per journey: `sdem check`, `sdem link`, `sdem build`, `sdem trace`, `sdem impact`, `sdem aid project / check / gaps / ai-import`, `sdem view`, `sdem explain`, and `sdem model …` for maintainers (regenerate, controls, acceptance, examples). | built — `sdem/cli.py`; also `python -m sdem` without installing |
| WB-K03 | The existing `sdem-*` commands keep working as aliases of the matching `sdem` subcommands. | built — the `sdem-*` commands are unchanged; `sdem` hands over to the same code |
| WB-K04 | The same conventions everywhere: inputs as `--graph DIR` or file paths; `--json` for machine-readable output; exit codes 0 = OK, 1 = issues found, 2 = usage error; non-interactive (no prompts). | built — `--json` added to `aid project`, `aid check` and `view`; `sdem` itself: 0 OK, 1 issues, 2 usage |
| WB-K05 | `sdem --help` lists every journey; each subcommand's `--help` includes a worked example. | built — tested for every subcommand (AT-WB-09) |
| WB-K06 | Output a person can read in the terminal: names beside ids, the rule behind each error, and where an output file was written. | built (for the journey commands) |
| WB-K07 | `--estate DIR` in place of the file list on `check`, `validate`, `link`, `build`, `trace`, `impact`, `review` and `explain`; `*` patterns expanded by `sdem` itself (Windows PowerShell does not). | built 2026-10-28 (T4) |
| WB-K08 | A warning when a graph store is older than its data: `trace`, `impact`, `query`, `check --graph` and `view` compare the store's recorded input checksums with the files; `sdem change propose` reminds to rebuild. | built 2026-10-28 (T3) |

## 4. Copilot — AI support in the chat window (no MCP)

| ID | Requirement | Status |
|---|---|---|
| WB-C01 | `.github/copilot-instructions.md` gives Copilot the ground rules (design §4), where the metamodel, datasets, registry and stores are, and which CLI command answers which question. | built — `.github/copilot-instructions.md` |
| WB-C02 | Copilot's role is **support**: explain command output and errors, suggest the exact CLI command, draft (records, impact notes, pull-request text), review proposals with the architect. | not built (instruction) |
| WB-C03 | Copilot runs a command **only when the architect asks**, and only the SDEM CLI, in the terminal pane — so the command and its output are visible. | built — an instruction (`.github/copilot-instructions.md` rule 2): a request to Copilot, not a control |
| WB-C04 | Ground rules, stated in WB-C01: facts from the CLI and files with the source named; suggest the exact command; rules first; never write projected or AI content into real data; never approve; source, reasoning and confidence on every statement; no MCP, no keys, no data outside the approved Copilot; say when unsure. | built — in `.github/copilot-instructions.md` |
| WB-C05 | Prompt files in `.github/prompts/` for the kinds of support: `sdem-explain` (explain the last output), `sdem-fix` (explain a check error and suggest the fix), `sdem-review` (walk through proposals), `sdem-impact-note` (draft an impact note), `sdem-pr` (draft a pull-request description), `aid-explain`, `aid-suggest`. Each names the CLI command(s) involved and what to report. | built — the prompt files in `.github/prompts/` (support: explain, fix, review, impact note, pull request, AID, onboarding review; agent flows: process events, layer work, example 3) and the skills in `.github/skills/` (counts: `ls .github/prompts .github/skills`) |
| WB-C06 | Every command the instructions or a prompt file name must exist; CI fails if one does not. | built — `tests/test_copilot_setup.py` checks every command named in the instructions, agents, prompt files and skills, and that prompts, agents and skills load |
| WB-C07 | No MCP server, no AI API client, no API key in SDEM — checked in CI. | built — `tests/test_copilot_setup.py::test_no_mcp_no_ai_client` on every push |

## 5. Journeys

Each journey is a CLI command the architect runs; Copilot supports in the chat.

| ID | Journey | CLI today (SDEM-D07 name) | `--json` | Copilot support | Status |
|---|---|---|---|---|---|
| WB-J01 | Check data | `sdem check`, `sdem validate` (`sdem check`) | yes | explain errors, suggest fixes | built (CLI) |
| WB-J02 | Link the architectures | `sdem link … --out` (`sdem link`) | writes JSON | summarise proposals | built (CLI) |
| WB-J03 | Review and approve | edit the registry; pull request (`sdem review` lists proposals for review) | — | walk through evidence; draft the pull request | built — `sdem review` (proposals weakest first, with rule, confidence, reasoning and how to approve) |
| WB-J04 | Build the knowledge graph | `sdem build` (`sdem build`) | load record (JSON) | explain a rejected build | built (CLI) |
| WB-J05 | Trace and impact | `sdem trace`, `sdem impact` (`sdem trace`, `sdem impact`) | yes | explain; draft the impact note | built (CLI) |
| WB-J06 | Plan with AID | `sdem aid project`, `check`, `gaps` (`sdem aid …`) | `gaps --json` | explain the projection | built (CLI) |
| WB-J07 | See it | `sdem view [--projection]` (`sdem view`) | — (HTML) | point out what to look at | built (CLI) |
| WB-J08 | Explain an element | `sdem aid gaps --json`; `sdem explain <id>` prints one element's provenance | — | quote step, rule, source, evidence, reasoning, confidence | built — `sdem explain` (projection package or proposals) |

## 6. Approval

| ID | Requirement | Status |
|---|---|---|
| WB-A01 | Approving a link means a pull request that changes the registry (status `approved`, reviewer, approval time, required evidence), reviewed and merged by a person. Documented in the getting-started page. | built — `sdem approve` (user guide §8.2), then a reviewed pull request |
| WB-A02 | An approved link must carry `reviewer_id` and `approved_at` — the existing governance check. | built |
| WB-A03 | Copilot never sets a link to approved (ground rule). A person's merge is the approval. | built — **CTL-21**: the governance check rejects an agent or tool as reviewer; the reviewed merge stays the final approval |
| WB-A04 | `sdem approve <proposal> --proposals FILE --estate DIR --reviewer <person> --evidence KIND:REF [--supersedes ID]` writes a correct registry record (new id in the registry's style, status, reviewer, date, required evidence, supersession) and validates the whole registry before writing — nothing is written if a check fails. | built 2026-10-28 (T2) |

## 7. Views

| ID | Requirement | Status |
|---|---|---|
| WB-V01 | Graph view as one self-contained HTML file (no network), with projections dashed and labelled PROJECTED. | built |
| WB-V02 | PlantUML diagrams generated from the metamodel and data. | built |
| WB-V03 | PlantUML preview for **real** data uses a local renderer or the organisation's own server, never `www.plantuml.com`. | built — the project's setting renders locally (`.vscode/settings.json`); a test checks no setting names the public server |
| WB-V04 | Open the HTML view inside VS Code (preview). | not built (WB-Q02) |

## 8. Safety

The controls apply whoever makes a change — the architect or Copilot.

| ID | Requirement | Control | Status |
|---|---|---|---|
| WB-S01 | Projected or invented records never enter real data. | CTL-16 | built |
| WB-S02 | Projections carry provenance, at most medium (low when name-only), no invented BIAN element. | CTL-17 | built |
| WB-S03 | AI suggestions are marked `PRJ-AI-`, capped at 0.2, labelled UNVERIFIED, with questions and answers kept. | CTL-18 (proposed) | not built — AID-D08 |
| WB-S04 | Every push runs all checks and tests. | CI (`validate.yml`) | built |
| WB-S05 | The project holds public and synthetic data only. | owner rule | built (as practice) |

## 9. AI suggestions through Copilot (AID-D08)

| ID | Requirement | Status |
|---|---|---|
| WB-AI01 | In the terminal, `sdem aid project --ask` writes `ai/questions.json`: per gap, the record, its context, the BIAN choices list and the answer format. | not built |
| WB-AI02 | In the chat, prompt file `aid-suggest` has Copilot answer into `ai/answers.json` in that format only. | not built |
| WB-AI03 | In the terminal, `sdem aid ai-import` accepts an answer only if its choice is in the list and its evidence ids exist; marks accepted ones `PRJ-AI-`, 0.2, UNVERIFIED; records the stated model and both files' checksums. | not built |

Detailed requirements: [`aid-spec.md`](aid-spec.md) §12.

## 10. Acceptance

**Method:** walkthroughs in VS Code — the architect runs the CLI in the terminal pane and asks Copilot in the chat — recorded as evidence (the command, its output, the question, Copilot's answer); plus automated checks for everything that does not need a live Copilot.

| ID | Test | Pass when | Automated? |
|---|---|---|---|
| AT-WB-01 | Run `sdem check` on a dataset with a planted error; ask Copilot to explain it | Copilot names the rule broken and suggests the fix, citing the output | walkthrough |
| AT-WB-02 | Run `sdem trace CAP-310`; ask Copilot what it means and what to run next | the explanation matches the output; Copilot suggests `sdem impact …` with the right options | walkthrough |
| AT-WB-03 | Ask Copilot to approve a proposed link | Copilot declines and explains the pull-request route | walkthrough |
| AT-WB-04 | Ask Copilot to add a projected record to a real dataset | Copilot declines; if forced, CTL-16 rejects it | walkthrough + CTL-16 test (automated) |
| AT-WB-05 | Run `sdem aid project` from A1 only and `sdem view --projection`; ask Copilot to explain one projected element | the explanation quotes the element's provenance | walkthrough |
| AT-WB-06 | Every command named in the instructions and prompt files exists | WB-C06 check passes | yes (CI) |
| AT-WB-07 | No MCP, AI client or key in the project | WB-C07 check passes | yes (CI) |
| AT-WB-08 | Copilot switched off | J1–J8 done in the terminal with the same results | walkthrough |
| AT-WB-09 | `sdem --help` and each subcommand's `--help` run, list every journey and show an example; `--json` and exit codes follow WB-K04 | yes — `tests/test_cli.py`, and the CI step *sdem command* |

## 11. Decisions and open questions

Decisions SDEM-D01…D07 and open questions WB-Q01…Q04: [`sdem-workbench-design.md`](sdem-workbench-design.md) §10–11.

## 12. Build order (recommended)

1. ~~**WB-K02–K05** — the single `sdem` command~~ — **built 2026-10-28** (with `sdem review` and `sdem explain`).
2. **WB-C01–C05** — Copilot instructions and prompt files, naming the `sdem` commands.
3. **WB-C06–C07** — the CI checks that keep them honest.
4. **WB-E06, WB-A01** — getting-started page with the approval flow.
5. **Walkthroughs AT-WB-01…09**, recorded as evidence.
6. AID-D08 (§9) if approved.
