# Synthetic Trade Finance — coverage cases C1, C2, C3

All identifiers are **synthetic**; `SD-LC`, `BIAN-LETTER-OF-CREDIT` and the rest are stand-ins, not BIAN content.

One estate authored so that **every plan row the first seven cases never exercised has data**: a documentary letter-of-credit capability with a value stream, processes, activities, two business services, three requirements, an actor and a role; a synthetic business area and domain over two Service Domains with operations, qualifiers, control records with lifecycle states, a scenario, BOM objects and attributes; a solution building block over two components with services, interfaces, six APIs, three application functions, three tables and an event; and a technology estate with a node pool, a container runtime, a scanning device, a database, four technology services, two technology interfaces, a network, a path, three artefacts, an environment and two deployments.

| File | What it holds |
|---|---|
| `a1–a4-*.json` | 85 instances to `metamodel/export-conventions.json` 0.5.10 (the new keys: `inputs/outputs`, `applies_to`, `lifecycle_states`, `exposed_through`, `built_as`, `network_zone`, `published_to`, `components`, `hosts` on a device, `connects`, `carries`, `of_service`/`exposes`, `of_component`) |
| `mappings.json` | the 24 registry arrows, all approved, each rationale tagged with its plan ID |
| `candidates.json` | the 100 candidate-rule gold reports, `relationship` = plan ID |
| `c1-*`, `c2-*`, `c3-*` | per case: `-mappings-given.json`, `-gold-mappings.json` (sealed), `-gold-candidates.json` (sealed) |

| Case | Hidden level pair | Registry rows | Candidate rows |
|---|---|---|---|
| C1 | A1→A2 | S12 | S03 S06 S07 S08 S09 S13 S14 S15 S16 |
| C2 | A2→A3 | S17 S24 S30 | S18 S19 S20 S21 S22 S23 S25 S26 S27 S28 S29 S31 |
| C3 | A3→A4 | S32 S33 S34 S35 | S37 S38 S39 S40 S41 S42 S43 S44 S45 S46 S47 S48 S49 S50 S51 S52 S53 S54 |

```bash
python -m sdmm.graph check examples/trade-finance/a*.json examples/trade-finance/mappings.json
python -m sdmm.evaluate examples/trade-finance/c2-gold-candidates.json --proposals examples/trade-finance/c2-candidates.json
```
