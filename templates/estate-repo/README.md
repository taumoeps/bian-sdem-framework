# Architecture estates — private

This repository holds **our real architecture data**, checked and built with a pinned release of [SDEM](https://github.com/taumoeps/bian-sdem-framework). It is **private**: SDEM itself is public and holds only made-up data; our data lives here and nowhere else.

```mermaid
flowchart LR
    S["SDEM (public)<br/>the tool and the rulebook<br/>tagged releases"] -- "pinned in requirements.txt" --> E["This repository (private)<br/>estates/ — our data<br/>CI checks every change"]
    E -- "after merge" --> D["Dashboards<br/>local files for now;<br/>later internal, sign-in only"]
    A["Architects<br/>VS Code + sdem"] -- "pull requests" --> E
    R["Reviewers (code owners)"] -- "approve and merge" --> E
```

## Set up (once — the platform owner)

1. **Create a private repository** in your organisation and copy this folder's contents into it (including the hidden `.github/`, `.gitignore` and `.vscode/`).
2. **Pin SDEM**: `requirements.txt` names the release tag. Keep it on a released tag, never `main`. If your network cannot reach GitHub, mirror the SDEM repository internally and point the line at the mirror.
3. **Name real reviewers** in `.github/CODEOWNERS` — people or teams, never a bot or an agent account.
4. **Protect `main`** — after the checks have run once (open a first pull request): require a pull request; **1 approval** and **review from Code Owners**; dismiss stale approvals; require the status check **`check`** (shown as *Estate checks / check* — not `validate`, which is SDEM's own); block force pushes and deletion; include administrators. Step by step, and how to test it: SDEM's [repository protection guide](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/sdem-repository-protection.md) §1–§4.
5. **Dashboards** — local HTML files for now; later, authenticated internal hosting only (see *Dashboards* below).
6. **Copilot (optional)** — only if your organisation allows it; SDEM works without it. After step 2, in this repository: `sdem copilot install` — it writes SDEM's Copilot instructions, agents, prompts and skills into `.github/`, matching the SDEM version you pinned. Commit them.
7. **Your BIAN layer** — once, by whoever owns BIAN for you, shared by every domain:
   ```bash
   sdem bian import --base --only "<service domain>" "<service domain>" … -o bian/a2-service-domain.json
   ```
   Read `bian/a2-service-domain.report.md` (confirm the derived asset types and functional patterns), then commit `bian/`. `--base` is BIAN's public Semantic APIs that ship with SDEM; to use your organisation's own BIAN instead, see [`bian/README.md`](bian/README.md). Add service domains later the same way, with `--previous bian/a2-service-domain.json`.
8. **Policies to confirm** before real designs come in: legal and IP clearance, Copilot (allowed or not), and reading text in pictures (OCR — allowed or `--ocr off`). The checklist: SDEM's [adoption checklist](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/sdem-adoption-checklist.md).

## Every architect (once)

```bash
git clone <this repository> && cd <it>
python3.13 -m venv .venv && source .venv/bin/activate   # Python 3.10 or later (3.13 recommended); not found? /opt/homebrew/bin/python3.13
pip install -r requirements.txt
sdem --version                                           # the pinned version
bash ci/check-estates.sh                                 # the same checks CI runs (approved links compared with main)
```

## Daily work — always on a branch, always through a pull request

```bash
git switch -c onboard/<design>
sdem transform run work/imports/<design> -o work/history       # keep the export in work/ — never committed; add --ocr off if your policy says so
sdem load work/history --estate estates/<domain> --person <you> --exclude <ids you reject> \
    --a2 bian/a2-service-domain.json                          # the shared BIAN layer (first load of a domain); gaps are recorded
sdem check --estate estates/<domain>
sdem link --estate estates/<domain> --out work/links              # proposed links
sdem approve P-RUN-001 --proposals work/links/proposals.json --estate estates/<domain> \
    --reviewer <you> --evidence application_architecture_document:<doc>#<section>   # a person approves, with evidence
git add estates/<domain> && git commit -m "Onboard <design> (LOAD-001)" && git push -u origin HEAD
```
Open a pull request; CI runs the **Estate checks**; a code owner reviews and merges. **Approvals become final when the pull request is merged.** Your BIAN layer is `bian/a2-service-domain.json` (set-up step 7; [what it is](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/sdem-onboarding-workflow.md#your-bian-a2-layer)). To practise first, the made-up sample export is in a clone of SDEM: `tests/fixtures/confluence-folder-export`. The full walk-through: SDEM's [onboarding workflow](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/sdem-onboarding-workflow.md) and [user guide](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/sdem-workbench-user-guide.md).

## Adding a domain

Any domain works the same way: create `estates/<domain>/` (by onboarding its designs, or with its datasets and an empty `mappings.json`), add its reviewers to `.github/CODEOWNERS`, and name its estate owner. CI picks it up automatically.

**No per-domain settings are needed.** If your organisation's designs use table headings SDEM does not recognise (they show up as *column not mapped* or *no entity type* gaps), write a copy of SDEM's rules once — `sdem transform rules -o rules/transform-rules.json` — add the headings under `tables`, commit it, and pass `--rules rules/transform-rules.json` to `sdem transform` — for every domain.

## What CI checks (`ci/check-estates.sh`)

| Check | Command | Fails when |
|---|---|---|
| Follows the rulebook | `sdem check --estate` | a record or link breaks a rule or control |
| Approved links unchanged | `sdem diff --git <base>` | an approved link was edited or removed (supersede it instead) |
| Builds | `sdem build --estate` | the knowledge graphs cannot be built |
| Open gaps | `sdem designs --gaps --status open` | never — listed for information |

After a merge to `main`, CI builds the home page and one dashboard per estate (`sdem home --root estates`) as the artifact **sdem-dashboards**.

## Dashboards

They show real architecture. Publish them **only** behind your organisation's sign-in — an internal web server or intranet, or GitHub Pages with **private** visibility if your plan offers it. Never public GitHub Pages, a public bucket, or a link without sign-in. Add your upload step at the end of `.github/workflows/estate-ci.yml`.

**For now (OM-3): local files.** Each architect builds them on their own machine — `sdem home --root estates -o work/sdem`, then open `work/sdem/index.html` in a browser. `work/` is never committed. CI's *sdem-dashboards* artifact is the same pages, for anyone without SDEM installed.

## Upgrading SDEM

1. On a branch, change the tag in `requirements.txt` to the new release; read its CHANGELOG.
2. `pip install -r requirements.txt`, then `bash ci/check-estates.sh`.
3. If SDEM says an estate's `metamodel_version` does not match, the rulebook changed: `sdem migrate --estate estates/<name> --person <you> --dry-run`, then without `--dry-run`. See SDEM's [rulebook versioning](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/design/sdem-rulebook-versioning.md).
4. If you use Copilot: `sdem copilot install` — it updates the Copilot files to the new SDEM version and keeps any your team has changed (it lists them).
5. Pull request; CI green; merge.

## Rules

- **Real data stays here.** Never copy it to the public SDEM repository, an issue, or a chat outside your organisation. Design exports stay in `work/`, on the machine allowed to hold them.
- **Approved connections and loads change only through SDEM commands** (`sdem approve`, `sdem load`, `sdem designs resolve|accept`): they check first and record who did what. Never edit `mappings.json`, `loads/` or `designs/` by hand — CI refuses an edited approved connection.
- **Editing a layer's records by hand is fine** (e.g. adding an application to `a3-application.json`): then run `sdem check --estate estates/<domain>` and open a pull request. Once agents work on a layer through change sets, SDEM asks you to record a hand edit with `sdem change adopt` (it tells you when).
- **A reviewer is a person.** Agents and bots propose; people approve.
- Problems with SDEM itself: an issue on the SDEM repository **without any real data**; security problems: SDEM's `SECURITY.md`.
