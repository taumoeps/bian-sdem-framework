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

Links **inside** a layer go in the dataset's `relationships` list: `{"source": "…", "kind": "composition", "target": "…"}`; which kinds are allowed between which types is in [`metamodel/level-relationships.json`](https://github.com/taumoeps/bian-sdem-framework/blob/v0.18.0/metamodel/level-relationships.json).

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

## Records imported from past designs (`HIS-` ids)

Records loaded from a Confluence export (`sdem transform` → `sdem load`) have ids `HIS-<layer>-<NAME>` and `attributes.source_id` = `confluence:<page ids>`. They are real records once loaded — change them through change sets like any other — but they were **read from a document**: links the engine proposes for them are capped at low (DEC-E-11). The transform's own output folder holds **candidates**, not data: never copy from it into a dataset, and a graph store refuses it (CTL-23). Skill **sdem-onboard-designs**.

Example records to copy: [`examples/payment-initiation/`](https://github.com/taumoeps/bian-sdem-framework/tree/v0.18.0/examples/payment-initiation) (the user guide §6.2 explains two of them).

`sdem check --workspace <workspace>` names any missing field as `$.instances[N]: missing required property '…'` — `N` counts from 0.
