# SDEM — Graph Store Specification (local, JSON)

> **Status: approved and built, 2026-10-25.** Requirements for the local JSON graph store described in [`graph-store-design.md`](graph-store-design.md). Each requirement has an ID (GS-*), says what it satisfies in [`knowledge-graph-spec.md`](knowledge-graph-spec.md) (KG-*), and how it is accepted. All requirements are built. Acceptance tests AT-01…AT-10 run in `tests/test_store.py`; AT-11 in `scripts/store_perf.py` (CI) — 10,000 records and 16,125 links built in 0.6 s, opened in 0.04 s (the synthetic estate has no cross-level links, so trace timing is not yet representative). AT-10's interaction was checked in headless Chrome; a second browser is still to be checked by hand.

## 1. Scope

**In scope:** persisting the four local knowledge graphs and the federated graph of approved links as JSON files on the local device; building them from checked exports and the Relationship Registry; a single read interface (the graph access layer); queries over the stored files; baselines; a self-contained HTML view.

**Out of scope:** adapters from source tools (ingestion, v0.10); change detection and refresh triggers (v0.11); a database server or multi-user editing (later, behind the same interface); proposing links (the inference engine, v0.9 — a *consumer* of the store).

**Normative references:** JSON Graph Format v2 (`https://github.com/jsongraph/json-graph-specification`, schema `json-graph-schema_v2.json`, `$id` `http://jsongraphformat.info/v2.1/json-graph-schema.json`, MIT licence; checked 2026-10-25); SDEM level export schema (`schema/level-model.schema.json`); Relationship Registry schema (`schema/relationship-registry.schema.json`); SDEM logical rules LC-01…LC-13 (`logical-data-model.md`).

## 2. File set

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-F-01 | A store is one directory holding exactly: `a1-business.graph.json`, `a2-service-domain.graph.json`, `a3-application.graph.json`, `a4-technology.graph.json`, `federated.graph.json`, `load-record.json`; optionally `baselines/<name>/` and `view.html`. A level with no export has no file. | DEC-03 | AT-01 |
| GS-F-02 | Every `*.graph.json` file is a valid JGF v2 document with a single top-level `graph` object (edge-based variant; no hyperedges), `directed: true`. | DEC-01 | AT-02 |
| GS-F-03 | Every `*.graph.json` file also conforms to the **SDEM profile** `schema/graph-store.schema.json` (§3–§5), which constrains `metadata` only and never contradicts JGF. | — | AT-02 |
| GS-F-04 | Output is deterministic: identical inputs produce byte-identical graph files — UTF-8, LF line endings, two-space indent, fields in a fixed order, nodes and edges in the order of the export or registry they came from (so every reader sees records in the source's order and answers stay identical). Graph files contain no build timestamps. | KG-V-01 | AT-06 |

## 3. Graph-level metadata

| ID | Requirement | Acceptance |
|---|---|---|
| GS-G-01 | Each graph has `id` (`sdem:<model_id>` for a local graph; `sdem:federated:<registry id or file stem>` for the federated graph), `type` (`sdem.local` or `sdem.federated`), `label` (human-readable). | AT-02 |
| GS-G-02 | `metadata` holds: `sdem_store_version` (`"1.0"`), `metamodel_version`, and for a local graph `level`, `model_id`, `model_version`, `source_system`, `export_sha256`; for the federated graph `registry_version`, `registry_sha256`, `levels` (the level → `model_version` map of the local graphs it joins) and `statuses` (the edge statuses included; default `["approved"]`). | AT-02, AT-03 |

## 4. Nodes

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-N-01 | Every export instance becomes one node in its level's file, keyed `<level>:<id>@<version>` (e.g. `A1:PRC-PAY-01@1.0`). Keys are unique across the store. | KG-I-01 | AT-01, AT-03 |
| GS-N-02 | `label` = the instance `name`. `metadata` = `level`, `type`, `id`, `version`, and every other core field present in the export (`lifecycle_status`, `canonical_id`, `description`, `definition_uri`) plus `attributes` copied unchanged. Nothing is added, renamed or dropped. | KG-I-03, KG-I-04 | AT-03 (round trip) |
| GS-N-03 | The federated file has a **stub node** for every edge end: `label`, and `metadata` = `level`, `type`, `id`, `version`, `stub: true`, `graph` (the local file holding the full node). | — | AT-02 |

## 5. Edges

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-E-01 | Every within-level relationship of an export becomes one edge in its level's file: `source`/`target` = node keys, `relation` = the relationship `kind`, `id` = `<level>:<source id>-<kind>-<target id>` (suffixed `#2`, `#3` … when repeated), `label` = the relationship `name` if present. `metadata` = `scope: "within-level"` and `row` = the ID of the within-level row that allowed it (or `"association"`). | KG-L-02 | AT-03 |
| GS-E-02 | Every registry record whose `status` is in the federated graph's `statuses` (default: approved only) becomes one edge in the federated file: `id` = `mapping_id`, `relation` = `relationship`, `source`/`target` = node keys from the record's ends (id and version as recorded), `metadata` = `scope: "cross-level"` plus every other field of the record unchanged. | KG-V-03 | AT-03 |
| GS-E-03 | An approved record whose end does not resolve to a node fails the build (it would already fail `sdem-graph check`). | LC-11 | AT-05 |

## 6. Build

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-B-01 | `sdem-graph build <exports…> <registry…> --out <dir>` reads the inputs, runs every check `sdem-graph check` runs (entity typing, within-level rows, data-model conformance LC-04…LC-13, registry validation, resolution), and writes the store only if there are **no errors**. Warnings are recorded, not fatal. | KG-L-01…03 | AT-01, AT-05 |
| GS-B-02 | On any error the existing graph files are left untouched; a `rejected` entry listing every error is appended to `load-record.json`; exit code 1. | KG-L-03, KG-R-03 | AT-05 |
| GS-B-03 | Files are written to a temporary directory and moved into place only when all are complete, so a crash never leaves a half-written store. | KG-R-03 | AT-05 |
| GS-B-04 | Rebuilds are full; a build of unchanged inputs changes no graph file (only a new load-record entry). | KG-R-02 | AT-06 |
| GS-B-05 | `--check` builds in memory and compares with the stored files; exit 1 if they differ (for CI). | — | AT-07 |

## 7. Load record and baselines

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-R-01 | `load-record.json` = `{ "store": <dir name>, "entries": [ … ] }`, newest last. Each entry: `build` (sequence number), `at` (UTC timestamp), `result` (`accepted` / `rejected`), `inputs` (per file: path, kind, `model_id`/`model_version` or `registry_version`, sha256), `metamodel_version`, `errors`, `warnings`, and for accepted builds `outputs` (per file: name, sha256, node and edge counts). | KG-V-01 | AT-01, AT-05 |
| GS-R-02 | Every query answer from the store states the baseline it was answered from: the latest accepted entry's `build` number and the local `model_version`s. | KG-V-01 | AT-04 |
| GS-R-03 | `sdem-graph baseline <name> --graph <dir>` copies the current graph files and the latest accepted entry into `<dir>/baselines/<name>/`; any query accepts `--graph <dir>/baselines/<name>` to answer against it. A baseline is never overwritten. | KG-V-02 | AT-08 |

## 8. Graph access layer

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-A-01 | One read interface, `sdem/store.py` `GraphReader`, with: `levels()`, `baseline()`, `node(level, id, version=None)` (latest version if omitted), `nodes(level=None, type=None, include_subtypes=True, where=None)`, `edges(scope, source=None, target=None, relation=None)`, `neighbours(node, relation=None, direction='both')`, `links(node, direction)` (approved cross-level edges), `is_a(type, ancestor)`. Return values are plain dicts in the shapes of §4–§5. | KG-L-04 | AT-03 |
| GS-A-02 | Two implementations: `StoreReader` (reads a store directory) and `ExportReader` (builds the same structures in memory from exports and registry — today's path). | — | AT-04 |
| GS-A-03 | `trace`, `impact`, `stats` and `query` use only `GraphReader`; for every example estate their output is identical whichever implementation backs them. | KG-Q-01, 02, 06 | AT-04 |
| GS-A-04 | The inference engine (v0.9) reads only through `GraphReader`. | DEC-01 | engine tests |

## 9. Queries

| ID | Requirement | Satisfies | Acceptance |
|---|---|---|---|
| GS-Q-01 | `trace`, `impact`, `stats` accept `--graph <dir>` as an alternative to export paths; behaviour and output otherwise unchanged. | KG-Q-01, 02, 06 | AT-04 |
| GS-Q-02 | `sdem-graph query --graph <dir>` with filters `--level`, `--type` (subtypes included), `--where attr=value` (repeatable; matches core fields and attributes; list attributes match on membership), output as a table or `--json`. | KG-L-04 | AT-09 |
| GS-Q-03 | `--neighbours <id> [--kind <relation>] [--direction in|out|both]` lists within-level neighbours. | KG-L-04 | AT-09 |
| GS-Q-04 | `--unmapped <level>` lists nodes of that level with no approved cross-level edge where a catalogue relationship type expects one for their type — the engine's work list. | KG-Q-04 | AT-09 |

## 10. View

| ID | Requirement | Acceptance |
|---|---|---|
| GS-V-01 | `sdem-graph view --graph <dir> [-o file]` writes one self-contained HTML file (data, script and style inline; no network access, no CDN), default `<dir>/view.html`. | AT-10 |
| GS-V-02 | Layout: four horizontal bands A1 (top) … A4 (bottom); within-level edges inside a band; approved cross-level edges between bands. Node colour by level; shape or badge by entity type. | AT-10 |
| GS-V-03 | Interaction: click a node to see its metadata and links; filter by level and type; select a node and highlight its trace down or up. Works in current Chrome, Edge, Firefox and Safari; readable at phone width. | AT-10 (manual) |

## 11. Non-functional

| ID | Requirement | Acceptance |
|---|---|---|
| GS-X-01 | Python standard library only; no server, no service, no install beyond the SDEM package; works on Windows, macOS and Linux (paths via `pathlib`). | CI matrix |
| GS-X-02 | Performance on a typical laptop: build of 10,000 nodes and 20,000 edges ≤ 10 s; opening a store of that size ≤ 2 s; a trace ≤ 1 s. | AT-11 |
| GS-X-03 | Real institution data is never committed to this repository; the store directory for real data is configured outside it. Example stores are synthetic. | review |
| GS-X-04 | Graph files are readable by generic JGF tooling: an SDEM store must not need SDEM code to be understood. | AT-02 |

## 12. Acceptance tests

| ID | Test |
|---|---|
| AT-01 | Build a store for each of the 8 example estates; all succeed; each has the files of GS-F-01 and an `accepted` load-record entry. |
| AT-02 | Every graph file validates against the JGF v2 schema structure and the SDEM profile `schema/graph-store.schema.json`. |
| AT-03 | Round trip: for every estate, every export instance and relationship and every approved registry record is in the store exactly once with identical content (GS-N-02, GS-E-01, GS-E-02); nothing else is. |
| AT-04 | For every estate, `trace` (both directions, with and without part–whole), `impact` (every change kind on a sample of nodes) and `stats` give identical output from `StoreReader` and `ExportReader`; answers from the store name their baseline. |
| AT-05 | A store with a good build, then a build from a deliberately broken export (and separately an unresolvable approved link): graph files unchanged byte for byte, a `rejected` entry listing the errors, exit 1. |
| AT-06 | Build twice from identical inputs: graph files byte-identical; only the load record grows. |
| AT-07 | `build --check` passes on a current store and fails after an export changes. CI runs it for the committed example stores. |
| AT-08 | Create a baseline, change an export and rebuild; a query against the baseline returns the old answer, against the store the new one. |
| AT-09 | `query`: type, attribute and neighbour filters return the expected records on payment-initiation; `--unmapped` returns exactly the records a hand count expects on two estates. |
| AT-10 | `view.html` is generated for every estate, contains every node and edge, makes no network request (no `http` URL in a script or stylesheet reference); interaction checked by hand in two browsers. |
| AT-11 | Performance against GS-X-02 on a generated synthetic estate of 10,000 nodes. |

## 13. Changes made to existing documents

- `knowledge-graph-spec.md` §12: DEC-01 → *local JSON files in JGF v2 (this specification)*; DEC-03 → *one directory, four local files and one federated file*. KG-L-03, KG-R-03, KG-V-01, KG-V-02, KG-L-04, KG-Q-04 point to the GS requirements that build them.
- `ROADMAP.md`: the graph store moved ahead of the inference engine.
- `glossary.md`: *graph store*, *JGF*, *load record*, *baseline (graph)*.

## 14. Open questions

| ID | Question | Recommendation |
|---|---|---|
| GS-O-01 | Should proposed links be viewable before approval? | Not in the federated file. `view --include-proposed` can overlay the registry's proposals, marked as such, for review sessions. |
| GS-O-02 | Should the federated file embed full nodes instead of stubs? | No — duplication drifts; stubs point to the local file. |
| GS-O-03 | JSON-LD export for W3C interoperability? | Later (with DEC-05), as an export, not the store format. |
