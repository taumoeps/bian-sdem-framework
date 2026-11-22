# Metamodel integrity — is SDEM's metamodel current, sound and truly shown?

> **Status: analysed 2026-11-22** (the owner: "rewrite the analysis and document it first", then "yes"). This document
> states the concerns, the reference model they are tested against, the questions, how each is answered and what the analysis delivers.
> The findings are added in §6 once it is run. No change to SDEM follows from it without the owner's decision. Made-up data only.

## 1. The owner's concerns

**C1 — Is the metamodel really updated, and has it become brittle?** The 0.20 stack (A1 Business, A2 BIAN, A3 Data, A4 Application,
A5 Technology), the BIAN and Security extensions, and this week's additions (full trace, data domains, ownership, read and write) were
added in quick succession. The 3D views do not make it possible to tell whether they show the real state of the metamodel, and the
owner is concerned the core and what was added to it have made the core brittle.

**C2 — The views are mashed together.** Business, Service Domains, Data, Application and Technology feel mixed up across the
*Architecture*, *BIAN*, *Security* and *Metamodel* views. The owner's intent:

| View | What it is | Who reads it |
|---|---|---|
| **Architecture** | The design as an architect reads it — ArchiMate's view of Business, Data, Application and Technology, with BIAN and Security **integrated into** those layers, not beside them | an architect reviewing a design |
| **Metamodel** | The mapping view — how Business, BIAN, Data, Application and Technology are connected, which the knowledge graphs are derived from. **Every shape in every layer is connected upstream and downstream, directly or indirectly** — no orphans | tracing, impact, the knowledge graph |

## 2. The reference model

The owner's model (2026-11-22) and the corrections that reflect how SDEM is built:

```
                 Metamodel (core)  ◄── Metamodel extensions (BIAN, Security)
                  │ checks                         │ add types, links — and layers
                  ▼                                ▼
  A1 graph  A2 graph (BIAN)  A3 graph  A4 graph  A5 graph      S graph (Security, beside the stack)
     ▲         ▲               ▲         ▲         ▲              ▲
  A1 entities  A2 entities   A3 …      A4 …      A5 …          S1–S5 entities
     └─────────┴───────┬───────┴─────────┴─────────┴──────────────┘
                       │  joined by
            Mapping registry (approved links between layers)
              ▲ proposed by the rules engine, approved by a person
                       │
                       ▼
            Federated knowledge graph  →  trace, impact, the Metamodel view, the agent
```

| # | Owner's model | Correction |
|---|---|---|
| M1 | The federated graph sits above the layer graphs and feeds down | Data flows **up**: entities → a layer's graph → the federated graph, which is the layer graphs **plus the links between layers** |
| M2 | Nothing holds the links between layers | The **mapping registry** (`mappings.json`) — every approved link between layers, with its evidence and a named reviewer — is what joins the five graphs |
| M3 | The metamodel produces the graphs | The metamodel **checks** them: which types are valid, which links are allowed inside a layer (RA…), which link types between layers |
| M4 | Extensions only add to the metamodel | Extensions **also add layers**: BIAN *is* A2 (without it the stack is A1–A4); Security is a layer **S beside the stack**, joined to A1–A5 through the registry |
| M5 | Every extension has a knowledge graph of its own beside the stack (the owner's second model) | An extension places itself in **one of three ways**: (a) **beside the stack** (`position: across`) — Security's layer S, a graph of its own, as drawn; (b) **inside the stack** — BIAN inserts A2 and the stack is renumbered (A1 Business, A2 BIAN, A3 Data, A4 Application, A5 Technology); a profile's *above* or *below* layer the same way; (c) **inside an existing layer** — types that extend a core type (MX-32a), attributes, rules — no new graph |

**What an extension adds** (corrected with the owner, 2026-11-22: "BIAN and Security both have data entities and graphs"). An
extension brings **three things**: (1) **to the metamodel** — types, attributes, link types between layers, rules and a layer, merged when
a person switches it on (`sdem profile include`), never a change to the core's own definitions (the stable-core test); (2) **its own
entities** — the extension's records in the workspace; (3) **its own knowledge graph** — built from those entities like any layer's
(on the Payment example: `bian.graph.json` and `s.graph.json` beside `business`, `data`, `application`, `technology`), joined to the
others through the mapping registry.

- **BIAN** (inside the stack, A2) carries **an information model of its own** — the data architecture it had before it became an
  extension: BIAN's Business Object Model — business objects with typed fields (`A2.BusinessObject`, `A2.BusinessObjectAttribute`; IM-09,
  BO-01…), held by each domain's control record. On the Payment example: 3 control records, 1 business object (*Payment Transaction*)
  with 30 fields. It is BIAN's model, in BIAN's graph; SDEM's **Data layer** (A3) is the design's own data. The two are joined by
  links a person approves: a business object MAPPED_TO a data entity, a field FIELD_MAPPED_TO a data field (BD-01, BD-02).
- **Security** (beside the stack, S) has its own entities — controls, threats, trust boundaries (on the Payment example 15, 9 and 1) — in
  its own graph, S1–S5; it adds no data model, and reaches the Data layer through PROTECTS and THREATENS.

Without BIAN the stack is A1 Business, A2 Data, A3 Application, A4 Technology; the A2 BIAN graph is not there.

## 3. Questions

| Id | Question | Concern |
|---|---|---|
| **MI-Q0** | Does SDEM's structure match the reference model, box by box and arrow by arrow? | both |
| **MI-Q1** | **State** — does the metamodel SDEM loads hold everything added: the 0.20 stack, BIAN (domains, business objects, their links to Data and Application), Security (S1–S5 and its links), data domains, ownership, read and write (0.19.0)? | C1 |
| **MI-Q2** | **Evidence** — does each 3D view (Architecture, Security, Metamodel) draw that real state, or a published copy in 0.19's shape, or the site's own drawing? | C1 |
| **MI-Q3** | **Brittleness** — has the core become fragile? (a) the core depending on an extension's content; (b) one thing defined in two places that can drift; (c) counts and names written into code, tests and documents that break on every change; (d) the 0.19 and 0.20 shapes kept side by side, and every translation between them; (e) extensions that stop working whenever the metamodel's version moves | C1 |
| **MI-Q4** | **Purpose** — does each view show what it is for (§1, C2)? Where do they overlap, or mix the design with the mapping? | C2 |
| **MI-Q5** | **Integration** — in the Architecture view, do BIAN and Security appear within Business, Data, Application and Technology as ArchiMate would show them, or as plates and views of their own? | C2 |
| **MI-Q6** | **Completeness of the mapping** — in the Metamodel view and the knowledge graph, is every shape in every layer traceable A1–A5, directly or indirectly? Which are orphans, and is each a gap in the design or in SDEM's rules? | C2 |
| **MI-Q7** | **Consistency** — do the Metamodel view, `sdem trace` and the knowledge graph give the same chain for the same shape? | C2 |
| **MI-Q8** | **One trace, two implementations** — the full trace (FT-01…FT-10) is written twice, in SDEM (Python) and in the site (JavaScript); they disagreed three times on 2026-11-22 (access direction, business objects not drawn, paths not drawn). Should the rule have one source the site reads? | C1, C2 |
| **MI-Q9** | **Rules that hold in one form only** — an extension's rules are written in 0.19's shape and SDEM translates only its own standards to 0.20 (SEC-S11 answered wrongly on a 0.20 design until it was computed). Which other rules, patterns and checks do the same? | C1 |
| **MI-Q10** | **Versions and releases** — SDEM stays 0.20.0 while its metamodel moved 0.18.0 → 0.19.0; the tag `v0.20.0` no longer matches main; each extension pins a metamodel range, so one optional type needed three extension releases, and `sdem` 0.20.0 as released refuses the new extensions | C1 |
| **MI-Q11** | **SDEM's own rules and types against the standards** — which of the trace's hops and which types are ArchiMate's, BIAN's or NIST's, and which are SDEM's own (a business object part of its domain, a path the whole of its nodes, a control traced through what it protects; network zone, data domain, deployment, API operation)? Is each labelled so, and does an ArchiMate export stay valid? | C1 |
| **MI-Q12** | **Stated or inferred, visibly** — does every view and answer tell apart approved links, proposed links, inferred records, and hops the trace walks that no person approved (part-of)? | C2 |
| **MI-Q13** | **The cost of change** — one optional type touched 415 files, needed seven test fixes and 30-minute suite runs: hard-coded counts, embedded diagrams, recorded answers, the examples kept twice (0.19 and 0.20), generated files. What makes a change this expensive, and what would make it cheap? | C1 |

## 4. How each is answered — evidence, not views

| Id | Method | Evidence |
|---|---|---|
| MI-Q0 | Trace each box and arrow of §2 to the code that implements it | `sdem/metamodel.py`, `sdem/graph.py` (LevelGraph, FederatedGraph), the graph store (one file per layer + `federated.graph.json`), `mappings.json`, the profile merge (`sdem/profile.py`, `include_pack`) |
| MI-Q1 | An inventory of the metamodel as loaded, with no extension, with BIAN, with BIAN and Security | `sdem types` per layer, `metamodel/*.json`, `metamodel/identity.json`, `metamodel/stability.json`; the packs (`ext-bian-pack.json`, `sdem_security/pack.json`) |
| MI-Q2 | Compare the inventory with what each view draws, on the published Payment example | the published bundle (`/api/u/…/workspace`), `assets/archview.js`, the site's view models; which file shape each view reads (0.19 or 0.20) |
| MI-Q3 | A brittleness audit: run the stable-core test on/off; list duplicated definitions; list every 0.19↔0.20 translation; list every hard-coded count and name the last change touched; the extensions' version ranges | `tests/test_core_stability.py`, `scripts/core_stability.py`; `sdem/form020.py`, `sdem/migrate20.py`, `as_019`; this change's 415 files as a measure |
| MI-Q4, MI-Q5 | For each view, what it draws per layer, against the intent in §1 | `workbench.html`, `index.html`, `assets/archview.js`; screenshots of each view on the published example |
| MI-Q6 | The full trace (FT-01…FT-10) of every record on the Payment example; every record that reaches neither up nor down; each classified *design gap* (a link the design does not state) or *rule gap* (a link SDEM does not walk) | `sdem trace --direction up/down --json` per record; `sdem status` (completeness); the site's chain on the same model |
| MI-Q7 | The same records traced by `sdem trace` and by the Metamodel view; every difference | the two traces, record by record |
| MI-Q8 | List every trace rule and where each is implemented; run both on the same model and compare | `sdem/graph.py` (`structure`, `trace`, `across`); the site's `index.html` (`chain`, `WP`) and `assets/archview.js`; `tmp`-style checks used on 2026-11-22 |
| MI-Q9 | Run every standard, pattern and extension rule on the same design in both forms; list any that answer differently | `sdem comply`, `sdem status`, `sdem security review` on a 0.19 and a 0.20 copy; `sdem/form020.py` (`adapt`, `_rule`) |
| MI-Q10 | Map SDEM's version, the metamodel version, the tags and each extension's range; say what a person installing today gets | `sdem/releases.json`, `metamodel/migrations.json`, git tags, each `sdem-extension.json` |
| MI-Q11 | Classify every type and every trace hop by its source; check the ArchiMate export against the exchange format | `metamodel/*.json` (`reference`, `definition_source`), `sdem/graph.py`; `sdem export` (Open Exchange Format) |
| MI-Q12 | For each view and for `sdem trace` / `impact`, how each kind of link is shown | the site's line styles; `status: structural` on virtual hops in `sdem trace --json` |
| MI-Q13 | Count, for the 0.19.0 change, the files touched by kind and why; name each kind's cause | `git show --stat` of the change; the failing tests of 2026-11-22 and their fixes |

## 5. What the analysis delivers

1. **C1 verdict**: the metamodel as it is (inventory), whether the views show it, and the brittleness found — each cause named, with its
   evidence and its risk.
2. **C2 verdict**: what each view shows today against its purpose, and a proposal for the views — likely *Architecture* and *Metamodel*,
   with BIAN and Security inside them rather than views of their own.
3. **The orphan list** for the Payment design: each record, its layer, why it is an orphan, *design gap* or *rule gap*.
4. **Recommendations**, ranked by risk, each with what it would change and what it would cost. Nothing is changed until the owner decides.

**Out of scope:** new types or links (they would follow from a recommendation, as their own spec); the DESNRE workbench's layout, which
the DESNRE project owns — this analysis says what a view should show, not how it is laid out.

## 6. Findings (2026-11-22, on the Payment design `payment-v3-020`, SDEM main with metamodel 0.19.0, not yet pushed)

### Verdicts

**C1 — the metamodel is updated, and its core is not brittle; what surrounds the core is.** SDEM loads metamodel 0.19.0 with every
addition, and the stable-core test passes: switching BIAN and Security on and off leaves the core's types, links, attributes and text
unchanged — the extensions are additive. The brittleness is in five things around the core: two file shapes (0.19 and 0.20) translated
back and forth; the trace written twice; counts and diagrams written into tests and documents; the examples kept twice; extensions pinned
to a metamodel range.

**C2 — the views do not yet show what they are for.** The *Architecture* view draws 125 of the design's 201 records and BIAN as its own
plate (A2) in the one stack — but Security only in a separate view; the view called *Metamodel* draws the design's records and links (the
mapping), not the metamodel. And the full trace leaves gaps: **A3 Data is the weak link** — no Business or BIAN record reaches Data
downstream — for rule gaps and design gaps named below. The site's highlight and `sdem trace` disagree on 91 of 125 records.

### Per question

| Id | Finding | Evidence |
|---|---|---|
| MI-Q0 | **Matches the reference model (§2, with M1–M5).** One graph per layer file (`business`, `bian`, `data`, `application`, `technology`, and `s` for Security) built from its records and checked by the metamodel; the registry (`mappings.json`) joins them; `FederatedGraph(levels, registries, metamodel)` is what trace and impact run on; extensions are merged by `include_pack`, each with its layer's position. | graph store of the design: 8 files; `sdem/store.py` (`GraphReader.from_store`), `sdem/graph.py`, `sdem/profile.py` |
| MI-Q1 | **Updated.** Loaded for the design: A1 13 types, A2 (BIAN) 12, A3 (Data) 3 — data entity, field, domain —, A4 7, A5 13, S 3; metamodel 0.19.0 (51 core types, 164 rules inside layers). | `sdem types <layer> --workspace` |
| MI-Q2 | **The views show a translated copy.** Every view reads the published bundle in **0.19's shape** (four files, Data inside Application) and relabels it with the design's stack. Every visible mislabel this week came from that: A4 for A5, the Data tab's *Application* document, Technology's *A4* heading, the Data plate's file name. | `sdem-desnre` `as_019` → `workspace_bundle`; DW-74, DW-77 |
| MI-Q3 | **Core sound (a: no); surroundings brittle (b–e).** (a) The core depends on no extension — stable-core test passes. (b) Defined twice: BIAN's data in SDEM and in `sdem-bian` (BP-11 keeps them equal); the trace in SDEM and the site; each example in 0.19 and 0.20 form. (c) Seven tests and three documents carried counts or diagrams the 0.19.0 change broke. (d) Translations between forms: `form020`, `migrate20` (`to_019`, `export_019`), `as_019` in each extension and the publisher, `identity` renaming text. (e) Every extension pins a metamodel range — one optional type needed three releases. | `tests/test_core_stability.py` (12 pass); the 2026-11-22 test fixes |
| MI-Q4 | **Partly.** *Architecture* is the design in ArchiMate layout, as intended. *Metamodel* is the design's records and all their links — the mapping view the owner intends — but its name says the opposite. *Security* is a third stack beside them. | the three views on the published example |
| MI-Q5 | **BIAN yes, Security no.** BIAN is the A2 plate of the one stack. Security is not in the Architecture view: it has its own five plates (S1–S5) repeating the design underneath. | `workbench.html` (`archimateModel`, `secModels`) |
| MI-Q6 | **Every design layer is reached by some records; A3 Data is the gap.** Records that reach all of A1–A5 (up and down together): A1 0 of 48, A2 33 of 101, A3 12 of 38, A4 6 of 15, A5 21 of 28, S 16 of 25. **Orphans (reach nothing): 9** — 3 actors and the web channel (A1), 3 asset types and 2 functional patterns (A2). | the full trace of all 226 records (`fg.trace`, up and down) |
| MI-Q7 | **They disagree on 91 of 125 records — the site always reaches less.** The Architecture view shows structure by nesting (a process inside its capability) and draws no line for it; the site's trace walks only lines. 76 records are not drawn at all (34 BIAN operations, 30 business-object fields, 24 requirements…). | the site's chain run on its own model for every record, compared with `sdem trace` |
| MI-Q8 | **Confirmed.** The rule is written twice and differs: by what each draws (MI-Q7) and three times this week by fault. | `sdem/graph.py`; `index.html` (`chain`, `WP`), `assets/archview.js` |
| MI-Q9 | **Now consistent.** The standards give the same 213 findings on the design in either form. SEC-S11 was the one rule that differed; it is computed since 0.4.0. An extension's rules written in 0.19's shape remain untranslated by SDEM — a trap for the next rule. | `sdem comply` on the design and on its 0.19 export |
| MI-Q10 | **Out of step.** The `v0.20.0` tag has metamodel 0.18.0; main has 0.19.0 under the same version; `sdem-bian` 1.0.2, `sdem-security` 0.3.2 and `sdem-desnre` 0.10.1 refuse 0.19.0; their new releases (1.0.3, 0.4.0, 0.10.2) are built but not pushed. | `sdem/releases.json`, each `sdem-extension.json`, git tags |
| MI-Q11 | **Labelled by source.** Types: 25 ArchiMate 3.2, 15 BIAN, 1 TOGAF, 9 SDEM's own (value stream stage, business activity, BOM model, API operation, data attribute, data domain, deployment, deployment environment, network zone). Every link is an ArchiMate kind; *which* links the trace walks, and how, is SDEM's rule (FT-01…FT-10). ArchiMate export validity: **not checked** in this analysis. | `metamodel/a*.json` (`reference`, `definition_source`) |
| MI-Q12 | **Partly.** `sdem trace --json` marks a part-of hop `status: structural`; the site draws a lit part-of hop dashed and a proposed link dotted; nesting in the Architecture view carries no mark at all. | `sdem/graph.py` (`hop`); `index.html` (DW-68) |
| MI-Q13 | **84% of the cost is copies.** 416 files: 199 examples' version stamps, 129 example graph stores, 23 migration records (351 in all) — then 23 metamodel and schema, 13 documents, 9 generated, 8 code, 5 tests, 5 recorded answers. | `git status` of the 0.19.0 change |

### The gaps in the full trace (MI-Q6), sorted

| Kind | Gap | Records |
|---|---|---|
| **Rule** | **R1 — downstream, a whole reached by a link is never opened.** A process uses its service domain; the domain's information (its business object, mapped to PaymentLedger) is a part of the domain, and FT-02 steps into parts only from the record traced. So no A1 or A2 record reaches Data downstream. | 43 A1 and 63 A2 records lack only A3 |
| **Rule** | **R2 — *serving* inside a layer is not walked.** Actors and the web channel are linked only by a service or interface serving them. | 4 A1 orphans |
| **Rule** | **R3 — BIAN's classification links are not walked.** A domain's asset type and functional pattern are joined by association. | 5 A2 orphans |
| **Design** | Three of four tables — ConsentLedger, IdempotencyRegistry, SecurityEventLog — are mapped to no BIAN business object and no business object of A1, so they and their fields reach nothing above Data. | 26 A3 records lack A1, A2 |
| **Design** | Applications that access no data (Identity, Fraud), or realise no service domain. | 9 A4 records |
| **Design** | Their deployments and nodes, which follow. | 7 A5 records |

## 7. Recommendations, ranked

| # | Recommendation | Fixes | Cost |
|---|---|---|---|
| 1 | **One trace.** SDEM computes every record's chain (up and down) when the design is published; the site lights what it is given, never walks itself. | MI-Q7, MI-Q8 — the site and `sdem trace` can no longer differ | publisher + site; moderate |
| 2 | **Close the rule gaps** (a spec, FT-11…): R1 — from a whole reached by a link, step into its *information* parts (a domain's business objects, an entity's fields); R2 — walk *serving* inside a layer; R3 — walk BIAN's classification links. Each named as SDEM's rule. | A3 reachable from A1 and A2; 9 orphans | SDEM; small |
| 3 | **Publish the 0.20 form as it is** — the bundle carries the design's own layers; the site stops reading 0.19's shape and relabelling it. | MI-Q2, most visible mislabels, MI-Q3 (d) | publisher + site; moderate |
| 4 | **Views as intended:** *Architecture* — the design, BIAN in its plate, **Security as an overlay on the same stack** (a switch), not a third stack; *Metamodel* renamed **Connections** (it shows the design's records and links); every record drawn or listed, so none is untraceable for not being drawn. | MI-Q4, MI-Q5, part of MI-Q7 | the DESNRE project (owns the layout); this analysis is its brief |
| 5 | **Cheap change:** tests derive counts from the metamodel; documents embed generated diagrams by generation; the examples kept once (0.20), the 0.19 copies retired. | MI-Q13 — ~350 of 416 files | SDEM; moderate |
| 6 | **A version policy:** a metamodel change is an SDEM version (0.21.0, not 0.20.0 again); extensions accept any additive metamodel minor (their tests decide), so they are not re-released for each one. | MI-Q10 | policy + manifests; small |
| 7 | **The Payment design's gaps** — a person decides: map Consent, Idempotency and Audit to BIAN or A1 business objects; link the applications to their data and domains. | the design gaps of MI-Q6 | the architect |
| 8 | **Check the ArchiMate export** of the design against the Open Exchange Format. | MI-Q11 (not done) | small |

Nothing here is changed until the owner decides.
