# Protecting the repository — so a person approves what matters

> **Status: current (v0.9.1)** — branch protection and code owners are GitHub settings the repository's owner turns on (steps below). **Most readers protect their estate repository** (§1–§4); the SDEM project's own settings are in §5. Why it matters, for builders: [`sdem-agent-platform-principles.md`](design/sdem-agent-platform-principles.md) §3.

SDEM's controls refuse bad data and refuse an agent's or tool's name as a reviewer (CTL-21). They **cannot** stop someone — or an agent with a terminal — from typing a person's name. The final safeguard is GitHub: **nothing reaches `main` without a pull request that a person reviews and the checks pass.** That is a repository setting, not code — until it is on, approval by a reviewed pull request is a practice, not a control.

## 1. Code owners — your estate repository

The estate template's `.github/CODEOWNERS` names who must review changes to:

| Path | What it is | Reviewer to name |
|---|---|---|
| `estates/*/mappings.json` | the approved connections between layers — the decisions | your architecture reviewers |
| `estates/*/a1-business.json` … `a4-technology.json` | each layer's data | that layer's architects |
| `bian/` | your BIAN layer and any BIAN pack | whoever owns BIAN for you |
| `requirements.txt`, `ci/`, `.github/` | the SDEM version, the checks, Copilot's files | your SDEM maintainers or platform team |

Replace every `@YOUR-ORG/…` placeholder with **real people or teams** — never a bot or an agent account.

## 2. Branch protection on `main` — your estate repository

**First, let the checks run once:** push a branch and open a pull request, so GitHub knows the *Estate checks* workflow. Then **Settings → Rules → Rulesets → New branch ruleset** (or **Settings → Branches → Add branch protection rule**, classic):

| Setting | Value | Why |
|---|---|---|
| Target | `main` (the default branch) | |
| **Require a pull request before merging** | on | no direct pushes — every change is reviewed |
| Required approvals | **1** (more if your process says so) | a person approves |
| **Require review from Code Owners** | on | connections, data, the SDEM version and the checks need an owner's review |
| Dismiss stale approvals when new commits are pushed | on | an approval covers what was reviewed, nothing added later |
| **Require status checks to pass** | on — select **`check`** (the *Estate checks* workflow; pull requests show it as **Estate checks / check**) | every estate is checked and built, and approved connections unchanged, before a merge |
| Block force pushes | on | history cannot be rewritten |
| Restrict deletions | on | `main` cannot be deleted |
| **Do not allow bypassing** (include administrators) | on | the rules apply to everyone, owners too |

**Choose the check by its name, `check`.** If you select a name that never runs — for example `validate`, which is the SDEM project's own check (§5) — GitHub waits for it forever or never enforces it, and nothing blocks a bad merge.

## 3. What changes after it is on

- All changes — yours, Copilot agents' — go through a branch and a pull request; `git push` to `main` is refused.
- An approval made with `sdem approve` becomes final only when its pull request is merged by a reviewer.
- The agent platform's flow is unchanged: agents propose change sets on a branch; a person reviews and merges.

## 4. Check it works

Try `git push` of a small change straight to `main` — it should be refused. Open a pull request: it should show **Estate checks / check** and ask for a code owner's review. Then edit an approved connection in a `mappings.json` by hand on a branch: the check should fail with *an approved link was edited or removed*.

## 5. The SDEM project itself (maintainers only)

The public SDEM repository is protected the same way, with its own names: `.github/CODEOWNERS` covers the rulebook (`metamodel/`, `schema/`), the base BIAN (`bian/`), the documentation and `.github/`; the required status check is the **`validate`** job (tests, `sdem model check`, the CLI commands, the installed package). **One maintainer?** GitHub does not let you approve your own pull request: add a second reviewer, or set Required approvals to **0** and keep the pull request, the code-owner rule and the status checks — your merge is then the person's act, on record.
