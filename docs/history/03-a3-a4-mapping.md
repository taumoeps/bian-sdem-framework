# A3 → A4 mapping methodology

> **Terminology (v0.7.0).** SDMM was renamed **SDEM — Service Domain Enterprise Metamodel**. This document keeps its original wording as a record, so read: *mapping set* / *mapping document* = **Architecture Relationship Registry**; *mapping model*, *plan* / *new mappings* = **Architecture Relationship Rules Model**; *registry* (the nine relationship types) = **relationship type catalogue**, part of the **Architecture Metamodel**; *mapping engine* / *executor* = **Architecture Relationship Inference Engine**; *local graph* / *federated graph* = **local / federated architecture knowledge graph**. Commands shown as `sdmm-*` and paths under `sdmm/` are now `sdem-*` and `sdem/` (the old names still work in v0.7 and are removed in v0.8.0). *Export* / *level export* / *level model* (the file of one architecture's records) = **architecture dataset** (renamed 2026-10-27; W3C DCAT sense of *dataset*). See [`sdem-overview.md`](../sdem-overview.md).

Map application components to actual infrastructure components and deployments.

- `DEPLOYED_ON`: A3 Application Component → A4 Infrastructure Component.
- Infrastructure relationships use a bank-specific metamodel, optionally aligned with ArchiMate; BIAN is not a complete physical infrastructure specification.
- Include deployment environment, design baseline and evidence.
- Impact traversal must distinguish directly changed from potentially impacted components.
