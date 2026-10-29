# Using SDEM — free for any bank

> **Status: current (v0.9.4)** — what anyone may do with SDEM, what it contains from others, and what it does not claim. For an organisation's full checklist before go-live: the [adoption checklist](sdem-adoption-checklist.md). This page explains the licence in plain words; **it is not legal advice**.

## In one sentence

**SDEM is open source under the Apache License 2.0: any bank, firm or person may download it, use it privately, change it and build on it — free, with no registration and no reporting back.**

## What you may do

| You want to … | Allowed? | Conditions |
|---|---|---|
| Download and use SDEM | ✅ | none |
| Use it privately, on your own architecture | ✅ | none |
| Change it — your own BIAN, design formats, rules, code | ✅ | none |
| Keep your changes to yourself | ✅ | none — there is no obligation to share them |
| Use it commercially — inside a bank, a consultancy or a product | ✅ | none |
| **Give SDEM to someone else** — redistribute it, or ship it inside your own product | ✅ | keep the licence (`LICENSE`) with it, and say what you changed — the only conditions, and only when you pass SDEM on |

The Apache License 2.0 also means every contributor grants users a licence to any of their patents the code uses — no contributor can later claim against you for using SDEM.

## Your data and your privacy

- **SDEM collects nothing.** No telemetry, no account, no network connection: it runs on your machines and reads and writes files in your folders.
- **Your architecture data is yours** — it lives in your own private repository. SDEM adds nothing of its own to it, and the SDEM project never sees it.
- **No AI inside SDEM.** GitHub Copilot is optional and works under your organisation's own agreement with GitHub.

## What SDEM contains — and from whom

| Part | Whose | Licence |
|---|---|---|
| The tool, the rulebook, the schemas, the documentation, the templates, the made-up examples | the SDEM project | **Apache-2.0** (`LICENSE`) |
| The **base BIAN** (`bian/`) — BIAN's Semantic APIs 14.0.0, packed; descriptions left out | **BIAN e.V.**, published openly on GitHub | BIAN's **Apache-2.0** (`bian/LICENSE`, what was changed: `bian/README.md`) |

**Nothing else from others is included.** SDEM's rulebook *names* concepts from published reference architectures and explains each in its own words; it does not copy their text:

| Source | Public? | How SDEM uses it |
|---|---|---|
| **BIAN** — Service Landscape, Practitioner Guide, release notes (bian.org) | free to read and download; copyright BIAN | cited; BIAN's names and structure; no text copied (15 of 44 kinds of thing) |
| **ArchiMate 3.2** — The Open Group | **sign-in required** (an Open Group account); copyright The Open Group | concept names and relationship kinds, checked against **Archi**, an open-source ArchiMate tool (MIT licence); no text copied (21 of 44) |
| **TOGAF 10** — The Open Group | **sign-in required**; copyright The Open Group | one concept informs one kind of thing; no text copied (1 of 44) |
| **SDEM's own extensions** | — | defined by SDEM (7 of 44) |

Every kind of thing names its source, reasoning and confidence: [provenance](reference/reference-architecture-provenance.md). ArchiMate and TOGAF items were checked against the open Archi tool rather than the specification text, which needs a sign-in; this is stated with each of them.

## What SDEM does not claim

- **Not endorsed by BIAN or The Open Group.** BIAN® is a trademark of BIAN e.V.; ArchiMate® and TOGAF® are trademarks of The Open Group. SDEM is independent.
- **No compliance or certification.** Using SDEM does not make an architecture BIAN-compliant or certified.
- **No warranty.** SDEM is provided "as is", as the Apache License 2.0 says (§7–§8): you decide whether it fits your purpose.

## Making it your own

| Make it fit your organisation | How |
|---|---|
| Your own BIAN adoption | pack your BIAN with `sdem bian pack` and use `--base <your pack>` — [onboarding: your BIAN layer](sdem-onboarding-workflow.md#your-bian-a2-layer) |
| Your own design formats (how your Confluence pages are laid out) | your copy of the transform rules — `sdem transform rules` ([configuration](sdem-configuration.md#onboarding--reading-your-designs)) |
| Your reviewers, checks and hosting | the [estate repository template](../templates/estate-repo/README.md) |
| Your own kinds of thing or attributes in the rulebook | today: change your own copy of SDEM (the licence allows it) or propose it to the SDEM project |
