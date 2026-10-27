---
name: sdem-trace-impact
description: How to run and read SDEM trace and impact results — what depends on what across business, BIAN, application and technology, and what a change (modify, rehost, replace, retire) affects. Use when asked about dependencies, upstream or downstream effects, or the impact of a change, and when explaining or summarising trace or impact output.
---

# SDEM trace and impact

Both read a graph store (`sdem build --estate <estate> --out <graph>`) and follow **approved** links only.

## Trace

```bash
sdem trace <id> --direction down --graph <graph>   # what it depends on, towards A4 technology
sdem trace <id> --direction up   --graph <graph>   # what depends on it, towards A1 business
```

Each line is `-RELATIONSHIP-> ID 'name' [type] (link id)`. The link id in brackets is the approved link the chain follows — cite it as the source. A chain that stops early means a link is not approved yet: `sdem query --graph <graph> --unmapped A2`.

## Impact

```bash
sdem impact <id> --change modify|rehost|replace|retire --graph <graph>
```

| Classification | Means |
|---|---|
| `design_change_required` | this record's design must change |
| `review_required` | check its assumptions; nothing further unless the review finds something |
| `no_impact` | on the path, but unaffected by this kind of change |

`via` lists the approved links of the path; **mappings to supersede** are links an architect must replace with new ones. The last line is always true: *the classification is structural; an architect confirms before any design changes.*

| Kind | Effect (from `schema/impact-rules.json`) |
|---|---|
| modify | the record itself; direct neighbours review |
| rehost | hosting only: the record and its direct dependents need design change; functional layers unaffected; its links superseded |
| replace | direct dependents re-point their links; indirect ones review |
| retire | direct dependents lose a dependency; indirect ones review |

When summarising, say for each affected record: layer, id and name, classification, the path (link ids) and why — and that the architect confirms.
