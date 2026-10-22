# SDMM data architecture (v0.4)

Four kinds of data, three owners, one graph.

| Data | Owner | Format | Held in |
|---|---|---|---|
| **Entity catalogue** — the 41 core entities (+3 artefacts) of the A1–A4 vocabulary, with hierarchy and public-standard provenance | SDMM | `metamodel/entity.schema.json` | `metamodel/a1…a4-*.json` |
| **Within-level relationship catalogue** — the kinds a level model may use; BIAN's A2 structure as fixed constraints | SDMM | — | `metamodel/level-relationships.json` |
| **Level model exports** — an institution's instances and within-level relationships for one design model | the institution | `schema/level-model.schema.json` | the institution's repository (synthetic copies in `examples/`) |
| **Mapping documents** — the cross-level arrows between instances | the institution's architects | `schema/mapping.schema.json` | the institution's repository |

## Level model export

```jsonc
{
  "level": "A3", "model_id": "bank-a3", "model_version": "2026.10", "metamodel_version": "0.4.0",
  "source_system": "APM-TOOL",
  "instances": [
    { "id": "APP-FRAUD-ENGINE", "type": "A3.ApplicationComponent", "version": "4.2", "name": "Fraud Engine",
      "lifecycle_status": "active", "attributes": { "vendor": "in-house" } }
  ],
  "relationships": [
    { "source": "APP-FRAUD-ENGINE", "kind": "composition", "target": "CMP-SCORING" }
  ]
}
```

Rules enforced by `sdmm-graph check`: every instance `type` is a **concrete** entity of the file's level (abstract and artefact entities are rejected); `(id, version)` is unique; every relationship joins two instances in the same file using a catalogued kind; A2 relationships must match a BIAN-structure constraint row.

## Local and federated graphs

A **local graph** is one level export, validated. A **federated graph** is up to four local graphs plus any number of mapping documents, joined on instance id. `FederatedGraph` is also the validator's `EntityResolver`: a mapping endpoint resolves when an instance with that id and version exists in the level its entity prefix names, and the instance's concrete entity *is-a* the referenced entity. So a mapping written to `A4.InfrastructureComponent` resolves against an `A4.SystemSoftware` instance, and a mapping written with a legacy prefix resolves through the registry alias.

```bash
sdmm-graph check  a1.json a2.json a3.json a4.json mappings.json   # levels, then mappings resolved against them
sdmm-graph trace  CAP-310 --direction down <files>                  # chain with names and concrete entities
sdmm-graph impact INF-CLOUD-K8S-PROD --change rehost <files>        # structural impact classification
sdmm-graph stats  <files>
```

Files are classified by content (a level export has `level` + `instances`; a mapping document has `mappings`), so they may be passed in any order.

## Impact classification

Rules live in `schema/impact-rules.json` (owner, version, rationale per kind) and are loaded at run time; change them there, not in code. `impact` declares a change of one **kind** to one instance and classifies every reachable instance by its structural relation to it. `up` means *depends on the changed instance* (toward A1); `down` means *the changed instance depends on it* (toward A4). Anything not listed is `no_impact`.

| Change kind | Meaning | self | up1 (direct dependents) | up2+ | down1 | down2+ |
|---|---|---|---|---|---|---|
| `modify` | internal change, interfaces unchanged | design_change_required | review_required | no_impact | review_required | no_impact |
| `replace` | same role, new instance | design_change_required | design_change_required | review_required | review_required | no_impact |
| `retire` | instance removed | design_change_required | design_change_required | review_required | review_required | no_impact |
| `rehost` | hosting changes only (A4) | design_change_required | design_change_required | no_impact | no_impact | no_impact |

For `replace`, `retire` and `rehost` the result also lists the **mappings that touch the changed instance** — those are the records that must be superseded (never edited) once the change is approved.

The classification is **structural**: it follows arrows and applies the table. It does not know what the change means. An architect confirms every `design_change_required` and `review_required` before anything is redesigned, exactly as the design specification's §8 requires.

## What this is not

- Not a persistent store: graphs are built in memory from files on each run. A database adapter would load the same files.
- Not a UI.
- Not semantic: nothing here proposes, judges or assesses a mapping.
