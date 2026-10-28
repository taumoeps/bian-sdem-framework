# Protecting the repository — so a person approves what matters

> **Status: CODEOWNERS added 2026-10-28; branch protection is a GitHub setting the owner turns on (steps below).** Why: [`sdem-agent-platform-principles.md`](design/sdem-agent-platform-principles.md) §3.

SDEM's controls refuse bad data and refuse an agent's or tool's name as a reviewer (CTL-21). They **cannot** stop someone, or an agent with a terminal, from typing a person's name. The final safeguard is GitHub: **nothing reaches `main` without a pull request that a person reviews and the checks pass.** That is a repository setting, not code — until it is on, approval by a reviewed pull request is a practice, not a control.

## 1. Code owners (in the repository)

`.github/CODEOWNERS` names who must review changes to:
- the rulebook (`metamodel/`, `schema/`)
- approved links (`mappings.json`)
- architecture data (`a1…a4` datasets)
- load records and coordination records
- the agents' definitions and the CI checks (`.github/`)

In your organisation's copy, replace `@taumoeps` with the approving architects or team (e.g. `@your-org/architecture`).

## 2. Branch protection on `main` (you, in GitHub)

**Settings → Rules → Rulesets → New branch ruleset** (or **Settings → Branches → Add branch protection rule**, classic):

| Setting | Value | Why |
|---|---|---|
| Target | `main` (the default branch) | |
| **Require a pull request before merging** | on | no direct pushes — every change is reviewed |
| Required approvals | **1** (more for the work copy if your process says so) | a person approves |
| **Require review from Code Owners** | on | changes to the rulebook, links, data and agents need an owner's review |
| Dismiss stale approvals when new commits are pushed | on | an approval covers what was reviewed, nothing added later |
| **Require status checks to pass** | on — select the `validate` job (GitHub Actions) | tests, `sdem model check` and the CI commands must pass |
| Block force pushes | on | history cannot be rewritten |
| Restrict deletions | on | `main` cannot be deleted |
| **Do not allow bypassing** (include administrators) | on | the rules apply to everyone, owners too |

**One maintainer?** GitHub does not let you approve your own pull request. For a personal copy, either add a second reviewer (a colleague), or set Required approvals to **0** and keep the pull request, the code-owner rule and the status checks — then your merge is the person's act, on record. Your organisation's copy should have real reviewers.

## 3. What changes after it is on

- All changes — yours, Claude Code's, Copilot agents' — go through a branch and a pull request; `git push` to `main` is refused.
- Claude Code works on a branch and opens a pull request only with your approval; you review and merge.
- The agent platform's flow is unchanged: agents propose change sets on a branch; a person reviews and merges (docs/design/sdem-agent-platform-design.md).

## 4. Check it works

Try `git push` of a small change straight to `main` — it should be refused. Then open a pull request: it should show the `validate` check and ask for a code owner's review.
