# SDEM — Service Domain Enterprise Metamodel

**SDEM connects a bank's architecture — from what the business does, through BIAN, to the applications and the technology underneath — into one picture you can question.** It checks every connection against a rulebook and keeps a person in charge of every decision.

> **Status:** v0.9.1 (2026-10-29). Ready to try on made-up data; use on real designs follows a pilot ([what that needs](#using-sdem-on-real-designs)). Open source; aligned with BIAN, but **not** an official BIAN standard or endorsed by BIAN. Made-up example data only.

## Start here

| You are… | Start with |
|---|---|
| **New to SDEM** | read on, then run the dashboard: `sdem home -o work/sdem` and open `work/sdem/index.html` |
| **An architect who will use it** | [Install](#install), then the [user guide](docs/sdem-workbench-user-guide.md) — a 15-minute quick start and every task step by step |
| **Bringing in existing designs** | the [onboarding workflow](docs/sdem-onboarding-workflow.md); practise with [use-case example 4](docs/evidence/use-case-example-4.md) |
| **Planning to use it on real data** | the [operating model](docs/sdem-operating-model.md) and the [pilot plan](docs/sdem-pilot-plan.md) |
| **Setting up the AI agents** | [Copilot set-up](docs/sdem-copilot-setup.md) |
| **Looking for a document** | the [documentation index](docs/README.md) — every document by reader — and the [glossary](docs/glossary.md) |
| **A maintainer** | [CONTRIBUTING.md](CONTRIBUTING.md) |

## The four architectures

SDEM looks at a bank's architecture as four layers. Each has its own owners and its own data; SDEM connects them.

```mermaid
flowchart TB
    A1["<b>A1 · Business</b><br/>what the bank does<br/><i>e.g. Initiate Payment</i>"]
    A2["<b>A2 · BIAN Service Domains</b><br/>the industry's standard building blocks<br/><i>e.g. Payment Initiation</i>"]
    A3["<b>A3 · Applications</b><br/>the systems that do the work<br/><i>e.g. Payments Hub</i>"]
    A4["<b>A4 · Technology</b><br/>where the systems run<br/><i>e.g. the Kubernetes platform</i>"]
    A1 -->|"is supported by"| A2
    A2 -->|"is delivered by"| A3
    A3 -->|"runs on"| A4
    classDef l fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    class A1,A2,A3,A4 l
```

**Why it matters.** Today the answer to *"what does this depend on — and what breaks if we change it?"* is spread across Confluence, spreadsheets, the EA tool and the CMDB, and lives in people's heads. SDEM puts it in one connected place, with the evidence, and answers in seconds.

## SDEM in three layers

SDEM is built in three layers, each standing on the one below. **The agents are optional; the data and the tools are not.**

```mermaid
flowchart TB
    L3["<b>3 · AI agents</b> — optional<br/>helpers in GitHub Copilot that draft and explain,<br/>using only the tools"]
    L2["<b>2 · Tools</b><br/>the sdem command and dashboards: check, connect,<br/>approve, trace, impact, plan, onboard designs"]
    L1["<b>1 · Data architecture</b> — the foundation<br/>the rulebook, the architecture data,<br/>the approved connections, the knowledge graph"]
    L3 -->|"use"| L2
    L2 -->|"read and write, checked"| L1
    classDef l1 fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20
    classDef l2 fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    classDef l3 fill:#FFF3E0,stroke:#EF6C00,color:#E65100
    class L1 l1
    class L2 l2
    class L3 l3
```

### 1 · Data architecture

The rules, the data and the connections — kept as files, checked, with a full history.

```mermaid
flowchart LR
    R["📘 <b>The rulebook</b><br/>what may exist in each layer,<br/>how layers may connect"]
    D["🗂️ <b>Architecture data</b><br/>A1 · A2 · A3 · A4<br/>each layer owned by its team"]
    M["🔗 <b>Approved connections</b><br/>who approved, when,<br/>the evidence"]
    K["🕸️ <b>Knowledge graph</b><br/>all four layers<br/>in one picture"]
    R -.->|"checks"| D
    R -.->|"checks"| M
    D --> K
    M --> K
    classDef r fill:#FFF8E1,stroke:#F9A825
    classDef d fill:#E8F5E9,stroke:#2E7D32
    class R r
    class D,M,K d
```

The rulebook holds 44 types of thing (capability, application, server …), which may be linked inside a layer (132 rules) and between layers (9 kinds of connection), and the 69 rules for proposing connections — each traced to a public standard (BIAN, ArchiMate, TOGAF).

### 2 · Tools

One command, `sdem`, and dashboards on top of it. **Every function works without AI.**

```mermaid
flowchart LR
    D["📥 Architecture data<br/>(four layers)"] --> C["✔️ SDEM checks it<br/>against the rulebook"]
    C --> P["🔗 SDEM proposes<br/>connections, with reasons"]
    P --> H["👤 A person approves<br/>each one, with evidence"]
    H --> K["🕸️ Knowledge graph"]
    K --> U["📊 Answers: trace, impact,<br/>dashboards"]
```

**Follow one capability down to the technology** — every arrow an approved connection, with who approved it and the document that proves it:

```mermaid
flowchart LR
    A["<b>Initiate Payment</b><br/>A1 · capability"] -->|"supported by"| B["<b>Payment Initiation</b><br/>A2 · BIAN domain"]
    B -->|"delivered by"| C["<b>Payments Hub</b><br/>A3 · application"]
    C -->|"runs on"| D["<b>Kubernetes — production</b><br/>A4 · platform"]
    classDef a1 fill:#FFF8E1,stroke:#F9A825
    classDef a2 fill:#F3E5F5,stroke:#6A1B9A
    classDef a3 fill:#E3F2FD,stroke:#1565C0
    classDef a4 fill:#E8F5E9,stroke:#2E7D32
    class A a1
    class B a2
    class C a3
    class D a4
```

**Ask "what if?"** — *retire the production Kubernetes platform* — and SDEM follows the connections: two applications need a design change; one BIAN domain, one capability and two processes need a review. An architect confirms before anything changes.

**People stay in charge.** SDEM checks, proposes and works out impact; **only a person** approves a connection, loads onboarded designs, or merges a change after review. This is built into the software — SDEM refuses an approval with no evidence, or one signed by an AI agent.

### 3 · AI agents (optional)

Helpers in **GitHub Copilot** — one per layer and a coordinator — draft changes and explain results. They work only through SDEM's checked commands, stay in their own layer, and never approve. No MCP, no AI inside SDEM.

```mermaid
flowchart LR
    Arch(["👤 Architect"]) <--> O["🧭 Coordinator"]
    O --> G["A1 · A2 · A3 · A4<br/>layer agents"]
    G --> S["⚙️ SDEM commands only"]
    S --> Guard{{"🛡️ own layer only · checked first ·<br/>on record · a person approves"}}
    classDef g fill:#FFF3E0,stroke:#EF6C00
    class Guard g
```

## Onboarding your existing designs

Years of designs live in Confluence as pages, diagrams and pictures. SDEM turns an export of them into architecture data — **on your own machine, without AI**.

```mermaid
flowchart LR
    E["📄 Confluence<br/>export"] --> R["1 · SDEM reads it<br/>suggestions + a report"]
    R --> C["2 · You check<br/>the report"]
    C --> K["3 · You keep<br/>the good ones"]
    K --> L["4 · SDEM proposes<br/>connections —<br/>you approve"]
    L --> P["5 · SDEM builds<br/>the picture"]
    R -.->|"what does not fit"| G[["⚠️ gap records —<br/>kept, closed by a person"]]
    classDef you fill:#F3E5F5,stroke:#6A1B9A
    classDef sdem fill:#E3F2FD,stroke:#1565C0
    classDef g fill:#FFF3E0,stroke:#EF6C00
    class C,K you
    class R,L,P sdem
    class G g
```

**BIAN is included.** SDEM ships with a **base BIAN** — BIAN's public Semantic APIs (release 14.0.0) — so your BIAN layer is one command (`sdem bian import --base --only "<service domain>"`); your organisation can replace it with its own BIAN.

Every suggestion says **which page it came from, where, and how sure SDEM is** — never above "medium" until a person checks it. **Nothing is thrown away:** what does not fit — a risk table, text, a picture — is kept as a *gap record* beside the data. It works for any domain (tested on payments and lending).

**How:** the [onboarding workflow](docs/sdem-onboarding-workflow.md) — every step, its command, and what you will see. Data from tools (spreadsheets, CMDB) is planned.

## What's built and what's next

```mermaid
flowchart TB
    subgraph B1["1 · Data architecture"]
        direction LR
        d1["✅ Rulebook and data model"]
        d2["✅ Connections and<br/>knowledge graph"]
        d3["✅ Base BIAN included<br/>(BIAN Semantic APIs 14.0.0)"]
    end
    subgraph B2["2 · Tools"]
        direction LR
        t1["✅ Check, connect, approve,<br/>trace, impact, dashboards"]
        t2["✅ Plan missing layers (AID)"]
        t3["✅ Onboard designs"]
        t4["⏭️ Onboard data from tools"]
    end
    subgraph B3["3 · AI agents"]
        direction LR
        a1["✅ Agents, prompts, skills"]
        a2["⏭️ Try them in Copilot"]
    end
    subgraph B4["Operating it"]
        direction LR
        o1["✅ Operating model,<br/>estate template, pilot plan"]
        o2["⏭️ The pilot"]
    end
    B1 ~~~ B2 ~~~ B3 ~~~ B4
    classDef b fill:#E8F5E9,stroke:#2E7D32
    classDef n fill:#ECEFF1,stroke:#607D8B
    class d1,d2,d3,t1,t2,t3,a1,o1 b
    class t4,a2,o2 n
```

✅ built · ⏭️ next. Details: [ROADMAP](docs/design/ROADMAP.md) · what changed: [CHANGELOG](CHANGELOG.md).

## Install

You need **Python 3.10 or later** (3.13 recommended). Macs come with 3.9, which is too old. Install 3.13 with Homebrew (`brew install python@3.13`) or the installer from [python.org](https://www.python.org/downloads/macos/), then find it:

```bash
python3 --version                      # 3.10 or later? then use python3 below
for d in /opt/homebrew/bin /usr/local/bin; do ls "$d" 2>/dev/null | grep "^python3\.1[0-9]*$" | sed "s|^|$d/|"; done   # installed but "command not found"? it is one of these
```

```bash
git clone https://github.com/taumoeps/bian-sdem-framework.git && cd bian-sdem-framework
python3.13 -m venv .venv               # or the full path you found, e.g. /opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate              # do this in every new terminal
pip install -e .                       # installs the sdem command
sdem --version                         # 0.9.1
```

If `pip` says *File "setup.py" … not found* or *requires a different Python*, the `.venv` was made with an old Python: delete it (`rm -rf .venv`) and make it again with 3.13. More: [administration — troubleshooting](docs/sdem-administration.md#troubleshooting).

**Try it** on the made-up examples:

```bash
sdem home -o work/sdem && open work/sdem/index.html             # the dashboards, as local files
sdem check --estate examples/payment-initiation                 # the data against the rulebook
sdem build --estate examples/payment-initiation -o work/graph   # the knowledge graph
sdem impact INF-K8S-PAY-PROD --change retire --graph work/graph # what breaks if it goes
sdem --help                                                     # every command; sdem <command> --help shows an example
```

Every command, with examples: the [user guide](docs/sdem-workbench-user-guide.md#7-command-reference). `work/` is scratch space and is never committed.

## Using SDEM on real designs

This repository is **public and holds made-up data only**. Real architecture data lives in your organisation's **private estate repository**, made from [`templates/estate-repo`](templates/estate-repo/README.md): SDEM pinned to a release, CI checks on every change, reviewers named.

```mermaid
flowchart LR
    S["SDEM (public)<br/>tool + rulebook"] -- "pinned release" --> E["Estate repository (private)<br/>your data · CI · reviewers"]
    A["👤 Architects"] -- "pull requests" --> E
    E -- "after merge" --> D["📊 Dashboards<br/>local files for now"]
```

Before starting: legal and IP clearance, the private repository with branch protection, and Python 3.10+ on architects' machines. Roles, workflows and support: the [operating model](docs/sdem-operating-model.md). The first step: a ten-week [pilot](docs/sdem-pilot-plan.md) on one domain. Security: [SECURITY.md](SECURITY.md).

## How it was tested

| Test | Result |
|---|---|
| Rules engine against sealed answer keys | 8 of 8 acceptance cases |
| Use-case examples 1–4: datasets to graph · planning missing layers · agents · onboarding designs | 30 of 30 · 12 of 12 · 8 of 8 · replayed on every push |
| Design onboarding on a second domain (lending), expectations sealed first | 18 of 18 records, nothing lost |
| Links allowed inside a layer | 132 rows; 16 checked on BIAN's public pages, 113 against the open-source ArchiMate implementation, 0 contradicted |
| Automated tests on every push, Python 3.10–3.13, plus the installed package | the full suite |

**Caveats.** All data and answer keys were made by this project; a blind test by someone else is still to come. The ArchiMate and TOGAF specifications need a login, so those rows were checked against an implementation. The AI agents have not yet run in real Copilot.

## Where the rulebook comes from

Every entity type comes from a **public reference architecture** — BIAN, ArchiMate 3.2 or TOGAF 10 — or is a documented SDEM extension of one; none is copied from any institution's model, and no BIAN or Open Group text is reproduced ([provenance, entity by entity](docs/reference/reference-architecture-provenance.md)). BIAN®, ArchiMate® and TOGAF® are trademarks of their owners; SDEM is independent and not endorsed by them.

**Rules of use.** Keep historical designs; never overwrite or silently reclassify them. Keep BIAN reference content separate from your own design objects. A connection is a versioned, typed claim with evidence — an AI confidence value is not evidence. *Affected by a change* does not mean *must change*: impact needs an architect's assessment.

## Licences

Source code, schemas and templates: Apache-2.0 (`LICENSE`). Original prose in `docs/` and this README: CC BY 4.0 (`LICENSES.md`). The **base BIAN** in `bian/` is BIAN's public Semantic APIs 14.0.0, distributed under BIAN's Apache-2.0 licence (`bian/LICENSE`, `THIRD_PARTY.md`). An independent community proposal — not affiliated with, endorsed by, or sponsored by BIAN or any bank; no guarantees of fitness, correctness or compliance.
