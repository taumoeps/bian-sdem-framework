# A2 → A3 mapping methodology

> **Terminology (v0.7.0).** SDMM was renamed **SDEM — Service Domain Enterprise Metamodel**. This document keeps its original wording as a record, so read: *mapping set* / *mapping document* = **Architecture Relationship Registry**; *mapping model*, *plan* / *new mappings* = **Architecture Relationship Rules Model**; *registry* (the nine relationship types) = **relationship type catalogue**, part of the **Architecture Metamodel**; *mapping engine* / *executor* = **Architecture Relationship Inference Engine**; *local graph* / *federated graph* = **local / federated architecture knowledge graph**. Commands shown as `sdmm-*` and paths under `sdmm/` are now `sdem-*` and `sdem/` (the old names still work in v0.7 and are removed in v0.8.0). *Export* / *level export* / *level model* (the file of one architecture's records) = **architecture dataset** (renamed 2026-10-27; W3C DCAT sense of *dataset*). See [`sdem-overview.md`](../sdem-overview.md).

Map approved A2 functional responsibilities to actual A3 application components, and A2 service operations to A3 API operations.

- `REALIZED_BY`: A2 Service Domain → A3 Application Component. Many-to-many; never assume one Service Domain equals one microservice.
- `IMPLEMENTED_BY`: A2 Service Operation → A3 API Operation. Require contract-level evidence and check semantic mismatch.
- `MAPPED_TO`: A2 Business Object → A3 Data Entity. Track transformations and partial coverage.

A BIAN logical interface is not an assertion that an existing API already conforms. Document adaptations, gaps and design decisions.
