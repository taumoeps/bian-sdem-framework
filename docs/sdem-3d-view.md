# The 3D view — what it changed, and how a workspace gets there

> **Status: current (SDEM 0.18.0, metamodel 0.14.0).** The 3D view is the exploded four-layer drawing on the DESNRE site. It is an SDEM output, like a design document: every record, link and position comes from an SDEM workspace, nothing is typed in by hand. Related pages: [How SDEM draws each layer](sdem-layer-layouts.md) and [A4: the physical deployment](sdem-a4-physical-deployment.md).

## 1. Why the 3D view changed SDEM

A drawing shows every record. The 3D view made gaps visible that a list or a check never showed: shapes connected to nothing, a network drawn as a shape when it is a zone, records with no clear owner. Each gap was fixed **in the metamodel, the checks or the data**, not in the drawing — so every SDEM output benefits, not only the 3D view.

## 2. Metamodel — three versions

| Version | Change | The gap the drawing showed |
|---|---|---|
| **0.12.0** | **EXPOSED_THROUGH** — a component or interface is exposed through a gateway. Inferred by AID-X01; the A4 connections between shapes inferred by AID-C01…C06 | A4 shapes — the gateway among them — connected to nothing |
| **0.13.0** | **A network zone is an ArchiMate Grouping** (RA4-39); zones and networks split, with a migration (`sdem migrate`) | the private network was drawn as a shape when it is a zone |
| **0.14.0** | **BUILT_AS** — a component is built as an artifact (its image). Inferred by AID-X02 | the database and the container image connected to nothing |

All three are checked against ArchiMate 3.2 (EXPOSED_THROUGH as serving, BUILT_AS as realization, a zone as a Grouping); BIAN and TOGAF are unaffected.

## 3. Checks, inference and tools — no metamodel change

| Area | What was added |
|---|---|
| **Checks** | LC-16 is an error in a workspace with zones; LC-21 a shape connected to nothing; LC-22 a component exposed through nothing; ZC-05 a connection that cuts across zones; PR-13a zone kinds in patterns |
| **Hosting evidence** | hosting signals HS-11…13; the S37 platform route; an organisation's own signal overrides in its profile (PR-33); hosting evidence read on import (HI-H01) |
| **Layouts** | A4 by network zone (`sdem zones --layout`, ZL-01…06); A1–A3 by what owns what (`sdem layout`, decisions C1–C6); both used by `sdem view` and the `zones` viewpoint (T8) |

## 4. Data — the examples

- **Every example** has network zones.
- **payment-initiation**: its private zone and network; the A4 connections it was missing; an EXPOSED_THROUGH and a BUILT_AS mapping; a complete A2 — the business area, Party Authentication from BIAN 14.0.0, Payment Execution detailed (24 → 48 records, no warnings).
- **A1 and A3 data did not change** — their records already fitted the layouts.

## 5. From a workspace to the 3D layers

| Step | Who | Command |
|---|---|---|
| 1. Make the workspace complete and clean — fix or approve what is open | the architect | `sdem check --workspace <ws>`, `sdem zones --workspace <ws>`, `sdem trace A4 --direction up --graph <ws>/graph` |
| 2. Rebuild the graph | the architect | `python -m sdem.graph build <ws>/a*.json <ws>/mappings.json --out <ws>/graph` |
| 3. Preview each layer — what you see is what the 3D view draws | the architect | `sdem layout --layer A1\|A2\|A3\|A4 --workspace <ws>`, or `sdem view --graph <ws>/graph` |
| 4. Install the extension (once) | the architect | in SDEM's environment: `pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=desnre"` — then `sdem extensions` lists it |
| 5. Create a draft | the architect | `sdem desnre create <ws>` — the first time it asks you to confirm the workspace is made-up data; checks versions and `sdem check`; builds the model from `sdem layout` and `sdem zones --layout`; sends it as a **draft**, not public; opens the preview (`--dry-run` builds it and sends nothing) |
| 6. Publish | a person, after looking at the preview | `sdem desnre publish <ws>` — live at `?model=<the workspace's name>` |

Steps 4–6 are the **`sdem-desnre` extension** (in the [sdem-extensions](https://github.com/taumoeps/sdem-extensions) repository, `desnre/`): SDEM's first extension, following [the extension contract](design/sdem-extensions-spec.md) — SDEM runs it as `sdem desnre …` (EXT-15) and it uses SDEM only through `--json`. The site's own default model is still rebuilt with `scripts/build-hero.py`, which uses the same builder.

**What the 3D view draws:** each layer's records where `sdem layout` places them; the links inside a layer; the mappings between layers; regions with their own blocks and faint "part of" lines; links SDEM only implies are hidden.

## 6. Limits

- **The DESNRE site is public: only made-up workspaces go on it.** A real organisation's architecture never goes through step 6 (SDEM's rule: made-up data only).
- **Tried only with SDEM's own examples.** The extension finds SDEM on the PATH, above the workspace, or through `SDEM_CMD`.
- **The page's heading text is fixed** ("Example payments design"), so another model shows under it; the counts and records are the model's own.
