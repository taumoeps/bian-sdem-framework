# A complete design — every record connected (CPL-01…CPL-06, and what follows)

> **Status: stages 1 to 4 built (2026-11-17) — the owner's decisions in conversation: build it; on by default for new workspaces, by choice for existing ones.** Stages 4–6 are listed, not built. From the audit that followed the first full load of an independent design (Payment Initiation v3, the [public twin](../evidence/payment-initiation-v3/report.md)).

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
| CPL-07 | Three rules a single `link` could not say, with the profile's new `any_link` (PR-35 — at least one of several links): **an actor** is assigned to something or is served (CPL-A1-05); **an image or package** belongs to a deployment or a platform, or is what a component is built as (CPL-A4-02); **a function** is performed by a component, realises a service, or automates a process (CPL-A3-05). The standard is version 1.1, fourteen rules. *(Version 1.2, with stage 4: CPL-A1-02 no longer asks a step of a process to realise something of its own — found when `sdem aid` first read the standard.)* |

## How a design is completed — the owner's direction (2026-11-17)

An architect assesses a design by seeing it whole. A list of warnings about a structure they cannot yet picture is hard to judge. So:

1. **A standard or pattern is asked first** — what must be connected, and, where a pattern is specific, to what.
2. **What it does not supply, `sdem aid` infers** by its written rules — as an option, to complete the first full draft: every gap filled, the weakest placements included and flagged to review first.
3. **Everything inferred is marked and shown as inferred** — in the data, and in colour in the picture — with its basis: a pattern, or an AID rule and its confidence.
4. **The architect refines**: confirms, corrects or rejects. Nothing inferred counts as fact — in trace, impact or approval — until a person confirms it.

**Inference is AID's, never an AI's.** AID is fixed, written rules — deterministic, each with an id. An AI agent never adds an inferred link or record to a design; what it thinks, it says in words in its hand-back, and it enters the design only when the architect states it or an AID rule produces it. (On Payment Initiation v3 the operator — an AI — wrote sixteen guessed links in as facts; that is the failure this rules out.)

## Stage 3 — built (2026-11-17): the first pattern for a kind of solution

The owner approved the list of parts and that it ships with SDEM (2026-11-17). SDEM's pattern machinery (PR-17…PR-31) is used as it was, with two additions to what a part may say (PR-36, PR-37) — needed because a solution's parts are not all reached from one record.

| Id | Rule |
|---|---|
| CPL-08 | **SDEM ships a pattern for payment initiation**: `standards/sdem-pattern-payment-initiation.json` (`sdem-pattern/1`, id `PAT-PAYMENT-INITIATION`, owner SDEM). It applies to a design that has BIAN's service domain *Payment Order Initiation*, and to no other. Fourteen parts beside the domain, each with its reason, in all four layers: a process that receives the payment (uses the domain); the component that handles it (realises the domain); records of the consent, the payment and duplicate protection (at least three, read and written by that component); a database they are stored in; BIAN *Party Authentication* and a process that uses it; BIAN *Fraud Evaluation* and a process that uses it; the internet-facing API, its operations (at least four: create and read a consent, create and read a payment) and the component that offers it; an audit record that component writes; an edge platform the API is exposed through, in a DMZ; a key or secret store, in a restricted zone. **Every part is a warning** — to decide, never a failed check. What a part's meaning rests on is BIAN's own domain names and the design's structure, never a record's name; the one part structure cannot single out — the key store — is named by a person (`conforms_to`), and until then is *unresolved*. |
| CPL-09 | **SDEM says which pattern fits.** `sdem status` (and `sdem handback --json`: `compliance.patterns_available`) names each shipped pattern whose `applies_when` a record of the design meets and which the profile does not include, with that record — and the command for a person to include it. Nothing is applied until then. |
| CPL-10 | **A person includes it with one command**: `sdem profile include sdem:<file> --workspace … --person …` (PR-38). An existing workspace takes SDEM's completeness standard the same way (CPL-06). |
| CPL-11 | **Said once.** For each pattern SDEM ships and each record it applies to, `sdem status` gives one block — `Pattern Payment initiation (SD-…): 10 of 14 parts in place — 4 to decide`, then each open part with why it matters — not a line a part among the warnings; `sdem pattern draw` shows it over the design (PR-25). A design with open parts is *open*. An organisation's own patterns are listed as before. |

On Payment Initiation v3 (without the operator's guessed links): 10 of 14 parts in place. Open: no *Fraud Evaluation* domain (the design has a fraud-screening process that names no BIAN operation) and so no process that uses it; the API is exposed through nothing approved (SDEM's own proposal for it waits on the owner); nobody has said which platform is the key store.

**Not said by this pattern, and why:** that fraud screening comes *before* the debit (an order across several processes — the structure follows single links); which of the three records is the consent, the payment or the duplicate-protection record (nothing but a name tells them apart — stage 4).

## Stage 4 — built (2026-11-17): `sdem aid` completes the draft

`sdem aid` already wrote what it infers into the workspace, marked inferred, for a person to confirm or reject (AID-W01…W05). It now also asks the workspace's standards and patterns what is missing, and fills what the design gives evidence for ([aid-spec](aid-spec.md) AID-D01…AID-D05): a link a rule asks for, from a distinctive shared word (AID-D01) or by elimination (AID-D02); a BIAN domain a pattern names, from the catalogue, and the process that uses it (AID-D05). Each carries the rule that inferred it and the rule or part that asked for it. A person confirms or rejects a link by naming it (AID-D04); `sdem status` says how many records are connected only by an inferred link.

**A gap with no evidence (AID-D03, AID-D08).** By default a gap for which the design holds no evidence — a requirement whose name points nowhere — is left open and listed: a rule can only choose a partner on some ground. **With `sdem aid --complete-draft` it is placed all the same** (the owner's direction: the first draft is whole, the weakest placements flagged) — to the one candidate already linked to it, else the most connected candidate — and marked *placed by default … review this first*. On Payment Initiation v3, of fourteen gaps: eight inferred from evidence, six with none.

| Id | Rule |
|---|---|
| CPL-15 | **`sdem status` says what the draft rests on.** Beside the completeness figure — which counts only what is stated or confirmed — a second line: the records connected *counting what is inferred or proposed*, how many of those rest on an inferred link to confirm, how many were placed by default with no evidence, and how many on a link between layers that is proposed and waits for a person's approval. A proposed link never counts as a connection; it is said to cover the gap. |

**The rest of the stage (built 2026-11-17).** A part a pattern requires, where the design has *no record of that kind at all*, is added as a planned record marked inferred, with the pattern's link to it (AID-D06) — so an early design, with a business layer and little else, gets the skeleton of its kind of solution to refine. Where records of the kind exist, nothing is added: SDEM does not invent a fourth table beside three. Which record is a part (the key store) is suggested from its name and written by a person (AID-D07).

## Stage 5 — begun (2026-11-17): patterns for BIAN's functional patterns

BIAN gives every service domain a functional pattern — what it does with its asset — and each pattern a generic artefact (BIAN Semantic API Practitioner Guide v8.1 §3.2.1): *Transact* a transaction, *Fulfill* an arrangement. Eighteen patterns cover the 258 domains of release 14.0.0; a pattern file that applies by a domain's `functional_pattern` therefore serves every domain of that kind, with no file a domain.

| Id | Rule |
|---|---|
| CPL-12 | **SDEM ships a pattern for *Transact*** (`standards/sdem-pattern-bian-transact.json`, `PAT-BIAN-TRANSACT`; 14 domains — Payment Order Initiation, Currency Exchange, Letter of Credit …): the capability the domain supports; a process that uses it; BIAN's own service groups and operations, and an API operation that implements one; the component that realises it; a record of the transaction that component reads and writes; the platform it is stored on; the component's deployment. Warnings only. `sdem status` offers it for any design with a Transact domain — after a pattern for the solution itself, when there is one. |
| CPL-13 | **… and one for *Fulfill*** (`standards/sdem-pattern-bian-fulfill.json`, `PAT-BIAN-FULFILL`; 39 domains — Current Account, Consumer Loan, Credit Card …): the same, in terms of the arrangement — and the business service the process provides and **the product the arrangements are for**. |
| CPL-14 | **Two patterns on one design.** A solution's own pattern and its domain's kind may both be included; each is reported in its own block. `sdem aid` does not add the same kind of part for each (AID-D06): what an earlier pattern added counts as there. |

**What these patterns are and are not.** The two share most of their structure, because what makes a domain *complete across four layers* is the same whatever it does; they differ in BIAN's word for what the domain handles and, for Fulfill, the product. They do not say what a *lending* or a *cards* solution needs — that is a pattern for the solution, as payment initiation has. The other sixteen functional patterns are not built: each should be written when a design needs it, not copied from these.

## Stages to come — each its own change, tests first

| Stage | What | Kind |
|---|---|---|
| 5 (rest) | The other functional patterns, as designs need them; patterns for further kinds of solution | content |
| 6 | **Inferred, and seen to be.** `sdem view` and the data sent to DESNRE mark what is inferred; `sdem check` lists any link or record marked inferred that names no AID rule, and any link whose source is not a document, an AID rule or a named person | code |
