# SDEM documentation

> **Status: current (v0.9.5)** — start here. Everything on this page is written for people who will use or run SDEM; nothing assumes you know it already.

## New to SDEM? Read these, in order

```mermaid
flowchart LR
    A["1 · What SDEM is<br/><i>10 minutes</i>"] --> B["2 · Install and try it<br/><i>30 minutes</i>"] --> C["3 · Bring in your designs<br/><i>when you are ready</i>"]
```

| | Read | For |
|---|---|---|
| 1 | [**SDEM — read this first**](sdem-overview.md) | what SDEM is, the five ideas behind it, a worked example |
| 2 | [**User guide**](sdem-workbench-user-guide.md) | install, a 15-minute quick start, every task step by step, **the command reference** (§7), troubleshooting |
| 3 | [**Onboarding your existing designs**](sdem-onboarding-workflow.md) | turning a Confluence export into SDEM data, step by step |
| — | [Glossary](glossary.md) | any word you do not know |

## More tasks

| Read | For |
|---|---|
| [Planning missing layers with AID](sdem-planning-with-aid.md) | projecting the BIAN, application and technology layers you do not have yet — a planned design, kept apart from real data |

## Understanding SDEM

| Read | For |
|---|---|
| [The rulebook in plain words](sdem-rulebook-guide.md) | the kinds of thing, the nine connections between layers, how sure SDEM is, what it refuses |
| [SDEM architecture](sdem-architecture.md) | the parts, where every file lives, how a change flows, what checks it, limits |

## Setting it up and running it

| Read | For |
|---|---|
| [Using SDEM — free for any bank](sdem-licence-and-use.md) | the licence in plain words: what anyone may do, what SDEM contains from others, what it does not claim; enterprise use and customisation |
| [Privacy and data handling](../PRIVACY.md) | what SDEM reads, writes and stores; what optional tools around it may send |
| [Adoption checklist](sdem-adoption-checklist.md) | what your organisation clears first: legal and licences, data, security, AI, and depending on an open-source tool |
| [Operating model](sdem-operating-model.md) | where things live, who does what, how changes and upgrades flow, support |
| [Configuration](sdem-configuration.md) | everything you can set: estates, the SDEM version, how onboarding reads designs, OCR, reviewers, CI, VS Code, Copilot |
| [Administration](sdem-administration.md) | installing, upgrading, rulebook changes, backups, health, troubleshooting |
| [Repository protection](sdem-repository-protection.md) | branch protection and code owners, so a person's approval is enforced |
| [Copilot set-up](sdem-copilot-setup.md) · [agent spike checklist](sdem-agent-platform-spike.md) | GitHub Copilot and the SDEM agents (optional), and the checklist to try them |
| [Pilot plan](sdem-pilot-plan.md) | the first ten weeks on real designs |
| [Estate repository template](../templates/estate-repo/README.md) · [Security](../SECURITY.md) | your private repository for real data · keeping data safe |

## Looking something up

| Read | For |
|---|---|
| [Reference](reference/README.md) | generated from the rulebook: every kind of thing and attribute, the data models, the controls register, sources |

---

## For builders and reviewers — you do not need these to use SDEM

| Folder | Holds | Read it if you |
|---|---|---|
| [`design/`](design/README.md) | every design and specification, the governing specs, the roadmap, the reasoning behind the rules | change SDEM, review the rulebook, or want to know *why* |
| [`evidence/`](evidence/README.md) | the use-case examples and test records, with their recorded results | want proof that something was tested |
| [`history/`](history/README.md) | documents that are no longer current | are tracing how SDEM got here |

Maintaining SDEM: [CONTRIBUTING.md](../CONTRIBUTING.md).
