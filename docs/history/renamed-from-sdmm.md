# Renamed from SDMM

In v0.7.0 the project was renamed from **SDMM (BIAN Service Domain Mapping Model)** to **SDEM (Service Domain Enterprise Metamodel)**, and its terms aligned with model-driven enterprise architecture. Behaviour and data are unchanged. **The compatibility layer — the `sdmm` package, the `sdmm-*` commands, the `MappingEngine` name and the old schema path — was removed in the 2026-10-29 audit; the old enum values (`sdmm_extension` …) go with the 0.8 baseline, as they are part of the rulebook.** Commands are now one: `sdem <verb>` (`sdem-infer` → `sdem link`, `sdem-graph check` → `sdem check`, and so on).

| Before | Now |
|---|---|
| Python package `sdmm` | `sdem` |
| Commands `sdmm-*`, `sdmm-engine` | `sdem <verb>` (`sdem link`, `sdem check` …) |
| `sdmm/engine.py`, `MappingEngine` | `sdem/inference.py`, `RelationshipInferenceEngine` |
| `schema/mapping.schema.json` | `schema/relationship-registry.schema.json` |
| `metamodel/new-mappings.json` | `metamodel/relationship-rules.json` |
| mapping set / mapping document | Architecture Relationship Registry |
| mapping model (the rules) | Architecture Relationship Rules Model |
| registry (the nine relationship types) | relationship type catalogue, part of the Architecture Metamodel |
| mapping engine | Architecture Relationship Inference Engine |
| local / federated graph | local / federated architecture knowledge graph |
| export, level export, level model (one architecture's records) | architecture dataset (renamed 2026-10-27) |
| executor | Architecture Relationship Inference Engine |
| plan, new mappings | Architecture Relationship Rules Model |
| `sdmm_extension`, `sdmm_definition`, `sdmm_reading`, `sdmm_rule` | `sdem_*` (old values still accepted until the 0.8 baseline) |

**Not renamed:** the registry's record fields `mappings`, `mapping_id`, `previous_mapping_id` and the catalogue's `mapping_type_id`, `registry_version`, because they sit inside immutable approved records (see [`relationship-registry-spec.md`](../design/relationship-registry-spec.md) §7); file names such as `mappings.json` and `official-mappings.json` (BIAN's own mappings); and historical test logs and results, which record what ran under the old name. The GitHub repository was renamed from `bian-sdmm-framework` to `bian-sdem-framework`; the old URL redirects.


> Moved from the README on 2026-10-28. The project has been SDEM since v0.7.0.
