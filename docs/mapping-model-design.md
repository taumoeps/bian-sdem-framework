# How SDMM works — read this first

## The short version

SDMM connects four architectures: **A1 Business, A2 Service Domain (BIAN), A3 Application, A4 Technology**.

- Each architecture's **data** sits in its own **local graph**: *what exists*.
- Architects write the **mapping model**: the **rules** for how things in one architecture connect to things in the next.
- The **mapping engine** applies those rules to the data and produces the **mapping set**: the **actual links**.
- Architects **review** the links. The **graph loader** joins the data with the approved links into the **federated graph**, which answers questions across architectures.

**Rules → engine → links → review → graph.**

---

## The three things that look alike

The **mapping model**, the **mapping set** and the **schema** all mention a source, a relationship and a target, so they are easy to mix up. They are different things.

| | **Mapping model** | **Mapping set** | **Schema** |
|---|---|---|---|
| In one word | **rules** | **links** | **form** |
| Says | which *kinds* of link may exist, and how the engine finds each one | that *these specific* things are linked | which fields a file must have |
| Talks about | entity **types**, e.g. `A2.ServiceOperation` | real **entities**, e.g. `SO-PI-01` | **fields**, e.g. `status` must be one of six values |
| Example ID | `S24` | `PAY-101` | — |
| Has a status, reviewer, date | no | **yes** | no |
| How many | one, for every bank | one per estate | one per file type |
| Written by | **architects** | the **engine** (architects review) | the SDMM model owner, rarely changed |
| Used by | the engine | the graph loader | the validators |
| Files | `schema/relationship-types.json`, `metamodel/new-mappings.json`, `metamodel/export-conventions.json` | `examples/<estate>/mappings.json` | `schema/mapping.schema.json`, `schema/level-model.schema.json` |

**Quick test:** if it names a real thing like `SO-PI-01`, it's the **mapping set**. If it names only types like `A2.ServiceOperation`, it's the **mapping model**. If it lists fields and allowed values, it's a **schema**.

> `schema/relationship-types.json` sits in the `schema/` folder but is **not** a schema. It is the list of nine allowed links: part of the mapping model.

### The same link at all three levels

**Mapping model: the rule.** *Any* Service Operation may be implemented by *any* API Operation. Find it by matching the HTTP method and the payload; rate it high; require an API contract as evidence.

```json
{ "id": "S24", "source": "A2.ServiceOperation", "relationship": "IMPLEMENTED_BY",
  "target": "A3.APIOperation", "fill_step": 2, "confidence": "high",
  "required_evidence": ["api_contract"] }
```

**Mapping set: one link, built by applying S24.** *This* operation is implemented by *this* API, here's the evidence, and Jane approved it.

```json
{ "mapping_id": "PAY-101",
  "source": { "id": "SO-PI-01", "type": "A2.ServiceOperation" },
  "relationship": "IMPLEMENTED_BY",
  "target": { "id": "API-PI-01", "type": "A3.APIOperation" },
  "status": "approved",
  "evidence": ["api_contract:payments-api-v2.yaml#/paths/~1payment-instructions/post"],
  "rationale": "Initiate ↔ POST; 8/8 attributes in payload",
  "reviewer_id": "jane.architect", "approved_at": "2026-10-22" }
```

**Schema: the form `PAY-101` must fit.** Every record needs `mapping_id`, `source`, `relationship`, `target`, `status`, `evidence`, `rationale` and `baseline_id`; `status` must be proposed, validated, needs_review, approved, rejected or superseded. The validator rejects a record that doesn't fit.

One rule, S24, produced five links in this estate (`PAY-101` … `PAY-105`), one per operation that matched an API.

---

## The mapping model in numbers

The same numbers appear in [`mapping-model-spec.md`](mapping-model-spec.md) and [`mapping-model-diagram.puml`](mapping-model-diagram.puml); a test keeps all three in step with the records.

| What | Count | Where in the spec | In the diagram |
|---|---|---|---|
| Entity types (boxes) | 44 | §2 | every box |
| Within-level rows: links allowed *inside* one architecture | 132 | §3.1 (`RA…`) | thin grey arrows |
| Registry: kinds of link allowed *between* architectures | 9 | §4.1 | named on the blue arrows |
| Plan rows: rules for finding cross-level links | 69 | §4.2 (`S…`, `B…`) | — |
| …of which drawn as cross-level rules | 50 | §4.3 | coloured arrows |
| …of which registry rules, the only ones that produce mapping-set links | 9 | §4.3 | blue arrows |
| Join keys the rules read from the exports | 52 | §5 (`K…`) | — |
| Engine requirements | 33 | §10 (`REQ-…`) | — |

## Reading the mapping-model diagram

[`mapping-model-diagram.puml`](mapping-model-diagram.puml) draws the **mapping model**, not the mapping set.

| On the diagram | Means |
|---|---|
| A box, e.g. `A3.APIOperation` | an entity **type**, not a real thing. No real instance like `API-PI-01` appears |
| Four columns | the four architectures, A1 to A4 |
| Thin grey arrow labelled `RA3-27 composition` | a **within-level row**: this link is allowed inside one architecture |
| Blue arrow labelled `S24 IMPLEMENTED_BY` | a **registry rule**: the engine uses it to build links in the mapping set |
| Green, orange, dashed or dotted arrow, e.g. `S20` | another **plan row**: the engine reports it as a candidate; it never becomes a mapping-set link |
| Grey box | an entity type with no cross-level rule, by decision (artefacts; actor and role) |

So the diagram shows *which links may exist and how they are found*. To see *which links do exist*, open a mapping set, e.g. `examples/payment-initiation/mappings.json`, or run `sdmm-graph trace`.

## All the parts

| Part | What it is | Owned by | Where |
|---|---|---|---|
| **Source tools** | the systems each team already uses: EA tool, BIAN workbench, application portfolio, CMDB | each architecture team | the institution |
| **Adapter** | a script that turns one tool's data into an export file | the institution | the institution's private repository (not built here) |
| **Export** | one file per architecture listing *what exists* and the links *inside* it | written by the adapter | `examples/<estate>/a1…a4-*.json` |
| **Local graph** | one export, loaded and checked | built by the graph loader | in memory |
| **Mapping model** | the **rules** for links *between* architectures | **architects** | the three records above; readable version: [`mapping-model-spec.md`](mapping-model-spec.md); picture: [`mapping-model-diagram.puml`](mapping-model-diagram.puml) |
| **Mapping engine** | applies the mapping model to the local graphs and builds the mapping set | runs on request | `sdmm/engine.py` (interface built; rule logic is the next build) |
| **Mapping set** | the **links** between architectures, each with evidence and a status | built by the engine; **reviewed** by architects | `examples/<estate>/mappings.json` |
| **Validators** | check that exports and the mapping set fit their schemas and rules, and that approved links are never edited | automatic | `sdmm-graph check`, `sdmm-validate`, `sdmm-diff` |
| **Graph loader** | loads the exports and the **approved** links; joins them | automatic, every run | `sdmm/graph.py` |
| **Federated graph** | the four local graphs joined by the approved links | nobody edits it | in memory; spec: [`knowledge-graph-spec.md`](knowledge-graph-spec.md) |
| **Query tools** | trace and impact across architectures | anyone | `sdmm-graph trace`, `sdmm-graph impact` |

## How they connect

```
 Source tools ──adapter──▶ Exports ──graph loader──▶ Local graphs (A1 · A2 · A3 · A4)
                                                          │                  │
                                                          │ read             │ joined by
                                                          ▼                  │
 Architects ──write──▶ Mapping model ──▶ Mapping engine                     │
                        (the rules)          │                               │
                                             ▼                               │
                                       Mapping set ◀── Architects review     │
                                        (the links)    (approve / reject;    │
                                             │          fix a wrong link     │
                                             │          by fixing the rule)  │
                               approved only │                               │
                                             ▼                               ▼
                                       Graph loader ───────────────▶ Federated graph ──▶ trace · impact
```

## Who does what

| Role | Does | Never |
|---|---|---|
| Architecture team (A1, A2, A3 or A4) | keeps its own tool up to date | writes links between architectures |
| Architect | writes the mapping model; reviews the mapping set; decides which rules may auto-approve | edits an approved link (it is superseded instead) |
| Mapping engine | applies the rules; writes links as `proposed` | changes the rules; approves its own links (except rules an architect declared auto-approved) |
| Graph loader | loads exports and approved links | changes any input |

## A worked example, start to finish

From `examples/payment-initiation/`:

1. **Export → local graph.** The A2 export lists the operation `SO-PI-01 Initiate Payment Instruction` (action *Initiate*). The A3 export lists `API-PI-01 POST /payment-instructions` with its payload fields.
2. **Mapping model.** Rule S24: an operation is implemented by an API when the API belongs to the domain's application, the HTTP method fits the action (*Initiate* ⇔ POST), and the payload carries the operation's attributes.
3. **Engine.** Applies S24: POST fits *Initiate*, 8 of 8 attributes match. Writes `PAY-101`, status `proposed`, confidence 0.8, with that working as evidence.
4. **Mapping set → review.** `PAY-101` is in `mappings.json`. Jane checks it and sets it to `approved`.
5. **Graph loader → federated graph.** Loads the four exports and the approved links.
6. **Query.** `sdmm-graph trace CAP-PAY-010 --direction down` walks from the *Initiate Payment* capability to the Service Domain, to the Payments Hub application, to the Kubernetes cluster it runs on — each step citing its link ID.

## Two kinds of question

| | Local query | Federated query |
|---|---|---|
| Example | "What is the Payments Hub made of?" | "What does the Initiate Payment capability run on?" |
| Uses | one local graph | all four local graphs + the approved mapping set |
| Asked by | the team that owns that architecture | enterprise architects; impact analysis |

## What is built

| Part | Status |
|---|---|
| Exports, local graphs, graph loader, federated graph, trace, impact | built (in memory) |
| Mapping model | built as records; tested across ten use cases |
| Mapping set format, schemas, validators | built |
| Mapping engine | interface built; the rules were applied by an AI executor in testing; the code is the next build |
| Adapters from real tools | not built — they belong in the institution's private repository |

## Glossary

| Term | Means |
|---|---|
| **A1 … A4** | the four architectures: Business, Service Domain (BIAN), Application, Technology |
| **Entity** | a *kind* of thing, e.g. `A3.APIOperation`. The full list is the entity catalogue |
| **Instance** | a *real* thing of that kind, e.g. `API-PI-01` |
| **Export** | the file an adapter writes for one architecture |
| **Local graph** | one architecture's instances and the links inside it |
| **Mapping model** | the rules for links between architectures (registry + plan + conventions) |
| **Registry** | the nine allowed kinds of cross-architecture link, e.g. `IMPLEMENTED_BY` |
| **Plan row** | one rule in the mapping model, e.g. `S24`, saying how a link is found and how confident it is |
| **Mapping set** | the links between real instances, e.g. `PAY-101` |
| **Schema** | the required form of a file — fields and allowed values |
| **Engine** | the program that applies the mapping model to produce the mapping set |
| **Graph loader** | the program that builds the local and federated graphs |
| **Federated graph** | the four local graphs joined by approved links |
| **Trace / impact** | follow links across architectures / find what a change affects |

## Read more

- [`mapping-model-spec.md`](mapping-model-spec.md) — the mapping model in full and the engine's requirements.
- [`mapping-model-diagram.puml`](mapping-model-diagram.puml) — the mapping model in one picture: every within-level row and cross-level rule by ID, between entity types (see *Reading the mapping-model diagram*).
- [`knowledge-graph-spec.md`](knowledge-graph-spec.md) — the local and federated graphs, every component, and what runs for each kind of change.
- [`relationships-planning.md`](relationships-planning.md) — every allowed link *inside* each architecture.
- [`use-case-testing.md`](use-case-testing.md) — how the mapping model was tested.
