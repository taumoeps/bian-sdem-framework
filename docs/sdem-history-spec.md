# SDEM History — Specification

> **Status: built 2026-10-28; tested on two synthetic exports only** — Confluence's standard layout (`tests/fixtures/confluence-export-sample`) and a prepared layout with provenance files in the root, raw HTML and diagrams in `archives/` and sections as folders (`tests/fixtures/confluence-folder-export`). Requirements for [`sdem-history-design.md`](sdem-history-design.md). Each has an ID (HI-*), a status and its test.

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

## 3a. Any folder layout

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-L01 | Pages are found in any folder and format — HTML, Markdown, text, CSV; folder names act as section headings (leading numbers dropped, container folders left out) | built | `test_pages_found_in_any_folder_and_format` |
| HI-L02 | Files in the root that are not HTML pages are provenance (size, SHA-256); JSON and CSV lists matched to pages fill in page id, link, title, date, space | built | `test_root_files_are_provenance_and_fill_in_the_page` |
| HI-L03 | A diagram is linked to the page that refers to it, resolved from the page's folder (or by unique file name) | built | `test_diagram_the_html_refers_to_is_linked_to_its_page` |
| HI-L04 | A diagram no page refers to is read with its folder as context and listed for a person; names already found decide a shape's type before label words; label words match whole words | built | `test_unlinked_diagrams_are_read_with_their_folder` |
| HI-L05 | Pictures shown on a page, and pictures in folders no page shows, are listed for a person | built | `test_pictures_shown_or_not_go_to_a_person` |
| HI-I02 | `inspect` shows what each folder holds; `--anonymous` replaces folder names and leaves out headings and column names | built | `test_inspect_layout_and_anonymous` |

## 3b. PlantUML and pictures

| ID | Requirement | Status | Test |
|---|---|---|---|
| HI-P01 | PlantUML is read from its source in every form: `.puml`/`.plantuml`/`.pu`/`.iuml`/`.wsd` files, `@startuml` blocks in HTML code blocks, Markdown fenced blocks and text files, PNG `plantuml` text chunks, SVG `plantuml-src` (PlantUML's encoding) and SVG comments | built | `test_plantuml_in_every_form` |
| HI-P02 | Element keywords, C4 macros and ArchiMate stereotypes/macros give the type (`plantuml_types` in the rules); boundaries and packages are groups; arrows (direction from the arrow head), `Rel(…)` and `Rel_<Kind>(…)` give links; nesting gives part-of or deployed-on; between architectures, only nesting or "runs on / hosted on" wording suggests a deployment | built | `test_plantuml_relations_and_nesting` |
| HI-P03 | Sequence diagrams (participants, messages, alt/loop blocks), short forms (`[A]`, `() I`, `:A:`), and other diagram kinds reported, not read | built | `test_plantuml_parser_notations` |
| HI-O04 | Pictures' text is read on the machine — macOS Vision (built in) or Tesseract; `--ocr auto|vision|tesseract|off`; SVG text read exactly; no network | built | `test_macos_vision_reads_the_whiteboard`, `test_tesseract_tsv`, `test_svg_text_is_read_without_ocr` |
| HI-O05 | Stacked lines are one label; small-letter captions, short or long text and low OCR confidence are skipped; a label becomes a candidate (low) only when a name found, a label word or the section decides its type; the picture is always listed for a person with the labels read | built | `test_grouping_and_filters`, `test_stand_in_engine_makes_low_candidates_and_a_review_item` |

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
