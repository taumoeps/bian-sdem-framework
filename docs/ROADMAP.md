# Roadmap

| Release | Deliverable | Acceptance test | Status |
|---|---|---|---|
| v0.1 | Mapping entity types, lifecycle, sample mappings, static validation | Example validates | done |
| v0.2 | Full registry metadata, JSON-Schema enforcement, supersession rules, reference-adapter interface, two examples, packaging, CI matrix | 35 tests green on 3.10–3.12 | done |
| v0.2.1 | Validator hardening: approval timestamps, canonical anchoring of BIAN-guided mappings, typed evidence against `required_evidence`, entity catalogue resolution, `sdmm-diff` for lifecycle transitions and immutability | Unanchored or edited-after-approval records are rejected in CI | done |
| v0.3 | Graph reference implementation (`sdmm-trace`), pure Python, no new dependencies | Traverse approved L0→L3 mappings in both directions from the CLI | next |
| v0.3.1 | Change-impact analysis (`sdmm-impact`) classifying reachable entities as `no_impact` / `review_required` / `design_change_required` | Re-hosting an L2 component flags L3/L2, leaves L0/L1 unchanged | |
| v0.4 | BIAN reference integration: a concrete `ReferenceResolver` against an authorised release (no redistribution) | Canonical ids validated against a named release | |
| v0.5 | AI-assisted mapping proposals with evidence and explanations; output is always `proposed` | Proposals fail validation unless evidence-backed; never auto-approved | |
| v1.0 | Stable methodology specification, interoperability tests, versioned conformance requirements | Documented conformance profile | |
