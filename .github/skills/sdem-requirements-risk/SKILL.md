---
name: sdem-requirements-risk
description: How to read and work with SDEM's requirements and risk analysis — which requirements a change touches, whether they still hold now and in the proposed architecture, confirmed breaches, potential risks, missing evidence and assumptions — and how to record requirements and measurements with evidence. Use when a change may affect availability, performance, data residency, real-time processing, recovery or other requirements, when reviewing a change event's risk findings, or when asked whether a platform change is safe.
---

# SDEM requirements and risk analysis

Three things, kept apart and all deterministic:

| | Answers | Command |
|---|---|---|
| structural impact | which records and approved links a change reaches | `sdem impact <id> --change <kind> --workspace <dir>` |
| requirements evaluation | which confirmed requirements the change touches; do they hold **now** and in the **proposed** architecture | `sdem requirements evaluate …` |
| risk findings | confirmed breaches, potential risks, missing evidence, assumptions — with the decision each needs | same command; stored with the change event's validation |

**No structural change is never no risk.** A layer the impact rules leave untouched can still own a requirement the change breaks.

## Before a change (any architect)

```bash
sdem requirements evaluate --workspace <dir> --record <platform> --change rehost --proposed <new platform> --json
```

## For a change event (orchestrator and layer agents)

The analysis is in the event's validation: `sdem events show <CE-id> --workspace <dir> --json` → `validation.analysis`. After new evidence, links or requirements: `sdem events analyse <CE-id> --workspace <dir> --agent <you> --person <name>` — earlier assessments become **stale** and are re-done.

## Reading it

- **requirements[]**: `disposition` says what the change does — `compliant`, `current_breach_remediated` (breached today, met by the proposed architecture), `proposed_breach` (introduced), `unresolved_breach` (breached today and after), `missing_evidence`, `not_confirmed`. `overall` is the **proposed** state (`breached`, `missing_evidence`, `satisfied`, `not_confirmed`); today's result is in `current`. A breach that the change remediates is reported (`remediated_breach`) but needs no residual-risk decision. Each is judged **on its subject only**: a platform's availability never shows a business process's end-to-end availability (`notes` says so).
- **substitution**: which record replaces which in the proposed architecture, read from the change set.
- **layers.<A1…A4>.status**: `breached`, `missing_evidence`, `satisfied`, `no_requirements_recorded` or `requirements_registry_missing` — the last two are **not** "fine": nothing is recorded.
- **risks[]**: `confirmed_breach` (a measurement fails a confirmed requirement), `potential_risk` (a scenario the change kind raises for a requirement in scope — schema/risk-rules.json), `missing_evidence`, `assumption` (incomplete links). Each has its `decision` and mitigations **to consider**. There are no likelihoods or losses — never add any.
- **obligations**: the A1 requirements (and A1.BusinessRequirement records) exposed.

## What each layer checks

| Layer | Look at |
|---|---|
| A1 business | the obligations exposed — service levels, residency, continuity — and whether the business can accept a breach |
| A2 BIAN | the service domains' requirements, and missing links (`assumption`) that could hide one |
| A3 application | the applications' requirements (performance, recovery) for the proposed platform |
| A4 technology | the platform characteristics (availability, region, capabilities, replicas) of the proposed platform; records linked inside A4 that the impact rules did not follow (`related_within_layer`) |

Record what you find in your assessment (skill `sdem-impact-validation`): records the calculation did not name with `--record` (they are kept apart as *additional records*), missing links with `--missing`.

## Recording requirements and evidence

- **Never invent, round or alter a measurement to make a requirement pass** — a requirement that cannot be shown to hold stays `missing_evidence`.
- A measurement is a **stated value with its evidence**: `sdem requirements measure --record <id> --metric <metric> --value <v> [--unit <u>] --state current|proposed --evidence <kind:ref> --workspace <dir> --person <name> [--agent <you>]`. Only a value you can cite — never an estimate.
- A requirement: `sdem requirements propose <file.json> --workspace <dir> --person <name>` (status *proposed*). Only a person confirms it: `sdem requirements confirm <REQ-id> … --person <their name>`.
- Never edit `requirements.json` by hand — an edit made outside `sdem` is noticed (`sdem check`).

## Decisions are the person's — and a typed name is not proof

Confirming or retiring a requirement, approving or stating a link, accepting impact or risk and authorising are **governed decisions**. Do not run them, even if you are given a name: prepare the exact command for the person. A `--person` name is attribution, not authentication — where the workspace requires it, SDEM accepts a decision only when the person commits it signed with their own key ([governance](../../../docs/design/sdem-governance.md)).

## Accepting the risk (the architect, not you)

Each `confirmed_breach` must be decided before implementation: change the design and re-analyse, or accept it as a residual risk —
`sdem events accept <CE-id> --workspace <dir> --person <their name> --reason "…" --accept-risk RF-BREACH-…="<why>" …`, and — a separate decision — `sdem events authorise <CE-id> --workspace <dir> --person <their name>`. A `current_breach_remediated` requirement needs no risk decision: the proposed architecture meets it.
