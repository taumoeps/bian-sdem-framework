# Configuring SDEM

> **Status: current (v0.9.3)** — everything you can set, where, and who decides. SDEM works with no configuration at all; this page is for setting it up for a team.

SDEM has **no configuration file and no server settings**. What you can set is: where your data lives, how design onboarding reads your documents, your tools (VS Code, Copilot), and your estate repository. The rulebook itself is **not** configurable — it is the same for everyone, and only the SDEM owner changes it.

## At a glance

| What | Where | Who decides | Default |
|---|---|---|---|
| [Your estates](#estates) | a folder per estate, in your private estate repository | estate owner | — |
| [The SDEM version](#the-sdem-version) | `requirements.txt` in the estate repository | platform owner | the latest release |
| [How onboarding reads designs](#onboarding--reading-your-designs) | your copy of `transform-rules.json`, passed with `--rules` | estate owner, once | SDEM's rules |
| [Text in pictures](#text-in-pictures-ocr) | `sdem transform run --ocr …` | your organisation's policy | on, on the machine |
| [Reviewers](#reviewers-and-protection) | `.github/CODEOWNERS` + branch protection | platform owner | — |
| [Estate checks (CI)](#estate-checks-ci) | `.github/workflows/estate-ci.yml` | platform owner | the template's checks |
| [VS Code](#vs-code) | `.vscode/` | the template | PlantUML local; recommended extensions |
| [Copilot (optional)](#copilot-optional) | `.github/` agents, prompts, skills | your organisation's policy | off unless you set it up |
| [Dashboards](#dashboards) | `sdem home` / `sdem dashboard` options | estate owner | local HTML files |
| [Error detail](#error-detail) | `SDEM_DEBUG=1` | you, when reporting a fault | off |

## Estates

An **estate** is one folder of architecture data — usually one per domain. SDEM needs `mappings.json` and at least one layer file in it; everything else it creates when needed ([what is inside](sdem-architecture.md#inside-an-estate)). Every command takes `--estate <folder>`. Keep estates in your **private** estate repository, under `estates/`; the [template](../templates/estate-repo/README.md) sets that up.

To start an estate: onboard designs into a new folder (`sdem load … --estate estates/<domain>`), or copy your layer files in with an empty registry: `{"registry_version": "0.4.0", "metamodel_version": "0.4.0", "mappings": []}`.

## The SDEM version

The estate repository installs one **released** version of SDEM, named in `requirements.txt`:

```
sdem @ git+https://github.com/taumoeps/bian-sdem-framework@v0.9.3
```

Never point it at `main`. If your network cannot reach GitHub, mirror the SDEM repository internally and point the line at the mirror. Changing the version: [Administration — upgrading](sdem-administration.md#upgrading-sdem).

## Onboarding — reading your designs

`sdem transform` reads Confluence exports using **rules in a file**, `transform-rules.json`. SDEM's own rules work for any domain. If your organisation writes designs differently, make a copy once and pass it every time:

```bash
sdem transform rules -o rules/transform-rules.json                      # in your estate repository: a copy to tune
sdem transform run work/<export> -o work/history --rules rules/transform-rules.json
```

`sdem transform inspect <export>` shows what SDEM could and could not read — start there. What you can change in the copy:

| Section | Decides | Change it when |
|---|---|---|
| `tables` | which table headings mean which kind of record (e.g. *Application*, *System* → application) and which columns hold its details | your tables use headings SDEM does not recognise (they show up as *column not mapped* or *no entity type* gaps) |
| `diagram_shapes`, `shape_words`, `label_words`, `diagram_colours` | which draw.io shapes, words and colours mean which kind of record | your diagrams use your own shapes or colour code |
| `plantuml_types`, `plantuml_groups` | PlantUML and C4 elements → kinds of record | you use other PlantUML stereotypes |
| `section_layers`, `layer_default_type` | which page headings belong to which layer (e.g. *Infrastructure* → A4) | your section headings differ |
| `phrases`, `line_kinds` | which words between two names mean a link (*runs on*, *calls*) | your designs use other verbs |
| `skip_folders`, `skip_files`, `skip_images` | what to ignore (icons, thumbnails, index pages) | your export has other clutter |
| `ocr` | text-recognition settings | rarely |

You **cannot** change how sure SDEM is allowed to be: onboarded records are never above *medium*, and nothing is loaded without a person. Optional flags: `--known <dataset>` (match names to records you already have), `--model-id` (name the candidate datasets).

## Your BIAN layer (`sdem bian`)

SDEM ships with a **base BIAN** — BIAN's public Semantic APIs 14.0.0 (Apache-2.0; `bian/`). To use your organisation's own BIAN instead, pack it once (`sdem bian pack <folder> -o bian/our-bian.json`, kept in your estate repository) and use `--base bian/our-bian.json`. Every A2 record records which BIAN it came from.

| Option | Means |
|---|---|
| `--base` · `--base <file>` · `<folder>` | the BIAN to import from: the base that ships with SDEM · your own pack · a folder of BIAN's files (one must be named) |
| `--only <names>` · `--from <file>` · `--all` | which service domains to import (you must choose; a whole release is about 7,000 records) |
| `--patterns <csv>` | asset type and functional pattern per service domain (`service domain,asset type,functional pattern`) — for domains SDEM cannot work them out for, or to correct a derived one |
| `--descriptions` | include BIAN's descriptions — from a folder of BIAN's files only (the base leaves them out) |
| `--objects` | also import BIAN's business objects — from a folder only |
| `--previous <file>` | report what changed against your previous BIAN layer (nothing is removed from your estate) |

After changing the shared file, `sdem bian update --root estates --a2 bian/a2-service-domain.json --person <you>` brings every estate up to date — checked, all-or-nothing, recorded in each estate's `bian-updates/`; it refuses if an approved connection points to a service domain you dropped.

**Where it lives:** in your estate repository, write it to `bian/a2-service-domain.json` and commit it — one file shared by every domain (`sdem load … --a2 bian/a2-service-domain.json`); keep a `--patterns` table beside it (`bian/patterns.csv`) and your own pack if you have one (`bian/our-bian.json`). The estate template's `bian/README.md` walks through it. How: [onboarding — your BIAN (A2) layer](sdem-onboarding-workflow.md#your-bian-a2-layer).

## Text in pictures (OCR)

When onboarding, SDEM reads text in pictures with the computer's own text recognition (macOS) or Tesseract if installed — nothing leaves the machine.

| `--ocr` | Means |
|---|---|
| `auto` (default) | macOS text recognition if available, else Tesseract, else skip |
| `vision` · `tesseract` | only that one |
| `off` | do not read pictures — they become gap records for a person |

Use `off` if your organisation does not allow automated reading of document images.

## Reviewers and protection

`.github/CODEOWNERS` in the estate repository names **who must approve** a change — people or teams, never a bot or an agent account. It only takes effect with **branch protection** on `main`: require a pull request, one approval, review from code owners, and the *Estate checks* status. Step by step: [repository protection](sdem-repository-protection.md).

## Estate checks (CI)

The template's `.github/workflows/estate-ci.yml` runs `ci/check-estates.sh` on every pull request: every estate is checked, built, and its approved connections compared with the base branch; open gaps are listed. After a merge it builds the dashboards as a downloadable artifact. You can add steps (for example, publishing dashboards to internal hosting behind sign-in); do not remove the checks.

## VS Code

The project's `.vscode/` folder sets:

| Setting | Value | Why |
|---|---|---|
| PlantUML preview | `"plantuml.render": "Local"` | diagrams are drawn on your machine (needs Java and Graphviz: `brew install plantuml`); **never** switch to the public server for real data |
| Recommended extensions | Python, GitHub Copilot Chat, Markdown Mermaid preview | VS Code offers them when you open the project |

## Copilot (optional)

If your organisation allows GitHub Copilot, SDEM's Copilot files make it useful — **no MCP, no AI inside SDEM**:

| Folder | Holds |
|---|---|
| `.github/copilot-instructions.md` | the rules Copilot follows in this project (suggest commands, never approve) |
| `.github/agents/` | five agents: one per layer (A1–A4) and an orchestrator |
| `.github/prompts/` | prompts (9 installed into an estate repository; the SDEM project also has one for its made-up example): `/sdem-explain`, `/sdem-fix`, `/sdem-review`, `/sdem-onboarding-review` … |
| `.github/skills/` | five skills: change sets, records, approving links, trace and impact, onboarding designs |

In an estate repository, put them in place with `sdem copilot install` — they match the SDEM version you installed; run it again after an upgrade (files your team changed are kept and listed). Agents work in rounds; the limit is a cap an agent may lower but never raise — the architect decides. Set-up: [Copilot set-up](sdem-copilot-setup.md).

## Dashboards

| Command | Options |
|---|---|
| `sdem home -o <folder>` | `--root <folder of estates>` (repeatable), `--estate <folder>` (repeatable) — the home page and one dashboard per estate |
| `sdem dashboard --estate <folder> -o <file.html>` | `--title`, `--graph <store>` (warn if it is out of date), `--projection <AID package>` |

They are local HTML files for now; open them in a browser. Never publish them where people can see them without signing in.

## Error detail

If SDEM reports an internal error (exit code `3`), run the command again with `SDEM_DEBUG=1` in front to see the details — then remove any real names before sharing them:

```bash
SDEM_DEBUG=1 sdem build --estate estates/payments -o work/graph
```
