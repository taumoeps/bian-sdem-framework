# Glossary

Plain-language meanings of the terms used across the SDEM documents. Grouped by topic; alphabetical within each group.

## The model

| Term | Means |
|---|---|
| **A1 … A4** | the four architectures: A1 Business, A2 Service Domain (BIAN), A3 Application, A4 Technology |
| **Abstract entity type** | a type that groups others and never has instances of its own, e.g. `A4.InfrastructureComponent` (a node, device or system software is one) |
| **Architecture Metamodel** | the definition of what can exist: entity types, the links allowed inside each architecture, and the nine link types allowed between them |
| **Artefact** | a published document or model file (e.g. BIAN's Business Object Model, a Semantic API definition), recorded for reference but never an instance in an architecture dataset |
| **Attribute** | one piece of information recorded about an entity, e.g. a process's `owner` or `criticality`. *Field* means the same |
| **Common attribute** | an attribute every entity type has, in all four architectures (11: owner, created, modified, valid from/to, replaces, replaced by, conforms to, subject, source id, access classification) |
| **Core field** | the identity fields every record has: `id`, `type`, `version`, `name`, `lifecycle_status`, `canonical_id`, `description`, `definition_uri`, plus the `attributes` container |
| **Derived attribute** | a value computed from approved data and never stored, so it cannot drift, e.g. a Service Domain's criticality from the processes that use it |
| **Entity type** | a *kind* of thing, e.g. `A1.BusinessProcess` |
| **Entity / instance / record** | one *real* thing of a type, e.g. the process `PRC-PAY-01` |
| **Natural key** | the attributes that identify a record in business terms (besides its `id`); two records of a type may not share it |
| **SDEM extension** | an entity type SDEM defines itself because no standard has it, e.g. `A1.ValueStreamStage` |

## Links

| Term | Means |
|---|---|
| **Within-level row** | a link allowed inside one architecture, e.g. `RA3-27`; taken from that architecture's reference (BIAN, ArchiMate, TOGAF) |
| **Cardinality** | how many links of a kind a record may or must have, e.g. a service group belongs to exactly one Service Domain |
| **Relationship type catalogue** | the nine link types allowed between architectures, e.g. `USES_DOMAIN`, `IMPLEMENTED_BY` |
| **Relationship Rules Model** | how each cross-level link is found: 69 plan rows (S01…S54, B01…B15) and the join keys |
| **Plan row / rule / S-rule** | one way of establishing a cross-level link, e.g. `S24` (a BIAN operation is implemented by an API operation) |
| **Join key** | an attribute in an architecture dataset that names a record in another architecture, e.g. an application's `deployed_on`; the engine uses it to propose a link exactly |
| **Relationship Registry** | the store of actual cross-level links, each with a status (proposed, approved, rejected, superseded) and evidence. Older files call these *mappings* |
| **Mapping** | the old name for a cross-level link record; kept in file and field names (`mappings.json`, `mapping_id`) so approved records never change |

## Data model layers

| Term | Means |
|---|---|
| **Conceptual model** | what kinds of thing exist and how they relate (`architecture-entity-design.md`) |
| **Logical model** | identifiers, attributes, types, allowed values, references, link counts and the 14 rules LC-01…LC-13 (`logical-data-model.md`) |
| **Physical model** | the files a tool uses: one JSON Schema per entity type (`schema/entities/`, `physical-data-model.md`) |
| **Conformance** | whether an architecture dataset obeys the logical rules; checked by `sdem-graph check` — errors fail the architecture dataset, warnings do not |
| **Architecture dataset** | one architecture's records and the links between them, in SDEM's format — e.g. the A1 architecture dataset `a1-business.json`. A *dataset* in the W3C DCAT sense (a collection of data from one source); its format is the architecture dataset schema `schema/level-model.schema.json`. Earlier documents call it an *export*, *level export* or *level model* |
| **Adapter** | the program that converts a tool's own data into an architecture dataset; not built yet |
| **Ingestion** | getting data in: source → adapter → architecture dataset → check → load (planned v0.11) |

## Graphs and engine

| Term | Means |
|---|---|
| **Local knowledge graph** | one architecture's records and within-level links, built from its architecture dataset |
| **Federated knowledge graph** | the four local graphs joined by approved registry links |
| **Graph loader** | the program that builds the graphs from architecture datasets and the registry (`sdem/graph.py`) |
| **Inference engine** (formerly *mapping engine*) | the program that reads the graphs, applies the rules and *proposes* cross-level links for an architect to approve. Built (v0.10): `sdem-infer rules` |
| **Fill steps 0–5** | the engine's order of work: load BIAN, exact joins, REST matching, closure, structural matching, bounded text matching |
| **Architecture Inference Design (AID)** | the planning function that projects missing architecture layers from the ones an architect has — forward (down) or reverse (up) — as a **projected design** with inference confidence, not a validated design ([`aid-design.md`](aid-design.md)) |
| **Projected design** | records and links inferred, not observed; kept apart from real data, marked `PRJ-`, never approved |
| **Gap analysis** | comparing a projected design with the real one: matched, projected only, real only, differs |
| **Proposal** | a link the engine suggests, status `proposed`, with evidence and a confidence |
| **Trace / impact** | follow links across architectures / find what a change affects |
| **Graph store** | the local knowledge graphs and the federated graph saved as JSON files on the device (`sdem-graph build`); no server ([`graph-store-design.md`](graph-store-design.md)) |
| **JSON Graph Format (JGF)** | the published file format the graph store uses: `nodes` and `edges`, each with its own data |
| **Load record** | the store's log of every build: inputs, checks, accepted or rejected, outputs |
| **Graph access layer** | the one read interface every query, the view and the engine use, whether the graph comes from the store or from architecture datasets |
| **Baseline (engine)** | the naive name-matching engine any real engine must beat (F1 0.62) |

## The workbench

| Term | Means |
|---|---|
| **CLI** | the command line in VS Code's terminal pane — SDEM's only interface: every engine and function is a `sdem` command (today `sdem-*`) |
| **Copilot instructions** | `.github/copilot-instructions.md` — standing rules GitHub Copilot reads in this repository: use SDEM's commands for facts, never approve, never put projected content into real data, always give source, reasoning and confidence |
| **Prompt file** | a `.github/prompts/*.prompt.md` file that gives Copilot Chat one `/` command for a journey, e.g. `/sdem-trace` — which SDEM command to run and what to report |
| **SDEM workbench** | how architects use SDEM: the SDEM project open in VS Code, SDEM run from the terminal pane (the CLI), the Copilot Chat window for AI support, Git as history and approval trail ([`sdem-workbench-design.md`](sdem-workbench-design.md)) |

## Evidence and confidence

| Term | Means |
|---|---|
| **Source reference** | where an item comes from: the standard, section or page, and a link |
| **Confidence** | **high** — a public standard defines it and it was checked; **medium** — built on a standard concept, or the standard could not be checked; **low** — SDEM-defined with no standard basis |
| **Archi oracle** | the open-source Archi tool's table of allowed ArchiMate relationships, used to check rows because the ArchiMate specification text needs a login |
| **Login-gated** | readable only with an Open Group account (TOGAF, ArchiMate text) — not checked |
| **Use case / run** | a test estate with a sealed answer key, e.g. M1, H2, C3; the rules were executed by hand on each and scored |
| **Sealed answers / gold** | the expected links for a run, written before the run and not shown to the executor |
| **Validated against sealed answers** | a rule's output matched the answer key in at least one run |
| **Precision / recall / F1** | of the links proposed, how many were right / of the right links, how many were found / the balance of both |
| **Baseline (model)** | a frozen, reviewed version of the model, e.g. `SDEM-METAMODEL-0.8` |
