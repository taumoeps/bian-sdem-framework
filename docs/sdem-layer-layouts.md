# How SDEM draws each layer

> **Status: current — A2 and A4 are built (SDEM 0.18.0); A1 and A3 follow.** The decisions behind it are in the [containment design](design/sdem-layer-containment-design.md) (C1–C6) and, for A4, the [network-zones design](design/sdem-network-zones-design.md); this page is for the people who read the drawings.

SDEM draws every layer **by what owns what**: each record sits inside the record that owns it, using that layer's own framework — BIAN for A2, ArchiMate and TOGAF for A1 and A3. A4 is the exception: it is drawn by network zone, because it is the physical deployment ([A4: the physical deployment](sdem-a4-physical-deployment.md)).

The same layout is used everywhere a layer is drawn: the 3D view, `sdem view`, and anything that reads `sdem layout --layer … --json`.

## 1. The rules

1. **The regions are existing records of the layer's framework** — a BIAN business domain or service domain, a capability, an application. Nothing is invented to hold them (unlike A4's zones).
2. **A record sits inside a region only through a structural link** — composition, aggregation, assignment or realisation. A link that only uses, serves, triggers, flows to or is associated with something is drawn as a line, never as nesting. (ArchiMate lets nesting stand for these structural links; SDEM takes the strict set — stricter than Archi's default, which also nests for access.)
3. **One primary hierarchy per layer.** A record with two structural owners is nested in one — the layer's main hierarchy — and its other owner is linked by a line.
4. **What no structural link owns sits in a group of its kind** — for example BIAN's business scenarios, or business objects in A1 — drawn beside the hierarchy.
5. **Every region also has its own block**, in its header band; lines to the record end on it. A record nested in its owner also has a faint dotted **"part of"** line to the owner's block, so every record is visibly connected.
6. **Links between regions are derived, never stored.** When records in two regions are linked, their regions are shown as related — a *potential* link, marked as derived. It is never written into the data.
7. **What has no owner at all** goes in a strip labelled "Not in …" — the layout says so rather than hiding it.

## 2. A2 — BIAN's service landscape (built)

| Region | Holds | Rule |
|---|---|---|
| Business area | its business domains | RA2-01 |
| Business domain | its service domains | RA2-02 |
| Service domain | its service groups; its control record | RA2-03; RA2-05 |
| Service group | its service operations | RA2-04 |
| Control record | its behaviour qualifiers | RA2-11 |

**In groups of their own:** business scenarios (they gather operations from several domains), the business object model (business objects and their attributes), asset types and functional patterns, semantic APIs.

**Derived:** two service domains are related when one business scenario uses operations of both.

**The payment example:**

| Region | Holds |
|---|---|
| Operations and Execution (business area) | Payments |
| Payments (business domain) | Payment Initiation, Payment Execution, Party Authentication |
| Payment Initiation | control record *Payment Initiation Procedure* (qualifiers Execution, Validation); service groups *Instruction* and *Processing* with six operations |
| Payment Execution | control record *Payment Execution Operating Session* (two qualifiers); service group *Execution* with three operations |
| Party Authentication | control record *Party Authentication Assessment* (six qualifiers, from BIAN 14.0.0); service group *Party Authentication Assessment* with seven BIAN operations |

Beside the landscape: the *Customer credit transfer* scenario, the business objects *Payment Instruction* (with *amount*) and *Party* (with *party reference*), and the asset types and functional patterns.

## 3. A1 — the capability map (coming)

Capability → sub-capability → the processes that realise it → their activities. Value streams and their stages, actors and roles, business objects and requirements stay in groups of their own, linked by lines — TOGAF and BIZBOK cross-map value streams to capabilities rather than nest them, and actors belong to the organisation, not to a capability.

## 4. A3 — the application structure (coming)

Application → its components, the services it realises, the functions assigned to it and its interfaces → each interface's API operations. Data entities and events stay in groups of their own: they are accessed and triggered, not owned.

## 5. A4 — by network zone (built)

Cloud or on premises → DMZ or internal → private segments, with every shape in its zone and the zone connections as arrows. See [A4: the physical deployment](sdem-a4-physical-deployment.md).

## 6. How it lines up with the standards

- **BIAN** defines what belongs to what — the landscape and the parts of a service domain; the drawing follows it and adds nothing BIAN does not say.
- **ArchiMate 3.2** allows nesting to stand for composition, aggregation, assignment and realisation, a line to end on a container, and an element drawn as well as its box. The links between regions follow ArchiMate's derivation of relationships, marked as derived.
- **TOGAF** — the capability map and the application structure are the standard views of the business and application architectures.

## 7. Commands

| Command | Shows |
|---|---|
| `sdem layout --layer A2 --workspace <dir>` | A2 as BIAN's landscape — each region and what it holds; `--json` for the coordinates every drawing uses |
| `sdem layout --layer A4 --workspace <dir>` | A4 by network zone (the same as `sdem zones --layout`) |
| `sdem view --graph <dir>/graph` | all four layers; A2 and A4 drawn by these layouts |

The DESNRE site's 3D view draws the same layouts.
