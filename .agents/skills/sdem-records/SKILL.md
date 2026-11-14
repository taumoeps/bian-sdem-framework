---
name: sdem-records
description: How SDEM architecture records are written — the fields every record needs, and the attributes that let the rules engine link A1 business, A2 BIAN, A3 application and A4 technology records. Use when creating or editing records in a1-business.json, a2-service-domain.json, a3-application.json or a4-technology.json, or when `sdem check` reports a record error.
---

# SDEM records

If the workspace has `sdem-profile.json`, the organisation's own types (`BANK.A3.…`), attributes, required fields and names apply on top of SDEM's — `sdem profile show --workspace <dir>` lists them, and `sdem check` enforces them. A profile may add layers above A1 or below A4 (e.g. `a0-strategy.json`, `a5-physical.json`) with their own types; their records follow the same fields.

Every record in an architecture dataset (`instances` list) has:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | unique across the workspace; never `PRJ-` or `DSN-` (those are plans) |
| `type` | yes | `A1.…`, `A2.…`, `A3.…` or `A4.…` — the entity types are in [`metamodel/a1-business.json`](https://github.com/taumoeps/bian-sdem-framework/blob/v0.18.0/metamodel/a1-business.json) … `a4-technology.json` |
| `version` | yes | approved links point to a record's version |
| `name` | yes | plain language |
| `lifecycle_status` | no | `planned`, `active`, `deprecated`, `retired` |
| `description` | no | what the engine reads when names are not enough |
| `attributes` | depends on type | required attributes per type are checked by `sdem check` (rule LC-04) |

**A value nobody knows is left out — never a placeholder.** `sdem check` reads `TBD`, `unknown`, `?`, a path such as `/TBD`, or an empty string as *missing* (LC-04): an error on an `active` record. Leave the attribute out and mark the record `planned` until the value is known; `sdem handback` lists every value still missing. An empty list (`[]`) means *none* and is a value.

**Where it came from:** a record cites its source in `attributes.source_id` (`document:<file>#<section>`, `confluence:<page>`); a value that came from another section or document cites it in `attributes.sources` (`{"integration_type": "document:DESIGN.md#4.2"}`, CA-13, checked by LC-14); a link cites its source in its own `source_id`.

Links **inside** a layer go in the dataset's `relationships` list: `{"source": "…", "kind": "composition", "target": "…", "source_id": "document:DESIGN.md#4"}` (`source_id` optional); which kinds are allowed between which types is in [`metamodel/level-relationships.json`](https://github.com/taumoeps/bian-sdem-framework/blob/v0.18.0/metamodel/level-relationships.json).

## Before you write

- `sdem types <layer or type> --workspace <dir> --json` lists every kind of record, its fields (type, required, allowed values) and the links it may have — your organisation's profile included. Use only what it lists; a value outside `allowed_values` is refused (LC-06), an unlisted field is warned about.
- `sdem bian search <words> --json` finds the BIAN service domains and operations for plain words, with the `SO-…` ids to put in a process's or activity's `invokes`.
- `sdem types requirement` gives the requirements registry's format; `sdem types change-set` the change-set format.

## Attributes the rules engine links from

Give these and the engine (`sdem link`) can propose the cross-layer links with high confidence; without them it falls back to names (low confidence).

| Layer | Attribute | Lets the engine link |
|---|---|---|
| A1 process / activity | `invokes`: the BIAN service operation ids it uses | process **USES_DOMAIN** domain; capability **SUPPORTED_BY** domain |
| A1 business object | `attributes`: its data items | **ALIGNED_TO** a BIAN business object |
| A3 API operation | `method`, `path`, `payload_fields` | BIAN operation **IMPLEMENTED_BY** API (BIAN REST mapping) |
| A3 component | `deployed_on`, `deployed_as` | **DEPLOYED_ON** platform, **DEPLOYED_AS** deployment |
| A3 data entity | `attributes`: its data items | BIAN business object **MAPPED_TO** entity |
| A4 platform | `hosts`: the applications it runs | **DEPLOYED_ON** |
| A4 deployment | `component_id`, `environment_id`, `platform_id` | **DEPLOYED_AS** |

## A4 is the physical deployment: zones and connections

Every A4 shape sits in a network zone and is connected inside A4 — `sdem check` warns otherwise (LC-15, LC-16, LC-21, LC-22).

- **Zones** are `A4.NetworkZone` records — an ArchiMate Grouping, not a network: `zone_level` 0 (`zone_kind` `cloud` or `on_premises`), 1 (`internal` or `dmz`), 2 (`private`). A zone is part of the one above by `composition` (zone → zone, RA4-39); a zone holds a shape by `aggregation` (zone → shape, RA4-38). A network is its own `A4.CommunicationNetwork` record that platforms are associated with (RA4-37) — never put a network's attributes (an address range) on a zone. A shape a platform runs (a deployment, an artifact) is in its platform's zone — do not place it again.
- **Internet facing**: `internet_facing: true` on an A4 shape puts it in a DMZ (LC-18). On an A3 interface it means it is reached from the internet: it needs an `EXPOSED_THROUGH` connection to the edge platform (LC-22) — proposed by `sdem aid`, approved by a person with `network_design` evidence, never written by hand.
- **Connected inside A4** (another layer does not count): a deployment is assigned from the platform in its `platform_id`; a platform is on a network (`association`, RA4-37) or in a zone; a database is associated from the platforms that use it; a technology service serves the platforms it is for; an edge platform is associated with the deployment it fronts.
- **Zone connections are worked out, never recorded** (ZC-01…ZC-04): `sdem zones --workspace <dir>` lists them; `sdem zones path <a> <b>` shows how two shapes reach each other.
- **Let SDEM propose, a person decides**: `sdem aid` proposes a zone for each shape (AID-Z01…Z04, from the hosting evidence — cloud first unless the record says otherwise) and the A4 links a shape lacks (AID-C01…C06), each marked inferred with what it read; the person confirms or rejects them by the shape's id: `sdem aid confirm|reject <shape> --workspace <dir> --person <person>`. Say in a record's name or description what decides its hosting (a site, "on premises", a cloud provider) so the proposal is right.
- **See it**: `sdem zones --layout --workspace <dir>` (the deployment-zones viewpoint — zones as regions, every shape in its zone); `sdem view --graph <dir>/graph` draws A4 the same way.

## Records imported from past designs (`HIS-` ids)

Records loaded from a Confluence export (`sdem transform` → `sdem load`) have ids `HIS-<layer>-<NAME>` and `attributes.source_id` = `confluence:<page ids>`. They are real records once loaded — change them through change sets like any other — but they were **read from a document**: links the engine proposes for them are capped at low (DEC-E-11). The transform's own output folder holds **candidates**, not data: never copy from it into a dataset, and a graph store refuses it (CTL-23). Skill **sdem-onboard-designs**.

Example records to copy: [`examples/payment-initiation/`](https://github.com/taumoeps/bian-sdem-framework/tree/v0.18.0/examples/payment-initiation) (the user guide §6.2 explains two of them).

`sdem check --workspace <workspace>` names any missing field as `$.instances[N]: missing required property '…'` — `N` counts from 0.
