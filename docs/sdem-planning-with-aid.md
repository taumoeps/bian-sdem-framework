# Planning missing layers with AID

> **Status: current (v0.9.6)** — for architects: projecting the layers you do not have yet (*Architecture Inference Design*). Moved from the user guide §8.5. It assumes you have done the user guide's quick start (§5) and copied an example estate to `work/my-estate` (§8.1).


*Goal: you have only the business design; see what BIAN domains, applications and deployments it implies — before anything is built.*

AID needs a **BIAN catalogue** — the BIAN service domains your organisation uses, as an A2 dataset. Here the example estate's A2 file stands in for it.

```bash
sdem aid project --have work/my-estate/a1-business.json --catalogue work/my-estate/a2-service-domain.json --out work/prj
```
```
projection PRJ-A1 written to work/prj: A2 16 records, A3 6 records, A4 1 records, 11 links
NOTE: SO-PI-06: Notify has no REST form — no API projected
```

- AID chose the BIAN domain the business needs (*Payment Initiation*, because the processes name its operations), projected **one application component** for it, **one API per operation** in BIAN's REST style, and **one deployment** — but **no platform or environment**, because nothing in the business design says anything about them.
- Everything projected has an id starting `PRJ-`, a confidence (never above 0.6) and its reasoning. **It is a plan, not real data** — SDEM refuses to load it into real data.

See it on top of what you have:
```bash
sdem view --graph work/graph --projection work/prj -o work/plan.html
```
Projected records and links are **dashed** and labelled **PROJECTED**. Ask why any element exists:
```bash
sdem explain SD-PI --projection work/prj
```
```
PROJECTED ELEMENT  SD-PI  Payment Initiation (synthetic selection)  (A2 A2.ServiceDomain)
  step              F1
  rule              BIAN catalogue reference
  source reference  BIAN reference catalogue … — the element is copied, not invented
  inferred from     ACT-PAY-01a 'Capture instruction', …, PRC-PAY-01 'Capture and validate payment instruction', …
  reasoning         the business layer points to it — S04 — invokes SO-PI-01 (PRC-PAY-01.invokes); …
  confidence        0.6
```

**Later, when the real design exists**, compare plan and reality:
```bash
sdem aid gaps work/prj --actual work/my-estate/a2-service-domain.json work/my-estate/a3-application.json work/my-estate/a4-technology.json work/my-estate/mappings.json
```
```
A2 service domains: {'projected': 1, 'real': 1, 'matched': 1, 'precision': 1.0, 'recall': 1.0}
A3 APIs (method and path): {'projected': 5, 'compared': 5, 'matched': 3, 'differs': 2, …}
A4 deployments: {'projected': 1, 'real': 1, 'matched': 0, …}
```
Each line says how close the plan was: here the domain and component were right, 3 of 5 APIs matched the real method and path, and the real application is deployed twice where AID planned once.

AID also works upwards — e.g. from technology only (`--have a4-technology.json`) it suggests the applications, domains and capabilities that technology appears to support, at low confidence. See [`aid-design.md`](design/aid-design.md).
