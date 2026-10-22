# Synthetic Card Fraud Alerts mapping — a change event

All identifiers (`CAP-310`, `SD-044`, `BIAN-FRAUD-DETECTION`, `BIAN-RELEASE-X`, …) are **synthetic**. They are not official BIAN IDs and do not represent verified BIAN release content.

Where `customer-onboarding` shows a static chain, this example shows what happens **when something changes**: the fraud engine is re-hosted from an on-prem VM cluster to managed Kubernetes.

| Record | Status | What it shows |
|---|---|---|
| FRD-001 | approved | A1 capability → A2 domain; BIAN-grounded, so it carries `bian_release` and a `canonical_id` |
| FRD-002 | approved | A2 domain → A3 fraud engine; rationale records what is *out* of scope (case management) |
| FRD-003 | **superseded** | The original on-prem deployment, kept as history with `valid_to` |
| FRD-005 | approved | The new cloud deployment; `previous_mapping_id: FRD-003` closes the supersession chain |
| FRD-004 | approved | Operation → API, approved after the M0 run on REST-rule evidence (rules 1, 3, 4; Notify has no REST form) |
| FRD-008 | approved | Process perspective: the alert process `USES_DOMAIN` the fraud domain |
| FRD-009 | proposed | Engine candidate at 0.55 — the scoring component may realise part of the domain; not yet a fact |
| FRD-006 | approved | `DEPLOYED_AS` to the production deployment `DEP-FRAUD-PROD` — the precise form of FRD-005 |
| FRD-007 | approved | Process perspective: the *Use Card Safely* value stream aligned to the fraud-alert scenario |

Things to notice:

- **FRD-001 and FRD-002 were not touched** by the re-hosting. The change was A3/A4 only; reachability from A4 does not imply A2 must change.
- **FRD-003 was not edited or deleted.** A baseline query for a date before `2026-12-01` still finds it.
- **FRD-009 is excluded** from any "approved edges only" traversal until an architect sets `reviewer_id` and a reviewed status.

`entities.json` is a catalogue of every entity the mappings refer to — a stand-in for the bank's EA tool, BIAN model and CMDB. Evidence is cited as `kind:reference` so the validator can check each arrow carries the evidence kinds its type requires.

```bash
python -m sdmm.validate --strict --catalogue examples/card-fraud-alerts/entities.json examples/card-fraud-alerts/mappings.json
python -m sdmm.diff --git HEAD~1 examples/card-fraud-alerts/mappings.json
```

Try breaking it: remove `previous_mapping_id` from FRD-005 and the validator reports that FRD-003 has no successor. Change FRD-001's `rationale` and `sdmm-diff` reports an edit to an approved record. Point FRD-001 at `SD-NOT-REAL` and the catalogue check fails.

## Walk the chain

```bash
python -m sdmm.trace CAP-310 examples/card-fraud-alerts/mappings.json                      # both directions
python -m sdmm.trace INF-CLOUD-K8S-PROD --direction up examples/card-fraud-alerts/mappings.json
python -m sdmm.trace INF-ONPREM-VM-CLUSTER-B --direction up --status approved,superseded examples/card-fraud-alerts/mappings.json
```

Only `approved` arrows are followed by default, so the superseded on-prem deployment (FRD-003) and the unreviewed candidate (FRD-009) do not appear; the third command includes history and shows the old host's former chain. Every hop prints the `mapping_id` that justifies it.

## Level models and the federated graph (v0.4)

`a1-business.json` … `a4-technology.json` are synthetic exports of the four design models in `schema/level-model.schema.json` format — the instances the mappings refer to, with names and within-level relationships. They stand in for an institution's EA tool, BIAN workbench, APM and CMDB.

```bash
python -m sdmm.graph check  examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
python -m sdmm.graph trace  CAP-310 examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
python -m sdmm.graph impact INF-CLOUD-K8S-PROD --change rehost examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
python -m sdmm.graph impact SD-044 --change retire examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json
```

`proposals-baseline.json` is the output of `sdmm-engine baseline` over the level files; `sdmm-eval mappings.json --proposals proposals-baseline.json` scores it at F1 0.62 — four of five approved arrows found, the deployment to the platform missed.

Notice that `INF-CLOUD-K8S-PROD` is an `A4.SystemSoftware` in the level model while the mappings call it `A4.InfrastructureComponent`: the federated graph resolves it through the entity hierarchy. The rehost impact marks A4 and A3 `design_change_required`, A2 and A1 `no_impact`, and names `FRD-005` as the mapping to supersede.
