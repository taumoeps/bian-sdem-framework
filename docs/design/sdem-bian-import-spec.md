# BIAN import — specification

> **Status: proposed 2026-10-29**, for the owner's approval, with the design [`sdem-bian-import-design.md`](sdem-bian-import-design.md). Each requirement has an id (BI-*), what it requires, and how it is accepted. Requirements marked *(BI-Dn)* follow the recommended option of that decision and change if the owner chooses another.

## Inputs and command

| ID | Requirement | Accepted by |
|---|---|---|
| BI-C01 | `sdem bian list <folder>` lists the service domains in a BIAN release folder — name, operations, control record — and the release; it writes nothing. | test on the made-up release |
| BI-C02 | `sdem bian import <folder> -o <file>` writes one A2 dataset for the chosen service domains, and a report beside it (`<file>.report.md`). | test |
| BI-C03 | The folder is read from disk only; SDEM makes no network call. | `test_no_mcp_no_ai_client` extended to `sdem/bian.py` |
| BI-C04 | Accepted inputs: OpenAPI 3 YAML (releases 10–14) and Swagger 2 JSON (release 9.1). Anything else is refused with a message naming the file. *(BI-D1)* | tests, good and bad files |
| BI-C05 | The YAML reader reads only: `info.title`, `info.version`, `info.description`, each operation's path, method, `operationId` and tags, and the names under `components.schemas`. A file whose structure it does not recognise is refused, not guessed. *(BI-D1)* | test with a malformed file |
| BI-C06 | Selection: `--only <names…>`, `--from <file>` (one name per line), or `--all`; with none of these the command refuses and points to `sdem bian list`. A name not in the release is an error listing the closest names. *(BI-D5)* | tests |

## What is written

| ID | Requirement | Accepted by |
|---|---|---|
| BI-W01 | Per service domain: one `A2.ServiceDomain` (name; `canonical_id` = BIAN's name; `bian_release`), its `A2.ServiceOperation`s (action term from `operationId`, method, path), its `A2.ControlRecord` (from the `CR -` tag) and `A2.BehaviorQualifier`s (from `BQ -` tags), with the links inside A2 the rulebook defines between them. | test: records and links as expected for the made-up release |
| BI-W02 | Every service domain names an `A2.AssetType` and an `A2.FunctionalPattern` (required by the rulebook). By default they are derived from the control record's name — asset type + generic artefact; the generic artefact gives the functional pattern — and marked `derived`, confidence *medium*. `--patterns <file>` (CSV: service domain, asset type, functional pattern) overrides. A name that cannot be derived is an error naming the domain and pointing to `--patterns`. *(BI-D2)* | tests: derived, overridden, underivable |
| BI-W03 | Descriptions only with `--descriptions`; otherwise records have no BIAN description text. *(BI-D3)* | test |
| BI-W04 | `A2.BusinessObject` records from the schemas only with `--objects`. *(BI-D4)* | test |
| BI-W05 | Every record carries its provenance: `source_system` `BIAN-SEMANTIC-API-<release>`, the source file, and how each value was obtained (`read`, `derived`, `table`). | test |
| BI-W06 | Ids are stable: the same BIAN name always gives the same id (`SD-<NAME>`, `SO-<NAME>-<ACTION>…`), so a re-import never orphans an approved link. | test: import twice, same ids |
| BI-W07 | The dataset is checked against the rulebook before anything is written; on any error nothing is written (all-or-nothing). Advice (`WARN`) is reported, not fatal. | test: a forced error writes nothing |

## Re-import and report

| ID | Requirement | Accepted by |
|---|---|---|
| BI-R01 | With `--previous <file>`, the report lists what was added, renamed or dropped against the previous A2 dataset; a dropped record is reported, never deleted from the estate. | test |
| BI-R02 | The report lists: the release; every record and its source file; every derived asset type and functional pattern for a person to confirm; anything in the files that was not read. | test |

## Documentation

| ID | Requirement | Accepted by |
|---|---|---|
| BI-U01 | The onboarding workflow's *Your BIAN (A2) layer* shows `sdem bian list` / `import` as the first way to get the layer; the command reference (user guide §7) lists both. | doc tests (links, drift) |
| BI-U02 | A made-up BIAN-shaped release (no BIAN text) is in `tests/fixtures/`; the public repository holds no BIAN content. | review |

## Open before building

- Check the generic-artefact → functional-pattern list (BI-W02) against BIAN's published material, and record its source.
- Run the reader against a real downloaded release (all 259 files of 14.0.0, and 9.1 JSON) on the maintainer's machine; every file must be read or refused with a reason. Not committed.
