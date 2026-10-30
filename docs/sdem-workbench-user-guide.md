# SDEM Workbench — User Guide

> **Status: current guide (v0.9.11) — the one full command reference is §7.**

> For architects who are new to SDEM. No prior knowledge assumed. Every command and output in this guide was run on the examples in this project (2026-10-28).
>
> Related: [read this first](sdem-overview.md) (what SDEM is) · [glossary](glossary.md) (every term) · [configuration](sdem-configuration.md) and [administration](sdem-administration.md) (setting SDEM up for a team).

**Contents:** [1 What SDEM is](#1-what-sdem-is--in-two-minutes) · [2 Key words](#2-key-words) · [3 Set up](#3-set-up--once) · [4 The workbench screen](#4-the-workbench-screen) · [5 Quick start](#5-quick-start--15-minutes) · [6 Your architecture data](#6-your-architecture-data) · [7 Command reference](#7-command-reference) · [8 Workflow examples](#8-workflow-examples) · [9 Working with Copilot](#9-working-with-copilot) · [10 Rules you must know](#10-rules-you-must-know) · [11 Troubleshooting](#11-troubleshooting) · [12 Questions people ask](#12-questions-people-ask) · [13 Where to go next](#13-where-to-go-next)

---

## 1. What SDEM is — in two minutes

Every organisation describes its architecture in four separate places, usually kept by different teams in different tools:

| | Architecture | Describes | Example |
|---|---|---|---|
| **A1** | Business | capabilities, value streams, processes | *Initiate Payment*, *Capture and validate payment instruction* |
| **A2** | Service Domain (BIAN) | the BIAN service domains and their operations — the banking industry's standard building blocks | *Payment Initiation*, *Initiate Payment Instruction* |
| **A3** | Application | applications, components, APIs, data | *Payments Hub*, `POST /payment-instructions` |
| **A4** | Technology | platforms, clusters, deployments | *Managed Kubernetes — payments (production)* |

The hard questions cross all four: *Which applications support this capability? What breaks if we move this cluster? What would a new business design need underneath?* Nobody can answer them if the four architectures are not **linked**.

**SDEM — the Service Domain Enterprise Metamodel — links them**, with BIAN in the middle as the common language:

```
 A1 Business ──uses / supported by──► A2 BIAN service domains ──realised / implemented by──► A3 Applications ──deployed on / as──► A4 Technology
```

SDEM gives you:

- a **metamodel** — what may exist in each architecture and how things may be linked, each rule with its published source;
- **checks** — your data is tested against the metamodel before it is trusted;
- an **inference engine** — proposes the links between the architectures, each with its reasoning and confidence, for **you** to approve;
- a **knowledge graph** — the checked data and approved links, which you can **trace** end to end and use for **impact analysis**;
- **AID (Architecture Inference Design)** — a planning tool that projects the architecture layers you don't have yet, from the ones you do.

You run all of it from **VS Code**: commands in the terminal, and GitHub Copilot in the chat window to help.

## 2. Key words

| Word | Means |
|---|---|
| **Architecture dataset** | one file holding one architecture (A1, A2, A3 or A4) — its records and the links inside it |
| **Record** | one thing in an architecture: a capability, a service domain, an application, a cluster … each with an `id`, `type`, `name` |
| **Link** (relationship) | a connection between records of **different** architectures, e.g. *service domain Payment Initiation* is **REALIZED_BY** *application Payments Hub* |
| **Registry** (`mappings.json`) | the file of links, each with a status: `proposed` (suggested) or `approved` (a person accepted it) |
| **Metamodel** | the rules: which record types exist, which links are allowed, what evidence a link needs |
| **Inference engine** | proposes links by applying the metamodel to your data; never approves |
| **Graph store** | a folder holding the checked datasets and approved links as a knowledge graph — what trace, impact and the view read |
| **Trace** | follow the links from a record down (to technology) or up (to business) |
| **Impact** | which records a change (replace, rehost, retire …) affects, and how |
| **AID / projection** | Architecture Inference Design: a **projected** (planned, not real) design for the layers you don't have; ids start `PRJ-` |
| **Confidence** | how sure a proposal or projection is: 0.4 low, 0.6 medium, 0.8 high |
| **CLI** | the command line — typing `sdem …` commands in VS Code's terminal |

## 3. Set up — once

You need four things. Your IT team may install some of them for you.

| Tool | Why | Get it |
|---|---|---|
| **VS Code** | the workbench | code.visualstudio.com |
| **Python 3.10 or later** (3.13 recommended) | SDEM runs on it | Macs come with 3.9, which is too old: `brew install python@3.13` or the installer from python.org |
| **Git** | history, review and approval | git-scm.com (often already installed) |
| **GitHub Copilot** (optional) | the AI help in the chat window | a Copilot plan on your GitHub account — step by step in [`sdem-copilot-setup.md`](sdem-copilot-setup.md) |

Then:

1. **Get the SDEM project** (the tool and the made-up examples — public):
   ```bash
   git clone https://github.com/taumoeps/bian-sdem-framework.git && cd bian-sdem-framework
   ```
   Your organisation's **real** data is in its private workspace repository, set up from [`templates/workspace-repo`](../templates/workspace-repo/README.md) — its README installs SDEM the same way, pinned to a release.
2. **Open it in VS Code:** *File → Open Folder…* → choose the `bian-sdem-framework` folder. When VS Code offers to install the **recommended extensions** (Python, GitHub Copilot Chat, Markdown Preview Mermaid Support), accept.
3. **Open the terminal pane:** *View → Terminal* (shortcut **Ctrl+`**).
4. **Find your Python 3.10 or later.** `python3 --version` — if it says 3.10 or later, use `python3` below. If it says 3.9, or `python3.13` gives *command not found* after you installed it, it is in Homebrew's folder:
   ```bash
   for d in /opt/homebrew/bin /usr/local/bin; do ls "$d" 2>/dev/null | grep "^python3\.1[0-9]*$" | sed "s|^|$d/|"; done
   ```
5. **Install SDEM** into a private Python environment for this project:
   ```bash
   python3.13 -m venv .venv           # or the full path you found, e.g. /opt/homebrew/bin/python3.13 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -e .
   ```
   If `pip` says *File "setup.py" … not found* or *requires a different Python*, the `.venv` was made with an old Python: `rm -rf .venv` and make it again with 3.13.
6. **Check it works:**
   ```bash
   sdem --help
   ```
   You should see the list of commands, starting with `check J1 check architecture datasets and registry against the metamodel`.

Each time you open a new terminal later, run the `activate` line from step 5 again. If you cannot install anything, every command also works as `python3 -m sdem …` from the project folder.

## 4. The workbench screen

```
┌─ VS Code — SDEM project ─────────────────────────────────────────────────────────────────────┐
│ EXPLORER               │ EDITOR                               │ COPILOT CHAT                 │
│ the project's files:   │ the file you opened, e.g. a dataset  │ ask for help in plain words  │
│ ▸ docs/      guides    │                                      │                              │
│ ▸ examples/  workspaces   │                                      │ "explain this output"        │
│ ▸ metamodel/ metamodel  │                                      │ "which command shows …?"     │
│ ▸ schema/              ├──────────────────────────────────────┤ "draft the impact note"     │
│ ▸ sdem/      the code  │ TERMINAL — where you run sdem        │                              │
│                        │ $ sdem check …                       │                              │
│                        │ OK: level A1 …                       │ [ Ask Copilot …            ] │
└────────────────────────┴──────────────────────────────────────┴──────────────────────────────┘
```

| Part | Open it | Use it for |
|---|---|---|
| **Explorer** | the file icon on the left | find and open files |
| **Editor** | click a file | read and edit datasets and the registry |
| **Terminal** | *View → Terminal* (**Ctrl+`**) | **run SDEM** — every `sdem` command |
| **Copilot Chat** | the chat icon, or **Ctrl+Alt+I** (Mac **⌃⌘I**) | **help** — explanations, the right command, drafts |
| **Source Control** | the branch icon on the left | see your changes, commit, open a pull request |

**The one idea to remember:** you run SDEM in the **terminal**; Copilot **helps** in the chat. Copilot never approves anything and never changes real data on its own.

## 4a. The dashboards — SDEM and each workspace on one page

**Start here:**

```bash
sdem home -o work/sdem
```

and open `work/sdem/index.html` (the command prints the full `file://` address). It opens on **SDEM's architecture** — every component (the BIAN reference, the metamodel, the mapping engine, validation and approval, the knowledge graph, the four architectures, AID and its projections, change coordination, the workbench), marked built or not, each clickable for what it is, where it lives and its live figures. The other tabs show SDEM itself — its health (checked as the page is made), the metamodel (every entity type, the links allowed inside and between the architectures, the engine's rules, a clickable picture), the configuration — and **every workspace**, each linking to its own dashboard. Add your own workspaces with `--workspace <folder>` or `--root <folder of workspaces>`.

**One workspace's dashboard** on its own:

```bash
sdem dashboard --workspace examples/payment-initiation -o work/dashboard.html
```

Open `work/dashboard.html` in your browser — or in VS Code: *Command Palette → Simple Browser: Show*, then paste the file's path. It works offline and needs no AI.

| Tab | Shows |
|---|---|
| **Overview** | what needs your attention; the health of each architecture (errors, advice); how much of each is linked to the other layers; records not linked yet |
| **Review** | the links the rules engine proposes, weakest first — rule, reasoning, the evidence you need to approve, and the `sdem approve` command to copy |
| **Trace & impact** | type a record: what it depends on, what depends on it, and the impact of a change (modify, rehost, replace, retire) |
| **Matrices** | capability → service domain → application → technology, from approved links |
| **Changes & work** | change events, work items, change sets, and any hand edits waiting to be adopted |
| **AID plans** | with `--projection <folder>`: the projected design beside the real one |
| **Controls** | every control and when it was last tested |

The page is **read-only**: it shows the exact `sdem` command for every action (with a *copy* button). It is a snapshot — run `sdem dashboard` again after a change. Design: [`sdem-dashboard-design.md`](design/sdem-dashboard-design.md).

## 5. Quick start — 15 minutes

This uses the example workspace `examples/payment-initiation` — a made-up bank's payments architecture, all four layers, already linked. Type each command in the terminal.

**Step 1 — name the example folder, so commands stay short:**
```bash
E=examples/payment-initiation
```
*(Windows PowerShell: `$E="examples/payment-initiation"` — and see §11 about `a*.json`.)*

**Step 2 — check the data against the metamodel (J1):**
```bash
sdem check --workspace $E
```
(`--workspace` names the workspace folder; it is the same as listing its five files, `$E/a*.json $E/mappings.json`.) You see one `OK` line per architecture and for the registry. `WARN` lines are advice (something the metamodel expects but does not require); `ERROR` lines must be fixed.
```
OK: level A1 (synthetic-bank-payments-a1)
WARN: level A2 (synthetic-bank-payments-a2): instance BD-PAYMENTS: 0 composition links with A2.BusinessArea, RA2-01 expects at least 1 (LC-10m)
… (six WARN lines in all)
OK: level A2 (synthetic-bank-payments-a2)
OK: level A3 (synthetic-bank-payments-a3)
OK: level A4 (synthetic-bank-payments-a4)
OK: mappings #1
```
The six warnings are expected for this example: the made-up BIAN layer leaves out some detail the metamodel recommends — a business area, the service groups and control records of two service domains, and the attributes of one business object. `OK` on every layer means the data is accepted.

**Step 3 — build the knowledge graph (J4):**
```bash
sdem build --workspace $E --out work/graph
```
```
WARN: … (the same six warnings)
build 1 accepted: a1-business.graph.json (16 nodes, 14 edges), …, federated.graph.json (26 nodes, 18 edges)
```
`work/` is your own scratch folder; Git ignores it.

**Step 4 — trace a business process down to technology (J5):**
```bash
sdem trace PRC-PAY-01 --direction down --graph work/graph
```
```
baseline: graph store work/graph, build 1 (A1 2026.10, A2 2026.10, A3 2026.10, A4 2026.10)
DOWNSTREAM (depends on):
PRC-PAY-01 'Capture and validate payment instruction'  [A1 Business · Business Process]
└─ -USES_DOMAIN-> SD-PI 'Payment Initiation (synthetic selection)'  [A2 BIAN · Service Domain]  (PAY-003)
   └─ -REALIZED_BY-> APP-PAY-HUB 'Payments Hub'  [A3 Application · Application Component]  (PAY-106)
      ├─ -DEPLOYED_ON-> INF-K8S-PAY-PROD 'Managed Kubernetes — payments (production)'  [A4 Technology · System Software]  (PAY-108)
      ├─ -DEPLOYED_AS-> DEP-PAYHUB-PROD 'Payments Hub — production'  [A4 Technology · Deployment]  (PAY-109)
      ├─ -DEPLOYED_AS-> DEP-PAYHUB-UAT 'Payments Hub — UAT'  [A4 Technology · Deployment]  (PAY-110)
      └─ -DEPLOYED_ON-> INF-K8S-PAY-UAT 'Managed Kubernetes — payments (UAT)'  [A4 Technology · System Software]  (PAY-113)
```
Read it as: *the process uses the Payment Initiation domain, which the Payments Hub realises, which runs on the production Kubernetes cluster.* Each record shows its layer (`[A2 BIAN · Service Domain]`). The codes in brackets (`PAY-003`) are the **approved connections** the chain follows — each one's id in `mappings.json`; under the tree, *CONNECTIONS FOLLOWED* lists who approved each, when, and the evidence.

**Step 5 — see it as a picture (J7):**
```bash
sdem view --graph work/graph
```
Open `work/graph/view.html` in your browser. Four bands, A1 to A4; click a record to see its details and links; choose *Trace: down* to highlight a chain.

**Step 6 — ask Copilot.** Open the chat and type:
> *Explain the trace output in the terminal in plain words. Which links does it rely on?*

Copilot reads the terminal output and explains it, naming the links. If it suggests a command, you decide whether to run it.

**You have now used the workbench.** Next, try the workflow examples in §8 — they are what you will do with your own architecture.

## 6. Your architecture data

### 6.1 The files

A workspace is a folder with up to five data files — and, once you use them, the records SDEM keeps beside them (loads, gaps, BIAN updates; [the full list](sdem-architecture.md#inside-a-workspace)):

| File | Holds |
|---|---|
| `a1-business.json` | the business architecture: capabilities, value streams, processes, activities, business objects, roles |
| `a2-service-domain.json` | the BIAN layer: the service domains you use, their operations, business objects |
| `a3-application.json` | applications, components, interfaces, APIs, data entities |
| `a4-technology.json` | platforms, clusters, system software, environments, deployments |
| `mappings.json` | the registry: the links between the architectures |

Eight example workspaces are in `examples/` (`payment-initiation`, `card-fraud-alerts`, `digital-lending`, `trade-finance`, `legacy-core-ledger`, `acquired-fintech`, `customer-onboarding`, and `reference-structure` — a test workspace with one example of every kind of thing and link, not a bank). **Start your own workspace by copying one** and changing its contents.

### 6.2 What a record looks like

Every record has an `id`, a `type`, a `version` and a `name`; most have a `description` and `attributes`. An application, from `a3-application.json`:

```json
{
  "id": "APP-PAY-HUB",
  "type": "A3.ApplicationComponent",
  "version": "7.1",
  "name": "Payments Hub",
  "lifecycle_status": "active",
  "description": "The bank's payment initiation platform: captures instructions …",
  "attributes": {
    "deployed_on": ["INF-K8S-PAY-PROD", "INF-K8S-PAY-UAT"],
    "deployed_as": ["DEP-PAYHUB-PROD", "DEP-PAYHUB-UAT"],
    "owner": "ROLE-PAY-OFFICER"
  }
}
```

A business process, from `a1-business.json` — note `invokes`: naming the BIAN operations a process uses is the strongest help you can give the engine:

```json
{
  "id": "PRC-PAY-01",
  "type": "A1.BusinessProcess",
  "version": "1.0",
  "name": "Capture and validate payment instruction",
  "attributes": { "invokes": ["SO-PI-01", "SO-PI-02"], "criticality": "high" }
}
```

Links **inside** one architecture go in that file's `relationships` list, e.g. `{"source": "APP-PAY-HUB", "kind": "composition", "target": "CMP-PAY-CAPTURE"}` (the hub is made of the capture component). Links **between** architectures go in the registry (§8.2).

You don't need to memorise the rules: write the data, run `sdem check`, and it tells you exactly what is missing or not allowed — and Copilot can explain each message.

**Editing by hand is fine for a layer's records** — add an application to `a3-application.json`, correct a name — then run `sdem check --workspace <dir>` and open a pull request. Two things are never edited by hand: **approved connections** (`mappings.json` — use `sdem approve`, and `--supersedes` to replace one; CI refuses an edited approved connection) and **SDEM's records** (`loads/`, `designs/`, `coordination/`). Once agents work on a layer through change sets, SDEM asks you to record a hand edit with `sdem change adopt` — it tells you when.

### 6.3 Where your real data may go

- **This project holds public and made-up data only.** Your organisation's real architecture data belongs in its **private workspace repository** ([template](../templates/workspace-repo/README.md); [operating model](sdem-operating-model.md)). `workspaces/` and `work/` are ignored here, so real data cannot be pushed to this repository by mistake.
- Diagrams previewed with the PlantUML extension are drawn **on your machine** (this project's setting; it needs Java and Graphviz — `brew install plantuml`). Never switch it to the public PlantUML server for real data.

## 7. Command reference

The *Journey* column groups commands by task: **J1** check · **J2** propose links · **J3** review and approve · **J4** build and store · **J5** trace, impact, matrices · **J6** plan missing layers (AID) · **J7** dashboards and views · **J8** explain · **J9** onboarding and your BIAN layer · **AG** agents.

**This is the one full list of SDEM's commands** — other documents show only the commands of their own task and link here. `sdem --help` lists them all; `sdem <command> --help` shows the options and a worked example. Exit codes: `0` OK, `1` issues found (or a check refused the action), `2` the command was typed wrongly or its input is unusable (a missing folder, a file that is not valid JSON), `3` an internal error in SDEM — one line; set `SDEM_DEBUG=1` to see the details. `sdem --version` shows the version.

| Command | Journey | What it does | When you use it | Typical next step |
|---|---|---|---|---|
| `sdem check --workspace <dir>` (or the files) | J1 | checks datasets and registry against the metamodel | after any change to the data | fix errors; `sdem build` |
| `sdem validate <registry>` | J1 | checks a registry or proposals file on its own (`--strict` treats warnings as errors) | after `sdem approve` or `sdem connect`, or before a pull request | `sdem check` |
| `sdem link --workspace <dir> --out <dir>` | J2 | the inference engine proposes the missing links, writes `proposals.json` and **shows them straight away**, weakest first (`--no-review` just writes them) | when data is new or changed | `sdem approve` (§8.2) |
| `sdem review <proposals.json>` | J3 | lists any proposals file again, weakest first, with rule, confidence and reasoning — `sdem link`'s, AID's (`<workspace>/aid/AID-nnn-proposals.json`), or a colleague's in a pull request | before approving | `sdem approve` (§8.2) |
| `sdem approve <id> --proposals … --workspace … --reviewer <you> --evidence <kind:ref> [--bian-release <release>]` | J3 | **you** approve a proposed link: writes a correct registry record, checks it first | after review | pull request |
| `sdem build <files> --out <dir>` | J4 | checks everything and writes the graph store | after approval, before trace and impact | `sdem trace`, `sdem view` |
| `sdem query --graph <dir> …` | J4 | finds records: `--type`, `--level`, `--where attr=value`, `--unmapped A2` (records still without a link) | to look things up | — |
| `sdem baseline <name> --graph <dir>` | J4 | freezes the graph store under a name (e.g. a release) | at milestones | — |
| `sdem home -o <dir> [--root <folder of workspaces>] [--workspace <dir>]` | J7 | the home page: SDEM's architecture, health, and a dashboard for every project (§4a) | first, and any time | open `<dir>/index.html` |
| `sdem dashboard --workspace <dir> -o <file.html>` | J7 | one workspace on one read-only page (§4a) | any time | the commands it shows |
| `sdem matrix --workspace <dir> [--md file.md]` | J5 | capability → domain → application → technology from approved links | for a report or review | — |
| `sdem trace <id> --graph <dir>` | J5 | follows links `--direction down` (to technology), `up` (to business) or both | "what does this depend on / what depends on it?" | `sdem impact` |
| `sdem trace A1|A2|A3|A4 --direction down|up|both --graph <dir>` | J5 | traces a **whole layer**: how many of its records are connected, which layers they reach, the **gaps** (records connected to nothing that way), then every chain; `--only-gaps`, `--to <layer>`, `--tree`, `--csv <file>` | "which technology supports no business? which capabilities have nothing behind them?" | `sdem matrix` |
| `sdem impact <id> --change <kind> --graph <dir> [--report file.md]` | J5 | classifies what a change affects; kinds: `modify`, `rehost`, `replace`, `retire`; `--report` writes a printable impact report | before a change | share the report |
| `sdem aid --workspace <dir> --person <you>` | J6 | **fills the workspace's gaps**: from whatever you wrote (any of A1…A4), adds the missing records to the layer files, each marked *inferred* with source, reasoning and confidence, and proposes the connections ([designing with AID](sdem-planning-with-aid.md)) | a new design | `sdem aid --workspace workspaces/payments --person jane.architect` |
| `sdem aid confirm <ids>` · `sdem aid reject <ids> --reason "…"` (`--workspace <dir> --person <you>`) | J6 | you decide on each inferred record: confirmed keeps the mark with your name; rejected is removed and never inferred again | after reviewing | |
| `sdem aid project --workspace <dir>` (or `--have <files> --catalogue <bian> --out <dir>`) | J6 | plans the layers you don't have, from the workspace's business and BIAN layers — kept apart in `<workspace>/plans/` (planning, not real data) | early design, scoping | `sdem view --projection`, `sdem explain` |
| `sdem aid check <dir>` · `sdem aid gaps <dir> --workspace <dir>` (or `--actual <files>`) | J6 | checks a projection; compares it with a real design | later, when the real design exists | — |
| `sdem view --graph <dir> [--projection <dir>] [-o file.html]` | J7 | writes the HTML picture | to see and share | open in a browser |
| `sdem explain <id> --proposals <file>` · `--projection <dir>` | J8 | why one link or projected element exists: rule, published source, evidence, reasoning, confidence | when you question a proposal | approve, reject or fix the data |
| `sdem change propose <file> --workspace <dir> --agent … --person …` | AG | a layer's change set: checked before it lands, then its impact recorded as a change event | agent platform (§9a) | the orchestrator plans the work |
| `sdem change revert <CS-id> --workspace <dir> --agent … --person …` | AG | undo the latest change set of a layer — restores it exactly, on record | a change was wrong | rebuild the graph store |
| `sdem connect <source> <TYPE> <target> --workspace <dir> --reviewer <you> --evidence <kind:ref> --rationale "<why>"` | J3 | **you** state a connection the engine did not propose (e.g. a BIAN service domain *realised by* an application) — the same checks as `sdem approve` | when you know a connection the design does not show in detail | pull request |
| `sdem bian update --root workspaces --a2 bian/a2-service-domain.json --person <you>` | J9 | brings every workspace's BIAN layer up to date with your shared one — checked; never strands an approved connection; `--dry-run` first shows what would change | after changing the shared BIAN layer | pull request |
| `sdem copilot install [--to <repo>] [--dry-run] [--force]` | AG | puts SDEM's Copilot instructions, agents, prompts and skills into your workspace repository's `.github/`, matching this SDEM version; keeps files your team changed | once after installing SDEM in a workspace repository; again after each upgrade | reload VS Code |
| `sdem change adopt --workspace <dir> --layer <A1…A4> --person <you> --reason "<what you changed>"` | AG | records a hand edit to a layer that agents work on through change sets, so their next change set starts from it | when SDEM says a dataset *was changed outside a change set* | `sdem check` |
| `sdem events --workspace <dir> [--open]` | AG | change events, their impact and open work | to see what is waiting | `sdem work plan` |
| `sdem work plan · list · claim …` | AG | work items: planned by the orchestrator, claimed and answered by the layer agents | agent platform (§9a) | `sdem change propose --work …` |
| `sdem transform inspect <export>` · `sdem transform run <export> -o <dir>` | J9 | **transforms** an export of past designs (Confluence) into candidate architecture entities, with rules: tables, draw.io and PlantUML diagrams, known names in the text, text in pictures (on-device OCR) → entities and links with their source; pictures listed for you | bringing in past designs (§8.7) | review `extraction-report.md` |
| `sdem new --workspace <dir> --person <you>` | J9 | **starts a workspace**: the four layers — A2 your BIAN layer (the shared one, or all of the base BIAN; `--no-bian` for none) — and an empty set of connections; checked, recorded in `workspace.json` |
| `sdem bian custom --workspace <dir> --only <names…> --person <you>` (or `--from <file>`, `--all`) | J9 | **narrows one workspace's BIAN layer** to the service domains it uses — checked, recorded; refuses to remove a domain an approved connection uses |
| `sdem load <candidates> --workspace <dir> --person <you> --exclude <ids>` | J9 | **loads** the candidate entities you keep into a workspace — checked first, recorded; `--a2` adds your BIAN layer; `--dry-run` | after reviewing a transform (§8.7) | `sdem link` |
| `sdem designs --workspace <dir> [--entity <id>] [--gaps] [--category …] [--status open]` | J9 | the pages onboarded designs came from, and the **gap records** — what did not fit an entity, by category; `sdem trace` also ends with an entity's pages | after a load; to find what still needs a person | — |
| `sdem bian list --base` · `sdem bian import --base --all -o <file>` (or `--only <names…>`, `--from <file>`) · `sdem bian pack <folder> -o <file>` | J9 | your **BIAN (A2) layer**: from the **base BIAN** that ships with SDEM (BIAN's public Semantic APIs 14.0.0), from your own packed BIAN (`--base <file>`), or from a folder of BIAN's files; imports the service domains you name, checked, with a report of what to confirm; `--patterns`, `--previous`; from a folder also `--descriptions`, `--objects` | once, before onboarding; again for a new BIAN release | `sdem load … --a2 <file>` |
| `sdem bian inference list` · `show <id>` · `accept` · `challenge` · `change` · `reject <id> --person <you> --reason "…"` | J9 | SDEM's **inference record**: the asset types and functional patterns it infers for the 66 BIAN service domains BIAN does not publish them for — each with source, reasoning, confidence, status and history; the import applies **accepted** entries only ([BIAN inferences](reference/bian-inferences.md)) |
| `sdem designs resolve <gap id …> --workspace <dir> --person <you> --note "<what you did>"` · `accept` (same options) · `reopen` | J9 | closes a gap — *resolved* (now recorded in an entity) or *accepted* (deliberately not modelled); reopens one; each step kept in the gap's history | working down the gaps | `sdem designs --gaps --status open` |
| `sdem commands --json` | AG | every command and its options as data, with what each supports — for an agent. On **every** command: `--json` (results and failures as JSON, marked with the SDEM version), `--limit N` (cut long lists), `--dry-run` (nothing written; what would be is listed) — [built for agents](design/sdem-agent-cli-spec.md) | "what can an agent run, and how?" | `sdem copilot install` |
| `sdem diff --git HEAD~1 <registry>` | — | proves approved links were not edited | before a pull request | — |
| `sdem migrate --workspace <dir> --person <you> [--dry-run]` | — | moves a workspace to a new metamodel version ([versioning](design/sdem-metamodel-versioning.md)) | when SDEM says the `metamodel_version` does not match | — |
| `sdem model check` · `regenerate` · `accept` · `examples` | — | maintainers: generated documents, engine acceptance tests, use-case examples | when changing the metamodel | — |

Add `--json` to most commands for machine-readable output (Copilot can read it more reliably).

## 8. Workflow examples

The diagram shows how the workflows fit together; each is then written out step by step.

```mermaid
flowchart LR
    A["8.1 Onboard data<br/>sdem check"] --> B["8.2 Link + approve<br/>sdem link · review · PR"]
    B --> C["Build the graph<br/>sdem build"]
    C --> D["8.3 Trace<br/>sdem trace · view"]
    C --> E["8.4 Impact of a change<br/>sdem impact"]
    F["8.5 Plan a new design<br/>sdem aid"] --> G["See + explain<br/>sdem view · explain"]
    G -.->|"when the real design exists"| H["sdem aid gaps"]
```

### 8.1 Onboard a workspace and fix its data

*Goal: get your four architecture datasets accepted by SDEM.*

1. Copy an example workspace as a starting point and put your records in it:
   ```bash
   cp -r examples/payment-initiation work/my-workspace
   ```
2. Check it:
   ```bash
   sdem check --workspace work/my-workspace
   ```
3. Read each `ERROR`. Example — a record without a name, and a misspelt type:
   ```
   ERROR: level A3 (synthetic-bank-payments-a3): $.instances[0]: missing required property 'name'
   ```
   `$.instances[0]` means the first record in the `instances` list. Add the name, save, run `sdem check` again. Errors can appear a batch at a time — keep going until every line is `OK`.
4. Stuck on a message? In the chat:
   > *Explain this sdem check error and show me the fix in a3-application.json.*

**Done when:** every line is `OK` (warnings are advice).

### 8.2 Link the architectures and approve the links

*Goal: the engine proposes the links between your architectures; you decide which become real.*

The example workspace already has its links approved, so to practise, start from the registry **as it was before** they were approved — the example ships it as `m1-mappings-given.json`. Work in a separate practice copy, so the other examples in this guide keep working:

```bash
cp -R examples/payment-initiation work/practice-links
cp work/practice-links/m1-mappings-given.json work/practice-links/mappings.json   # the registry before approval
```

1. **Propose** (J2):
   ```bash
   sdem link --workspace work/practice-links --out work/links
   ```
   ```
   13 proposed link(s) written to work/links/proposals.json; candidates, inference log and any design datasets in work/links/
   next: sdem review work/links/proposals.json
   ```
2. **Review** (J3):
   ```bash
   sdem review work/links/proposals.json --names work/practice-links/a*.json
   ```
   ```
   13 proposed link(s), weakest first:

     [0.6] P-RUN-011  SO-PI-04 'Retrieve Payment Instruction' -IMPLEMENTED_BY-> API-PI-04 'Get payment instruction'   rule S24
           why: … method mismatch, proposed one band lower
     [0.8] P-RUN-001  APP-PAY-HUB 'Payments Hub' -DEPLOYED_AS-> DEP-PAYHUB-PROD 'Payments Hub — production'   rule S32
     …
     [0.8] P-RUN-013  SD-PI 'Payment Initiation (synthetic selection)' -REALIZED_BY-> APP-PAY-HUB 'Payments Hub'   rule S17
           why: implements SO-PI-01 via API-PI-01 (P-RUN-007); SO-PI-02 via API-PI-02 (P-RUN-008); …
   ```
   The weakest is first: P-RUN-011 is a lower band because the operation *Retrieve* is exposed by a `POST`, not a `GET` — worth a look. *Rule S17* is the rule the engine used; to see everything behind a proposal — the rule in words, its published source, the data, the reasoning: `sdem explain P-RUN-013 --proposals work/links/proposals.json`.
3. **Decide.** Ask yourself: is this true of our architecture, and do we have the document that shows it? Copilot can help:
   > *Walk me through the proposals in work/links/proposals.json, weakest first. What evidence would I need for each?*
4. **Approve — you, with `sdem approve`.** It writes the registry record for you — a new id, status `approved`, you as reviewer, today's date and the evidence — and checks the whole registry before writing anything:
   ```bash
   sdem approve P-RUN-013 --proposals work/links/proposals.json --workspace work/practice-links \
        --reviewer your.name --evidence application_architecture_document:AA-PAYHUB-HLD#s3
   ```
   ```
   approved PAY-006: SD-PI -REALIZED_BY-> APP-PAY-HUB  (reviewer your.name, 2026-10-29, evidence application_architecture_document:AA-PAYHUB-HLD#s3)
   work/practice-links/mappings.json updated and checked. Next: commit on a branch and open a pull request — the reviewed merge makes it final; then rebuild the graph store (sdem build --workspace … --out …).
   ```
   The reviewer must be a person — try `--reviewer copilot` and SDEM refuses: `ERROR: CTL-21: the reviewer must be a person, not 'copilot' — give your own name`. To replace an old link, add `--supersedes <old id>`. The record it writes:
   ```json
   {
     "mapping_id": "PAY-006",                                  ← a new id, unique in the registry
     "source": { "id": "SD-PI", … },
     "relationship": "REALIZED_BY",
     "target": { "id": "APP-PAY-HUB", … },
     "status": "approved",                                     ← was "proposed"
     "reviewer_id": "your.name",                               ← who approved
     "approved_at": "2026-10-29",                              ← when
     "evidence": ["application_architecture_document:AA-PAYHUB-HLD#s3", "engine_rationale:…"],
     …
   }
   ```
   **The evidence a link needs depends on its type** — the engine's reasoning alone is not enough. Where two kinds are listed, **both** are needed; links that rest on BIAN's guidance also need the **BIAN release** you relied on:

   | Link | Evidence — every kind listed | Also needs |
   |---|---|---|
   | capability **SUPPORTED_BY** service domain | `business_architecture_document` **and** `domain_scope_assessment` | `--bian-release` |
   | value stream **ALIGNED_TO** business scenario | `process_model` **and** `scenario_suitability_review` | `--bian-release` |
   | process **USES_DOMAIN** service domain | `process_model` | — |
   | business object **ALIGNED_TO** BIAN business object | `business_glossary` **and** `object_alignment_review` | `--bian-release` |
   | service domain **REALIZED_BY** application | `application_architecture_document` | — |
   | service operation **IMPLEMENTED_BY** API | `api_contract` | — |
   | BIAN business object **MAPPED_TO** data entity | `data_model` | — |
   | application **DEPLOYED_ON** / **DEPLOYED_AS** technology | `deployment_design` | — |

   Write each as `kind:document-reference`, and give each kind its own `--evidence`. For example, a capability supported by a BIAN domain:
   ```bash
   sdem approve P-RUN-… --proposals … --workspace … --reviewer your.name \
        --evidence business_architecture_document:BA-PAYMENTS#cap-map --evidence domain_scope_assessment:DSA-2026-04 \
        --bian-release 14.0.0
   ```
   If something is missing, SDEM says exactly what — e.g. `evidence missing required kind(s) ['domain_scope_assessment']`, or `add --bian-release <release>`.
5. **Check:**
   ```bash
   sdem validate --strict work/practice-links/mappings.json
   sdem check --workspace work/practice-links
   ```
   Both should end with `OK`.
6. **Pull request.** In *Source Control*, commit the registry change on a branch and open a pull request. A reviewer checks it; CI runs every check. **Merging the pull request is the approval.** Copilot can draft the description:
   > *Draft a pull-request description for the link I approved in mappings.json, citing its evidence.*
7. **Rebuild the graph** (J4) and see the link in use:
   ```bash
   sdem build --workspace work/practice-links --out work/practice-graph
   sdem trace SD-PI --direction down --graph work/practice-graph
   ```
   ```
   DOWNSTREAM (depends on):
   SD-PI 'Payment Initiation (synthetic selection)'  [A2 BIAN · Service Domain]
   └─ -REALIZED_BY-> APP-PAY-HUB 'Payments Hub'  [A3 Application · Application Component]  (PAY-006)
   ```

### 8.3 Trace a capability to technology — and back

*Goal: answer "what does this depend on?" and "what depends on this?".*

```bash
sdem trace CAP-PAY-010 --direction down --graph work/graph      # business → technology
sdem trace INF-K8S-PAY-PROD --direction up --graph work/graph   # technology → business
sdem view --graph work/graph                                    # the picture; choose Trace: down or up
```

Trace follows **approved** links only. If a chain stops early, a link is missing: `sdem query --graph work/graph --unmapped A2` lists records still waiting for one — then go back to §8.2.

### 8.4 Assess the impact of a technology change

*Goal: before rehosting the production payments cluster, know what it affects.*

```bash
sdem impact INF-K8S-PAY-PROD --change rehost --graph work/graph
```
```
IMPACT of 'rehost' on INF-K8S-PAY-PROD: hosting changes only; deployment records must be superseded, functional layers unaffected

  design_change_required   A4  INF-K8S-PAY-PROD  Managed Kubernetes — payments (production)  via -
  design_change_required   A3  APP-PAY-HUB       Payments Hub  via PAY-108
  no_impact                A2  SD-PI             Payment Initiation (synthetic selection)  via PAY-108, PAY-106
  no_impact                A1  CAP-PAY-010       Initiate Payment  via PAY-108, PAY-106, PAY-001
  …
  design_change_required   A3  CMP-PAY-EXEC      Execution Gateway  via PAY-111

  mappings to supersede: PAY-108, PAY-111

  Classification is structural; an architect confirms before any design changes.
```

Read it as: *rehosting the cluster needs design changes for the Payments Hub and the Execution Gateway (and their deployment links PAY-108 and PAY-111 must be replaced); the business capability and processes are not affected.* Then in the chat:
> *Draft an impact note for rehosting INF-K8S-PAY-PROD from the impact output, with each affected record and the reason.*

Other kinds of change: `--change modify`, `--change replace` (e.g. an application is replaced), `--change retire`.

### 8.5 Plan a new design with AID

*Goal: you have only the business design; see what BIAN domains, applications and deployments it implies — before anything is built.* `sdem aid project` projects the missing layers as a **planned** design, kept apart from your real data and never approved. Step by step, with every command and output: [planning missing layers with AID](sdem-planning-with-aid.md).

### 8.6 Question a proposal or projection

*Goal: understand exactly why SDEM suggests something before you accept it.*

```bash
sdem explain P-RUN-001 --proposals work/links/proposals.json     # a proposed link
sdem explain SD-PI --projection work/prj                         # a projected element
```
Every answer shows the **rule** (e.g. S17), its **published source** where one exists (e.g. BIAN's Semantic API Practitioner Guide), the **records it came from**, the **reasoning** and the **confidence**. Low confidence (0.4) means weak evidence — often names only; treat it as a hint.

### 8.7 Onboard your existing designs (from Confluence)

*Goal: turn your organisation's past designs (Confluence pages with tables and diagrams) into SDEM data — on your machine, without AI, without the content leaving it.*

**The full walkthrough, every step with what you will see, is the [onboarding workflow](sdem-onboarding-workflow.md)** — follow that. In short:

```bash
mkdir -p work/imports && cp -r examples/designs/confluence-folder-export work/imports/payarch     # the made-up sample; your real export goes in work/imports/<name>/
sdem transform inspect work/imports/payarch --ocr off                    # what is in the export, what SDEM can read — changes nothing
sdem transform run work/imports/payarch -o work/history --ocr off        # suggestions + work/history/extraction-report.md
# read the report; note the ids you reject
sdem new --workspace workspaces/history --person <your name>               # start the workspace once — BIAN is read from the catalogue, not copiedomains
sdem load work/history --workspace workspaces/history --person <your name> --exclude HIS-A3-PAYMENT-ORDER
sdem link --workspace workspaces/history --out work/links                      # then review, approve, build — as in §8.2
```

- **Keep exports in `work/`** — it is never saved to Git. The result you keep is `workspaces/history/` (for real data, in your private workspace repository).
- Every suggestion says **which page, where on it, which rule and how sure** (never above medium); nothing is loaded until you run `sdem load`; anything that did not fit becomes a **gap record** — nothing is lost.
- **Your BIAN layer** holds only the domains your designs need: after the load, `sdem aid` brings them in; add one with `sdem bian custom --add` — what it is and where it comes from: [the workflow's *Your BIAN (A2) layer*](sdem-onboarding-workflow.md#your-bian-a2-layer).
- If your designs use table headings SDEM does not recognise: [configuration — onboarding](sdem-configuration.md#onboarding--reading-your-designs).

> **Never** put the real export or its outputs in a public repository or paste them into an AI chat outside what your organisation allows.

## 9. Working with Copilot

Copilot is your **assistant**, not your architect. It reads the project's files and your terminal output and helps you understand and decide.

**Ready-made prompts:** type `/` in the chat for SDEM's prompt files — `/sdem-explain`, `/sdem-fix`, `/sdem-review`, `/sdem-impact-note`, `/sdem-pr`, `/aid-explain`, `/sdem-onboarding-review` (and `/sdem-process-events`, `/sdem-layer-work` for the agents). Copilot also loads SDEM's skills (`.github/skills/`) when they fit your question.

**Good things to ask:**

| You want to … | Ask |
|---|---|
| understand output | *Explain the output in the terminal in plain words.* |
| fix data | *Explain this sdem check error and show the fix.* |
| find the right command | *Which sdem command shows what depends on INF-K8S-PAY-PROD?* |
| review proposals | *Walk me through work/links/proposals.json, weakest first, and what evidence each needs.* |
| write | *Draft an impact note from the impact output.* · *Draft the pull-request description.* |
| learn | *What does REALIZED_BY mean in SDEM, and which evidence does it need?* |

**What Copilot will not do** (and you should not ask it to):

- **approve** a link — a person approves, through a pull request;
- put **projected (`PRJ-`)** or AI-suggested content into real data — SDEM blocks it anyway;
- answer architecture questions **from memory** — it should run or point to an `sdem` command and name its source. If an answer has no source, ask: *Which command or file is that from?*

If Copilot suggests a command, read it before running it. If it is wrong, the command's output will show it — SDEM's checks, not Copilot, decide what is valid.

Copilot is optional: everything in this guide works without it.

### 9a. The SDEM agents

The project includes five Copilot agents (`.github/agents/`): **sdem-orchestrator** and one per architecture — **sdem-a1-business**, **sdem-a2-bian**, **sdem-a3-application**, **sdem-a4-technology**. Pick one in the Copilot Chat agent picker.

- A **layer agent** changes only its own architecture, and only through a checked **change set** (`sdem change propose`). Every change records the agent and **you** as the person.
- The **orchestrator** turns a change's impact into **work items**, calls the layer agents to do them, and reports to you. It never changes data and never approves.
- Agents never talk to each other directly — they coordinate through the work items and change events SDEM records in the workspace's `coordination/` folder.
- You still approve, by merging the pull request.

Try it on a copy of an example (the spike: [`sdem-agent-platform-spike.md`](sdem-agent-platform-spike.md)): ask **sdem-a4-technology** to rehost the production payments cluster, then ask **sdem-orchestrator** to *"process the open change events"*. The full flow, with real output, is in [`use-case-example-3.md`](evidence/use-case-example-3.md); the design in [`sdem-agent-platform-design.md`](design/sdem-agent-platform-design.md).

## 10. Rules you must know

1. **A person approves links** — with `sdem approve`, giving your name, the date and the required evidence, then a reviewed pull request. Never the engine, never Copilot (CTL-21 rejects an agent as reviewer).
2. **Approved links are never edited.** To change one, add a new record that supersedes it (`sdem diff` checks this).
3. **Once agents work on a layer, change it through change sets.** A hand edit is reported by `sdem check` until you record it with `sdem change adopt`.
4. **Projected (`PRJ-`) content is a plan, never real data.** SDEM rejects it in datasets, the registry and the graph store.
5. **Check before you trust.** Run `sdem check` after every change; CI runs everything again on every push.
6. **Public and made-up data only in this project.** Real architecture data goes only in your organisation's own copy.
7. **No PlantUML public server for real data** — use a local or company server.

## 11. Troubleshooting

| You see | Means | Do |
|---|---|---|
| `sdem: command not found` | SDEM is not installed in this terminal | run `source .venv/bin/activate` (Windows `.venv\Scripts\activate`), or use `python3 -m sdem …` |
| `ERROR: … missing required property 'name'` | a record lacks a required field | add it; `$.instances[0]` is the first record in the list |
| `ERROR: … duplicate mapping_id` | two links share an id | give the new one an unused id |
| `ERROR: … evidence missing required kind(s) [...]` | an approved link lacks the evidence its type needs | add `kind:document-reference` (§8.2 table) |
| `ERROR: … CTL-20 (AG-S08): … was changed outside a change set since CS-…` | **change provenance (CTL-20):** a dataset was edited by hand after agents started changing that layer | if it was you: `sdem change adopt --workspace <dir> --layer <A?> --person <you> --reason <why>`; if not, find out who and undo it |
| `ERROR: … CTL-21 …` | a link was approved with an agent or tool as reviewer | approve as yourself: `--reviewer your.name` |
| `ERROR: CTL-19: …` | a change set crosses its layer, or an agent works outside its layer | keep each change set to one layer; let the orchestrator plan the other layers' work |
| `ERROR: CTL-20: …` (other messages) | **change provenance (CTL-20):** a change set or work-item step without the agent or the person behind it | add `--agent` and `--person` |
| `ERROR: … cannot enter a real architecture dataset (CTL-16)` | projected content was put into real data | remove it; projections stay in their own folder |
| `WARN: … expects at least 1 (LC-10m)` | the metamodel recommends a link that is missing | advice — fix when you can |
| `build … rejected: N error(s); the previous graph store is unchanged` | the data has errors, so the graph was not rebuilt | run `sdem check` and fix the errors |
| `ERROR: 'CAP-999' is not an instance in any loaded level model` | that id is not in the data | check the spelling; `sdem query --graph work/graph --level A1` lists ids |
| a trace stops early | a link in the chain is not approved yet | `sdem query --graph … --unmapped A2`; then §8.2 |
| `no proposed links to review` | everything the engine can find is already approved | nothing to do — or add data that names its links (e.g. `invokes`) |
| `WARN: the graph store is out of date …` | the data changed after the graph store was built, so trace, impact and the view show the old picture | rebuild: `sdem build --workspace <workspace> --out <graph>` |
| Windows PowerShell and `a*.json` | PowerShell does not expand `*` — `sdem` does it itself | nothing to do; or use `--workspace <folder>` |
| Mermaid diagrams show as text | the preview extension is missing | install *Markdown Preview Mermaid Support*, or view the file on GitHub |

## 12. Questions people ask

**How do I reject a proposal?** Don't approve it. Proposals are only suggestions: they live in the `proposals.json` that `sdem link` writes to `work/`, and are made afresh each time you run it. Nothing is stored for a proposal you leave alone.

**An approved connection turned out to be wrong. How do I remove it?** Approved connections are never edited or deleted — that is how the history stays trustworthy. Replace it with the right one: `sdem approve <the right proposal> … --supersedes <wrong id>` (or `sdem connect … ` and then supersede). SDEM has **no command yet to withdraw a connection without a replacement**; until it does, ask your in-house SDEM lead — never edit `mappings.json` by hand.

**How do I retire an application or a server?** First see what it affects: `sdem impact <id> --change retire --graph <graph>`. Then, on a branch, set the record's `lifecycle_status` to `retired` in its layer's file (`planned`, `active`, `deprecated` and `retired` are the allowed values), supersede the connections the impact report lists, run `sdem check`, and open a pull request. Keep the record — history is kept, not deleted.

**Does SDEM work on Windows or Linux?** Yes — it needs only Python 3.10 or later (its checks run on Linux on every release). On Windows, activate the environment with `.venv\Scripts\activate`, and PowerShell does not expand `a*.json` (use `--workspace`). Reading text in pictures uses the Mac's own text recognition, or Tesseract where it is installed; otherwise add `--ocr off`. PlantUML previews need Java and Graphviz.

**How does SDEM relate to our EA tool or CMDB?** It does not replace them. Today data comes in from designs (onboarding) or as files in SDEM's format; reading straight from tools — spreadsheets, a CMDB, an application portfolio — is planned (*tool onboarding*, see the ROADMAP). What SDEM builds is open: the knowledge graph is written as JSON Graph Format files (`sdem build`), and the workspace itself is plain JSON in documented formats, so other tools can read both.

## 13. Where to go next

| To learn … | Read |
|---|---|
| how SDEM fits together | [`sdem-overview.md`](sdem-overview.md) |
| the metamodel: kinds of thing, connections, what SDEM refuses | [the metamodel in plain words](sdem-metamodel-guide.md) |
| the parts of SDEM and where every file lives | [SDEM architecture](sdem-architecture.md) |
| setting SDEM up and running it for a team | [configuration](sdem-configuration.md) · [administration](sdem-administration.md) · [operating model](sdem-operating-model.md) |
| every control and where it is checked | [controls register](reference/controls-register.md) |
| how SDEM was designed (for builders and reviewers) | [`design/`](design/README.md) |
| any term | [`glossary.md`](glossary.md) |
