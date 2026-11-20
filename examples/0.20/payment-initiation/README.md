# Synthetic Payment Initiation — use case M1 (brownfield), in SDEM 0.20's form

**In SDEM 0.20's form** (migrated 2026-11-21 with `sdem migrate --to 0.20`, DL-D9): files named by layer, records naming types by id, and Data a layer of its own — each access from an application element to a data entity is now an approved `ACCESSED_BY` link (MIG-020-…). SDEM 0.19's form is `examples/payment-initiation` — a test reconciles the two record by record (`tests/test_data_layer.py`, `Reconciled`). Start a workspace from it with `sdem new --example payment-initiation --form 0.20` and `SDEM_EXAMPLES=examples/0.20`.

All identifiers are **synthetic**; `SD-PI`, `BIAN-PAYMENT-INITIATION` and the rest are stand-ins, not BIAN content.

The business and domain architecture are mapped and approved (`m1-mappings-given.json`, PAY-001…005). The payments platform exists — applications, APIs, data entities and deployments are extracted from the APM and CMDB into architecture datasets conventions — but no A2→A3 or A3→A4 mappings have been written. The sealed gold (`m1-gold-mappings.json`, PAY-101…112) holds the connections an architect approved; `mappings.json` is the union.

| File | Instances | Notes |
|---|---|---|
| `business.json` | 16 | two capabilities, a value stream with four stages, two processes with activities (`invokes`), two business objects, a role |
| `bian.json` | 48 | three Service Domains (initiation, execution, party authentication — so step 5 has a real candidate set), asset types, functional patterns, a control record with attributes, two qualifiers, six operations with action terms, a scenario, two BOM objects |
| `data.json` | 3 | three data entities — the Data layer of its own (SDEM 0.20, DL-01) |
| `application.json` | 13 | the hub and three components, a service and interface, six API operations with method/path/payload, an event |
| `technology.json` | 20 | network zones, hybrid — cloud (internal and a DMZ; inside internal the payments private network with both clusters and PostgreSQL) and on premises (internal, with the core banking ledger host the Execution Gateway posts to); an API gateway in the DMZ (it fronts the Payments Hub), two technology services in internal, two environments, three deployments, an image |

**Planted for the executor:** `API-PI-04` implements a *Retrieve* operation as **POST** (a legacy-channel constraint, recorded in the gold's rationale) — REST rule 2 must fail and be reported as a finding while rules 1, 3, 4 hold. `API-PI-06` (events) implements no operation; `SO-PI-06` (Notify) has no REST form. `CMP-PAY-CAPTURE` and `CMP-PAY-VALIDATE` have no deployment records of their own — no `DEPLOYED_ON` may be proposed for them. `ENT-ACCOUNT-CACHE` matches no BOM object. `SD-PE` and `SD-PA` realise nothing in this workspace.

Run from this folder (or give `--workspace` the folder's path):

```bash
sdem check --workspace .
sdem validate --strict --workspace .
sdem build --workspace . --out graph
sdem trace CAP-PAY-010 --direction down --graph graph
```
