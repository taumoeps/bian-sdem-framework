# Synthetic Legacy Core Ledger — use case H1 (hard, reverse mapping)

All identifiers are **synthetic**; `SD-CA`, `BIAN-CURRENT-ACCOUNT` and the rest are stand-ins, not BIAN content.

A twenty-year-old core banking ledger ("LedgerMaster"). Its A3 — five modules, four SOAP interfaces, fourteen operations and three batch jobs, five tables — and its A4 — mainframe LPAR, DB2, MQ — are fully documented in the CMDB. **No mappings exist.** A2 is a synthetic BIAN-style architecture dataset of the four domains the ledger touches. A1 is only a **draft capability list** (six names with descriptions): no processes, no value streams, no mappings.

| File | Instances | Notes |
|---|---|---|
| `a1-business.json` | 6 | draft capabilities only — two of them (Consumer Lending, Treasury) have nothing in this estate |
| `a2-service-domain.json` | 42 | four domains with asset types, patterns, control records, qualifiers, 14 operations with action terms, four BOM objects |
| `a3-application.json` | 32 | the ledger, five modules, four interfaces, 14 SOAP operations (**every one is POST**) and 3 batch jobs (`method: BATCH`), five tables |
| `a4-technology.json` | 7 | LPAR, DB2, MQ, scheduler, environment, deployment, network |

`h1-mappings-given.json` is **empty**: nothing is known. `h1-gold-mappings.json` (sealed) holds 28 approved connections: 14 `IMPLEMENTED_BY` (every SOAP operation; those whose action term does not fit POST are approved with a recorded deviation), 4 `REALIZED_BY` at **module** level, 4 `MAPPED_TO`, `DEPLOYED_ON` / `DEPLOYED_AS`, and 4 `SUPPORTED_BY` for the capabilities the architect recognised.

**Planted / to refuse:** all operations are POST, so step 2 check 2 passes only for Initiate/Register and fails for every Retrieve, Update, Control and Execute — those must be proposed one band lower with a *systematic* finding, not dropped. Three batch jobs have `method: BATCH` and map to nothing. The ledger as a whole (`APP-LEDGER`) composes the modules that expose the operations — realisation is at module level; the whole is a derived path. `ENT-AUDIT` matches no BOM object. `CAP-LENDING` and `CAP-TREASURY` match no domain — no proposal, not a low-confidence guess.
