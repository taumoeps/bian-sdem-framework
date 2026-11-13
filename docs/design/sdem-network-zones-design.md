# Network zones — where every technology record sits

> **Status: approved and built — the owner approved Z1–Z6 as recommended (2026-11-14); metamodel 0.10.0, SDEM 0.18.0.** Built: `A4.NetworkZone` with `zone_level` and `zone_kind` (AT-A4-34, AT-A4-35), `internet_facing` (AT-A4-36), placement RA4-38, checks LC-16…LC-18 (`sdem/conformance.py`), trace and impact through zones (KG-Q-08), examples payment-initiation (cloud) and legacy-core-ledger (on premises); tests `tests/test_network_zones.py`. Not built: patterns checking zone records (PR-13a) — an organisation's own `network_zone` attribute still works as before. The zone structure is the owner's (2026-11-14, §2); this page proposes how SDEM records and checks it. It follows metamodel 0.9.0 (a platform's network is a link, RA4-37; LC-15; KG-Q-08). A metamodel change: it needs the owner's approval, a new `metamodel_version` and a migration.

## 1. The problem

SDEM's technology layer (A4) is ArchiMate's: nodes, devices, system software, networks, paths, deployments. It cannot say **where** each record is deployed — on premises or in the cloud, inside the internal network or in the internet-facing DMZ, inside a private network within it — nor that records in the same zone, or in connected zones, can reach each other. Today a zone is only a string attribute, `network_zone` (`restricted`, `dmz` …), on A3 components and A4 platforms, read by the organisation's patterns (PR-21…PR-31) and S37. A string cannot nest, cannot be checked against a structure, and does not place a deployment, a service or an environment at all.

## 2. The zone structure (the owner's, 2026-11-14)

```
 ┌─────────── Level 0 · Cloud ────────────────────────┐        ┌──── Level 0 · On premises ────────────┐
 │ ┌ Level 1 · Security / DMZ ┐  ┌ Level 1 · Internal ┐│◀──────▶│ ┌ Level 1 · Internal ─────────────────┐│
 │ │ API gateway              │──│ ┌ Level 2 · Payments││        │ │ Core ledger   ESB                   ││
 │ │ (internet facing)        │  │ │  private network  ││        │ └─────────────────────────────────────┘│
 │ └──────────────────────────┘  │ │ K8S prod, K8S UAT,││        └────────────────────────────────────────┘
 │                               │ │ PostgreSQL, Hub … ││
 │                               │ └───────────────────┘│
 │                               │ Messaging, Secrets   │
 │                               └──────────────────────┘│
 └─────────────────────────────────────────────────────┘
   zone ── zone : connected by the structure (never drawn record by record)
   shape ─▶ shape : the ArchiMate links, drawn directly only where a design needs them
```

| Level | Zones | Connected |
|---|---|---|
| **0 — deployment** | **on premises** and/or **cloud** | when a workspace has both, they are connected |
| **1 — network**, inside a level 0 | **internal** (always) and, optionally, **security / DMZ** — for internet-facing shapes (a web server, an API gateway). Firewalls are not shapes: they are the DMZ's boundary | the level-1 zones of one level 0 are connected |
| **2 — sub-network**, optional, inside a level 1 | e.g. the **payments private network** (`NET-PAY-PRIVATE` in payment-initiation) | to the level-1 zone it sits in |

**Every shape is in a zone** — at least a level-1 zone (internal or DMZ), or a level-2 zone inside one. Shapes are connected **indirectly, through their zones**. **Above the zones, the ArchiMate links** connect shapes directly where a design needs them (serving, flow, assignment …) — unchanged.

## 3. The model (proposed)

| # | What | How | Basis |
|---|---|---|---|
| M1 | **A zone is a record**: `A4.NetworkZone`, a specialisation of `A4.CommunicationNetwork` | so a zone is a network: impact through it (KG-Q-08) and nesting (RA4-27) work as they do | SDEM extension of ArchiMate's Communication Network |
| M2 | **What kind of zone**: `zone_level` 0, 1 or 2, and `zone_kind`: level 0 `on_premises` · `cloud`; level 1 `internal` · `dmz`; level 2 `private` | the owner's structure, §2 | SDEM |
| M2b | **Internet facing**: a boolean `internet_facing` on A4 shapes (SDEM's own — today only an example profile has `exposure`) | so LC-18 can check a DMZ | SDEM |
| M3 | **Zones nest**: a level-1 zone is part of a level 0, a level-2 zone part of a level 1 | composition (RA4-27, already allowed) | ArchiMate (network decomposition) |
| M4 | **A shape is placed in its zone**: the zone aggregates the shape — one innermost zone per shape | a new row, RA4-38: `A4.NetworkZone` aggregation `A4.InfrastructureComponent`; a shape not placed directly is in the zone of what hosts it (a deployment through its platform) | the owner's structure |
| M5 | **Zone connections are not records**: SDEM works them out from §2 — same level 0 → its level-1 zones are connected; on premises ↔ cloud when both exist; a level 2 ↔ its level 1 | nothing to draw or keep in step | the owner's structure |
| M6 | **The ArchiMate links** between shapes | unchanged | ArchiMate |
| M7 | **`network_zone` (the string)** is deprecated: a shape's zone kind is read from its zone. `sdem migrate` cannot invent zones, so it lists each value for the person to place (Z5) | — | — |

## 4. Checks (proposed ids)

| Id | Rule | Severity |
|---|---|---|
| LC-16 | every A4 shape is in exactly one zone of level 1 or 2 — directly, or through what hosts it | warning (Z4) |
| LC-17 | the structure holds: a level-1 zone is in a level 0, a level-2 zone in a level 1; each level 0 has one internal zone and at most one DMZ; at most one on-premises and one cloud level 0 | error — a level 0 with no internal zone yet is a warning (incomplete, not contradictory) |
| LC-18 | a shape with `internet_facing: true` (M2b) is in a DMZ; a DMZ holds only internet-facing shapes | warning |

## 5. Trace and impact (extends KG-Q-08)

A change to a zone reaches every shape in it (and in its level-2 zones), and through them what runs on them and up to A1, each hop labelled with its row (RA4-38). The connections of §2 are followed too: losing the link between on premises and cloud reaches the shapes whose ArchiMate links cross it.

## 6. What people see

The workbench and the DESNRE hero draw A4 as the structure: level-0 regions side by side, level-1 regions inside, level-2 inside those, every shape in its zone; the connections between zones as thick joins; the ArchiMate links between shapes on top. The hero's topology layout (2026-11-14) becomes this. `sdem diagram` and `sdem pattern draw` draw the same.

## 7. Decisions for the owner

| # | Question | Recommendation |
|---|---|---|
| Z1 | Placement (M4) by **aggregation** (the zone holds the shape), with RA4-37 (*a platform is connected to a network*, 0.9.0) kept for the ArchiMate view — or one mechanism only? | **aggregation for placement**; a platform placed in a zone counts as on that network for LC-15, so RA4-37 links stay valid but are no longer needed |
| Z2 | Which shapes must be placed: every A4 record, or not environments (they group deployments, they are not deployed)? | **every A4 record except environments** |
| Z3 | Do A3 components get a zone directly, or only through the A4 shapes they are deployed on? | **through their deployment** — one source of truth |
| Z4 | LC-16 a warning, or an error? | **warning**; an error for workspaces whose profile says `zones: required` |
| Z5 | `network_zone`: deprecate (M7)? | **yes** — the migration lists the values to place, never guesses |
| Z6 | Examples (made up): payment-initiation — cloud → internal → payments private network (both clusters, PostgreSQL, the deployments) and internal (messaging, secrets), and a DMZ for an API gateway; legacy-core-ledger — on premises → internal | **yes** |

Version: metamodel **0.10.0** — a new entity, one row (RA4-38), the `internet_facing` attribute, checks LC-16…LC-18, `network_zone` deprecated.

## 8. Decided alongside

The link type `COMPONENT_DEPLOYED_ON_INFRASTRUCTURE`, deprecated in 0.8.0, was removed in metamodel 0.9.0 as release 0.15.0 had scheduled (the owner, 2026-11-14).
