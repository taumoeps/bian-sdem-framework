# A1 → A2 mapping methodology

> **Terminology (v0.7.0).** SDMM was renamed **SDEM — Service Domain Enterprise Metamodel**. This document keeps its original wording as a record, so read: *mapping set* / *mapping document* = **Architecture Relationship Registry**; *mapping model*, *plan* / *new mappings* = **Architecture Relationship Rules Model**; *registry* (the nine relationship types) = **relationship type catalogue**, part of the **Architecture Metamodel**; *mapping engine* / *executor* = **Architecture Relationship Inference Engine**; *local graph* / *federated graph* = **local / federated architecture knowledge graph**. Commands shown as `sdmm-*` and paths under `sdmm/` are now `sdem-*` and `sdem/` (the old names still work in v0.7 and are removed in v0.8.0). See [`sdem-overview.md`](sdem-overview.md).

## Purpose
Align a bank's business capabilities, processes/value streams and business concepts to approved BIAN-aligned A2 domain design instances.

## Three evidence perspectives

1. **Functional:** Compare capability descriptions and accountabilities with Service Domain functional boundaries. Allow many-to-many candidate matches.
2. **Process / behaviour:** Compare bank value-stream and process activities with BIAN Business Scenarios and Service Operations; use scenario evidence, not names alone.
3. **Information:** Compare A1 business concepts with BIAN business objects, Control Record structures and BOM relationships.

## Relationship types
- `SUPPORTED_BY`: A1 Business Capability → A2 Service Domain (BIAN alignment guidance).
- `ALIGNED_TO`: A1 Value Stream → A2 Business Scenario (BIAN alignment guidance).
- `USES_DOMAIN`: A1 Business Process → A2 Service Domain (enterprise rule); a process activity invokes the domain's operations.
- `ALIGNED_TO`: A1 Business Object → A2 BIAN Business Object (BIAN alignment guidance).

## Procedure
1. Retrieve A1 entity instances and source documents with versioned evidence.
2. Retrieve authoritative BIAN release-specific definitions through a separately licensed reference adapter.
3. Generate candidate mappings with evidence citations and reasoned alternatives.
4. Validate source/target type, terminology, release, scope and domain boundary.
5. Require architect approval before publishing an approved mapping.

A BIAN scenario is guidance, not proof of exact fit. All examples in this repository are synthetic and avoid distributing official BIAN model content.
