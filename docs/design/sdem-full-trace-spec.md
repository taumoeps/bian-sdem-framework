# The full trace — every record's chain from A1 to A5, direct and through its parent shapes

> **Status: approved by the owner (2026-11-22: "write spec and implement … it must show a full trace") — being built.** Extends the
> knowledge graph's trace (`sdem/graph.py`, KG-Q-…; `--follow-composition`, which already climbed from a part to its whole downstream).
> Made-up data only.

## 1. Why

A design's links between layers join specific records, and many records link only through a **parent shape in their own layer**: a
BIAN operation is *part of* its service domain, which an A1 process uses; an API operation is *part of* its interface, which is exposed
through an A5 node. A trace that follows only the links between layers stops at the operation — `sdem trace` of *Payment Order
Initiation: Retrieve* found nothing upstream — and the 3D view, which lights a record's chain when it is clicked, showed fragments: a
line from A2 to A4 with nothing to A1 or A5. The chain is in the design; the trace did not walk it.

## 2. Rules

| Id | Rule |
|---|---|
| **FT-01** | **A trace walks "part of" as well as the links between layers.** A part-whole link inside a layer (composition, aggregation — ArchiMate's structural links) is a hop the trace may take, shown as such (`PART_OF`, `HAS_PART`, `COMPOSES`) and marked structural — nothing to approve. The links between layers are followed as before: approved only (statuses as given). |
| **FT-02** | **Which hops, so the chain is whole and never a sibling's.** From every record reached, the trace climbs to its whole (an operation to its service group and domain; an API operation to its interface and component). It steps down into parts only from the record traced, and — upstream — from a record reached by a link between layers (whatever depends on an application's modules depends on the platform it runs on). It never steps down from a record it reached by climbing: tracing *Retrieve* reaches its domain, not the domain's other operations. |
| **FT-03** | **The full trace is the default.** `sdem trace` (one record, or a layer) gives the full trace; `--direct-only` gives the links between layers alone, as before. `--follow-composition` is still accepted and means the default. Impact (`sdem impact`) is unchanged by this spec. The static dashboard (`sdem dashboard`) shows the full trace too, as the command does. |
| **FT-04** | **A trace ends only where the design does.** Where no link continues — a record with no link to the next layer, directly or through a whole — the chain ends there; the design's gaps are said by `sdem status` and the GAPS view, never filled by the trace. |
| **FT-05** | **The 3D view and the 2D map light the same chain.** Clicking a record lights FT-02's chain, across every layer, with the part-whole links it passed through, so a highlighted line never stands alone without its chain to A1 and A5 where the design has one. (DESNRE `index.html`, DW-67.) |
| **FT-07** | **A BIAN business object is part of its domain's information** *(the owner, 2026-11-22: "it's missing up and down links")*: a control record's link to a business object (BIAN's B08 — the domain's Business Object Model) is a part-whole hop for the trace, so *Payment Transaction* climbs to *Payment Order Initiation* and the A1 processes that use it. |
| **FT-06** | **Proved**: on a made-up design, *Retrieve*'s full trace reaches the A1 process that uses its domain and the A5 node its API's interface is exposed through; it does not reach the domain's other operations; `--direct-only` gives the old answer; the existing composition traces keep their answers (module → whole → platform downstream; platform → modules upstream). |

## 3. Decision

| # | Decision | The owner's choice |
|---|---|---|
| FT-D1 | The full trace (FT-01, FT-02) is the default for `sdem trace` and the 3D highlight; the direct-only trace stays a flag | **yes** (2026-11-22) |
