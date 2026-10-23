# How SDMM works — the five parts in one page

Read this first. The specifications go into detail; this page says what each part is, who owns it, and how they connect.

## The five parts

| Part | What it is | Who owns it | Where it lives |
|---|---|---|---|
| **Local graphs** | one per architecture (A1 Business, A2 Service Domain, A3 Application, A4 Technology). Each holds *what exists* at that level and the links inside it, e.g. an application and its interfaces | the team that runs that architecture, through its own tool | built from an export file per level, e.g. `examples/payment-initiation/a3-application.json` |
| **Mapping model** | the **rules** for linking across architectures: which kinds of link are allowed, how each one is found, with what confidence, from which data | **architects** design and manage it | the records `schema/relationship-types.json`, `metamodel/new-mappings.json`, `metamodel/export-conventions.json`; readable version: [`mapping-model-design-spec.md`](mapping-model-design-spec.md) |
| **Mapping engine** | a program that **applies the mapping model** to the local graphs and **builds the mapping set** | runs on request | `sdmm/engine.py` (interface built; step logic not yet built) |
| **Mapping set** | the **links** the engine built for one estate, each with evidence, confidence and a status (proposed, approved, rejected, superseded) | built by the engine; **reviewed** by architects | `examples/<estate>/mappings.json` |
| **Federated graph** | the four local graphs **joined** by the approved links, so you can ask questions across architectures | nobody edits it; the graph loader rebuilds it | in memory, built by `sdmm-graph` each run; spec: [`knowledge-graph-spec.md`](knowledge-graph-spec.md) |

## How they connect

```
 Source tools (EA tool, BIAN workbench, app portfolio, CMDB)
        │  adapter → export file
        ▼
 ┌────────────────── Local graphs (A1 · A2 · A3 · A4) ──────────────────┐
 │                       what exists, per level                          │
 └───────────────┬───────────────────────────────────────┬───────────────┘
                 │ read                                  │ joined by
                 ▼                                       │
 Architects ──design──▶ Mapping model ──▶ Mapping engine │
                         (the rules)       applies rules │
                                                │        │
                                                ▼        │
                                          Mapping set ◀──┼── Architects review
                                          (the links)    │   (approve / reject;
                                                │        │    fix a wrong link by
                                  approved only │        │    fixing the rule)
                                                ▼        ▼
                                         Graph loader ──▶ Federated graph ──▶ trace · impact
```

**In one sentence:** architects write the rules (mapping model), the engine applies them to the data (local graphs) to produce the links (mapping set), architects review the links, and the graph loader joins the data with the approved links (federated graph) so questions can be answered across architectures.

## A worked example

From `examples/payment-initiation/`:

1. **Local graphs.** The A2 export lists the operation `SO-PI-01 Initiate Payment Instruction` (action term *Initiate*). The A3 export lists the API `API-PI-01 POST /payment-instructions` with its payload fields.
2. **Mapping model.** Rule S24 says: an operation is `IMPLEMENTED_BY` an API when the API belongs to the domain's application, the HTTP method fits the action term (*Initiate* ⇔ POST), and the payload carries the operation's attributes. Confidence: high.
3. **Mapping engine.** Applies S24 to the two exports: POST fits *Initiate*, 8 of 8 attributes match. It writes record `PAY-101: SO-PI-01 IMPLEMENTED_BY API-PI-01`, status `proposed`, confidence 0.8, with that working as evidence.
4. **Mapping set.** `PAY-101` is now in `mappings.json`. An architect reviews it and sets it to `approved`.
5. **Federated graph.** The graph loader reads the four exports and the approved records. Now `sdmm-graph trace CAP-PAY-010 --direction down` walks from the *Initiate Payment* capability to the domain, the application, and the Kubernetes cluster it runs on — each step citing its mapping ID.

## What each part never does

| Part | Never |
|---|---|
| Local graphs | hold links between architectures |
| Mapping model | name a real entity — it speaks only of entity *types* |
| Mapping engine | change the rules, approve its own output (except rules an architect has declared auto-approved), or write to a graph |
| Mapping set | contain an approved record that was later edited — changes are superseded, never overwritten |
| Federated graph | hold a proposal, or be edited directly |

## Two kinds of query

| | Local query | Federated query |
|---|---|---|
| Question | "What is the Payments Hub made of?" | "What does the Initiate Payment capability run on?" |
| Uses | one local graph | all four local graphs + the approved mapping set |
| Asked by | the team that owns that architecture | enterprise architects; impact analysis |

## What is built

| Part | Status |
|---|---|
| Local graphs, federated graph, graph loader, trace, impact | built (in memory) |
| Mapping model | built as records; tested across ten use cases |
| Mapping set format, validator, history guard | built |
| Mapping engine | interface built; the rule logic was run by an AI executor in testing and is the next build |
| Adapters from real tools | not built — they belong in the institution's private repository |

## Where to read more

- [`mapping-model-design-spec.md`](mapping-model-design-spec.md) — the mapping model and the engine's requirements.
- [`knowledge-graph-spec.md`](knowledge-graph-spec.md) — the local and federated graphs, every component, and which components run for each kind of change.
- [`relationships-planning.md`](relationships-planning.md) — every allowed link inside each architecture.
- [`use-case-testing.md`](use-case-testing.md) — how the mapping model was tested.
