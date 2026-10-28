# Renamed from SDMM

In v0.7.0 the project was renamed from **SDMM (BIAN Service Domain Mapping Model)** to **SDEM (Service Domain Enterprise Metamodel)**, and its terms aligned with model-driven enterprise architecture. Behaviour and data are unchanged. **The compatibility layer below — the `sdmm` package, the `sdmm-*` commands, the `MappingEngine` name, the old schema path and the old enum values — is removed in v0.8.0.**

| Before | Now |
|---|---|
| Python package `sdmm` | `sdem` (`sdmm` still imports, with a deprecation warning, in v0.7) |
| Commands `sdmm-*`, `sdmm-engine` | `sdem-*`, `sdem-infer` (`sdmm-*` still installed in v0.7) |
| `sdmm/engine.py`, `MappingEngine` | `sdem/inference.py`, `RelationshipInferenceEngine` (old class name kept as an alias) |
| `schema/mapping.schema.json` | `schema/relationship-registry.schema.json` (old path kept as a deprecated copy) |
| `metamodel/new-mappings.json` | `metamodel/relationship-rules.json` |
| mapping set / mapping document | Architecture Relationship Registry |
| mapping model (the rules) | Architecture Relationship Rules Model |
| registry (the nine relationship types) | relationship type catalogue, part of the Architecture Metamodel |
| mapping engine | Architecture Relationship Inference Engine |
| local / federated graph | local / federated architecture knowledge graph |
| `sdmm_extension`, `sdmm_definition`, `sdmm_reading`, `sdmm_rule` | `sdem_*` (old values still accepted) |

**Not renamed:** the registry's record fields `mappings`, `mapping_id`, `previous_mapping_id` and the catalogue's `mapping_type_id`, `registry_version`, because they sit inside immutable approved records (see [`relationship-registry-spec.md`](relationship-registry-spec.md) §7); file names such as `mappings.json` and `official-mappings.json` (BIAN's own mappings); and historical test logs and results, which record what ran under the old name. The GitHub repository was renamed from `bian-sdmm-framework` to `bian-sdem-framework`; the old URL redirects.


> Moved from the README on 2026-10-28. The project has been SDEM since v0.7.0.
