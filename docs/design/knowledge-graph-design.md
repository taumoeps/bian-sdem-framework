# How the knowledge graphs work — local and federated

> **Status: current — explains the built knowledge graphs (v0.9.10); the requirements are in the generated spec.**

Read this before [`knowledge-graph-spec.md`](knowledge-graph-spec.md). That spec lists every requirement and component; this page explains how the graphs are built and how you query them. It uses the same terms as [`sdem-overview.md`](../sdem-overview.md).

## The short version

- There are **four local knowledge graphs**, one per architecture: A1 Business, A2 Service Domain, A3 Application, A4 Technology. Each is built from its **architecture dataset** and holds *what exists* in that architecture and the links *inside* it.
- There is **one federated knowledge graph**. It is built from the **relationship registry** and holds the approved links *between* architectures, pointing into the local knowledge graphs.
- The **graph loader** builds all five, every time it runs, from files. Nothing edits a graph directly.
- A **local query** stays inside one local knowledge graph. A **federated query** crosses architectures using the approved links.

**Architecture datasets → local knowledge graphs. Relationship registry → federated knowledge graph. Both joined → questions across architectures.**

> **A common mix-up.** Local knowledge graphs are **not** built from a relationship registry. They are built from architecture datasets. The relationship registry holds only links *between* architectures, so it feeds only the federated knowledge graph.

---

## What each graph is built from

| Graph | Built from | Holds | Owned by |
|---|---|---|---|
| A1 local knowledge graph | the A1 architecture dataset, e.g. `examples/payment-initiation/a1-business.json` | capabilities, value streams, processes, activities, business objects, and the links between them | business architecture |
| A2 local knowledge graph | the A2 architecture dataset, `a2-service-domain.json` | Service Domains, service groups, operations, control records, scenarios, and the links between them | BIAN alignment |
| A3 local knowledge graph | the A3 architecture dataset, `a3-application.json` | applications, interfaces, API operations, data entities, events, and the links between them | application architecture |
| A4 local knowledge graph | the A4 architecture dataset, `a4-technology.json` | platforms, nodes, deployments, environments, and the links between them | infrastructure |
| **Federated knowledge graph** | the **relationship registry**, `mappings.json` — **approved records only** — plus the four local knowledge graphs | the links *between* architectures; each one points to a node in two local knowledge graphs | nobody edits it |

In the payment-initiation example:

| Graph | Nodes | Links |
|---|---|---|
| A1 local | 16 | 14 within A1 |
| A2 local | 24 | 33 within A2 |
| A3 local | 16 | 17 within A3 |
| A4 local | 12 | 5 within A4 |
| Federated | — (it points into the four above) | 18 approved cross-architecture links |

---

## How the graph loader builds them

The graph loader is `sdem/graph.py`, run as `sdem check` and `sdem build`. It does the same steps every run.

```
 1. For each architecture:
      read the architecture dataset  ──▶  check it  ──▶  build the local knowledge graph
                             (types in the catalogue? links allowed by the
                              relationship rows? if not, stop and report)

 2. Read the relationship registry  ──▶  keep approved records only

 3. For each approved record:
      find its source node in one local knowledge graph   (by level, id, version, type)
      find its target node in the next local knowledge graph
      both found?  ──▶  add the link to the federated knowledge graph
      not found?   ──▶  report it as unresolved, leave it out

 4. Answer the query (check · trace · impact · stats)
```

### Step 1 — loading a local knowledge graph

| Check | Rejected example |
|---|---|
| every node's type is a concrete entity in the catalogue | a node typed `A3.Widget`, or the abstract `A4.InfrastructureComponent` |
| every link inside the level matches a relationship row, or is `association` | `A3.ApplicationComponent composition A3.ApplicationFunction` (ArchiMate says *assignment*) |
| both ends of a link are in the same architecture dataset | a link from an A2 node to an A3 node inside the A2 architecture dataset |

### Step 3 — resolving a federated link

Take relationship registry record `PAY-106`: *SD-PI `REALIZED_BY` APP-PAY-HUB*.

1. The source type is `A2.ServiceDomain`, so look in the **A2 local knowledge graph**. `SD-PI` is there, version 1.0. Found.
2. The target type is `A3.ApplicationComponent`, so look in the **A3 local knowledge graph**. `APP-PAY-HUB` is there, version 7.1. Found.
3. Add the link `SD-PI → APP-PAY-HUB` to the federated knowledge graph, labelled `PAY-106`.

If an architecture dataset no longer contains `APP-PAY-HUB`, the link can't be resolved. It is reported and left out, and the architect supersedes the record. The graph never shows a link to something that doesn't exist.

A mapping may name a **parent type**. `DEPLOYED_ON` targets `A4.InfrastructureComponent`, and the loader accepts any node whose type inherits from it: a node, a device or system software.

---

## Query paths inside one architecture (local)

A local query uses one local knowledge graph and follows the links inside it. It never touches the relationship registry.

### Path L1 — what is a node made of, and what does it link to?

*"What does the Payment Initiation Service Domain contain?"* (A2 local knowledge graph)

```
SD-PI 'Payment Initiation'
├─ association → AT-PAY-INSTR   [AssetType]          the asset it manages
├─ association → FP-FULFIL      [FunctionalPattern]  what it does to the asset
├─ aggregation → CR-PI          [ControlRecord]      the record it governs
├─ composition → SG-PI-1        [ServiceGroup]
│                  └─ composition → SO-PI-01, SO-PI-05
├─ composition → SG-PI-2        [ServiceGroup]
│                  └─ composition → SO-PI-02, SO-PI-03, SO-PI-04, SO-PI-06
└─ flow        → SD-PE          [ServiceDomain]      the domain it hands over to
```

*"What is the Payments Hub made of?"* (A3 local knowledge graph)

```
APP-PAY-HUB 'Payments Hub'
├─ composition → CMP-PAY-CAPTURE, CMP-PAY-VALIDATE, CMP-PAY-EXEC   [components]
├─ composition → IFC-PAY-API     [ApplicationInterface]  → composes API-PI-01 … API-PI-06
├─ realization → SVC-PAY-INIT    [ApplicationService]
└─ triggering  → EVT-PAY-STATUS  [Event]
```

### Path L2 — part to whole, and whole to parts

Following only **composition** and **aggregation**:

| Direction | Example in A3 |
|---|---|
| up, part → whole | `API-PI-01` → `IFC-PAY-API` → `APP-PAY-HUB` |
| down, whole → parts | `APP-PAY-HUB` → its three components, its interface, its six API operations |

Assignment, realization, serving, flow and triggering are **not** part–whole, so this path doesn't follow them.

### Path L3 — everything of one kind

*"List every deployment in production"* (A4 local knowledge graph): the nodes of type `A4.Deployment` aggregated by `ENV-PAY-PROD`.

### Status

There is **no command for local queries yet** (requirement KG-L-04, partly built). The local knowledge graphs exist and are validated; the examples above were produced by reading one architecture dataset directly. Part–whole paths are available today inside a federated trace with `--follow-composition`.

---

## Query paths across architectures (federated)

A federated query starts in one local knowledge graph, crosses to the next by an **approved** link, and continues. Every crossing shows the relationship registry record that justifies it.

### Path F1 — downstream trace: what does this depend on?

*"What does the Initiate Payment capability run on?"*

```
sdem trace CAP-PAY-010 --direction down <architecture datasets> mappings.json
```

```
CAP-PAY-010 'Initiate Payment'                [A1]
└─ SUPPORTED_BY → SD-PI 'Payment Initiation'  [A2]   (PAY-001)
   └─ REALIZED_BY → APP-PAY-HUB 'Payments Hub' [A3]  (PAY-106)
      ├─ DEPLOYED_ON → INF-K8S-PAY-PROD         [A4]  (PAY-108)
      ├─ DEPLOYED_AS → DEP-PAYHUB-PROD          [A4]  (PAY-109)
      ├─ DEPLOYED_AS → DEP-PAYHUB-UAT           [A4]  (PAY-110)
      └─ DEPLOYED_ON → INF-K8S-PAY-UAT          [A4]  (PAY-113)
```

Path: **A1 local → (PAY-001) → A2 local → (PAY-106) → A3 local → (PAY-108 …) → A4 local.**

### Path F2 — upstream trace: what depends on this?

*"What depends on the production Kubernetes cluster?"*

```
sdem trace INF-K8S-PAY-PROD --direction up <architecture datasets> mappings.json
```

```
INF-K8S-PAY-PROD  [A4]
├─ ← DEPLOYED_ON  APP-PAY-HUB 'Payments Hub'     [A3]  (PAY-108)
│  └─ ← REALIZED_BY  SD-PI 'Payment Initiation'  [A2]  (PAY-106)
│     ├─ ← SUPPORTED_BY  CAP-PAY-010 'Initiate Payment'           [A1]  (PAY-001)
│     ├─ ← USES_DOMAIN   PRC-PAY-01 'Capture and validate payment' [A1]  (PAY-003)
│     └─ ← USES_DOMAIN   PRC-PAY-02 'Execute and confirm payment'  [A1]  (PAY-004)
└─ ← DEPLOYED_ON  CMP-PAY-EXEC 'Execution Gateway' [A3]  (PAY-111)
```

### Path F3 — trace through local structure as well

A federated trace can also walk part–whole links *inside* each architecture, so a chain doesn't stop at a part.

*"Where does the Create Payment Instruction API run?"*

```
sdem trace API-PI-01 --direction down --follow-composition <architecture datasets> mappings.json
```

```
API-PI-01 'Create payment instruction'      [A3]
└─ PART_OF → IFC-PAY-API 'Payments API v2'  [A3]   (local: composition)
   └─ PART_OF → APP-PAY-HUB 'Payments Hub'  [A3]   (local: composition)
      ├─ DEPLOYED_ON → INF-K8S-PAY-PROD      [A4]   (PAY-108)
      ├─ DEPLOYED_AS → DEP-PAYHUB-PROD       [A4]   (PAY-109)
      │  └─ PART_OF → ENV-PAY-PROD 'Production' [A4] (local: aggregation)
      └─ …
```

Path: **A3 local (part → whole) → (PAY-108, PAY-109) → A4 local (part → whole).** Local steps are labelled `PART_OF`; federated steps carry their record ID.

### Path F4 — impact: what is affected by a change?

*"What is affected if we replace the Payments Hub?"*

```
sdem impact APP-PAY-HUB --change replace <architecture datasets> mappings.json
```

| Classification | Nodes | Reached by |
|---|---|---|
| design change required | APP-PAY-HUB; SD-PI (A2) | PAY-106 |
| review required | CAP-PAY-010, PRC-PAY-01, PRC-PAY-02 (A1) | PAY-106 then PAY-001 / PAY-003 / PAY-004 |
| review required | both clusters and both deployments (A4) | PAY-108, PAY-109, PAY-110, PAY-113 |
| records to supersede | PAY-106, PAY-108, PAY-109, PAY-110, PAY-113 | |

The classification follows `schema/impact-rules.json`: the change kinds are modify, replace, retire and rehost.

### Known limit of path F2

An upstream trace from an **API** stops at its operation:

```
API-PI-01  ← IMPLEMENTED_BY  SO-PI-01 'Initiate Payment Instruction'   (PAY-101)
```

The next step, from an operation up to its Service Domain, is a *local* A2 link (domain ⊃ group ⊃ operation). An upward trace with `--follow-composition` walks *down* into parts, not up into wholes, so it doesn't climb from the operation to the domain. To reach the capability from an API today, trace up from the application (`APP-PAY-HUB`) instead. Climbing to the whole on upward traces is a gap to close in the query tools.

---

## Local query vs federated query

| | Local query | Federated query |
|---|---|---|
| Uses | one local knowledge graph | the four local knowledge graphs + the approved relationship registry |
| Follows | links inside one architecture | approved links between architectures, plus local part–whole links if asked |
| Each step shows | the link kind (composition, assignment …) | the relationship registry record ID (PAY-106 …) for every crossing |
| Paths | L1 contents · L2 part–whole · L3 all of a kind | F1 downstream · F2 upstream · F3 with local structure · F4 impact |
| Typical asker | the team that owns that architecture | enterprise architects; impact analysis |
| Command | not built yet (KG-L-04) | `sdem trace`, `sdem impact` |

---

## When something changes

The graphs are always rebuilt from files, so a change reaches them by changing a file.

| Change | File that changes | Graph that changes on the next load |
|---|---|---|
| A team adds, removes or edits something in its architecture | that architecture's architecture dataset | its local knowledge graph; the federated knowledge graph if a link pointed at it |
| An architect approves, rejects or supersedes a link | the relationship registry | the federated knowledge graph |
| The rules change | the relationship rules model; the engine rebuilds affected links | the federated knowledge graph, after review |

Which components run for each kind of change, in order, is in [`knowledge-graph-spec.md`](knowledge-graph-spec.md) §9.

## What is built

| Part | Status |
|---|---|
| Graph loader, all five graphs (in memory), check, federated trace and impact, `--follow-composition` | built |
| Local query command | not built (KG-L-04) |
| Upward trace climbing to the whole | not built (the F2 limit above) |
| Keeping the last good graph when an architecture dataset fails; recording which file versions each load used; a persistent graph store | not built (knowledge-graph-spec §5, §7, DEC-01) |

## Read more

- [`knowledge-graph-spec.md`](knowledge-graph-spec.md) — every requirement, component and change workflow for the graphs; §11 specifies each service: graph loader, adapter contract, architecture dataset diff, refresh trigger, query service, review queue, assistant access.
- [`sdem-overview.md`](../sdem-overview.md) — the relationship rules model, the engine and the relationship registry.
- [`relationships-planning.md`](../reference/relationships-planning.md) — every link allowed *inside* each architecture.
