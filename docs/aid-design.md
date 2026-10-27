# Architecture Inference Design (AID) — Design

> **Status: approved 2026-10-27 (decisions AID-D01…07).** Not built, except the first piece (forward projection from BIAN to applications — today's "design mode", proven in test case M2). Requirements: [`aid-spec.md`](aid-spec.md).

## 1. What AID is

**Architecture Inference Design (AID)** is a planning function. An architect starts with the architecture datasets they have — often only one or two of the four — and AID **projects** what the missing layers should look like, using SDEM's rulebook (the metamodel) and the BIAN reference.

| Architect has | AID projects | Used for |
|---|---|---|
| A1 Business only | the BIAN service domains, applications and technology it implies | previewing scope and impact before designing |
| A4 Technology only | the applications, service domains and business it appears to support | understanding what an estate is for, and confirming the upstream design |
| some layers, gaps between | the missing layer in the middle | joining up partial designs |

**The output is a projected design, not a validated design.** It shows how the real design *should* align, each element with an inference confidence. It is for planning — scope, impact, gaps — never a substitute for real architecture data.

## Where AID fits in SDEM

AID is SDEM's **planning lane**, beside the **mapping lane** (the engine, approval, the registry and the federated knowledge graph). Both use the same rulebook and engine rules; gap analysis compares their outputs. AID may read real data but never writes into the mapping lane (control CTL-16). It works **with** the standards — TOGAF gives the method (baseline, target and gap analysis in Phases B–D), ArchiMate the relationship language, BIAN the reference — and automates the projection and the gap analysis they leave to people. Recorded in the detail-level metamodel spec §20 (gap G-18), the knowledge-graph spec (component C-18), the controls register (CTL-16, CTL-17 planned) and the ROADMAP (v0.12).

## 2. Key terms

| Term | Meaning |
|---|---|
| **Projected design** | records and links **inferred, not observed**, each with its reasoning and inference confidence |
| **Forward projection** | from what you have, **down**: A1 → A2 → A3 → A4 |
| **Reverse projection** | from what you have, **up**: A4 → A3 → A2 → A1 |
| **Gap analysis** | comparing a projected design with the real design, once the real one exists |
| **BIAN reference** | BIAN's catalogue of service domains, operations and business objects — the anchor every projection passes through |

## 3. How it works

```
 architecture datasets you have  ─┐
 BIAN reference (catalogue)      ─┼─► AID ─► projected design ─► view · trace · impact
 the rulebook (metamodel)        ─┘            (separate package)       │
                                                                         ▼
                                       real datasets, when they exist ─► gap analysis
```

### Forward projection — downstream

| Step | From → to | How | Typical confidence |
|---|---|---|---|
| F1 | A1 → A2 | choose the BIAN service domains the business needs: from operations a process names (strong), otherwise by matching activity and capability wording to BIAN's catalogue (weaker) | medium → low |
| F2 | A2 → A3 | BIAN's container pattern: one application component per service domain, one API per service operation (method and path from BIAN's REST mapping) | low (a pattern, not a fact) |
| F3 | A3 → A4 | one deployment per component; **no** platform, environment or network invented | low |

F2 and F3 exist today as the engine's design mode.

### Reverse projection — upstream

| Step | From → to | How | Typical confidence |
|---|---|---|---|
| R1 | A4 → A3 | technology records already name the applications they run (`hosts`, deployments' `component_id`): project those applications | high for existence, nothing else known |
| R2 | A3 → A2 | match APIs to BIAN operations, data entities to BIAN business objects, names to BIAN asset types — the engine's rules, run against the BIAN catalogue | medium → low |
| R3 | A2 → A1 | suggest the business capabilities and processes a service domain usually supports | low — BIAN publishes no capability mapping, so this is the weakest step |

### Middle gap

With A1 and A3 but no A2, AID projects A2 from **both sides** (F1 and R2) and keeps only service domains both sides point to, at higher confidence than either side alone.

### Gap analysis

When the real layers exist (or for testing, when they are known but hidden), AID compares projection with reality:

| Result | Meaning |
|---|---|
| ✅ **matched** | projected and real agree |
| ➕ **projected only** | AID projected it; the real design has no such thing — over-projection, or a gap in the real design |
| ➖ **real only** | the real design has it; AID did not project it — under-projection, or something the business did not require |
| ≠ **differs** | both exist but differ (e.g. a different service domain) |

## 4. Safety rules — a projected design must never be mistaken for a real one

1. **Kept apart.** A projected design lives in its own **projection package**, never in an architecture dataset, the Relationship Registry or the graph store of real data.
2. **Marked everywhere.** Every projected record and link says it is projected, by whom, from what, and when; ids start `PRJ-`; views and traces label it **PROJECTED**.
3. **Never approved.** Projected links cannot be approved into the registry. To become real, a design is built, then exported in a real architecture dataset and linked by the engine in the normal way.
4. **Reasons and confidence on every element**, including what it was inferred from — so an architect can see why each element exists.
5. **BIAN is referenced, not invented.** Service domains, operations and business objects come only from the BIAN reference; AID never makes up a BIAN element.
6. **Nothing beyond the pattern.** AID projects only what a rule or pattern supports. It does not invent platforms, environments, owners or names it has no basis for.

## 5. Illustration (from the payment-initiation example)

**Forward** — the architect has only the A1 business process *Capture and validate payment instruction*, which names two BIAN operations:

| Projected | From | Confidence |
|---|---|---|
| service domain **Payment Initiation** | the operations the process names belong to it (F1) | medium |
| component **PRJ-APP-Payment-Initiation** | one component per domain (F2) | low |
| API **POST /payment-instructions** | BIAN REST mapping of *Initiate Payment Instruction* (F2) | low |
| deployment **PRJ-DEP-Payment-Initiation** | one deployment per component (F3) | low |

**Gap analysis** against the real estate (*checked 2026-10-27 with today's design mode*): the domain ✅ **matched**; the real design has one *Payments Hub* with three sub-components where AID projected one component — ≠ **differs**; APIs by method and path, operation by operation:

| Operation | Projected | Real | Result |
|---|---|---|---|
| Initiate | POST /payment-instructions | same | ✅ matched |
| Update | PATCH /payment-instructions/{id} | same | ✅ matched |
| Evaluate (Validation) | POST /payment-instructions | POST /payment-instructions/{id}/validation | ≠ differs — the pattern ignores the qualifier for create-type operations (improvement for F2) |
| Execute (Execution) | POST …/{id}/execution | PUT …/{id}/execution | ≠ differs — method |
| Retrieve | GET …/{id} | POST …/{id} | ≠ differs — the real API departs from BIAN's REST mapping, which is what gap analysis should surface |
| Notify | none (no REST form) | GET …/{id}/events | ➖ real only |

**2 of 6 matched.** That is the point of gap analysis: it shows where the real design departs from the projected one, and where the projection rules need improving.

**Reverse** — the infrastructure architect has only A4: the production Kubernetes cluster *hosts* `APP-PAY-HUB` → AID projects the application (R1); its APIs are unknown from A4 alone, so R2 can only use the application's name — low confidence, likely **Payment Initiation** or **Payment Execution**.

## 6. What AID depends on

| Dependency | Status |
|---|---|
| The rulebook and the engine's rules | built |
| BIAN reference catalogue | **partial** — public BIAN material is limited; the examples hold small synthetic A2 datasets. A complete catalogue needs licensed BIAN data |
| Graph store and view, to show projections | built; needs a projection mode |
| A projection package format | new (spec) |

## 7. Decisions — approved by the owner 2026-10-27, as recommended

| # | Decision | Recommendation |
|---|---|---|
| AID-D01 | Where projections live | a separate **projection package**, never the registry or the real graph store |
| AID-D02 | Marking | ids `PRJ-…`; every element carries `projection` provenance; views label **PROJECTED** |
| AID-D03 | Approval | projected links can never be approved; the path to real is build → dataset → engine |
| AID-D04 | Confidence | no projected element above **medium**; pattern-derived elements are **low** |
| AID-D05 | BIAN | projections pass through the BIAN reference catalogue; never invent BIAN elements |
| AID-D06 | Today's design mode | becomes AID forward steps F2–F3 |
| AID-D07 | First build order | forward F1–F3 → reverse R1–R2 → gap analysis → middle gap → R3 (weakest, last) |
