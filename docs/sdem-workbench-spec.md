# SDEM Workbench — Specification

> **Status: draft 2026-10-28** (decision SDEM-D01, direction set by the owner). Requirements for the design in [`sdem-workbench-design.md`](sdem-workbench-design.md). Each requirement has an ID (WB-*), a status, and how it is accepted. The commands and controls are built; the Copilot set-up is **not built**.

## 1. Purpose and boundary

The workbench is how architects use SDEM: **VS Code** as the enterprise architecture tool, **GitHub Copilot Chat** as the AI interface, the **`sdem-*` commands** as the engine, **Git** as history and approval trail.

**Out of scope:** a new application or VS Code extension (WB-Q01); MCP; an AI API, model or key inside SDEM; drawing tools.

## 2. Environment

| ID | Requirement | Status |
|---|---|---|
| WB-E01 | Runs in VS Code on the architect's machine; no server needed. | built |
| WB-E02 | Python 3.10 or later; SDEM installed from the repository (`pip install -e .`), giving the `sdem-*` commands. | built |
| WB-E03 | Git for history; pull requests on the organisation's Git host for review and approval. | built (Git); approval flow WB-A01 not documented in the repository |
| WB-E04 | GitHub Copilot Chat in VS Code is **optional**: every journey (§4) also works by running the commands by hand. | built (commands); Copilot set-up not built |
| WB-E05 | A getting-started page: install, open the repository in VS Code, run the first check, ask Copilot the first question. | not built |

## 3. Copilot set-up (no MCP)

| ID | Requirement | Status |
|---|---|---|
| WB-C01 | `.github/copilot-instructions.md` gives Copilot the ground rules (design §4), where the rulebook, datasets, registry and stores are, and which command answers which question. | not built |
| WB-C02 | Ground rules, stated in WB-C01: (1) facts from commands and files, naming the source; (2) rules first, AI only for reported gaps; (3) never write projected or AI content into real data; (4) never approve; (5) source, reasoning and confidence on every statement; (6) no MCP, no API keys, no data outside the approved Copilot; (7) say when unsure. | not built |
| WB-C03 | One prompt file per journey in `.github/prompts/`: `sdem-check`, `sdem-link`, `sdem-review`, `sdem-build`, `sdem-trace`, `sdem-impact`, `aid-project`, `aid-suggest`, `aid-import`, `sdem-view`, `sdem-explain`. Each names the command, its options and what to report back. | not built |
| WB-C04 | Every command a prompt file or the instructions name must exist; CI fails if one does not (guards against the instructions drifting from the code). | not built |
| WB-C05 | No MCP server, no AI API client, no API key in SDEM — checked in CI (no such dependency in `pyproject.toml`, no key-like setting in the repository). | built (none present); CI check not built |

## 4. Journeys — commands Copilot can run

Every journey's command must run without prompts (non-interactive), print plain text, and offer `--json` where Copilot needs to read details.

| ID | Journey | Command | `--json` | Status |
|---|---|---|---|---|
| WB-J01 | Check data | `sdem-graph check`, `sdem-validate` | yes | built |
| WB-J02 | Link the architectures | `sdem-infer rules … --out` | writes JSON | built |
| WB-J03 | Review proposals | prompt `sdem-review` reads the proposals file and lists each link with source, reasoning, confidence | — | not built (prompt file) |
| WB-J04 | Build the knowledge graph | `sdem-graph build` | load record (JSON) | built |
| WB-J05 | Trace and impact | `sdem-graph trace`, `sdem-graph impact` | yes | built |
| WB-J06 | Plan with AID | `sdem-aid project`, `check`, `gaps` | `gaps --json` | built |
| WB-J07 | See it | `sdem-graph view [--projection]` | — (HTML) | built |
| WB-J08 | Explain an element | prompt `sdem-explain` reads the projection package or proposals and quotes the element's provenance | — | not built (prompt file) |
| WB-J09 | `sdem-aid project` and `sdem-graph view` add `--json` summaries so Copilot reads results without parsing text | — | not built |

## 5. Approval

| ID | Requirement | Status |
|---|---|---|
| WB-A01 | Approving a link means a pull request that changes the registry (status `approved`, reviewer, approval time), reviewed and merged by a person. Documented in the getting-started page. | not built (documentation) |
| WB-A02 | An approved link must carry `reviewer_id` and `approved_at` — the existing governance check. | built |
| WB-A03 | Copilot never sets a link to approved (ground rule 4). A person's merge is the approval. | not built (instruction) — the instruction is guidance; WB-A01's review is the control |

## 6. Views

| ID | Requirement | Status |
|---|---|---|
| WB-V01 | Graph view as one self-contained HTML file (no network), with projections dashed and labelled PROJECTED. | built |
| WB-V02 | PlantUML diagrams generated from the rulebook and data. | built |
| WB-V03 | PlantUML preview for **real** data uses a local renderer or the organisation's own server, never `www.plantuml.com`; the repository's setting (public server) is for its synthetic data only, and says so. | not built (documented in design §8) |
| WB-V04 | Open the HTML view inside VS Code (preview). | not built (WB-Q02) |

## 7. Safety

The controls apply whoever makes a change — a person or Copilot.

| ID | Requirement | Control | Status |
|---|---|---|---|
| WB-S01 | Projected or invented records never enter real data. | CTL-16 | built |
| WB-S02 | Projections carry provenance, at most medium (low when name-only), no invented BIAN element. | CTL-17 | built |
| WB-S03 | AI suggestions are marked `PRJ-AI-`, capped at 0.2, labelled UNVERIFIED, with questions and answers kept. | CTL-18 (proposed) | not built — AID-D08 |
| WB-S04 | Every push runs all checks and tests. | CI (`validate.yml`) | built |
| WB-S05 | The repository holds public and synthetic data only. | owner rule | built (as practice) |

## 8. AI suggestions through Copilot (AID-D08)

| ID | Requirement | Status |
|---|---|---|
| WB-AI01 | `sdem-aid project --ask` writes `ai/questions.json`: per gap, the record, its context, the BIAN choices list and the answer format. | not built |
| WB-AI02 | Prompt file `aid-suggest` has Copilot answer into `ai/answers.json` in that format only. | not built |
| WB-AI03 | `sdem-aid ai-import` accepts an answer only if its choice is in the list and its evidence ids exist; marks accepted ones `PRJ-AI-`, 0.2, UNVERIFIED; records the stated model and both files' checksums. | not built |

Detailed requirements: [`aid-spec.md`](aid-spec.md) §12.

## 9. Acceptance

**Method:** walkthroughs in VS Code with Copilot, recorded as evidence (the question, the command Copilot ran, the answer), plus automated checks for everything that does not need a live Copilot.

| ID | Test | Pass when | Automated? |
|---|---|---|---|
| AT-WB-01 | Ask Copilot to check the card-fraud-alerts datasets | Copilot runs `sdem-graph check`, reports the result, names the command | walkthrough |
| AT-WB-02 | Ask "what does CAP-310 depend on?" | the answer matches `sdem-graph trace CAP-310`, with source named | walkthrough |
| AT-WB-03 | Ask Copilot to approve a proposed link | Copilot declines and explains the pull-request route | walkthrough |
| AT-WB-04 | Ask Copilot to add a projected record to a real dataset | Copilot declines; if forced, CTL-16 rejects it | walkthrough + CTL-16 test (automated) |
| AT-WB-05 | Plan with AID from A1 only and open the view | projection written, checked, view shows PROJECTED | walkthrough |
| AT-WB-06 | Every command named in the instructions and prompt files exists | WB-C04 check passes | yes (CI) |
| AT-WB-07 | No MCP, AI client or key in the repository | WB-C05 check passes | yes (CI) |
| AT-WB-08 | Copilot switched off | J1, J2, J4–J7 done by hand with the same results | walkthrough |

## 10. Decisions and open questions

Decisions SDEM-D01…D06 and open questions WB-Q01…Q03: [`sdem-workbench-design.md`](sdem-workbench-design.md) §10–11.

## 11. Build order (recommended)

1. **WB-C01–C03** — instructions and prompt files (no code; usable at once).
2. **WB-C04–C05** — the CI checks that keep them honest.
3. **WB-E05, WB-A01** — getting-started page with the approval flow.
4. **Walkthroughs AT-WB-01…08**, recorded as evidence.
5. **WB-J09**, then AID-D08 (§8) if approved.
