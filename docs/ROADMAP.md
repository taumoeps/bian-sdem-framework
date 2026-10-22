# Roadmap

| Release | Deliverable | Acceptance test | Status |
|---|---|---|---|
| v0.1 | Mapping entities, lifecycle, sample mappings, static validation | Example validates | done |
| v0.2 | Full registry metadata, JSON-Schema enforcement, supersession rules, reference-adapter interface, two examples, packaging, CI matrix | 35 tests green on 3.10–3.12 | done |
| v0.2.1 | Validator hardening: approval timestamps, canonical anchoring of BIAN-guided mappings, typed evidence against `required_evidence`, entity catalogue resolution, `sdmm-diff` for lifecycle transitions and immutability | Unanchored or edited-after-approval records are rejected in CI | done |
| v0.3 | Graph reference implementation (`sdmm-trace`), pure Python, no new dependencies | Traverse approved A1→A4 mappings in both directions from the CLI | done |
| v0.3.1 | SDADM level naming A1–A4 with legacy-prefix aliases; adjacency and BIAN-level rules driven by the registry | Legacy-prefixed documents validate unchanged; aliased rename is not an immutability violation | done |
| v0.4.0 | Data architecture: 41-entity catalogue (+3 artefacts) with `extends`/`abstract`, is-a registry matching, `DEPLOYED_AS`, per-mapping verdicts; level-model export schema; local and federated graphs (`sdmm-graph check/trace/impact/stats`); structural impact classification — see `docs/06-data-architecture.md` | v0.2.1 examples validate unchanged; `DEPLOYED_ON → A4.SystemSoftware` resolves; rehost impact leaves A1/A2 `no_impact` | done |
| v0.4.1 | Bank Architecture Profiles (JSON, static rules) and `resolve_entity(ref)`; `example-bank` and `example-cloud` profiles | Bank types resolve through a profile; storage bucket → compute rejected | |
| v0.4.2 | BIAN verification register: `evidence_status` computed from recorded checks against a named release | No `bian_reference` entity confirmed without a register entry | |
| v0.5 | Generated views (matrices, diagrams) projected from the federated graph; baseline-aware impact comparing dated baselines | Capability-to-domain matrix generated from approved data only | |
| v0.6 | BIAN reference integration: a concrete `ReferenceResolver` against an authorised release (no redistribution) | Canonical ids validated against a named release | |
| v0.7 | AI-assisted mapping proposals with evidence and explanations; output is always `proposed` | Proposals fail validation unless evidence-backed; never auto-approved | |
| v1.0 | Stable methodology specification, interoperability tests, versioned conformance requirements | Documented conformance profile | |
