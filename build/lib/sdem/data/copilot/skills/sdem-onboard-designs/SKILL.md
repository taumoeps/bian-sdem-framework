---
name: sdem-onboard-designs
description: Design onboarding — how past designs (a Confluence export) become SDEM architecture entities — running `sdem transform`, reading its extraction report, explaining each candidate's evidence, and suggesting what the architect should keep or reject before they run `sdem load`. Use when the architect asks about importing, transforming or loading past designs, or about HIS- records.
---

# Onboarding past designs

The whole journey (design onboarding): [`docs/sdem-onboarding-workflow.md`](../../../docs/sdem-onboarding-workflow.md). In short:

```
export (the architect) → sdem transform run → review (the architect, you help) → sdem load (the architect) → sdem link → sdem approve (a person) → sdem build
```

**Your part is the review.** You may run the transform and explain its report. **You never run `sdem load`** — loading is the person's decision, recorded under their name (`--person`), and `sdem build` refuses unloaded candidates (CTL-23). You never run `sdem approve`.

## Commands

| Step | Command | Notes |
|---|---|---|
| what is in the export | `sdem transform inspect <export>` | structure only; `--anonymous` hides folder names |
| transform | `sdem transform run <export> -o <dir> [--known <datasets>] [--rules <file>] [--ocr off]` | writes candidate datasets, `extraction.json`, `design-index.json`, `extraction-report.md` |
| try a load | `sdem load <dir> --workspace <workspace> --person <the architect> --exclude <ids> --dry-run` | **only `--dry-run`** — shows what would load and whether the workspace would pass its checks; writes nothing |

## Reading the report (`<dir>/extraction-report.md`, detail in `<dir>/extraction.json`)

Every candidate has its **sources**: page, place (table and row, diagram and shape, paragraph), **rule**, confidence (never above medium), reasoning.

| Rule | Read from | How sure |
|---|---|---|
| `HT-…` | a table — its column heading names the type | medium |
| `HL-…` | a source/target table — a link; new names in it are assumed applications | medium (link), low (new names) |
| `HD-01…23` | a draw.io ArchiMate shape | medium |
| `HD-L`, `HD-S`, `HD-D` | a plain draw.io box — typed by a label word, its shape, or the section's default | low |
| `HD-K`, `HD-N`, `HU-K`, `HU-N`, `HO-K`, `HO-N` | named like an existing record or one found elsewhere | low |
| `HU-T` | a PlantUML element with a type (component, node, C4, ArchiMate) | medium (low for sequence participants) |
| `HU-…` other | a PlantUML element typed by its name or section | low |
| `HO-…` | text read from a picture by OCR — **can be misspelt** | low |
| `HN-01` | the name appears in the text | (a mention, adds no type) |
| `HP-…` | a phrase between two names ("sends … to", "calls", "is hosted on") | low |

## What to suggest the architect rejects (`--exclude`)

Point these out, with the reason; **the architect decides**:
- **fails the check** (the report's *Check* section, e.g. a data entity without its attribute list, LC-04) — load would refuse it;
- **OCR labels** (`HO-…`) that look misspelt or are not a system (compare with names elsewhere in the export);
- **section defaults** (`HD-D`, `HU-D`, `HO-D`) — typed only by where they sit; check the type;
- **same name, different types** (listed under *For a person*) — keep one;
- records with a **single low source** and no other page mentioning them.

Also report:
- **pictures** and **diagrams not linked to a page** — the architect records or places them by hand;
- **BIAN names** found — they are never entities (A2 comes only from a BIAN source — the transform never creates A2 records, CTL-24); they are hints for `sdem link` once the entities are loaded.

Then give the architect the load command to run themselves, e.g.:
`sdem load work/history --workspace workspaces/history --person <their name> --exclude HIS-A3-… HIS-A3-…` — the workspace must exist first: `sdem new --workspace workspaces/history --person <their name>` (once).

## After loading — what to expect

- What did not fit an entity is kept as **gap records** beside the workspace (`<workspace>/designs/design-records.json`): `sdem designs --workspace <workspace> --gaps` lists them by category; `sdem designs --entity <id>` shows an entity's pages and gaps. Help the architect work through the open ones — suggest, per gap, whether it is now in the data (`sdem designs resolve`) or stays as it is (`sdem designs accept`), with a note; **the architect runs those commands** (their name is recorded); a recurring *no entity type* is evidence for a metamodel decision by the owner — never change `metamodel/`.

- Loaded records keep their `HIS-` ids and `attributes.source_id` = `confluence:<pages>`.
- `sdem link` proposes links between architectures from them — **capped at low** when an end was read from a document (DEC-E-11); say so when you explain a proposal, and suggest checking it against the page (`design-index.json` gives the page).
- Changes to loaded records later go through change sets like any other record.

## Tuning the rules

When `inspect` shows tables marked `no rule` or shapes `unclassified`: the architect copies `metamodel/transform-rules.json`, adds the words, and passes `--rules`. You may suggest the exact entries (e.g. add `"system name"` to rule HT-01's `name` list). Never edit `metamodel/` itself.

## Confidentiality

The export is the organisation's information: read it only in the workspace; never paste it anywhere outside the organisation's approved Copilot; no MCP.
