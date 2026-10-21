# L1 → L2 mapping methodology

Map approved L1 functional responsibilities to actual L2 application components, and L1 service operations to L2 API operations.

- `REALIZED_BY`: L1 Service Domain → L2 Application Component. Many-to-many; never assume one Service Domain equals one microservice.
- `IMPLEMENTED_BY`: L1 Service Operation → L2 API Operation. Require contract-level evidence and check semantic mismatch.
- `MAPPED_TO`: L1 Business Object → L2 Data Entity. Track transformations and partial coverage.

A BIAN logical interface is not an assertion that an existing API already conforms. Document adaptations, gaps and design decisions.
