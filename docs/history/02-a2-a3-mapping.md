# A2 → A3 mapping methodology

> **A record, in its original words.** It uses SDEM's old names (SDMM, *mapping set*, *export*, `sdmm-*` …) — what each means today: [`renamed-from-sdmm.md`](renamed-from-sdmm.md).

Map approved A2 functional responsibilities to actual A3 application components, and A2 service operations to A3 API operations.

- `REALIZED_BY`: A2 Service Domain → A3 Application Component. Many-to-many; never assume one Service Domain equals one microservice.
- `IMPLEMENTED_BY`: A2 Service Operation → A3 API Operation. Require contract-level evidence and check semantic mismatch.
- `MAPPED_TO`: A2 Business Object → A3 Data Entity. Track transformations and partial coverage.

A BIAN logical interface is not an assertion that an existing API already conforms. Document adaptations, gaps and design decisions.
