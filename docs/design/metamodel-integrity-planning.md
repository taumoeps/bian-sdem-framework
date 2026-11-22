# Metamodel integrity — the plan

> **Status: plan, for the owner's decisions (2026-11-22)** — nothing in it is built. It turns the findings of the
> [metamodel integrity analysis](sdem-metamodel-integrity-analysis.md) (MI-Q0…MI-Q13) into one target and the work that reaches it, in
> order, each step with what it fixes, what it delivers and how it is accepted. Every step that changes the metamodel or a view needs the
> owner's approval (AGENTS.md rule 2); the DESNRE workbench's layout is the DESNRE project's. Made-up data only.

## 1. The target — one source of truth, one place that computes

```
   Metamodel Core  (+ Extensions merged in: BIAN in the stack, Security beside it)
        │  the ARCHITECTURE mapping — which types may exist, which links may join them, and how a trace walks them
        │  checks ▼                                                         ▲ built from
   A1 … A5 graphs  +  extension graphs (BIAN, Security)  ◄── each layer's entities
        │  joined by the mapping registry (approved links between layers, each with evidence and a named person)
        ▼
   Federated Knowledge Graph — the DATA mapping: what this design holds and how it connects
        │
        ▼
   SDEM CLI — the only place anything is computed: trace (direct and indirect, up and down), impact, completeness, gaps
        │
        ▼
   Views — render what the CLI returns, never compute their own:
   ArchiMate views per layer (Business, Data, Application, Technology) with BIAN in its layer and Security as an overlay;
   the Connections view (every record and link); the agent
```

## 2. The principle (MIP-00)

| Id | Rule |
|---|---|
| **MIP-00** | **The Metamodel Core (with the extensions merged in) and the Federated Knowledge Graph are the only sources of truth; the SDEM CLI is the only place anything is computed.** Every view — the DESNRE site, the workbench, the dashboard — and the agent render what the CLI returns: a chain, an impact, a gap is never worked out a second time elsewhere. The metamodel decides *what may be* and *how a trace walks*; the graph holds *what is*; the CLI combines them. |
| **MIP-00a** | **Every shape is accounted for.** For a design, every record either reaches upstream and downstream through the CLI's trace, or is on a gap list, each gap marked *design gap* (a link the design does not state — a person decides) or *rule gap* (a link SDEM does not walk — SDEM is fixed). "No orphans" is tested, not hoped for (MIP-05). |

## 3. The work, in order

| Step | Id | What | Fixes (analysis) | Delivers | Accepted when | Needs |
|---|---|---|---|---|---|---|
| 1 | **MIP-01** | **A version policy, then ship what is built.** A metamodel change is an SDEM version: metamodel 0.19.0 ships as **SDEM 0.21.0**, not 0.20.0 again; the `v0.20.0` tag stays as released. Extensions accept any additive metamodel minor — their tests decide — so they are not re-released for each. Then push SDEM, `sdem-security` 0.4.0, `sdem-bian` 1.0.3, `sdem-desnre` 0.10.2. | MI-Q10, MI-Q3 (e) | `releases.json` 0.21.0; manifest ranges; tags; CI green | CI passes on SDEM main and every extension; a fresh install of SDEM 0.21.0 with the three extensions runs `sdem status` on the Payment design | owner's decision (0.21.0) |
| 2 | **MIP-02** | **Close the rule gaps (spec FT-11…).** R1 — from a whole reached by a link, step into its *information* parts (a service domain's business objects, an entity's fields), so Business and BIAN reach Data downstream. R2 — walk *serving* inside a layer (actors, channels). R3 — walk BIAN's classification links (asset type, functional pattern). Each labelled SDEM's rule. | MI-Q6 rule gaps R1–R3 | the spec; `sdem/graph.py`; tests | on the Payment design: every A1 and A2 record that reaches A2/A4/A5 reaches A3 too where the design maps the data; the 9 orphans reach their layers | owner's approval of the spec |
| 3 | **MIP-03** | **The CLI computes every chain; the views render it.** On publishing, SDEM computes each record's full trace (up and down, with each hop's kind — approved link, part-of, proposed) and sends it with the design; the site lights the chain it is given. The site's own walk (`chain`, `WP`, `ACX`) is removed. | MI-Q7, MI-Q8, MI-Q12 | `sdem trace --all --json` (or the publisher calling it); `sdem-desnre` ships it; the site reads it | the site and `sdem trace` give the same chain for every record of the Payment design — one check in the site's tests | owner's approval; the DESNRE project for the site |
| 4 | **MIP-04** | **Publish the design in its own form.** The bundle carries the design's layers as SDEM numbers them (0.20 form: business, bian, data, application, technology, and the extensions' layers); the site stops reading 0.19's shape and relabelling it. | MI-Q2, MI-Q3 (d) | `sdem-desnre` without `as_019` for a 0.20 design; the site reads the stack | no label on the site names a layer by 0.19's number; the Data tab, file names and documents are the design's own | the DESNRE project for the site |
| 5 | **MIP-05** | **The completeness test (MIP-00a).** `sdem trace --gaps` (or `sdem status`) lists every record that does not reach upstream and downstream, each *design gap* or *rule gap* with its reason; it runs on every published design and on the examples in CI. | MI-Q6 | the command and its CI check | the Payment design's list matches the analysis (design gaps only, once MIP-02 is built); no example has a *rule gap* | — |
| 6 | **MIP-06** | **Views as intended** — a brief to the DESNRE project. *Architecture*: the design in ArchiMate per layer, BIAN in its plate, **Security as an overlay on the same stack** (a switch), not a third stack. *Metamodel* renamed **Connections** — the design's records and links. Every record drawn or listed, so none is untraceable for not being drawn. | MI-Q4, MI-Q5, MI-Q7 (undrawn records) | the brief; the DESNRE project's design decisions | an architect finds every record of the design in a view, and Security on the stack it protects | the DESNRE project |
| 7 | **MIP-07** | **Make change cheap.** Tests derive counts from the metamodel instead of writing them; documents embed generated diagrams by generation; each example kept once (the 0.20 form), the 0.19 copies retired; recorded 0.19 answers kept only where they still prove something. | MI-Q13, MI-Q3 (b, c) | test and generator changes; examples folded | an additive metamodel change touches its own files, its tests and its spec — not hundreds of example copies | owner's approval (retiring the 0.19 copies) |
| 8 | **MIP-08** | **Check the ArchiMate export** of the Payment design against the Open Exchange Format; SDEM's own types say how they are exported. | MI-Q11 | a test of `sdem export` | the export validates; each SDEM-own type is exported as its ArchiMate base | — |
| 9 | **MIP-09** | **The Payment design's gaps** — the architect's: map ConsentLedger, IdempotencyRegistry and SecurityEventLog to BIAN or A1 business objects; link Identity and Fraud to their data, and the applications that realise no service domain; name the owners of the two tables holding personal data. | MI-Q6 design gaps | the architect's decisions, as change sets and approved links | MIP-05 lists no gap for the Payment design | the architect |

| 10 | **MIP-10** *(built 2026-11-22: G1 the trace and any new extension by pattern, G2 the overlay declared, G3 `requires`, G4 two vertical extensions linked, FT-14)* | **Extensions by pattern** (design §3a, MID-08…MID-10): remove the BIAN-only code paths (G1); a vertical extension drawn as an overlay from its manifest (G2); `requires` for any extension (G3); a rule for two vertical extensions together (G4). Proved with two made-up extensions — *Networks* (H2, in Technology) and *Disaster Recovery* (V1) — switched on with BIAN and Security. | the design's G1–G4 | SDEM, publisher and site changes; two test extensions | both test extensions place, trace, check and publish with no change to SDEM's code for them | owner's approval |

**Order and dependencies.** MIP-01 first: it releases what is built and sets the rule for every later metamodel change. MIP-02 before
MIP-03 and MIP-05, so the chains the CLI hands out are complete. MIP-03 and MIP-04 change the publisher and the site together and can
ship as one DESNRE release. MIP-06 follows MIP-03 (the views render the CLI's chains). MIP-07 and MIP-08 at any time. MIP-10 after MIP-03, MIP-04 and MIP-06 (it generalises what they build). MIP-09 is the
architect's, whenever the design is next worked on; MIP-05 then shows it closed.

## 4. Decisions for the owner

| # | Decision | Recommended |
|---|---|---|
| MIP-D1 | The principle MIP-00 / MIP-00a: the metamodel and the federated graph the only sources of truth, the CLI the only place that computes, every shape accounted for | **yes** |
| MIP-D2 | Ship metamodel 0.19.0 as SDEM **0.21.0**; extensions accept additive metamodel minors (MIP-01) | **yes** |
| MIP-D3 | Close the rule gaps R1–R3 (MIP-02), as SDEM's rules | **yes** |
| MIP-D4 | The site renders the CLI's chains and the design's own form (MIP-03, MIP-04) — with the DESNRE project | **yes** |
| MIP-D5 | Retire the 0.19 copies of the examples (MIP-07) | **yes**, once MIP-04 ships |
| MIP-D6 | Extensions by pattern, proved with made-up *Networks* and *Disaster Recovery* extensions (MIP-10) | **yes** |
