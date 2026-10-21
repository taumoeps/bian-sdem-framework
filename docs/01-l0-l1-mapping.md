# L0 → L1 mapping methodology

## Purpose
Align a bank's business capabilities, processes/value streams and business concepts to approved BIAN-aligned L1 domain design instances.

## Three evidence perspectives

1. **Functional:** Compare capability descriptions and accountabilities with Service Domain functional boundaries. Allow many-to-many candidate matches.
2. **Process / behaviour:** Compare bank value-stream and process activities with BIAN Business Scenarios and Service Operations; use scenario evidence, not names alone.
3. **Information:** Compare L0 business concepts with BIAN business objects, Control Record structures and BOM relationships.

## Relationship types
- `SUPPORTED_BY`: L0 Business Capability → L1 Service Domain (BIAN alignment guidance).
- `ALIGNED_TO`: L0 Value Stream → L1 Business Scenario (BIAN alignment guidance).
- `USES_DOMAIN`: L0 Business Process → L1 Service Domain (enterprise rule); a process activity invokes the domain's operations.
- `ALIGNED_TO`: L0 Business Object → L1 BIAN Business Object (BIAN alignment guidance).

## Procedure
1. Retrieve L0 entities and source documents with versioned evidence.
2. Retrieve authoritative BIAN release-specific definitions through a separately licensed reference adapter.
3. Generate candidate mappings with evidence citations and reasoned alternatives.
4. Validate source/target type, terminology, release, scope and domain boundary.
5. Require architect approval before publishing an approved mapping.

A BIAN scenario is guidance, not proof of exact fit. All examples in this repository are synthetic and avoid distributing official BIAN model content.
