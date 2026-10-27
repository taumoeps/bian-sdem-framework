# SDEM Load — Putting reviewed entities into an estate

> **Status: approved 2026-10-28 ("go ahead"); built 2026-10-28.** `sdem load`. Requirements: [`sdem-load-spec.md`](sdem-load-spec.md). The **L** of the ETL for past designs; the **T** is [`sdem transform`](sdem-transform-design.md).

**Objective:** take the candidate entities `sdem transform` produced, **after an architect has reviewed them**, and load the ones the architect keeps into an SDEM estate — checked first, recorded, never unreviewed.

## 1. Where it fits — the ETL

| ETL | In SDEM | Command | Output |
|---|---|---|---|
| **E — Extract** | get the designs out of Confluence | the Confluence export (architect) | an export folder |
| **T — Transform** | read the export → candidate A1, A3, A4 entities with evidence | `sdem transform run` | a candidates folder (`work/history`) |
| *review* | the architect reads `extraction-report.md` and decides what to keep | — | a decision |
| **L — Load** | put the kept entities into an estate | **`sdem load`** | the estate's datasets, a load record |
| *after* | SDEM's normal processing — the same for every estate | `sdem link` → `sdem approve` → `sdem build` | proposals, `mappings.json`, the knowledge graph |

`link`, `approve` and `build` are not part of the ETL: they are SDEM's governance, the same however data arrived.

```mermaid
flowchart LR
    exp[("Confluence export")] --> T["sdem transform run<br/>T — candidates + evidence"]
    T --> cand[("work/history<br/>candidates")]
    cand --> rev(["architect reviews<br/>extraction-report.md"])
    rev --> L["sdem load<br/>L — select · check · record"]
    a2[("your A2 dataset<br/>(BIAN catalogue)")] -.->|"--a2, once"| L
    L --> est[("estate<br/>a1 · a2 · a3 · a4 + loads/")]
    est --> link["sdem link"] --> appr["sdem approve<br/>(a person)"] --> reg[("mappings.json")]
    est --> build["sdem build"]
    reg --> build --> kg[("knowledge graph")]
    cand -. "CTL-23: never built directly" .-x build
```

## 2. The command

```bash
sdem load work/history --estate estates/history --person jane.architect --exclude HIS-A3-SANCTIONS-CHECKEL --a2 estates/current/a2-service-domain.json
```

| Option | Meaning |
|---|---|
| `CANDIDATES` | the folder `sdem transform run` wrote (must hold its `extraction.json`) |
| `--estate DIR` | the estate to load into — created if it does not exist. Recommended for past designs: **a separate historical estate** (e.g. `estates/history/`), apart from current designs (HI-D03) |
| `--person NAME` | who reviewed and loads — a person, never an agent or a tool (as CTL-21) |
| `--all` · `--only ID …` · `--exclude ID …` · `--keep FILE` | **what to load — one is required**, so loading is always a decision: everything, only these, all but these, or the ids listed in a file (one per line, `#` comments) |
| `--a2 FILE` | your organisation's A2 dataset (from the BIAN catalogue), copied into the estate if it has none — so the engine can propose capability → domain → application links (§4) |
| `--dry-run` | check and show what would be loaded; write nothing |
| `--json` | machine-readable result |

## 3. What it does

1. **Checks the source** is a transform output: `extraction.json` present, its datasets marked `CONFLUENCE-EXTRACT`. Anything else is refused.
2. **Selects** the entities the person chose. A link inside an architecture is kept only when **both** ends are loaded; a `deployed_on` reference to an entity not loaded is dropped. What was dropped is listed.
3. **Merges** into the estate: an entity already there with the **same content** is skipped; with **different content** the load is refused (a person resolves it — rename, exclude, or edit the estate). A dataset the estate does not have yet is created (`model_id` `<estate>-<A>`, `source_system` `SDEM-LOAD`).
4. **Checks the whole estate as it would be** — every dataset, the registry, the rulebook — **before writing**. Any error: nothing is written.
5. **Writes** the datasets and a **load record** `<estate>/loads/LOAD-<n>.json`: who, when, from which transform run (export and rules fingerprints), what was loaded, excluded and dropped, the A2 dataset added, the check result.
6. **Prints next steps** and the **BIAN mentions** from the transform as hints for `sdem link`.

Every loaded entity keeps `attributes.source_id` = `confluence:<pages>`, so its origin stays visible after loading.

## 4. Getting links between architectures

The knowledge graph needs links **between** architectures (`mappings.json`), proposed by the engine and approved by a person. Two changes make transformed designs usable there:

| Change | Phase | What it does |
|---|---|---|
| **"Deployed on" written as data** (R2) | Transform | a candidate "application deployed on node" (from nesting in a diagram or "runs on / hosted on" in text) is written as the A3 entity's `deployed_on` attribute — the form the engine reads (rule S33–S35) |
| **Document-derived links capped at low** (DEC-E-11) | Engine | any link the engine proposes that touches an entity transformed from a document (`source_id` `confluence:…`) is capped at **low** confidence, with the reason in its rationale — a person sees it came from a document, as name-only evidence is capped (DEC-E-10) |
| **Your A2 dataset** (`--a2`) | Load | with the BIAN layer present, the engine can propose capability → Service Domain and Service Domain → application links; the transform's BIAN mentions are hints for the reviewer |

## 5. The control — CTL-23

**Unreviewed candidates never enter a knowledge graph.** `sdem build` refuses a dataset marked `CONFLUENCE-EXTRACT`, as it refuses AID projections (CTL-16); the only way in is `sdem load`, which a person runs and which is recorded. Candidate folders still pass `sdem check`, so they can be reviewed.

## 6. Agent-managed estates

In an estate with coordination records (the agent platform), loading is a change to a layer like any other direct edit: `sdem check` reports it as a direct edit waiting to be adopted (AG-S08) until `sdem change adopt` records it. Load on a branch and merge through a reviewed pull request, as for any change.

## 7. Decisions

| # | Decision | Status |
|---|---|---|
| LD-D01 | Load is its own command (`sdem load`), separate from the transform — one job each | approved 2026-10-28 |
| LD-D02 | What to load is always explicit (`--all`, `--only`, `--exclude` or `--keep`) | built |
| LD-D03 | Conflicting content is refused, never overwritten | built |
| LD-D04 | Transform subcommand `extract` renamed `run` (no clash with ETL's Extract) | approved 2026-10-28, built |
| HI-D03 | Past designs load into a separate historical estate | recommended; `--estate` takes any folder |
| HI-D04 | CTL-23 | approved 2026-10-28, built |
| DEC-E-11 | Engine caps document-derived links at low | approved 2026-10-28, built |
