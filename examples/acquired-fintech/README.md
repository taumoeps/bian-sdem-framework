# Synthetic Acquired Fintech "Zippa" — use case H2 (hard, hostile naming)

All identifiers are **synthetic**; `SD-PI`, `BIAN-PAYMENT-INITIATION` and the rest are stand-ins, not BIAN content. "Zippa", moneyflows, zaps, pots, buddies, vaults and perks are invented product names.

A recently acquired fintech. Its A3 — seven microservices, 23 REST endpoints known only from OpenAPI stubs — and A4 — one Kubernetes cluster, PostgreSQL, Redis, seven deployments from the manifest — are documented. **There is no A1 export at all** and no mappings. A2 is a synthetic BIAN-style export of six domains. The integration architect has decoded product names for four asset types (`aliases` on `AT-PI`, `AT-PE`, `AT-CA`, `AT-PRD`); **Savings Account and Fraud Case have no aliases**.

| File | Instances | Notes |
|---|---|---|
| `a2-service-domain.json` | 59 | six domains, 20 operations with action terms, six control records and BOM objects; aliases on four asset types |
| `a3-application.json` | 45 | seven services (`flow`, `zap`, `pots`, `buddies`, `vaults`, `perks`, `shield`), 23 endpoints with method, path and payload fields, eight tables |
| `a4-technology.json` | 12 | EKS cluster, PostgreSQL, Redis, queue, namespace, seven deployments |

`h2-mappings-given.json` is **empty**. `h2-gold-mappings.json` (sealed) holds 41 approved connections the architect reached after interviews: 17 `IMPLEMENTED_BY`, 5 `REALIZED_BY`, 5 `MAPPED_TO`, 14 deployment arrows. Several are reachable only by interview, not by the plan — that is the point: the case measures what the plan reaches from hostile names, and precision matters more than recall.

**What the executor must do and refuse.** Money fields follow ISO-style names (`debtor_account_reference`, `amount`, `value_date`) but ids and paths are product names. `zap-svc` uses `sender`/`recipient`/`outcome`: no field matches — no proposal for its endpoints even though the gold maps them. `vaults-svc` reaches Savings Account by **data** (table attributes) but not by API (no alias, no asset word anywhere) — proposing its endpoints at step 2 would be a gate violation. `DELETE` cancel and `POST .../release` / `.../close` fail the method check; `/release` and `DELETE` tie as *Control*'s payload match — a tie is no proposal. `perks`, `shield`, `/ledger`, and `/buddies` map to nothing. No A1: every A1 question is "requires authoring".
