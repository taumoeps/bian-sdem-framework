# SDEM operating model — running SDEM for real

> **Status: current (v0.9.7)**. How an organisation runs SDEM on real architecture data: where things live, who does what, how changes, upgrades and rulebook changes flow, support, and what has to be true before starting. The pilot that tests it: [`sdem-pilot-plan.md`](sdem-pilot-plan.md).

## 1. Where things live

```mermaid
flowchart LR
    subgraph PUB["Public — this repository"]
      T["SDEM tool + rulebook<br/>made-up data only"] --> REL["Tagged releases<br/>v0.9.7 …"]
    end
    subgraph ORG["Inside the organisation"]
      ER["Estate repository (private)<br/>estates/ · pinned SDEM · CI"]
      WS["Architect's machine<br/>VS Code · sdem · work/ (exports)"]
      H["Dashboards<br/>local HTML files (for now)"]
    end
    REL -- "pinned by tag" --> ER
    WS -- "pull requests" --> ER
    ER -- "after merge" --> H
```

| Thing | Lives in | Never in |
|---|---|---|
| The tool and the rulebook | this public repository, as tagged releases | — |
| Real architecture data (estates) | the organisation's **private estate repository**, made from [`templates/estate-repo`](../templates/estate-repo/README.md) | this repository, issues, public chat |
| Design exports (Confluence) | `work/` on the machine allowed to hold them | any repository |
| Dashboards | **local HTML files for now** — each architect runs `sdem home` / `sdem dashboard` and opens the page; later, authenticated internal hosting | public Pages, public buckets, links without sign-in, email attachments outside the organisation |

**One estate per domain.** Every domain works the same way — same rulebook, same commands, same checks; a domain joins by adding a folder in `estates/` with its owner and code owners. There are no per-domain settings; the one optional setting — the table headings your organisation's designs use — is shared by every domain ([pilot plan](sdem-pilot-plan.md#no-per-domain-settings)).

**Why:** the employer owns its designs; this repository is public. One private estate repository per organisation (or per division) keeps the boundary simple and auditable.

## 2. Roles

| Role | Who | Does |
|---|---|---|
| **Architect** | the architects of each layer (A1, A3, A4; A2 if your organisation keeps its own BIAN layer) | onboard designs, keep their layer's data current, propose and approve links in their area, resolve gaps |
| **Reviewer** (code owner) | named senior architects per layer, in `CODEOWNERS` | review and merge pull requests; a reviewer is always a person |
| **Estate owner** | one person per estate — usually the domain's lead architect | accountable for the estate's quality: gaps worked down, links reviewed, CI green |
| **In-house SDEM lead** | one named person **in your organisation** — usually the estate owner of the first domain, or an architecture lead | looks after SDEM for your organisation: keeps the pinned version current, triages questions and rulebook requests before they go upstream, owns `bian/` and the `--patterns` table, and acts if the SDEM maintainer is unavailable (§4) |
| **Rulebook owner** (upstream) | the SDEM project's owner (see the SDEM repository) | approves every rulebook change and baseline; the high-level spec stays frozen without them |
| **SDEM maintainer** (upstream) | whoever builds SDEM (today: the owner) | tool fixes and releases, migrations, answering SDEM questions |
| **Platform owner** | the organisation's engineering platform team | the private repository, branch protection, CI runners, internal hosting, Copilot policy |

### Who does what (R = does it, A = accountable, C = consulted)

| Activity | Architect | Reviewer | Estate owner | Rulebook owner | Maintainer | Platform |
|---|---|---|---|---|---|---|
| Onboard a design | R | C | A | | | |
| Approve a link (`sdem approve`, `sdem connect`) — final when its pull request is merged | R | R (merges) | A | | | |
| Merge a pull request | | R | A | | | |
| Resolve or accept a gap | R | C | A | C (if it needs a new entity type) | | |
| Change the rulebook | C | | C | **A** | R | |
| Release SDEM | | | | A | R | |
| Upgrade SDEM in the estate repository | | R | A | | C | |
| Migrate an estate (`sdem migrate`) | R | R | A | | C | |
| Branch protection, CI, hosting | | | C | | C | **R/A** |

The **in-house SDEM lead** is consulted on every row above and is accountable for *Upgrade SDEM*, for `bian/`, and for taking rulebook requests upstream.

## 3. How work flows

**Everyday change** — always a branch and a pull request: an SDEM command (load, approve, designs resolve) → `sdem check` locally → pull request → CI *Estate checks* → code-owner review → merge → dashboards rebuilt. Approvals become final at merge.

**A gap that needs a new entity type or attribute** — the estate owner raises it with the rulebook owner, **without real data** (describe the kind of thing, not the design). If approved: the maintainer changes the rulebook, bumps `metamodel_version` with a recorded migration ([`sdem-rulebook-versioning.md`](design/sdem-rulebook-versioning.md)), and releases; estates upgrade (below).

**Upgrading SDEM** — the estate owner changes the pin in a pull request; CI runs; `sdem migrate` if the rulebook version changed; merge. Upgrade within a month of a release; skip none that carry a migration.

**Release cadence** — SDEM releases when there is something worth releasing, tagged by the owner after CI passes; a rulebook change is always its own release, named in the CHANGELOG.

## 4. Support

| Problem | Where it goes | Rule |
|---|---|---|
| An SDEM error or bug | an issue on the SDEM repository | **no real data** — reproduce with the examples or describe it |
| A question about our data | the estate owner | in the estate repository's issues or the team channel |
| A rule seems wrong, or a new kind of thing is needed (e.g. a *no entity type* gap) | your **in-house SDEM lead**, who raises it with the upstream rulebook owner | describe the kind of thing, not the design |
| Security | SDEM's [`SECURITY.md`](../SECURITY.md) — private report | |
| CI or hosting is down | the platform owner | |

**If the upstream maintainer is unavailable.** Nothing stops: your estates keep working on the release you pinned, and your data is plain JSON files in your repository. The in-house SDEM lead decides between (1) staying on the pinned release, (2) keeping `no entity type` gaps open — they lose nothing — until a rulebook change is possible, or (3) under Apache-2.0, maintaining your own copy (fork) of SDEM, with your organisation's open-source process ([adoption checklist §5](sdem-adoption-checklist.md#5-depending-on-an-open-source-tool)).

SDEM failures say what to do: exit `1` a check refused (read the message), `2` the input is wrong, `3` a fault in SDEM — report it with `SDEM_DEBUG=1` output, after removing any real names.

## 5. Health — what the estate owner watches

| Measure | From | Healthy |
|---|---|---|
| CI on `main` | Estate checks | always green |
| Open gaps | `sdem designs --gaps --status open`, dashboard | going down month on month |
| Proposals waiting | dashboard *Attention* | reviewed within two weeks |
| SDEM version | `requirements.txt` | the latest release, or the one before |
| Coverage of onboarded designs | `sdem transform run`; each load's reconciliation | tables and diagrams 90% or more captured; every item captured or kept as a gap record |

## 6. Before starting — what must be true

| # | Precondition | Owner | Why |
|---|---|---|---|
| 1 | **Legal, data, security and AI clearance** to run SDEM on the organisation's designs — the [adoption checklist](sdem-adoption-checklist.md) | owner | the designs belong to the employer; SDEM is personal open source |
| 2 | Private estate repository with **branch protection and code owners** | platform | without it a person's approval is not enforced ([`sdem-repository-protection.md`](sdem-repository-protection.md)) |
| 3 | **Python 3.10 or later** on architects' machines (3.13 recommended) | platform | SDEM requires 3.10; Python 3.9 reached end of life in October 2025 |
| 4 | **Dashboard hosting decided** — local HTML files to start (§7) | owner | dashboards show real architecture |
| 5 | **Copilot and OCR policies** known — Copilot allowed or not (no MCP); reading text in pictures allowed or `--ocr off` | platform | SDEM works without Copilot; with it, Copilot files must match the pinned release |
| 6 | **A2 (BIAN)**: which BIAN to use — the **base** that ships with SDEM (BIAN's public Semantic APIs 14.0.0, Apache-2.0), or your organisation's own, packed with `sdem bian pack` | owner | business connects to applications only through BIAN; the base works for everyone, your own BIAN replaces it |

## 7. Starting choices — our recommendations

Your organisation makes these; these are the defaults we recommend for a first pilot.

| Choice | Recommended | Why |
|---|---|---|
| One estate repository for the organisation, or one per division | **one**, with one folder per estate | simplest to protect and to report across — split only if divisions must not see each other's data |
| Who is the first estate owner | the architect leading the pilot domain (often also the in-house SDEM lead) | they know the designs and review the work anyway |
| Where dashboards are hosted | **local HTML files** to start (`sdem home -o work/sdem`, open `work/sdem/index.html`) — nothing to set up, nothing leaves the machine | move to internal hosting behind sign-in when more people need to see them |
| Support | best effort during the pilot, reviewed at its end | the pilot shows what support is really needed |
