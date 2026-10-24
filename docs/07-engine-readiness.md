# Engine readiness (v0.5)

> **Terminology (v0.7.0).** SDMM was renamed **SDEM — Service Domain Enterprise Metamodel**. This document keeps its original wording as a record, so read: *mapping set* / *mapping document* = **Architecture Relationship Registry**; *mapping model*, *plan* / *new mappings* = **Architecture Relationship Rules Model**; *registry* (the nine relationship types) = **relationship type catalogue**, part of the **Architecture Metamodel**; *mapping engine* / *executor* = **Architecture Relationship Inference Engine**; *local graph* / *federated graph* = **local / federated architecture knowledge graph**. Commands shown as `sdmm-*` and paths under `sdmm/` are now `sdem-*` and `sdem/` (the old names still work in v0.7 and are removed in v0.8.0). See [`sdem-overview.md`](sdem-overview.md).

> **Current state (2026-10-25).** The engine interface and baseline are in `sdem/inference.py` (`sdmm/engine.py` moved there in v0.7.0); the rule logic is built (v0.10): `sdem/rules_engine.py`, run with `sdem-infer rules --graph <store>`; passes all 8 acceptance cases (`sdem-accept`).

v0.5 is the last release before software starts proposing mappings. It adds nothing that decides a mapping; it adds what an engine needs to read, where its output must go, and how it is scored.

## What an engine is

```python
class MappingEngine(Protocol):
    name: str
    def propose(self, graph: FederatedGraph) -> list[dict]: ...
```

It reads the federated graph (four level exports with `description` text, plus existing mappings) and returns mapping records with `status: proposed`, a `confidence`, a `rationale`, `evidence` beginning with `engine_rationale:`, and `created_by` naming the engine and version. The `proposal()` helper in `sdmm/engine.py` shapes every record identically.

## What an engine may not do

| Rule | Enforced by |
|---|---|
| Never emit any status but `proposed` | `sdmm-validate`: approval needs `reviewer_id` and `approved_at`, which an engine does not have |
| Never name an instance that is not in a level export | `sdmm-graph check` (referential verdict); test `test_engine_never_invents_instances` |
| Never use an entity outside the catalogue, or an arrow outside the registry | `sdmm-validate` structural checks |
| Never store BIAN definition text in this repository | `ReferenceBinding.definition` is populated only by an institution's licensed resolver at run time |

A proposal lacking the evidence kinds its arrow type requires, or the `bian_release` / `canonical_id` a BIAN-guided arrow needs, is accepted with a **warning** ("must be supplied before approval"); the same gap on an `approved` record is an error. Evidence and anchoring are completed during review, not invented by the engine — though an engine carries a `canonical_id` through when the level export already has one.

## What an engine reads

- `instances[].name` and `instances[].description` from each level export (`schema/level-model.schema.json`); `definition_uri` says where the authoritative text lives.
- Within-level relationships (what an application is composed of, which operations a domain exposes).
- Existing approved mappings (what is already realised, what patterns recur).
- BIAN definitions through `ReferenceResolver.resolve(...).definition` — only inside an environment that holds the licence.

## How an engine is scored

```bash
sdmm-engine baseline a1.json a2.json a3.json a4.json > proposals.json
sdmm-validate proposals.json
sdmm-eval mappings.json --proposals proposals.json [--min-f1 0.5]
```

`sdmm-eval` treats the **approved** records in the gold documents as truth, matches proposals on `(source.id, relationship, target.id)`, and reports precision / recall / F1 per relationship type and overall, plus the exact misses and false proposals. `--min-f1` makes it a CI gate. Superseded and proposed records in the gold set are not truth.

The shipped `baseline` engine (name and description word overlap, overlap coefficient ≥ 0.2) scores **P 0.56 / R 0.71 / F1 0.62** on the Card Fraud Alerts example: it finds 5 of 7 approved arrows by name overlap, still misses `DEPLOYED_ON` to the Kubernetes platform (no shared vocabulary — a structural signal is needed), mistakes a deployment for a platform, and proposes one pair an architect had left at `proposed`. That is the floor the v0.6 engine must beat, and the shape of the gap it must close.

## Acceptance for v0.6

An engine is accepted when, on a held-out set of an institution's approved mappings, it reaches an agreed F1 per relationship type, every proposal validates, and a reviewer accepts a tracked share of them. The harness, the gate and the record shape exist now; only the engine is missing.
