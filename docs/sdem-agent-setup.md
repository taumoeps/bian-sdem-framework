# SDEM — AI agent setup guide

> **Status: current guide.** How to use SDEM with an AI agent — GitHub Copilot, Claude Code, OpenAI Codex or Gemini CLI — and with SDEM's own Copilot agents. Agent products, plans and menus change; check the vendor's pages if a step differs. How far each platform has been proven is kept in the [readiness assessment](evidence/agent-cli-readiness.md).

> **Before agents work on real data:** turn on branch protection for `main` ([repository protection](sdem-repository-protection.md)), and work through the agent rows of the [adoption checklist](sdem-adoption-checklist.md). Without them, a person's approval is a practice, not a control. Until then, use made-up data only.

## 1. Overview

SDEM links an organisation's architecture across four layers:

| Layer | Architecture | What it holds |
|---|---|---|
| A1 | Business | capabilities, value streams, processes and activities |
| A2 | BIAN | service domains, service operations and business objects |
| A3 | Application | applications, components, APIs, interfaces and data |
| A4 | Technology | platforms, infrastructure, networks and deployments |

It gives you a command line (`sdem`), a metamodel, a rules engine that proposes links, a knowledge graph and governance controls. SDEM contains no AI: the same command always gives the same answer. AI agents use it through the same command line and a shared set of instructions and skills.

### Two ways to work

| | Mode 1 — your own agent + SDEM skills | Mode 2 — SDEM's Copilot agents |
|---|---|---|
| **What** | the agent you already use — GitHub Copilot, Claude Code, Codex or Gemini CLI — reads SDEM's instructions and skills and runs `sdem` | five ready-made GitHub Copilot agents: an orchestrator and one agent per layer (A1–A4) |
| **For** | everyday questions: query, check, trace, impact, explain | specialist work on one layer, and changes that run across layers |
| **Needs** | any of the four agents | GitHub Copilot in VS Code |

Both use the same `sdem` command, the same architecture data, the same rules and the same governance. **Start with Mode 1**; reach for Mode 2 when a change touches several layers.

## 2. How it fits together

### 2.1 Mode 1 — your own agent

```text
Architect
   |
   v
Your AI agent  (GitHub Copilot · Claude Code · Codex · Gemini CLI)
   |
   +-- SDEM skills: records · trace & impact · change sets · approve links · onboard designs
   |
   v
sdem  (the command line: checks every request against the metamodel)
   |
   v
Your workspace: A1 · A2 · A3 · A4, approved links, knowledge graph
```

The agent decides which SDEM operation is needed; the skills teach it how; `sdem` carries it out and enforces the rules.

### 2.2 Mode 2 — SDEM's Copilot agents

```text
                 Architect
                     |
                     v
              SDEM orchestrator
                     |
      +--------+-----+-----+--------+
      v        v           v        v
   A1 agent  A2 agent   A3 agent  A4 agent
      \        |           |        /
       +-------+--- sdem --+-------+
                     |
       change sets, change events, work items
                     |
                     v
               Your workspace
```

The layer agents never talk to each other. A layer agent changes its own layer through a **change set**; `sdem` records the **change event** and its impact; the orchestrator turns the event into **work items** for the layers affected and calls their agents; each answers with its own change set. The architect makes every decision.

## 3. The parts

| Part | What it does | Needed? |
|---|---|---|
| SDEM core and the `sdem` command | the rules, the data, every operation | yes |
| SDEM skills | step-by-step know-how for an agent | recommended |
| `AGENTS.md` | the rules every agent follows — the same file for all four platforms | recommended |
| your AI agent | understands your request, runs `sdem`, explains the result | for AI-assisted work |
| SDEM orchestrator and A1–A4 agents (Copilot) | specialist and cross-layer work | optional |
| MCP server | another way to connect agents | not provided — every platform runs `sdem` directly ([why](design/sdem-agent-cli-spec.md#why-no-mcp)) |
| Agent2Agent (A2A) protocol | messages between separately hosted agents | not needed — agents coordinate through SDEM's records |

**In short:** the command line provides the capabilities, the skills and `AGENTS.md` provide the instructions, and the agent provides the reasoning.

### 3.1 What every command gives an agent

- `--json` on every command: one JSON object, starting with `"sdem": {"version", "command"}`; failures too — `{"error": {"code", "message", "hint"}}`.
- `sdem commands --json`: every command and option, for the agent to discover.
- `--dry-run` on every command that writes: what it would write, nothing written.
- `--limit N` to keep answers short; consistent exit codes (0 OK, 1 refused by a check, 2 usage or input error, 3 internal error).
- Edits made outside `sdem` are noticed (`sdem check` lists them).

In full: [built for agents](design/sdem-agent-cli-spec.md).

### 3.2 The skills

| Skill | For |
|---|---|
| `sdem-records` | understanding and writing architecture records |
| `sdem-trace-impact` | tracing dependencies and assessing the impact of a change |
| `sdem-change-sets` | preparing and proposing a change to a layer |
| `sdem-approve-links` | preparing a link for a person to approve, with its evidence |
| `sdem-onboard-designs` | reading existing designs (e.g. a Confluence export) into SDEM |

They are one set of files, installed into each platform's skills folder; they do not need SDEM's Copilot agents.

---

# Part A — Install and set up

## 4. What you need

- **Python 3.10 or later** and **Git**.
- **Your agent**, installed and signed in under your organisation's rules:
  - GitHub Copilot: VS Code with GitHub Copilot Chat ([§6](#6-github-copilot--account-plan-vs-code)).
  - Claude Code, OpenAI Codex or Gemini CLI: installed as its vendor describes, able to run terminal commands in your folder.
- **Made-up data** for the first tries.

**Which account.** *Learning, with SDEM's made-up examples:* a personal account is fine. *Real work, in your organisation's workspace repository:* your **organisation's** account and licence, under its rules (for example, no MCP) — never a personal account with employer data.

## 5. Install SDEM and the agent files

**Where.** For real work, in your organisation's **workspace repository** (from [the template](../templates/workspace-repo/README.md)), which pins one SDEM release in `requirements.txt`. To try it out, any empty folder.

**1. A Python environment** — in a terminal, in the folder:

```bash
python3 -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
```

**2. SDEM** — pin a release (the tags are on the [releases page](https://github.com/taumoeps/bian-sdem-framework/releases); never `main`):

```bash
pip install -r requirements.txt        # in a workspace repository (the pin is in the file)
pip install "sdem @ git+https://github.com/taumoeps/bian-sdem-framework@vX.Y.Z"   # anywhere else (vX.Y.Z: the release tag you chose)
sdem --version
sdem commands --json                   # what an agent can run
```

**3. The agent files** — preview, then install:

```bash
sdem agents install --dry-run
sdem agents install                    # all four platforms; or --platform copilot claude codex gemini
```

This writes, matching the SDEM version you installed:

```text
your-folder/
├── AGENTS.md                      the rules for every agent (Codex reads it; the others are pointed to it)
├── CLAUDE.md                      one line, @AGENTS.md — for Claude Code
├── sdem-agents.json               what was installed (so a later install keeps your team's own changes)
├── .claude/skills/                SDEM's skills, for Claude Code
├── .agents/skills/                the same skills, for Codex and Gemini CLI
├── .gemini/settings.json          tells Gemini CLI to read AGENTS.md
└── .github/
    ├── copilot-instructions.md    SDEM's ground rules for Copilot
    ├── agents/                    the five SDEM agents (orchestrator, A1–A4)
    ├── prompts/                   prompt files: /sdem-explain, /sdem-fix, /sdem-review, …
    ├── skills/                    the same skills, for Copilot
    └── sdem-copilot.json          what was installed for Copilot
```

Commit them. **Run `sdem agents install` again after upgrading SDEM**: it updates the files and keeps any your team has changed (it lists them; `--force` replaces them). If your team already has its own `.gemini/settings.json`, it is kept — add `"AGENTS.md"` to its `context.fileName` list.

Installing the agent definitions does not start any agent: they become available to pick, or to be called by the orchestrator.

## 6. GitHub Copilot — account, plan, VS Code

1. **A GitHub account** (github.com/signup), with two-factor authentication on.
2. **A Copilot plan** (github.com/features/copilot/plans). *Free* is enough to try the chat, prompt files and a layer agent. *Pro* or an organisation plan is recommended for Mode 2: agent mode and subagents (the orchestrator calling the layer agents) use the plan's monthly allowance. If subagents are not offered on your plan, the orchestrator can still plan the work and you hand each layer's work to its agent yourself (the handoff button, or `/sdem-layer-work`).
3. **VS Code** (code.visualstudio.com) → open the folder (*File → Open Folder…*) → **trust the folder** when asked (agents, prompt files and skills load only in a trusted folder) → install **GitHub Copilot Chat** (accept the recommended extensions) → sign in (Accounts icon, bottom left).
4. **A model:** open Copilot Chat (Ctrl+Alt+I, Mac ⌃⌘I) and pick one in the model picker. The SDEM agents do not fix a model; for Mode 2 choose a strong reasoning model.
5. **Check everything loaded:**

| Check | Expect |
|---|---|
| the chat's **agent picker** | the five `sdem-…` agents |
| type **`/`** in the chat | SDEM's prompts and skills |
| agent mode, ask *"Run `sdem commands --json`"* | Copilot runs it in the terminal (approve the command when asked) |
| *Configure Tools* (tools icon) | **Run Subagent** available, for the orchestrator |

If the agents do not appear, check the folder is trusted and VS Code is up to date (older versions called custom agents *chat modes*). If `sdem` is not found in the agent's terminal, activate the environment there, or use `.venv/bin/sdem` (Windows `.venv\Scripts\sdem`).

## 7. Claude Code, Codex, Gemini CLI

Start the agent **in the folder** where you ran `sdem agents install` — it reads its instructions when it starts there:

| Agent | Reads |
|---|---|
| Claude Code | `CLAUDE.md` → `AGENTS.md`; skills in `.claude/skills/` |
| OpenAI Codex | `AGENTS.md`; skills in `.agents/skills/` |
| Gemini CLI | `.gemini/settings.json` → `AGENTS.md`; skills in `.agents/skills/` |

**Check:** ask *"Run `sdem commands --json` and tell me which instructions you are following."* It should run the command and name `AGENTS.md`.

## 8. A made-up workspace to practise on

Copy SDEM's synthetic payments example into your folder:

```bash
git clone --depth 1 --branch vX.Y.Z https://github.com/taumoeps/bian-sdem-framework.git sdem-source
mkdir -p workspaces
cp -R sdem-source/examples/payment-initiation workspaces/payments      # Windows: Copy-Item -Recurse
sdem check --workspace workspaces/payments --json                      # it follows the metamodel
sdem build --workspace workspaces/payments --out workspaces/payments/graph --json   # the knowledge graph
```

The graph is what trace and impact read.

---

# Part B — Mode 1: your own agent

## 9. Everyday use

The recommended start. You do not pick an SDEM agent; ask your agent in plain words and say *"using SDEM"*. Three examples:

**Query.**
```text
Using SDEM, which applications support the Payment Initiation service domain in workspaces/payments?
Show the links and their evidence. Do not change any files.
```

**Trace.**
```text
Using SDEM, trace everything that depends on INF-K8S-PAY-PROD — applications, BIAN service domains,
business. Approved links only.
```
The agent runs `sdem trace INF-K8S-PAY-PROD --direction up --graph workspaces/payments/graph --json`; the `sdem-trace-impact` skill tells it how to read the result.

**Impact.**
```text
Using SDEM, what would rehosting INF-K8S-PAY-PROD affect? Which records need a design change and which
only a review? Do not change any files.
```
The agent runs `sdem impact INF-K8S-PAY-PROD --change rehost --graph workspaces/payments/graph --json`. SDEM works out the impact; you review the conclusions.

**In Copilot,** prompt files help too:

| You want to … | Type |
|---|---|
| understand an `sdem` output | `/sdem-explain` |
| fix a check error | `/sdem-fix` |
| review proposed links | `/sdem-review` |
| write an impact note | `/sdem-impact-note` |
| draft a pull request | `/sdem-pr` |

---

# Part C — Mode 2: SDEM's Copilot agents

## 10. The specialist agents

| Agent | Owns |
|---|---|
| `sdem-orchestrator` | coordination: change events, work items, reporting — changes no layer |
| `sdem-a1-business` | business capabilities, processes and activities |
| `sdem-a2-bian` | BIAN service domains and operations |
| `sdem-a3-application` | applications, components and interfaces |
| `sdem-a4-technology` | technology: platforms, infrastructure and deployments |

**Work with one directly** — pick it in the agent picker:

```text
(sdem-a3-application) Review the Payments Hub application architecture in workspaces/payments: its
components and interfaces, and any gaps. Use SDEM for the facts. Do not change any files.
```

```text
(sdem-a4-technology) Review the technology behind Payments Hub: the production Kubernetes platform, its
deployments and what it hosts. Are the records complete? Do not change any files.
```

A layer agent changes only its own layer (SDEM refuses anything else — control CTL-19) and never approves.

**Ask your regular Copilot agent to delegate** to a specialist — *where your Copilot supports subagents* (not yet verified):

```text
Delegate a read-only review of the Payments Hub application architecture to the sdem-a3-application agent,
and show me its findings and which agent produced them. Do not change any files.
```

## 11. Changes across layers — the orchestrator

For changes that reach several layers: replacing or rehosting a platform, retiring an application, a new business capability, a process change with application impact. Not needed for questions.

**How a cross-layer change runs** — the example of rehosting the production Kubernetes platform (the prompt `/example3-rehost` runs the first step on the made-up data):

1. **The layer agent drafts the change.** With `sdem-a4-technology`: *"Draft a change set in workspaces/payments that rehosts INF-K8S-PAY-PROD to the new cluster; I am &lt;your name&gt;."* It writes a change set and runs `sdem change propose …` — SDEM checks it, applies it to A4 only, and records a **change event with its impact** (which applications, links and layers are affected).
2. **The orchestrator plans the work.** Pick `sdem-orchestrator` and type `/sdem-process-events workspaces/payments <your name>`. It runs `sdem work plan --event CE-…`: one **work item** per affected layer — only the layers SDEM's impact names.
3. **The layer agents do their part.** The orchestrator calls each agent as a subagent (or you hand the work over: the handoff button, or `/sdem-layer-work`). Each claims its work item (`sdem work claim`), answers with its own change set, and SDEM records the next event.
4. **New links are proposed, never approved.** The orchestrator runs `sdem link …` and `sdem review …` and reports.
5. **You decide.** You review the change sets and approve links (`sdem approve`, with evidence), and merge the pull request.

A round limit stops changes bouncing between layers forever (an agent may lower it, never raise it — AG-S07). Picking the orchestrator directly in the chat avoids relying on nested delegation from another agent.

**How the agents coordinate.** Through SDEM's records, not by talking to each other: an agent finishes a task → SDEM records the change event or work-item step → the orchestrator reads it and assigns what follows → the orchestrator reports to you. This keeps every step traceable, avoids circular delegation and keeps each layer with its owner. It uses Copilot's subagents and SDEM's coordination records; it does not need the Agent2Agent protocol.

## 12. Later: changes that start themselves

The longer-term aim is **event-driven orchestration**: a change in one layer — say a new business requirement in A1 — raises a change event that starts the orchestrator automatically, which proposes the follow-on changes in A2–A4 for the architect to approve. SDEM already has the change events, impact, work items, orchestrator and layer agents. **Starting the agents automatically from a change event is not built**: it needs an approved trigger (for example a CI workflow). Even then, the aim is automatic impact and proposals — never automatic approval.

---

# Part D — Governance

## 13. What agents may and may not do

**Agents may:** query, trace and work out impact; prepare records and change sets; propose links; review evidence; explain.

**Agents must not:** approve a link; act as a person (put a person's name on a decision that person did not ask for); edit the architecture files directly (`a1…a4-*.json`, `mappings.json`) instead of using change sets; change another layer; treat an *inferred* record as confirmed.

**What enforces it:**

| Control | Kind | Where |
|---|---|---|
| a decision (approve, load, start a workspace, confirm or reject an inferred record, accept an edit) takes a person's name; an agent's name is refused | preventive | SDEM (CTL-21) |
| a layer agent changes only its own layer; the orchestrator none; cross-layer links only from the rules engine | preventive, when agents use `sdem change` | SDEM (CTL-19, CTL-20) |
| an edit made outside `sdem` is listed by `sdem check` and fails `sdem check --require-recorded` | detective | SDEM (AF-07) |
| who actually typed a person's name; what an agent's shell can write | — SDEM cannot know | the repository and the machine: branch protection with code-owner review, the CI switch `SDEM_REQUIRE_RECORDED: '1'`, the agent's file access limited to the repository |

```bash
sdem check --workspace workspaces/payments --require-recorded --json
```

Fails if a layer file or the registry changed since SDEM last wrote it. A person accepts their own edit with `sdem change adopt --workspace … --layer A1 --person <name> --reason "…"`. It is a detective control — not a substitute for repository review or access limits.

## 14. Which way for which job

| Activity | Use |
|---|---|
| general questions, tracing, impact | your agent (Mode 1) |
| a review of one layer | that layer's SDEM agent, when useful |
| a change across layers | the SDEM orchestrator |
| changes that start themselves | not built yet ([§12](#12-later-changes-that-start-themselves)) |
| decisions and approvals | you |

---

# Part E — Checks

## 15. Verification checklist

**Command line and skills**
- [ ] `sdem --version` shows the pinned release; `sdem commands --json` runs
- [ ] `sdem agents install` ran; the files are committed
- [ ] your agent runs `sdem` and names `AGENTS.md` (or Copilot's instructions) as its rules
- [ ] the practice workspace passes `sdem check`; the graph builds
- [ ] your agent completes a trace and explains an impact correctly

**Copilot's SDEM agents** — the [spike checklist](sdem-agent-platform-spike.md), eleven steps (S1–S11)
- [ ] the five agents appear; each completes a read-only review of its layer
- [ ] the orchestrator calls a layer agent as a subagent and gets its findings back
- [ ] work items and change events are recorded; ownership holds; nothing is approved by an agent

**The same scenario on every platform** — in a checkout of the SDEM repository:
- [ ] `python scripts/agent_eval.py prepare <empty folder>` → give the agent `TASKS.md`, one task at a time → `python scripts/agent_eval.py grade <folder>` passes; a reviewer ticks the transcript items in `TASKS.md`

**Before real data**
- [ ] your organisation allows the agent, and the data stays in approved services
- [ ] branch protection, code-owner review and the CI checks (including `SDEM_REQUIRE_RECORDED`) are on
- [ ] the agent workflows passed in a pilot ([pilot plan](sdem-pilot-plan.md))

## 16. In short

Use **your own agent with SDEM's skills** for everyday architecture work; use **SDEM's orchestrator and layer agents** for changes across layers. `sdem` does the work deterministically and enforces the rules; the orchestrator coordinates; each layer agent keeps its layer; **you keep every decision**. Where each platform stands: the [readiness assessment](evidence/agent-cli-readiness.md).
