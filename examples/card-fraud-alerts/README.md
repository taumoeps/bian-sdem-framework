# Synthetic Card Fraud Alerts mapping — a change event

All identifiers (`CAP-310`, `SD-044`, `BIAN-FRAUD-DETECTION`, `BIAN-RELEASE-X`, …) are **synthetic**. They are not official BIAN IDs and do not represent verified BIAN release content.

Where `customer-onboarding` shows a static chain, this example shows what happens **when something changes**: the fraud engine is re-hosted from an on-prem VM cluster to managed Kubernetes.

| Record | Status | What it shows |
|---|---|---|
| FRD-001 | approved | L0 capability → L1 domain; BIAN-grounded, so it carries `bian_release` and a `canonical_id` |
| FRD-002 | approved | L1 domain → L2 fraud engine; rationale records what is *out* of scope (case management) |
| FRD-003 | **superseded** | The original on-prem deployment, kept as history with `valid_to` |
| FRD-005 | approved | The new cloud deployment; `previous_mapping_id: FRD-003` closes the supersession chain |
| FRD-004 | proposed | Engine candidate at 0.71 confidence for an API-level link; not yet a fact |

Things to notice:

- **FRD-001 and FRD-002 were not touched** by the re-hosting. The change was L2/L3 only; reachability from L3 does not imply L1 must change.
- **FRD-003 was not edited or deleted.** A baseline query for a date before `2026-12-01` still finds it.
- **FRD-004 is excluded** from any "approved edges only" traversal until an architect sets `reviewer_id` and a reviewed status.

`entities.json` is a catalogue of every entity the mappings refer to — a stand-in for the bank's EA tool, BIAN model and CMDB. Evidence is cited as `kind:reference` so the validator can check each arrow carries the evidence kinds its type requires.

```bash
python -m sdmm.validate --strict --catalogue examples/card-fraud-alerts/entities.json examples/card-fraud-alerts/mappings.json
python -m sdmm.diff --git HEAD~1 examples/card-fraud-alerts/mappings.json
```

Try breaking it: remove `previous_mapping_id` from FRD-005 and the validator reports that FRD-003 has no successor. Change FRD-001's `rationale` and `sdmm-diff` reports an edit to an approved record. Point FRD-001 at `SD-NOT-REAL` and the catalogue check fails.

## Walk the chain

There is no graph engine yet, but the approved records are already connected arrows. This snippet loads them and answers the two traceability questions:

```python
import json
doc = json.load(open("examples/card-fraud-alerts/mappings.json"))
edges = [(m["source"]["id"], m["relationship"], m["target"]["id"])
         for m in doc["mappings"] if m["status"] == "approved"]

def walk(start, downstream=True):
    frontier, seen = [start], []
    while frontier:
        n = frontier.pop()
        for s, rel, t in edges:
            if downstream and s == n:   seen.append(f"{s} -{rel}-> {t}"); frontier.append(t)
            if not downstream and t == n: seen.append(f"{t} <-{rel}- {s}"); frontier.append(s)
    return seen

print("\n".join(walk("CAP-310")))                       # what does the capability depend on?
print("\n".join(walk("INF-CLOUD-K8S-PROD", False)))     # what is affected if the platform changes?
```

Only `approved` arrows are followed, so the superseded on-prem deployment (FRD-003) and the unreviewed candidate (FRD-004) do not appear. This is the behaviour the v0.3 graph adapter will provide as a service.
