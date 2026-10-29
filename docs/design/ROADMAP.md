# Roadmap

> **Status: current** — updated with every release; v0.9.9 released 2026-10-29.

Realigned 2026-10-25 after a full review of `docs/` against the code. Release numbers before v0.8 are history; earlier plans for v0.6–v0.8 (engine, BIAN reference integration, generated views) were renumbered below because v0.6.0 and v0.7.0 shipped the rules specification and the rename instead.

## Delivered

| Release | Deliverable | Acceptance test | Status |
|---|---|---|---|
| v0.1 | Mapping entities, lifecycle, sample mappings, static validation | Example validates | done |
| v0.2 | Full registry metadata, JSON-Schema enforcement, supersession rules, reference-adapter interface, two examples, packaging, CI matrix | 35 tests green on 3.10–3.12 | done |
| v0.2.1 | Validator hardening: approval timestamps, canonical anchoring, typed evidence, entity catalogue resolution, `sdem diff` for lifecycle and immutability | Unanchored or edited-after-approval records rejected in CI | done |
| v0.3 | Graph reference implementation (`sdem-trace`) | Traverse approved A1→A4 links in both directions | done |
| v0.3.1 | A1–A4 level naming with legacy aliases; adjacency rules from the relationship type catalogue | Legacy documents validate unchanged | done |
| v0.4.0 | Entity catalogue with `extends`/`abstract`, `DEPLOYED_AS`; architecture dataset schema; local and federated graphs (`sdem check/trace/impact/stats`); impact classification — see `06-data-architecture.md` | Rehost impact leaves A1/A2 `no_impact` | done |
| v0.5 | Engine readiness: descriptions, reference adapter interface, engine interface with a name-overlap baseline, `sdem-eval` scorer, impact rules as data — see `07-engine-readiness.md`. Mapping plan, procedure and the use-case runs (executed by hand). Within-level rows from BIAN, ArchiMate and TOGAF, verified | Baseline proposals validate and score F1 ≥ 0.5 | done |
| v0.6.0 | Relationship Rules Model specification (`relationship-rules-spec.md`); knowledge-graph design and specification with service specifications | Generated from the records; current in CI | done |
| v0.7.0 | Renamed SDEM; model-driven terminology; registry specification; compatibility aliases for the old names | Behaviour byte-identical to v0.6.2 | done |
| v0.8.0 | The tool release — see below | the full suite; acceptance 8 of 8; use-case examples 1–4; installed-package job | done |
| v0.9.9 | The inference record for BIAN's unpublished values (66 entries, source/reasoning/confidence/status/history; 48 accepted by the owner → `--all` gives 240 of 258 with full values); `sdem bian inference` commands; metamodel 0.5.0 → 0.6.0 | the full suite, with and without an install; every CI step run locally | done |
| v0.9.8 | All of BIAN with `sdem bian import --all` (258 domains; 66 marked *not known yet*); metamodel 0.4.0 → 0.5.0 (DA2-02); one name — *metamodel*; simpler README diagrams with a command table | the full suite; every CI step run locally; use-case examples re-run | done |
| v0.9.7 | Organisation-neutral wording: *any organisation*, not *any bank*, in the licence, terms and guides; no exclusivity stated | the full suite; every CI step run locally | done |
| v0.9.6 | Fixes from a new architect's review of the terms: README disclaimer visible again, redistribution conditions stated fully, adoption checklist matched to the privacy page, stricter pinning by commit | the full suite; every CI step run locally | done |
| v0.9.5 | Enterprise licensing, usage and privacy: `PRIVACY.md`, `LICENSES.md` by category, enterprise use and IP separation in *Using SDEM*; a test keeps the privacy claims true | the full suite; every CI step run locally | done |
| v0.9.4 | Documentation review fixes: one workspace-contents list, plain language in user documents, a FAQ, AID planning on its own page, recaptured samples; CI fix | the full suite; every CI step run locally | done |
| v0.9.3 | Fixes from the fifth walkthrough: one BIAN source in the onboarding workflow, code owners for SDEM's records, the in-house SDEM lead, the sample export in `examples/designs/` | the full suite | done |
| v0.9.2 | Gaps found by the fourth walkthrough: `sdem bian update` (the shared BIAN layer reaches every workspace, never stranding an approved connection) and `sdem connect` (a person states a connection the engine cannot see) — onboarded designs now trace from capability to technology | the full suite; end-to-end test | done |
| v0.9.1 | Team set-up fixes from the third new-architect walkthrough: workspace-first protection, local check compares with main, shared BIAN layer, `sdem transform rules`, adoption checklist; nine rule source references closed | the full suite | done |
| v0.9.0 | Base BIAN and operational readiness — see below | the full suite; BIAN import checked on releases 10.0–14.0; two new-architect walkthroughs | done |

## v0.9.0 — base BIAN and operational readiness (2026-10-29)

| Deliverable | Status |
|---|---|
| **Base BIAN**: BIAN's public Semantic APIs 14.0.0 ship with SDEM (Apache-2.0); `sdem bian list / import / pack` builds the BIAN layer from it or from an organisation's own BIAN | done |
| **Copilot where real work happens**: `sdem copilot install` puts the agents, prompts and skills into the workspace repository, matching the SDEM version | done |
| **Operating it**: approved operating model and pilot plan; private workspace-repository template with CI; documentation reorganised for newcomers and checked on every push (status, links, owners, drift); two new-architect walkthroughs and their fixes | done |
| **Metamodel**: CTL-24 registered; rule S17's source reference closed | done |

## v0.8.0 — the tool release (2026-10-29)

Everything built since v0.7.0, released as one tool release after the 2026-10-29 audit; the metamodel moved from `metamodel_version` 0.4.0 to 0.5.0 on 2026-10-30 (an additive change: BIAN service domains whose asset type and functional pattern are not known yet, DA2-02); the 0.8 baseline below is still to be approved. Details: [`../CHANGELOG.md`](../../CHANGELOG.md).

| Deliverable | Status |
|---|---|
| Data model: 11 common, 135 entity-specific and 3 derived attributes for A1–A4, each with source reference, reasoning and confidence; logical rules enforced by `sdem check`; per-entity JSON Schemas | done |
| **Graph store**: JSON Graph Format files, load record, baselines, queries, offline HTML view ([`graph-store-design.md`](graph-store-design.md)) | done |
| **Inference engine**: `sdem link` — steps 1–5 and design mode; 8 of 8 acceptance cases; fast and deterministic (2,040 records in about 1 s) | done |
| **Built ahead of their roadmap releases** (below): design onboarding (v0.11), AID (v0.12), change events (v0.13), the SDEM workbench (v0.14), dashboards (v0.16), agent platform Level 1 (v0.17) | done — see each row |
| **Operational readiness** (audit phases 1–3): works when installed, clear errors and exit codes, all-or-nothing writes, `sdem migrate` and metamodel versioning, `SECURITY.md`, real data kept out of this repository, the SDMM compatibility layer removed | done |

## Waiting on review — the 0.8 baseline (tag `SDEM-METAMODEL-0.8`)

| Deliverable | Status |
|---|---|
| Baseline review pack `baseline/SDEM-METAMODEL-0.8-review-pack.md` | done; **awaiting independent review** |
| On approval: record the baseline; `metamodel_version` 0.8.0 with a recorded migration (workspaces move with `sdem migrate`); remove the deprecated `accesses` definition and the `sdmm_*` spellings; tag `SDEM-METAMODEL-0.8` with the next tool release | waiting on review |

## Next — and what is already built of it

> Updated 2026-10-29. *Built (v0.8.0)* means released in v0.8.0 ahead of its own release number; the rest of that row is still to come.

| Release | Deliverable | Acceptance test | Status |
|---|---|---|---|
| v0.11 | **Onboarding and approval** — two routes, *design onboarding* (documents) and *tool onboarding* (tools): spreadsheet templates generated from the schemas and an ingest command; review of proposals into the registry | A synthetic workspace loaded from spreadsheets end to end to an impact query; proposals approved into the registry | **partly built** — **design onboarding built** (Confluence exports: `sdem transform` → review → `sdem load`, gap records; [`sdem-onboarding-workflow.md`](../sdem-onboarding-workflow.md)); approval built (`sdem approve`, with `--bian-release`); **tool onboarding not built** (spreadsheet templates, adapters, an ingest command) |
| v0.12 | **Architecture Inference Design (AID)**: forward and reverse projection of missing layers as a projected design (`PRJ-`), kept apart from real data; gap analysis against real design; controls CTL-16/17 — see `aid-design.md`, `aid-spec.md` | Hidden-layer runs on known workspaces report precision and recall per layer; a projection can never enter real data (CTL-16) | **built (v0.8.0)** — use-case example 2: 12 of 12 sealed expectations, CTL-16/17 15 of 15; spec complete 2026-10-28 (schema, view and trace overlay, finer gap analysis, process candidates); open: blind test, real BIAN catalogue |
| v0.13 | **Change handling**: architecture dataset diff, refresh trigger, re-checking links touched by a change; change events and impact results stored as records (the agent platform's foundation, AG-R01…R05) | A changed architecture dataset flags exactly the affected links | **partly built** — change sets, change events with stored impact, work items, revert (`sdem change`, `events`, `work`); registry diff (`sdem diff`); stale graph-store warnings. A diff of architecture datasets that flags affected links, and a refresh trigger, **not built** |
| v0.14 | **SDEM workbench**: VS Code with the SDEM project open — the CLI in the terminal pane (one `sdem` command, SDEM-D07), GitHub Copilot Chat for support — Copilot instructions and prompt files, CI checks that they name only real commands, getting-started and approval flow (`sdem-workbench-design.md`, `-spec.md`; no MCP); a database behind the access layer if scale requires. The instructions and prompt files need no code and can come first | Questions answered from the store with their baseline | **built (v0.8.0)** — one `sdem` command (J1–J9), Copilot instructions, 10 prompts, 5 skills, CI check that they name only real commands, user guide; no MCP. A database behind the access layer not needed yet |
| v0.15 | **BIAN reference integration**: licensed `ReferenceResolver`, BIAN verification register, Bank Architecture Profiles | Canonical ids validated inside the licensed environment | |
| v0.16 | **Generated views** (matrices, diagrams) from approved data; historical design repository — *partly built 2026-10-28 (status): `sdem dashboard`, `sdem matrix`, `sdem impact --report` ([`sdem-dashboard-design.md`](sdem-dashboard-design.md)); historical repository: Confluence reader built 2026-10-28 (`sdem transform`, [`sdem-transform-design.md`](sdem-transform-design.md)), tested on a synthetic export; load built 2026-10-28 (`sdem load`, [`sdem-load-design.md`](sdem-load-design.md)); past-baseline views remain* | Capability-to-domain matrix generated from approved data only | **partly built** — dashboards, matrices, impact reports; import of past designs (transform, load); past-baseline views **not built** |
| v0.17 | **Agent platform** (approved 2026-10-28): one Copilot agent per architecture (A1–A4) and an orchestrator, coordinating through the federated graph — change sets, change events, stored impact results, work items; `sdem change`, `sdem events`, `sdem work`; controls CTL-19 layer ownership and CTL-20 change provenance (`sdem-agent-platform-design.md`, `-spec.md`). Builds on v0.13 change handling and v0.14 workbench; can follow them directly | Use-case example 3: an A4 rehost carried by the agents to an approved pull request, expected results sealed before the run | **Level 1 built (v0.8.0)** — example 3: 8 of 8; spike pending in the owner's VS Code |
| v1.0 | Stable specification, interoperability tests, conformance profile | Documented conformance profile | |

**Outside the build** (owner only): publication checklist (`PUBLICATION_CHECKLIST.md`) — legal review of employment and IP terms, BIAN permissions, maintainers; an independent reviewer for the baseline; a blind test case authored by someone else.
