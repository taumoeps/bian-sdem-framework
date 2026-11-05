---
name: sdem-impact-validation
description: How a layer agent assesses a change event's calculated impact on its own layer — confirm it, confirm there is none (with evidence), dispute it, or ask for more investigation — and how the orchestrator runs the four-layer impact validation before any work is planned. Use when asked to validate, assess or check the impact of a change event, or before planning work from one.
---

# SDEM four-layer impact validation

`sdem` calculates a change event's impact deterministically, from **approved** links and the impact rules. That calculation is a starting point, not a decision: before any work is planned, **every layer's agent assesses it** — including layers with no detected impact — and **a person accepts** the final assessment and authorises implementation. `sdem work plan` refuses until then (AG-V08).

## What the calculation tells you

```bash
sdem events show <CE-id> --workspace <workspace> --json
```

The validation also holds the **requirements and risk analysis** (`validation.analysis` — skill `sdem-requirements-risk`): requirements in scope, breached or not shown to hold, and the risk findings. Review your layer's part of it as well as the structural impact.

Per layer, under `calculated_impact.coverage.<layer>`:

| Field | Meaning |
|---|---|
| `result` | `impact_detected` · `no_impact_by_rule` (reached, but the rules say this kind of change does not affect it) · `no_impact_detected` (no approved path reaches it) · `evidence_incomplete` (no approved path, and the layer's links are incomplete) |
| `records`, `paths`, `rule` | the records reached, the approved links (mapping ids) used, and the rule behind each classification |
| `unapproved_links`, `unmapped_records` | links the engine did not follow (not approved) and records with no approved link where one is expected |
| `evidence` | `complete` or `incomplete` |
| `related_within_layer` | records linked to the changed record inside its own layer — the impact rules do not follow them; check them |
| `confirmed` | always `false` — **no detected impact is not confirmed no impact** |

## Assess your layer (layer agents)

`sdem events pending --workspace <workspace> --layer <your layer>` lists what waits for you. Check your layer's records with read-only commands (`sdem trace`, `sdem impact`, `sdem query`, `sdem explain`) and the design documents you have, then record **one** of:

| Status | When | Needs |
|---|---|---|
| `impact_confirmed` | you agree with the calculated impact | evidence; the records affected (`--record`) |
| `no_impact_confirmed` | the calculation found no impact and you confirm it | **evidence** of what you checked; if the layer's evidence is `incomplete`, `--uncertainty` saying why the gaps do not change your conclusion |
| `impact_disputed` | you disagree — impact the engine missed, or none where it found some | `--recommend <classification>`, evidence; for a design change, the records (`--record`) |
| `further_investigation_required` | you cannot tell | what is missing (`--missing`) or uncertain (`--uncertainty`) |

```bash
sdem events assess <CE-id> --layer <A1…A4> --status <status> [--recommend <classification>] \
  --evidence <kind:ref> … --mapping <mapping ids you relied on> --record <affected records> \
  --missing "<link or record that should exist>" --uncertainty "<what you could not establish>" \
  --confidence high|medium|low --reasoning "<why, in a sentence or two>" \
  --workspace <workspace> --agent <your agent> --person <the architect's name> --json
```

- **A missing path is not proof of no impact.** Before confirming none, look for the links that *should* exist (`unmapped_records`, `unapproved_links`, and your design documents). If you find a gap, say so — `further_investigation_required`, or `impact_disputed` with evidence.
- **Repeat an option or give several values** — both are kept: `--missing "SD-PE REALIZED_BY CMP-PAY-EXEC" --missing "SO-PI-06 IMPLEMENTED_BY"`, `--evidence a:1 b:2`, `--record ART-PAYHUB-IMG --record DEP-PAYHUB-PROD`.
- **Name every affected record you find** with `--record`, even when you agree with the classification — those the calculation did not name are kept as *additional records* and get work items once accepted. Report a link that should exist with `--missing`.
- Your assessment is tied to the evidence at the time: if requirements, measurements, links or layers change — or the event is re-analysed after an SDEM upgrade — it becomes **stale** and you re-assess after `sdem events analyse`.
- **Structural impact is not exposure**: a layer with no structural change can still own a requirement the change breaks — read the requirements column, not only the impact.
- Assess **only your own layer** (CTL-19). Never accept an assessment, never authorise — those are the architect's (CTL-21).
- A later assessment of the same layer replaces yours in the summary; both stay on record.

## Run it (orchestrator)

1. `sdem events validate <CE-id> --workspace <workspace> --agent sdem-orchestrator --person <architect>` — opens all four layers.
2. Call **each** layer agent as a subagent: *"sdem-a2-bian: assess the impact of CE-001 on A2 in <workspace> for <person> (skill sdem-impact-validation); return your status, recommendation, evidence and reasoning."* All four, even the no-impact layers. **If your platform cannot call subagents** (or you are one), assess the layers yourself, one at a time, each with `--agent` set to that layer's agent (AG-V12): read that layer's coverage and records, cite that layer's own evidence, and give each layer its own reasoning — never one copied judgement for all four. The controls are the same either way: each assessment is recorded per layer, and only the architect accepts.
3. `sdem events show <CE-id> --workspace <workspace>` — report to the architect: calculated against assessed, per layer; the requirements column and the risk findings (confirmed breaches first); additional records and missing links; disagreements; gaps; stale assessments.
4. **Ask the architect to decide** — two decisions, both theirs: `sdem events accept <CE-id> --workspace <workspace> --person <their name> --reason "…" [--final <layer>=<class> --resolve <layer>="…"] [--accept-risk RF-…="…"]`, then `sdem events authorise <CE-id> --workspace <workspace> --person <their name>`. Every confirmed breach needs their decision. Only then `sdem work plan` (in the governed enterprise mode, once both are verified by their signed commit).

**Working efficiently as a specialist**: start from the orchestrator's brief (your layer's coverage, requirements and findings); read the full event only when the brief does not answer a question; use `sdem commands --json` rather than exploring `--help`. Efficiency never replaces evidence: cite what you checked.

Validating impact is not approving links — cross-layer links are still approved separately, by a person (`sdem approve`).
