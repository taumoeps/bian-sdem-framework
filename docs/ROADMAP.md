# Roadmap

Realigned 2026-10-25 after a full review of `docs/` against the code. Release numbers before v0.8 are history; earlier plans for v0.6–v0.8 (engine, BIAN reference integration, generated views) were renumbered below because v0.6.0 and v0.7.0 shipped the rules specification and the rename instead.

## Delivered

| Release | Deliverable | Acceptance test | Status |
|---|---|---|---|
| v0.1 | Mapping entities, lifecycle, sample mappings, static validation | Example validates | done |
| v0.2 | Full registry metadata, JSON-Schema enforcement, supersession rules, reference-adapter interface, two examples, packaging, CI matrix | 35 tests green on 3.10–3.12 | done |
| v0.2.1 | Validator hardening: approval timestamps, canonical anchoring, typed evidence, entity catalogue resolution, `sdem-diff` for lifecycle and immutability | Unanchored or edited-after-approval records rejected in CI | done |
| v0.3 | Graph reference implementation (`sdem-trace`) | Traverse approved A1→A4 links in both directions | done |
| v0.3.1 | A1–A4 level naming with legacy aliases; adjacency rules from the relationship type catalogue | Legacy documents validate unchanged | done |
| v0.4.0 | Entity catalogue with `extends`/`abstract`, `DEPLOYED_AS`; level export schema; local and federated graphs (`sdem-graph check/trace/impact/stats`); impact classification — see `06-data-architecture.md` | Rehost impact leaves A1/A2 `no_impact` | done |
| v0.5 | Engine readiness: descriptions, reference adapter interface, engine interface with a name-overlap baseline, `sdem-eval` scorer, impact rules as data — see `07-engine-readiness.md`. Mapping plan, procedure and the use-case runs (executed by hand). Within-level rows from BIAN, ArchiMate and TOGAF, verified | Baseline proposals validate and score F1 ≥ 0.5 | done |
| v0.6.0 | Relationship Rules Model specification (`relationship-rules-spec.md`); knowledge-graph design and specification with service specifications | Generated from the records; current in CI | done |
| v0.7.0 | Renamed SDEM; model-driven terminology; registry specification; compatibility aliases for the old names | Behaviour byte-identical to v0.6.2 | done |

## Unreleased — becomes v0.8.0

| Deliverable | Status |
|---|---|
| Data model: 11 common, 135 entity-specific and 3 derived attributes for A1–A4, each with source reference, reasoning and confidence (reviews in `drafts/`) | done |
| Logical data model: all 14 rules enforced by `sdem-graph check` (`sdem/conformance.py`) | done |
| Physical data model: 40 per-entity JSON Schemas (`sdem-physical`) | done |
| Baseline review pack `baseline/SDEM-METAMODEL-0.8-review-pack.md` | done; **awaiting independent review** |
| On approval: record the baseline, `metamodel_version` 0.8.0, remove the deprecated `accesses` definition and the `sdmm` compatibility layer, tag `SDEM-METAMODEL-0.8`, release v0.8.0 | waiting on review |

## Next

| Release | Deliverable | Acceptance test | Status |
|---|---|---|---|
| v0.9 | **Inference engine**: the rule logic of `relationship-rules-spec.md` (fill steps 0–5, caps, candidate file, inference log, design mode), with an acceptance harness over the use-case runs. Decisions DEC-E-01…06 in the spec settle the open questions | On every scored run, precision and recall ≥ the hand-executed run's; every proposal validates; beats the baseline | **next** |
| v0.10 | **Ingestion and approval**: spreadsheet templates generated from the schemas and an ingest command (convert, check, load record); review of proposals into the registry | A synthetic estate loaded from spreadsheets end to end to an impact query; proposals approved into the registry | |
| v0.11 | **Change handling**: export diff, refresh trigger, re-checking links touched by a change | A changed export flags exactly the affected links | |
| v0.12 | **Graph store and query service**; assistant access through a script (no MCP) | Queries answered from the store with history | |
| v0.13 | **BIAN reference integration**: licensed `ReferenceResolver`, BIAN verification register, Bank Architecture Profiles (formerly v0.4.1/v0.4.2/v0.7) | Canonical ids validated inside the licensed environment | |
| v0.14 | **Generated views** (matrices, diagrams) from approved data; historical design repository | Capability-to-domain matrix generated from approved data only | |
| v1.0 | Stable specification, interoperability tests, conformance profile | Documented conformance profile | |

**Outside the build** (owner only): publication checklist (`PUBLICATION_CHECKLIST.md`) — legal review of employment and IP terms, BIAN permissions, maintainers; an independent reviewer for the baseline; a blind test case authored by someone else.
