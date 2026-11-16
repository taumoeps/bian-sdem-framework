# A complete design — every record connected (CPL-01…CPL-06, and what follows)

> **Status: stage 1 built (2026-11-17) — the owner's decisions in conversation: build it; on by default for new workspaces, by choice for existing ones.** Stages 2–5 are listed, not built. From the audit that followed the first full load of an independent design (Payment Initiation v3, the [public twin](../evidence/payment-initiation-v3/report.md)).

## The problem

SDEM is strict about records and permissive about links. Outside the BIAN layer the metamodel makes every link inside a layer optional — of 162 in-layer link rules, 15 expect at least one, 14 of them in A2 — so an interface that belongs to no component, or a requirement nothing meets, is a valid record and `sdem check` says nothing. SDEM's own examples, written to fit it, have 23 unlinked records in 1,100; the first design from outside had 36 in 151. The operator then filled eight gaps by judgement, as plain facts — which is exactly what SDEM must not allow.

## What already existed — and is used, not rebuilt

The organisation profile (docs/design/sdem-profile-spec.md) already reads **standards** and **reference patterns**: a rule may require a link inside the layer (`link`: kind, direction, type, min) or an approved link between layers (`across`); a planned record that does not meet a rule is *unresolved*, not failed; `sdem comply` reports every rule on every record; `sdem exception grant` records a person's time-limited exception; `sdem status` lists what is open. A pattern applies to the records it names (`applies_when`) and may carry a structure of roles and connectors. **What was missing was the content, a default, a summary, and proposals.** ("Packs", in the conversation that led here, are SDEM's standards and patterns.)

## Stage 1 — built

| Id | Rule |
|---|---|
| CPL-01 | **SDEM ships its own standard for a complete design**: `standards/sdem-completeness.json` (`sdem-standard/1`, id `SDEM-COMPLETE`) — eleven rules, each true of any design in any domain, each with its reason. A1: a requirement is met; a process realises something; a business object is used; a channel serves someone. A3: an interface belongs to a component; a service is realised; an operation belongs to an interface; a data entity is used. A4: a technology service is provided by a platform. Between layers: a component has a deployment; a data entity is stored. |
| CPL-02 | A profile includes it — or any other file SDEM ships — as **`"sdem:<file>"`** (`"sdem:sdem-completeness.json"`); the name cannot leave SDEM's shipped folder. Everything else about it is PR-13. |
| CPL-03 | **On by default for a new workspace.** `sdem new --workspace …` on its own writes an `sdem-profile.json` that includes it; `sdem new --organisation …` puts it in the starter base profile, so every workspace of the organisation inherits it. Taking the include out switches it off. |
| CPL-04 | **A gap is a decision to take, never a wrong design.** Every rule is `severity: warning`: `sdem check` never fails on one. A *planned* record that does not meet a rule is *unresolved* and absent from `sdem check`; an *active* one is a warning there. A person may grant an exception (`sdem exception grant --rule CPL-…`). |
| CPL-05 | **Said once, as a figure.** `sdem status` (and `sdem handback --json`: `compliance.completeness`) gives the records the standard checked, how many are connected, and the gaps grouped by rule — `Completeness: 63 of 74 records connected (85%) — 11 gaps`, then a line per rule — not a line per gap. A workspace with gaps is *open*, not *clear*. |
| CPL-06 | **An existing workspace is not changed.** One with no profile, or a profile that does not include the standard, is checked exactly as before; it takes the standard by adding the include to its profile (a person's change, checked by `sdem profile check`). |

On Payment Initiation v3 without the operator's sixteen guessed links the standard finds eleven gaps: five technology services with no platform, four interfaces with no component, the requirement R-22, the payer account.

## Stages to come — each its own change, tests first

| Stage | What | Kind |
|---|---|---|
| 2 | **"At least one of these links"** in a rule (`any_of`), so the standard can say *an actor is assigned to a role or a process, or is served*; *an artifact belongs to a deployment or a platform*. Then those rules | the rule format (profile spec) — small |
| 3 | **`sdem aid` proposes the link a gap needs**, where the design gives evidence — an interface and the one component whose name shares its distinctive word; a technology service and the platform that the component it serves stores its data in — marked *inferred*, low confidence, for a person to confirm. No evidence: no proposal | code (AID rules) |
| 4 | **Where a link comes from.** A link's source is a document, an SDEM rule (the `inferred` mark) or a named person's decision; anything else is listed by `sdem handback`. **An agent's suggestion** has its own route — recorded as a suggestion with its reasoning, to confirm, never as a fact | code |
| 5 | **Patterns for kinds of solution** — one per BIAN functional pattern (about twenty cover every service domain), and specific ones where a design needs them, payment initiation first; `sdem status` names the pattern that fits the BIAN domains a design uses, a person includes it | content, and a suggestion in `sdem status` |
