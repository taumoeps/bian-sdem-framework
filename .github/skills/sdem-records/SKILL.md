---
name: sdem-records
description: How SDEM architecture records are written — the fields every record needs, and the attributes that let the rules engine link A1 business, A2 BIAN, A3 application and A4 technology records. Use when creating or editing records in a1-business.json, a2-service-domain.json, a3-application.json or a4-technology.json, or when `sdem check` reports a record error.
---

# SDEM records

Every record in an architecture dataset (`instances` list) has:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | unique across the estate; never `PRJ-` or `DSN-` (those are plans) |
| `type` | yes | `A1.…`, `A2.…`, `A3.…` or `A4.…` — the entity types are in `metamodel/a1-business.json` … `a4-technology.json` |
| `version` | yes | approved links point to a record's version |
| `name` | yes | plain language |
| `lifecycle_status` | no | `planned`, `active`, `deprecated`, `retired` |
| `description` | no | what the engine reads when names are not enough |
| `attributes` | depends on type | required attributes per type are checked by `sdem check` (rule LC-04) |

Links **inside** a layer go in the dataset's `relationships` list: `{"source": "…", "kind": "composition", "target": "…"}`; which kinds are allowed between which types is in `metamodel/level-relationships.json`.

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

Example records to copy: `examples/payment-initiation/` (the user guide §6.2 explains two of them).

`sdem check <estate>/a*.json <estate>/mappings.json` names any missing field as `$.instances[N]: missing required property '…'` — `N` counts from 0.
