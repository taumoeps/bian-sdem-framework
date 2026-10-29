# Using SDEM — free for any organisation

> **Status: current (v0.9.9)** — what anyone may do with SDEM, what it contains from others, and what it does not claim. For an organisation's full checklist before go-live: the [adoption checklist](sdem-adoption-checklist.md). This page explains the licence in plain words; **it is not legal advice**.

## In one sentence

**SDEM is open source under the Apache License 2.0: any organisation or person may download it, use it privately, change it and build on it — free, with no registration and no reporting back.**

SDEM is not limited to any industry or kind of organisation, and no one has exclusive rights to use it. Its A2 layer follows BIAN, the banking industry's published reference architecture, which any organisation may choose to use.

## What you may do

| You want to … | Allowed? | Conditions |
|---|---|---|
| Download and use SDEM | ✅ | none |
| Use it privately, on your own architecture | ✅ | none |
| Change it — your own BIAN, design formats, rules, code | ✅ | none |
| Keep your changes to yourself | ✅ | none — there is no obligation to share them |
| Use it commercially — inside your organisation, a consultancy or a product | ✅ | none |
| **Give SDEM to someone else** — redistribute it, or ship it inside your own product | ✅ | give them a copy of the licence, mark the files you changed, and keep the existing copyright and attribution notices (including BIAN's in `bian/`) — the licence's conditions (§4), which apply only when you pass SDEM on |

The Apache License 2.0 also includes a **patent licence** (§3): each contributor licenses any of their patents that their contribution necessarily uses. It ends for anyone who sues claiming SDEM infringes a patent. It does not cover patents held by people who did not contribute.

## Your data and your privacy

- **SDEM collects nothing.** No telemetry, no account, no credentials: it runs on your machine, makes no network requests, and reads and writes files in the folders you choose. (Installing it downloads it from GitHub.)
- **Your architecture data stays with you** — in your own folders and private repository. The SDEM project never receives it, and the licence gives it no rights in it.
- **No AI inside SDEM.** GitHub Copilot is optional and works under your organisation's own agreement with GitHub.

What SDEM reads, writes and stores, and what optional tools around it may send: [**SDEM — Privacy and Data Handling**](../PRIVACY.md).

## What SDEM contains — and from whom

| Part | Whose | Licence |
|---|---|---|
| The tool, the metamodel, the schemas, the documentation, the templates, the made-up examples | the SDEM project | **Apache-2.0** (`LICENSE`) |
| The **base BIAN** (`bian/`) — BIAN's Semantic APIs 14.0.0, packed; descriptions left out | **BIAN e.V.**, published openly on GitHub | BIAN's **Apache-2.0** (`bian/LICENSE`, what was changed: `bian/README.md`) |

**Nothing else from others is included.** SDEM's metamodel *names* concepts from published reference architectures and explains each in its own words; it does not copy their text:

| Source | Public? | How SDEM uses it |
|---|---|---|
| **BIAN** — Service Landscape, Practitioner Guide, release notes (bian.org) | free to read and download; copyright BIAN | cited; BIAN's names and structure; no text copied (15 of 44 kinds of thing) |
| **ArchiMate 3.2** — The Open Group | **sign-in required** (an Open Group account); copyright The Open Group | concept names and relationship kinds, checked against **Archi**, an open-source ArchiMate tool (MIT licence); no text copied (21 of 44) |
| **TOGAF 10** — The Open Group | **sign-in required**; copyright The Open Group | one concept informs one kind of thing; no text copied (1 of 44) |
| **SDEM's own extensions** | — | defined by SDEM (7 of 44) |

Every kind of thing names its source, reasoning and confidence: [provenance](reference/reference-architecture-provenance.md). ArchiMate and TOGAF items were checked against the open Archi tool rather than the specification text, which needs a sign-in; this is stated with each of them.

## What SDEM does not claim

- **Not endorsed by BIAN or The Open Group.** BIAN® is a trademark of BIAN e.V.; ArchiMate® and TOGAF® are trademarks of The Open Group. SDEM is independent.
- **No compliance or certification.** Using SDEM does not make an architecture BIAN-compliant or certified. SDEM itself has not been independently audited or certified, and is not approved for production use by any organisation or regulator — each organisation makes its own assessment ([privacy and data handling §9](../PRIVACY.md#9-security-responsibilities)).
- **No warranty.** SDEM is provided "as is", as the Apache License 2.0 says (§7–§8): you decide whether it fits your purpose.

## Enterprise internal use and customisation

The Apache License 2.0 permits all of the following — for one architect or a whole organisation, commercially, without fees, registration or reporting back. What the licence permits is separate from what your organisation allows: **the licence does not by itself approve installing software on an employer's device** — your organisation's software and security policies decide that.

| # | Use | How |
|---|---|---|
| 1 | **One architect, on an employer-managed device** | permitted by the licence, subject to your employer's approval; install as in the [user guide §3](sdem-workbench-user-guide.md#3-set-up--once) and keep work data on approved systems |
| 2 | **Internal commercial use** by any organisation | permitted — no fee, no notice to the SDEM project |
| 3 | **Organisation-wide deployment** across architecture teams | one private workspace repository, a pinned SDEM version, reviewers and checks — the [workspace repository template](../templates/workspace-repo/README.md) and [operating model](sdem-operating-model.md) |
| 4 | **Private modifications and extensions** | permitted; keep them in your own copy (a fork) of SDEM, under the Apache License 2.0 |
| 5 | **Your own BIAN service-domain catalogue** | without changing SDEM: choose service domains from the base BIAN, or pack your own BIAN and use it instead (`sdem bian pack`, `--base <your pack>`) — [your BIAN layer](sdem-configuration.md#your-bian-layer-sdem-bian) |
| 6 | **Your own kinds of thing, attributes and metamodel** | today, in your own copy of SDEM: the metamodel is the files in `metamodel/` and `schema/`, with `sdem model regenerate` and `sdem model check` keeping the generated documents in step ([contributing](../CONTRIBUTING.md#generated-files--never-edit-them-by-hand)) — or propose the change to the SDEM project |
| 7 | **Your own relationship and governance rules** | how your designs are read: your transform rules, without changing SDEM ([onboarding — reading your designs](sdem-configuration.md#onboarding--reading-your-designs)); who approves and what must pass: code owners, branch protection and CI in your workspace repository ([reviewers and protection](sdem-configuration.md#reviewers-and-protection)); the connection rules themselves (`metamodel/relationship-rules.json`): in your own copy |
| 8 | **Your own architecture repositories** | private workspace repositories you own and control |
| 9 | **Internal knowledge graphs and dashboards** | built on your machines (`sdem build`, `sdem home`); self-contained HTML files you may host internally behind sign-in |
| 10 | **No obligation to publish** | you never have to publish your architecture information, configurations or modifications |

## Separation of framework and organisation intellectual property

| What | Whose |
|---|---|
| **The open-source framework** as published in the SDEM repository | licensed to everyone under the Apache License 2.0 by its contributors; using it does not transfer it to anyone |
| **Modifications and extensions** your organisation's people make | owned according to applicable law, who wrote them and their employment or contract terms — the open-source licence alone does not decide this |
| **Your architecture records and design artefacts** — workspaces, exports, graphs, dashboards | your organisation's, under its own intellectual-property and confidentiality arrangements; never part of SDEM |
| **Contributions submitted to the public repository** | offered to everyone under the Apache License 2.0 (§5) — only with the right to do so; never with confidential information |

In short: using SDEM gives no one ownership of the framework; working on SDEM at work does not by itself give the person or the employer ownership of every change — the applicable agreements do; and **the Apache License 2.0 does not override employment agreements or confidentiality obligations**. Confidential organisation information may not be published, in a contribution or otherwise, without authorisation. Any organisation may keep and maintain its own fork under the Apache License 2.0.

Questions this page cannot answer — who owns a particular change, whether a particular use is allowed by an employer — are for that organisation's legal and policy owners.
