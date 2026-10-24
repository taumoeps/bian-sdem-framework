# BIAN reference model boundary

> **Terminology (v0.7.0).** SDMM was renamed **SDEM — Service Domain Enterprise Metamodel**. This document keeps its original wording as a record, so read: *mapping set* / *mapping document* = **Architecture Relationship Registry**; *mapping model*, *plan* / *new mappings* = **Architecture Relationship Rules Model**; *registry* (the nine relationship types) = **relationship type catalogue**, part of the **Architecture Metamodel**; *mapping engine* / *executor* = **Architecture Relationship Inference Engine**; *local graph* / *federated graph* = **local / federated architecture knowledge graph**. Commands shown as `sdmm-*` and paths under `sdmm/` are now `sdem-*` and `sdem/` (the old names still work in v0.7 and are removed in v0.8.0). See [`sdem-overview.md`](sdem-overview.md).

This repository contains **only original SDEM guidance**, synthetic examples, and cross-layer modelling conventions.

Do not check in copied BIAN Service Landscape content, BOM diagrams, BIAN proprietary datasets, or bank/company architecture artefacts without explicit distribution rights. Reference a named BIAN release and resolvable canonical identifiers when your runtime has separately licensed access.

## Authority categories
Every registry entry carries an `authority`, and every mapping inherits it:

| `authority` | Meaning | Validator behaviour |
|---|---|---|
| `bian_reference` | Constrained by a canonical published BIAN definition (with release and source record) | mapping must carry `bian_release`; `canonical_id`s are resolved if a reference adapter is attached |
| `bian_alignment_guidance` | Grounded in published BIAN alignment methodology, interpreted for a bank use case | as above |
| `enterprise_rule` | The institution's own mapping or implementation policy | no BIAN release required |

No bank-specific rule may be labelled as normative BIAN terminology.

## Reference adapter
`sdem/reference.py` defines the `ReferenceResolver` protocol: `resolve(canonical_id, release) -> ReferenceBinding | None`. A bank with the applicable rights implements it against its own licensed copy; the repository ships only `NullReferenceResolver` and an in-memory `StaticReferenceResolver` for tests. Pass a resolver to `validate(..., resolver=...)` to have every `canonical_id` on a BIAN-grounded mapping checked against the named release.

The example relationship labels are SDEM-defined, not claimed to be official BIAN/ArchiMate relationship names.
