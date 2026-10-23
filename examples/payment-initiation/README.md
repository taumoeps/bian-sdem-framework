# Synthetic Payment Initiation — use case M1 (brownfield)

All identifiers are **synthetic**; `SD-PI`, `BIAN-PAYMENT-INITIATION` and the rest are stand-ins, not BIAN content.

The business and domain architecture are mapped and approved (`m1-mappings-given.json`, PAY-001…005). The payments platform exists — applications, APIs, data entities and deployments are exported from the APM and CMDB to the export conventions — but no A2→A3 or A3→A4 mappings have been written. The sealed gold (`m1-gold-mappings.json`, PAY-101…112) holds the connections an architect approved; `mappings.json` is the union.

| File | Instances | Notes |
|---|---|---|
| `a1-business.json` | 16 | two capabilities, a value stream with four stages, two processes with activities (`invokes`), two business objects, a role |
| `a2-service-domain.json` | 24 | three Service Domains (initiation, execution, party authentication — so step 5 has a real candidate set), asset types, functional patterns, a control record with attributes, two qualifiers, six operations with action terms, a scenario, two BOM objects |
| `a3-application.json` | 16 | the hub and three components, a service and interface, six API operations with method/path/payload, three data entities, an event |
| `a4-technology.json` | 12 | two Kubernetes platforms, PostgreSQL, two technology services, two environments, three deployments, a network, an image |

**Planted for the executor:** `API-PI-04` implements a *Retrieve* operation as **POST** (a legacy-channel constraint, recorded in the gold's rationale) — REST rule 2 must fail and be reported as a finding while rules 1, 3, 4 hold. `API-PI-06` (events) implements no operation; `SO-PI-06` (Notify) has no REST form. `CMP-PAY-CAPTURE` and `CMP-PAY-VALIDATE` have no deployment records of their own — no `DEPLOYED_ON` may be proposed for them. `ENT-ACCOUNT-CACHE` matches no BOM object. `SD-PE` and `SD-PA` realise nothing in this estate.

```bash
python -m sdem.graph check  examples/payment-initiation/a*.json examples/payment-initiation/mappings.json
python -m sdem.validate --strict examples/payment-initiation/mappings.json
python -m sdem.graph trace CAP-PAY-010 --direction down examples/payment-initiation/a*.json examples/payment-initiation/mappings.json
```
