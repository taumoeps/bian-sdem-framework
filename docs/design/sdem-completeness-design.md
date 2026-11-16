# A complete design — every record connected (CPL-01…CPL-06, and what follows)

> **Status: stages 1 and 2 built (2026-11-17) — the owner's decisions in conversation: build it; on by default for new workspaces, by choice for existing ones.** Stages 3–5 are listed, not built. From the audit that followed the first full load of an independent design (Payment Initiation v3, the [public twin](../evidence/payment-initiation-v3/report.md)).

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

## Stage 2 — built (2026-11-17)

| Id | Rule |
|---|---|
| CPL-07 | Three rules a single `link` could not say, with the profile's new `any_link` (PR-35 — at least one of several links): **an actor** is assigned to something or is served (CPL-A1-05); **an image or package** belongs to a deployment or a platform, or is what a component is built as (CPL-A4-02); **a function** is performed by a component, realises a service, or automates a process (CPL-A3-05). The standard is version 1.1, fourteen rules. |

## How a design is completed — the owner's direction (2026-11-17)

An architect assesses a design by seeing it whole. A list of warnings about a structure they cannot yet picture is hard to judge. So:

1. **A standard or pattern is asked first** — what must be connected, and, where a pattern is specific, to what.
2. **What it does not supply, `sdem aid` infers** by its written rules — as an option, to complete the first full draft: every gap filled, the weakest placements included and flagged to review first.
3. **Everything inferred is marked and shown as inferred** — in the data, and in colour in the picture — with its basis: a pattern, or an AID rule and its confidence.
4. **The architect refines**: confirms, corrects or rejects. Nothing inferred counts as fact — in trace, impact or approval — until a person confirms it.

**Inference is AID's, never an AI's.** AID is fixed, written rules — deterministic, each with an id. An AI agent never adds an inferred link or record to a design; what it thinks, it says in words in its hand-back, and it enters the design only when the architect states it or an AID rule produces it. (On Payment Initiation v3 the operator — an AI — wrote sixteen guessed links in as facts; that is the failure this rules out.)

## Stages to come — each its own change, tests first

| Stage | What | Kind |
|---|---|---|
| 3 | **Patterns for kinds of solution** that say what a solution has and how its parts connect — payment initiation first, then BIAN's *Transact* and *Fulfill* functional patterns (about twenty functional patterns cover every service domain); `sdem status` names the pattern that fits the BIAN domains a design uses, and a person includes it | content, and a suggestion in `sdem status` |
| 4 | **`sdem aid` completes the draft** (an option): for each gap a standard or pattern finds, the link — or the missing part — marked *inferred*, with its basis and confidence; the weakest flagged | code (AID rules) |
| 5 | **Inferred, and seen to be.** `sdem view` and the data sent to DESNRE mark what is inferred; `sdem check` lists any link or record marked inferred that names no AID rule, and any link whose source is not a document, an AID rule or a named person | code |
