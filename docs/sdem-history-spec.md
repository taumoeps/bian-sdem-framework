# SDEM History — Specification

> **Status: built 2026-10-28; tested on the synthetic export `tests/fixtures/confluence-export-sample` only.** Requirements for [`sdem-history-design.md`](sdem-history-design.md). Each has an ID (HI-*), a status and its test.

## 1. General

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-G01 | Rules only: no AI, no network, Python standard library only; runs offline on a locked-down machine | built | `test_no_ai_no_network` |
| HI-G02 | Every word, shape, colour, phrase and confidence cap is in `metamodel/history-rules.json`; `--rules FILE` uses a copy; no code change needed to tune | built | `test_rules_file_tunes_without_code` |
| HI-G03 | The same export and rules give the same output | built | `test_deterministic` |
| HI-G04 | Exit codes: 0 done, 2 the folder is missing or holds no pages | built | `test_cli` |

## 2. Inspect

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-I01 | `sdem history inspect EXPORT [--rules] [--json]`: pages, tables (column headings → rule, or "no rule" / "not read"), diagram shapes (draw.io shape → type, or "unclassified"), headings (→ architecture), items for a person — structure only, no records written | built | `test_inspect_shows_structure` |

## 3. Reading

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-R01 | Tables: the heading row chooses the type (HT-*); description, lifecycle and attribute columns are read; source/target tables (HL-*) give links | built | `test_tables_become_records` |
| HI-R02 | draw.io: every attachment of a page is tested by content — XML (`<mxfile>`, `<mxGraphModel>`), compressed diagrams, PNG `mxfile` text chunks, SVG `content` — whatever its file name; ArchiMate shapes (HD-*), then fill colour, label words, shape words, known names, the heading's architecture | built | `test_every_kind_of_drawio_file_is_read` |
| HI-R03 | Lines become relationships of a kind the rulebook allows (else association); a phrase on the line chooses the kind; a shape inside another is part of it, or deployed on it across architectures; lines between architectures become candidates with their SDEM link type, merged by source, target and type | built | `test_lines_and_containment` |
| HI-R04 | Narrative: only known names (found in the export or `--known`); phrases between two names (HP-*) give links; text never creates records; a name equal to an existing record is flagged `same_as_existing` | built | `test_narrative_uses_known_names_only` |
| HI-R05 | Pasted pictures (not draw.io, not a draw.io preview, not an icon or emoticon) and shapes no rule types are listed for a person | built | `test_pictures_and_unknown_shapes_go_to_a_person` |

## 4. Candidates

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-C01 | Every record and link is a candidate with its sources: page, place, rule, confidence, reasoning | built | `test_candidates_never_above_medium_and_carry_their_source` |
| HI-C02 | Confidence never above medium | built | same |
| HI-C03 | The candidate datasets pass `sdem check` (schema, types, within-architecture rules); `version` = page date; `source_id` = `confluence:<pages>`; `source_system` = `CONFLUENCE-EXTRACT` | built | `test_candidate_datasets_pass_sdem_check` |

## 5. Outputs

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-O01 | `sdem history extract EXPORT -o OUT [--rules] [--known …] [--model-id] [--json]` writes the candidate datasets, `extraction.json`, `design-index.json`, `extraction-report.md` | built | `test_cli` |
| HI-O02 | `design-index.json`: every page — id, title, space, breadcrumb, file, last modified, its records, existing records mentioned, diagrams, pictures | built | `test_design_index_and_report` |
| HI-O03 | `extraction-report.md`: summary, check, records, links inside, candidate links between architectures, items for a person, designs, next steps | built | same |

## 6. Acceptance on the work machine (owner)

| ID | Test |
|---|---|
| AT-HI-01 | `inspect` on the real export finds every page and every draw.io diagram (count against Confluence) |
| AT-HI-02 | After tuning the rules, a sample of 20 extracted records checked against their pages: wrong types and wrong names counted and written down (no content) |
| AT-HI-03 | Every pasted picture on the sampled pages appears in "For a person" |
