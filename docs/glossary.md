# Glossary

> **Status: current — kept up to date with every release; a term used in a current document belongs here.**

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
| **`mappings.json`** | the file that holds a workspace's Relationship Registry — the approved (and superseded) links between architectures |
| **Mapping** | the old name for a cross-level link record; kept in file and field names (`mappings.json`, `mapping_id`) so approved records never change |

## Data model layers

| Term | Means |
|---|---|
| **Conceptual model** | what kinds of thing exist and how they relate (`architecture-entity-design.md`) |
| **Logical model** | identifiers, attributes, types, allowed values, references, link counts and the 14 rules LC-01…LC-13 (`logical-data-model.md`) |
| **Physical model** | the files a tool uses: one JSON Schema per entity type (`schema/entities/`, `physical-data-model.md`) |
| **Conformance** | whether an architecture dataset obeys the logical rules; checked by `sdem check` — errors fail the architecture dataset, warnings do not |
| **Architecture dataset** | one architecture's records and the links between them, in SDEM's format — e.g. the A1 architecture dataset `a1-business.json`. A *dataset* in the W3C DCAT sense (a collection of data from one source); its format is the architecture dataset schema `schema/level-model.schema.json`. Earlier documents call it an *export*, *level export* or *level model* |
| **Workspace** | the architecture of one area of your organisation (e.g. Payments) in one folder — kept permanently and shared by that area's architects: the four layer datasets, the approved connections (`mappings.json`) and the records SDEM keeps beside them ([the full list](sdem-architecture.md#inside-a-workspace)). Started once with `sdem new`; every design of the area is loaded into it. Example: `examples/payment-initiation/` |
| **Adapter** | the program that converts a tool's own data into an architecture dataset; not built yet |
| **Onboarding** | bringing data from a new source into SDEM until it is governed and ready for use: **ingestion**, then **normal processing**. Two routes: **design onboarding** and **tool onboarding** ([`sdem-onboarding-workflow.md`](sdem-onboarding-workflow.md)) |
| **Design onboarding** | existing designs (documents exported from Confluence): `sdem transform` → a person reviews → `sdem load`, then normal processing; what does not fit an entity is kept as gap records — **built** |
| **Tool onboarding** | data from tools (spreadsheets, CMDB, application portfolio): source → adapter → architecture dataset → check → load, then normal processing — **planned (v0.11)** |
| **Ingestion** | the first part of onboarding: getting the data into a workspace (for designs: transform → review → load) |
| **Normal processing** | the second part of onboarding, the same for every workspace however its data arrived: `sdem check` → `sdem link` → `sdem approve` → `sdem build` |
| **Base BIAN** | the BIAN that ships with SDEM — BIAN's public Semantic APIs 14.0.0, packed into `bian/base-14.0.0.json` (Apache-2.0); `sdem bian import --base` builds your BIAN layer from it; your organisation's own BIAN can replace it (`sdem bian pack`, `--base <file>`) |
| **Inference record** | SDEM's tracked record of the asset types and functional patterns it infers for BIAN service domains BIAN does not publish them for (`bian/inferences-14.0.0.json`): each value with source, reasoning and confidence; a status (proposed, accepted, challenged, rejected, open) and a history of who changed what and why. Applied only when accepted ([BIAN inferences](reference/bian-inferences.md)) |
| **Inferred record** | a record `sdem aid` added to a workspace's layer file (id `AID-…`), marked `inferred` with its source, reasoning and confidence; a person confirms it (the mark stays, with their name) or rejects it (`sdem aid confirm|reject`). Its connections are only proposals until approved |
| **BIAN Semantic APIs** | BIAN's published API definitions, one file per service domain, free under Apache-2.0 (github.com/bian-official/public); `sdem bian import` turns the ones you choose into your BIAN (A2) layer |
| **Candidate** | a record the transform suggests from a design; not real data until a person loads it (`sdem load`). Ids `HIS-…`; never above medium confidence |
| **Transform** | `sdem transform run`: reads an export of designs and writes candidates with their evidence (page, place, rule, confidence, reasoning) |
| **Load** | `sdem load`: copies the candidates a person keeps, unchanged, into a workspace — checked first, recorded in `loads/` |
| **Design record** | one per source page or file of an onboarded design (`DOC-…`): title, link, date, the page's facts, coverage, the entities loaded from it |
| **Gap record** | one per item that did not fit an architecture entity (`GAP-…`): category, place, original text, the entities it is about, status (open, resolved, accepted) — kept beside the workspace, never in the knowledge graph |
| **Coverage** | the share of an export's items the transform captured: captured ÷ (captured + not captured) |

## Graphs and engine

| Term | Means |
|---|---|
| **Local knowledge graph** | one architecture's records and within-level links, built from its architecture dataset |
| **Federated knowledge graph** | the four local graphs joined by approved registry links |
| **Graph loader** | the program that builds the graphs from architecture datasets and the registry (`sdem/graph.py`) |
| **Inference engine** (formerly *mapping engine*) | the program that reads the graphs, applies the rules and *proposes* cross-level links for an architect to approve. Built (v0.10): `sdem link` |
| **Fill steps 0–5** | the engine's order of work: load BIAN, exact joins, REST matching, closure, structural matching, bounded text matching |
| **Architecture Inference Design (AID)** | the planning function that projects missing architecture layers from the ones an architect has — forward (down) or reverse (up) — as a **projected design** with inference confidence, not a validated design ([`aid-design.md`](design/aid-design.md)) |
| **Projected design** | records and links inferred, not observed; kept apart from real data, marked `PRJ-`, never approved |
| **Gap analysis** | comparing a projected design with the real one: matched, projected only, real only, differs |
| **Proposal** | a link the engine suggests, status `proposed`, with evidence and a confidence |
| **Trace / impact** | follow links across architectures / find what a change affects |
| **Graph store** | the local knowledge graphs and the federated graph saved as JSON files on the device (`sdem build`); no server ([`graph-store-design.md`](design/graph-store-design.md)) |
| **JSON Graph Format (JGF)** | the published file format the graph store uses: `nodes` and `edges`, each with its own data |
| **Load record** | the store's log of every build: inputs, checks, accepted or rejected, outputs |
| **Graph access layer** | the one read interface every query, the view and the engine use, whether the graph comes from the store or from architecture datasets |
| **Baseline (engine)** | the naive name-matching engine any real engine must beat (F1 0.62) |

## The workbench

| Term | Means |
|---|---|
| **CLI** | the command line in VS Code's terminal pane — SDEM's only interface: every engine and function is a `sdem` command (today `sdem-*`) |
| **Copilot instructions** | `.github/copilot-instructions.md` — standing rules GitHub Copilot reads in this repository: use SDEM's commands for facts, never approve, never put projected content into real data, always give source, reasoning and confidence |
| **Prompt file** | a `.github/prompts/*.prompt.md` file that gives Copilot Chat one `/` command for a journey, e.g. `/sdem-explain` — which SDEM command to run and what to report |
| **Skill** | a `.github/skills/<name>/SKILL.md` file: know-how Copilot loads when a task needs it (e.g. `sdem-onboard-designs`) |
| **Agent file** | a `.github/agents/<name>.agent.md` file: one Copilot agent's role, boundaries and tools |
| **Dashboard** | a read-only HTML page SDEM generates: one per workspace (`sdem dashboard`) and the home page for SDEM and every project (`sdem home`) |
| **SDEM workbench** | how architects use SDEM: the SDEM project open in VS Code, SDEM run from the terminal pane (the CLI), the Copilot Chat window for AI support, Git as history and approval trail ([`sdem-workbench-design.md`](design/sdem-workbench-design.md)) |

## Agent platform

| Term | Means |
|---|---|
| **Change event** | a record that something changed (a change set applied, or a merge), with its stored impact result |
| **Change set** | proposed changes to the records of **one** architecture layer, checked before they land; records the agent and the person ([`sdem-agent-platform-design.md`](design/sdem-agent-platform-design.md)) |
| **Orchestration agent (orchestrator)** | the agent that turns impact into work items and tracks them; never changes layer data, never approves |
| **Layer agent** | the agent for one architecture (A1, A2, A3 or A4); changes only its own layer |
| **Work item** | one task for one layer, from a change event's impact, with a status and a holder |

## Evidence and confidence

| Term | Means |
|---|---|
| **Source reference** | where an item comes from: the standard, section or page, and a link |
| **Confidence** | **high** — a public standard defines it and it was checked; **medium** — built on a standard concept, or the standard could not be checked; **low** — SDEM-defined with no standard basis |
| **Archi oracle** | the open-source Archi tool's table of allowed ArchiMate relationships, used to check rows because the ArchiMate specification text needs a login |
| **Login-gated** | readable only with an Open Group account (TOGAF, ArchiMate text) — not checked |
| **Use case / run** | a test workspace with a sealed answer key, e.g. M1, H2, C3; the rules were executed by hand on each and scored |
| **Sealed answers / gold** | the expected links for a run, written before the run and not shown to the executor |
| **Validated against sealed answers** | a rule's output matched the answer key in at least one run |
| **Precision / recall / F1** | of the links proposed, how many were right / of the right links, how many were found / the balance of both |
| **Baseline (model)** | a frozen, reviewed version of the model, e.g. `SDEM-METAMODEL-0.8` |
| **In-house SDEM lead** | the one person in an adopting organisation who looks after SDEM there: the pinned version, `bian/`, triage of questions and metamodel requests, and what to do if the upstream maintainer is unavailable ([operating model](sdem-operating-model.md) §2) |
| **Control** | an automatic check that enforces a rule — e.g. CTL-21 *a reviewer is a person*. Every control, where it runs and its last result: `controls-register.md` |

## Reading the codes in SDEM's output

SDEM's messages name the rule behind them, so a reviewer can look it up. You do not need to learn them — the message always says what is wrong in words; the code says *which rule* said so.

| Code | Means | Example | Look it up |
|---|---|---|---|
| **CTL-nn** | a **control** — an automatic check SDEM enforces | `CTL-21` the reviewer must be a person | [the metamodel guide](sdem-metamodel-guide.md#the-controls--what-sdem-refuses), [controls register](reference/controls-register.md) |
| **LC-nn** | a **data check** on a record | `LC-04` a required attribute is missing · `LC-08` a reference to another layer does not resolve | [logical data model](reference/logical-data-model.md) |
| **LC-10m** | *advice*: the metamodel expects a link that is not there yet (a `WARN`, not an error) | a service domain with no control record yet | fix when you can |
| **RAn-nn** | a kind of link **allowed inside a layer** | `RA3-27` an application interface is made up of API operations | [links inside a layer](reference/relationships-planning.md) |
| **Snn**, **Bnn** | a **rule for finding a connection** between layers | `S24` operation implemented by API · `S17` domain realised by application · `S34` application deployed on a server (from the design's hosting details) | `sdem explain <proposal>` says it in words |
| **HT-**, **HD-**, **HU-**, **HP-**, **HL-**, **HN-** | a **transform rule** — how onboarding read an item: a **t**able, a **d**raw.io diagram, a Plant**U**ML diagram, a **p**hrase, a **l**ink table, a name in the **n**arrative | `HT-07` a table whose *Capability* column names capabilities | your copy of `transform-rules.json` ([configuration](sdem-configuration.md#onboarding--reading-your-designs)) |
| **J1 … J9**, **AG** | a **journey** (a group of commands) in `sdem --help`; AG = the agent platform | J1 check · J2 link · J3 approve · J4 build · J5 trace and impact | [command reference](sdem-workbench-user-guide.md#7-command-reference) |
| **DEC-E-nn** | an **engine decision** quoted in a proposal's reason | `DEC-E-11`: a connection to a record taken from a design document is never above *low* confidence until it is confirmed | — |
| **AG-xnn**, **WB-xnn**, **DEC-x-nn**, **REQ-nn** | a **requirement or design decision** in a specification | `AG-S07` the agents' round limit | for builders: [`design/`](design/README.md) |

**"Need attention"** (in `sdem home` and the dashboards): a project with errors, proposals waiting for review, open agent work or open gaps — the page lists which.

**Ids of records SDEM creates:** `P-RUN-nnn` a proposed connection · `PAY-nnn` (or your workspace's prefix) an approved connection · `HIS-…` a candidate from onboarding · `DOC-…` a design record · `GAP-…` a gap record · `LOAD-nnn` a load · `MIG-nnn` a migration · `CS-…` an agent's change set · `PRJ-…` a planned (AID) element.
