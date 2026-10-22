# Synthetic Digital Lending — use case M2 (greenfield: mapping ends, design begins)

All identifiers are **synthetic**; `SD-LO`, `BIAN-CONSUMER-LOAN-ORIGINATION` and the rest are stand-ins, not BIAN content.

A new product line. A1 (two capabilities, a value stream with four stages, three processes with activities, two business objects) and A2 (two synthetic Service Domains with eight operations, control records, qualifiers, a scenario, two BOM objects) are designed and the A1→A2 arrows are approved (`m2-mappings-given.json`, LN-001…008). **There is no A3 or A4 export** — nothing has been built.

| File | Instances | Notes |
|---|---|---|
| `a1-business.json` | 15 | capabilities, value stream and stages, processes with `invokes`, activities, objects |
| `a2-service-domain.json` | 23 | two domains, asset types with aliases, control records, two qualifiers with aliases, eight operations, a scenario, two BOM objects |

**The test** is not whether the plan can map A2 to A3 — it cannot, there is nothing to join. It is whether the executor produces a **target design** from BIAN's container pattern (one deployable component per Service Domain exposing its operations as a REST API) and labels it as design, not mapping. Design proposals use fixed ids so they can be scored: `DSN-APP-<domain id>`, `DSN-API-<operation id>`, `DSN-DEP-<domain id>`, written as `lifecycle_status: planned` instances in `m2-design-a3.json` / `m2-design-a4.json`, with `method` and `path` on each API. `m2-gold-design.json` (sealed, 12 records) is the reference design an architect accepted. Its records are `status: approved` **only so that `sdmm-eval` counts them** — the scorer keys on approved gold; each rationale says so. The executor's own records stay `proposed`.

**Must not appear:** any `DEPLOYED_ON` to a platform — there is no data to name one; any `MAPPED_TO` — no data entity exists; any proposal typed as a mapping (`created_by` must name the pattern source; rationale must say *target design*).
