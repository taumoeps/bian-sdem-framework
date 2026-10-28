# SDEM — Setting up GitHub Copilot

> **Before agents work on real data:** turn on branch protection for `main` — [`sdem-repository-protection.md`](sdem-repository-protection.md). Without it, a person's approval is a practice, not a control.

> How to set up a GitHub account and GitHub Copilot so the SDEM agents, prompt files and skills work in VS Code. Then run the spike ([`sdem-agent-platform-spike.md`](sdem-agent-platform-spike.md)). Written 2026-10-28 — Copilot plans, prices and feature names change; check the linked GitHub pages for the current details.

## What is in the project

| Folder / file | What it is | How you use it in VS Code |
|---|---|---|
| `.github/copilot-instructions.md` | SDEM's ground rules for Copilot | read automatically by every Copilot chat in this project |
| `.github/agents/` | 5 custom agents: `sdem-orchestrator`, `sdem-a1-business`, `sdem-a2-bian`, `sdem-a3-application`, `sdem-a4-technology` | pick one in the chat's **agent picker** |
| `.github/prompts/` | prompt files — `/sdem-explain`, `/sdem-fix`, `/sdem-review`, `/sdem-impact-note`, `/sdem-pr`, `/aid-explain`, `/sdem-onboarding-review`, `/sdem-process-events`, `/sdem-layer-work`, `/example3-rehost` | type `/` in the chat |
| `.github/skills/` | skills: `sdem-change-sets`, `sdem-records`, `sdem-approve-links`, `sdem-trace-impact`, `sdem-onboard-designs` | loaded by Copilot when relevant; or type `/` and the skill name |

No MCP servers and no API keys are used — SDEM runs through its `sdem` command in the terminal.

## Steps

### 1. A GitHub account

Sign up at **github.com/signup** (or use an existing account). Turn on two-factor authentication (*Settings → Password and authentication*).

**Use a personal account for this project.** It holds public and made-up data only. Never put an employer's architecture data in it, and follow your organisation's rules for any work account (for example, no MCP on Copilot).

### 2. A GitHub Copilot plan

Choose a plan at **github.com/features/copilot/plans**.

| Plan | For SDEM |
|---|---|
| **Free** | enough to try the chat, prompt files and a layer agent; chat and agent use is limited per month |
| **Pro** (paid, individual) | **recommended** for the agent platform: agent mode, subagents (the orchestrator calling the layer agents) and longer sessions use the plan's monthly allowance of premium requests |
| Pro+ / Business / Enterprise | more allowance and models; Business / Enterprise are managed by an organisation |

Sources disagree on 2026 billing details (premium requests vs. usage-based credits) and on which features the Free plan includes — check GitHub's plans page before choosing. If subagents are not offered on your plan, the orchestrator can still plan the work and you hand each layer's work to its agent yourself (the handoff button, or `/sdem-layer-work`).

### 3. VS Code and the Copilot extension

1. Install **VS Code** (code.visualstudio.com).
2. Open the SDEM project folder (*File → Open Folder…*). When VS Code asks whether you **trust the authors** of the folder, choose **Yes** — agents, prompt files and skills load only in a trusted folder.
3. Accept the **recommended extensions** prompt (GitHub Copilot Chat, Python, Markdown Preview Mermaid Support), or install *GitHub Copilot Chat* from the Extensions view.
4. **Sign in:** the Accounts icon (bottom left) → *Sign in with GitHub to use GitHub Copilot*. The Copilot icon in the status bar shows your plan when signed in.

### 4. SDEM itself

In the terminal pane (*View → Terminal*):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
sdem --help
```

(Details: the user guide [`sdem-workbench-user-guide.md`](sdem-workbench-user-guide.md) §3.)

### 5. Choose a model

Open Copilot Chat (**Ctrl+Alt+I**, Mac **⌃⌘I**). The **model picker** at the bottom of the chat lists the models your plan allows. The SDEM agents do not fix a model — they use the one you pick. For the agent platform, choose a strong reasoning model; for quick explanations a smaller one is fine. Some models count more against the monthly allowance — the picker shows a multiplier.

### 6. Check everything loaded

| Check | Expect |
|---|---|
| open the **agent picker** in the chat | the five `sdem-…` agents are listed |
| type **`/`** in the chat | the nine SDEM prompts (and the skills) are listed |
| pick `sdem-a4-technology` and ask *"Run `sdem --help`."* | Copilot runs it in the terminal (approve the command when asked) |
| *Configure Tools* (tools icon in the chat) | **Run Subagent** is available for the orchestrator |

If the agents do not appear, check that the folder is trusted and that VS Code is up to date (*Help → Check for Updates*); older versions called custom agents *chat modes*.

### 7. Run the spike

Follow [`sdem-agent-platform-spike.md`](sdem-agent-platform-spike.md) — nine steps that confirm the agents work in your set-up; the prompt `/example3-rehost` runs step S3 for you. Record the results in its table.

## Using it day to day

| You want to … | In Copilot Chat |
|---|---|
| understand an `sdem` output | `/sdem-explain` |
| fix a check error | `/sdem-fix` |
| review proposed links | `/sdem-review` |
| write an impact note | `/sdem-impact-note` |
| draft a pull request | `/sdem-pr` |
| let the agents carry a change | pick the layer agent for the change; then `/sdem-process-events` (orchestrator) |

The agents propose and explain; **you approve**, by merging the pull request.
