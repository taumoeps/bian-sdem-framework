# SDEM Load — Specification

> **Status: approved 2026-10-28; built 2026-10-28.** Requirements for [`sdem-load-design.md`](sdem-load-design.md). Each has an ID (LD-*), a status and its test (`tests/test_load.py` unless named).

| ID | Requirement | Status | Test |
|---|---|---|---|
| LD-G01 | `sdem load CANDIDATES --estate DIR --person NAME (--all \| --only ID… \| --exclude ID… \| --keep FILE) [--a2 FILE] [--dry-run] [--json]`; exit 0 loaded, 1 refused, 2 usage | built | `test_cli` |
| LD-G02 | The source must be a transform output (`extraction.json`, datasets marked `CONFLUENCE-EXTRACT`); otherwise refused | built | `test_refuses_a_folder_that_is_not_a_transform_output` |
| LD-S01 | One selection option is required; unknown ids are refused | built | `test_selection_is_required_and_checked` |
| LD-S02 | A link inside an architecture is loaded only when both ends are; `deployed_on` references to entities not loaded are dropped; everything dropped is listed | built | `test_links_follow_the_selection` |
| LD-M01 | An entity already in the estate with the same content is skipped; with different content the load is refused and nothing is written | built | `test_same_content_skipped_different_refused` |
| LD-M02 | A dataset the estate lacks is created (`model_id` `<estate>-<A>`, `source_system` `SDEM-LOAD`); an estate folder that does not exist is created with an empty registry | built | `test_loads_into_a_new_estate` |
| LD-C01 | The whole estate as it would be is checked before writing; any error → nothing written | built | `test_check_failure_writes_nothing` |
| LD-C02 | The person is a person — never an agent or tool name (CTL-21 list) | built | `test_person_must_be_a_person` |
| LD-R01 | Each load writes `<estate>/loads/LOAD-<n>.json`: person, time, transform run (export and rules fingerprints), loaded, excluded, dropped, A2 added, check | built | `test_loads_into_a_new_estate` |
| LD-A01 | `--a2 FILE` copies an A2 dataset into an estate that has none (checked; never edited); an estate that has one keeps it | built | `test_a2_dataset_added_once` |
| LD-B01 | The transform's BIAN mentions are printed as hints for `sdem link` | built | `test_cli` |
| LD-D01 | `--dry-run` checks and reports, writes nothing | built | `test_dry_run_writes_nothing` |
| LD-X01 | **CTL-23**: `sdem build` refuses a dataset marked `CONFLUENCE-EXTRACT` | built | `test_build_refuses_candidates` |
| LD-E01 | **DEC-E-11**: the engine caps at low any proposal touching an entity whose `source_id` starts `confluence:`, saying so in the rationale | built | `test_engine_caps_document_derived_links` |
| HI-R06 | Transform: a candidate "deployed on" (nesting, or "runs on / hosted on") from an A3 component to an A4 node is written as the component's `deployed_on` attribute | built | `tests/test_transform.py::test_deployed_on_written_as_data` |
| HI-O01 | Transform subcommand renamed `sdem transform run` (was `extract`) | built | `tests/test_transform.py::test_cli` |

## Acceptance — end to end

| ID | Test | Automated? |
|---|---|---|
| AT-LD-01 | transform the folder sample → load it (excluding the OCR misread and the entity that fails the check) → `sdem link` proposes Clearing Gateway DEPLOYED_ON PAYAPP01 **at low** → approve → `sdem build` accepts → `sdem trace` shows the link | yes — `test_end_to_end_transform_load_link_approve_build` |
