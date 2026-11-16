# Brief for the author of the reference design (Model A)

> For the assistant the owner has asked to write the reference — see [`sdem-public-twin-benchmark-plan.md`](sdem-public-twin-benchmark-plan.md) (PT-12…PT-18, decision D2). This brief is complete on its own: the owner can hand it over without the plan. It says what to produce; it contains none of the answers.

## What this is for

SDEM is a tool that holds a solution design as records in four layers — A1 business, A2 BIAN service domains, A3 application, A4 technology — with links inside and between the layers, checks it, proposes links for an architect to approve, and answers questions about it (what depends on what, what a change affects, where a field is stored).

We want to find out whether SDEM gets a realistic design right. To do that we need a design, and the right answers about it, written by someone who is **not** SDEM and is not the session operating SDEM. That is you. Your work is frozen before SDEM sees any of it, and SDEM's operator is given only your design document — never your expected lists or answer key. Afterwards SDEM's results are scored against your files.

So the value of your work is its **independence and its accuracy**. Two consequences:

- **Do not write towards SDEM.** You do not need to know its data model, and should not look for it. Write the design a careful solution architect would write, in the vocabulary of ArchiMate 3.2 and BIAN. If the design needs to say something, say it — whether a tool can hold it is what we are testing.
- **A wrong reference makes every score meaningless.** Where a statement comes from a standard, open the standard and cite the exact place. Where you could not verify something, say so in the file rather than state it with confidence. An honest "not verified" is useful; a plausible invention is harmful.

## The design to write

**A made-up New Zealand retail bank.** Give it an obviously invented name, and check it is not a real organisation's. Everything about the bank is invented — its systems, people, account numbers, addresses. The standards it follows are real.

**Scenario S1 — a third party initiates a single domestic payment.** A customer is paying a merchant. The merchant's payment provider (an accredited third party) asks the bank for consent to a single domestic NZD payment; the customer is redirected to the bank, authenticates and authorises the consent (the standard's **redirect** flow); the third party submits the payment; the bank validates it, screens it, debits the account and hands the payment on for execution; the third party reads the payment's status.

Cover the unhappy paths an architect would: the customer declines, authentication fails, the consent expires, validation fails (for example, insufficient funds or an invalid account number), the same payment is submitted twice.

**In scope:** everything inside the bank from the API being called to the payment being accepted for execution and its status being readable, through all four layers.

**Out of scope for S1** — mention as boundaries, do not design: the standard's second authorisation flow, **decoupled** (the customer authorises on another device or later) — a later scenario of its own; check whether the regulated standards require a bank to support both flows, and record what you find in the design's scope section, so that nobody reads S1 as the whole of payment initiation; enduring (repeated) payment consents, bulk files, direct debits, high-value and cross-border payments, cards, and how the payment clears and settles with other banks (that is a later scenario; show only the hand-off).

**The bank's existing systems** are yours to invent, but keep them ordinary: an online-banking identity service, an account ledger, a payments hub, fraud screening, notifications, an API gateway. Give the bank measurable requirements — availability, response time, recovery time and recovery point, how long a consent lasts — and label each a design decision of the made-up bank.

**Size.** One scenario, done properly. As a guide to scale only — not a target — expect roughly 60–90 records across the four layers and 30–50 links between layers; if the scenario needs more (consent, payment states, data protection, fraud controls, error handling, what the deployment depends on), write more. Completeness is judged by the coverage file (file 6), not by a count. Depth over breadth — fields with types, not a longer list of boxes.

## Sources

Use these, at the stated versions. Open each one you cite; record its URL, version and the date you read it.

| Layer | Source |
|---|---|
| A3 and the information | **NZ Banking Data API Specification, Payment Initiation API (domestic payment consents, domestic payments) and Security Profile — all v2.3.3.** Public to read at `paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards`. v2.3.3, not a later patch and not 3.0: it is the version MBIE's *Customer and Product Data (Banking and Other Deposit Taking) Standards 2025* incorporate by reference (in force 1 December 2025). Note for the source list: Payments NZ's API Centre closed on 30 September 2026 and MBIE now manages the standards; the specifications remain on the Payments NZ site. Read the individual resource and security pages before stating anything at field level |
| Regulation | Customer and Product Data Act 2025 and its banking designation regulations and standards (MBIE) — why the bank offers the API, consent, who may ask |
| A2 | **BIAN 14.0.0** — the semantic API files at `github.com/bian-official/public`, `release14.0.0`. Choose the service domains the scenario needs and justify each; name the operations, control records and business objects used |
| A4 | Reserve Bank of New Zealand — BS11 Outsourcing Policy and Guidance on Cyber Resilience; PCI DSS only where it applies. These set expectations; the deployment itself is your design decision |
| Notation | ArchiMate 3.2 element and relationship names |

Do **not** use SEPA, UK Open Banking as such, or any other market's scheme — this is New Zealand.

**Copyright — cite, never copy.** Payments NZ's standards may be read, but no other licence is granted. Name a resource, a field or a status and cite where it is defined; do not reproduce specification text, schemas, tables or diagrams. Treat BIAN and ISO material the same way.

**Nothing from any real bank.** Only the public sources above and your own invention.

## Mark every statement S or D

- **S — standards-derived:** it can be checked against a source. Give the source, its version and the exact location (the page and section, the file and object, the clause).
- **D — design decision:** the made-up bank's own choice. Give the reason in a few words.

If you believe something is standard but could not open the source to confirm it, mark it **S?** — never plain S.

## The seven files

Write them in this order; the first is what SDEM's operator will be given, so it must stand alone and must not contain the other files' content.

### 1. `design.md` — the solution design

A normal solution design document, in prose with tables where an architect would use them: the scenario and its actors; requirements; the business process and its events; the BIAN alignment; the applications, their services, interfaces and API operations; the data — entities and their fields with types, keys and which are personal information; how the API standard's fields, BIAN's fields and the bank's own columns correspond; the deployment — platforms, network zones, where things are located, what talks to what and over which protocol; the unhappy paths; the decisions and their reasons. Every statement marked S, S? or D.

Write it as a document for people, not as lists of relationships. It should be possible to build the design from it, and not possible to read the answers off it.

### 2. `expected-records.json`

Every record the design implies.

```json
{"records": [
  {"id": "short-stable-id", "layer": "A1|A2|A3|A4", "kind": "the ArchiMate element or BIAN term",
   "name": "…", "basis": "S|S?|D", "source": "for S: source, version, location",
   "fields": {"only the properties that matter for this record": "…"},
   "acceptable_alternatives": "optional — another equally valid way to model this (for example: one record instead of two), so a tool is not marked wrong for it"}
]}
```

Three kinds of fact, so that an invented choice is never scored as if it were a banking standard: **S** items have one right answer (a BIAN identity, a field of the API standard); **D** items are right only as this design states them; and where two ways of modelling the same thing are equally valid, say so in `acceptable_alternatives`.

### 3. `expected-links.json`

Every relationship, inside a layer and between layers — and the relationships that must **not** exist.

```json
{"links": [
  {"from": "record id", "relationship": "the ArchiMate relationship, or a plain phrase such as 'is stored in'",
   "to": "record id", "scope": "within-layer|between-layers", "basis": "S|S?|D", "source": "…",
   "in_design": "stated|implied", "needed": "mandatory|optional"}
 ],
 "must_not_exist": [
  {"from": "record id", "to": "record id", "why": "what would be wrong about linking these"}
 ]}
```

`in_design` matters: **stated** — `design.md` says it in so many words; **implied** — `design.md` gives the facts it follows from but never states the link itself (the component's data lives in a store; the store is on a platform; the platform is in a zone — the link from the component to the zone is implied). Do not hide anything from `design.md` to manufacture implied links; write the design naturally and classify honestly. A tool that records a stated link has shown it can hold a design; one that finds an implied link has shown it can reason — we score the two apart. `needed`: **optional** for a link that is correct but that a complete design could leave out.

Include 10–20 `must_not_exist` entries that a careless tool might plausibly propose — a tool should not score well by proposing everything.

### 4. `answer-key.json` — 30 to 50 questions

```json
{"questions": [
  {"id": "Q-01", "type": "lineage|trace|impact|standards|governance",
   "question": "…", "expected": "the answer, as record ids where it is a set", "basis": "S|D", "source": "…"}
]}
```

A mix: **lineage** (which column stores the instructed amount, and which field of the API standard and of BIAN is it?); **trace** (what does the payment consent depend on, down to its network zone?); **impact** (what is affected if fraud screening is retired, or the consent store moves zone?); **standards** (which BIAN service domain owns the payment order?); **governance** (may an automated agent approve a link it proposed itself? — expected: no). Every answer must follow from files 1–3.

### 5. `mutations.json` — 15 to 25 planted mistakes

```json
{"mutations": [
  {"id": "M-01", "change": "exactly what to alter, by record id, link or field and its new value — precise enough to apply mechanically",
   "category": "structure|standards|data|placement|governance|resilience", "why_wrong": "…",
   "a_tool_should": "refuse|warn|cannot-know", "basis": "S|D"}
]}
```

Cover a range: a link removed; a field given the wrong type; a record placed in the wrong zone; a table duplicated; an operation attached to the wrong service domain; evidence removed from an approved link; a dependency that recovery needs deleted. Use `cannot-know` honestly for mistakes that take an architect's judgement — we want to know where a tool's limits are, not to pretend it has none.

### 6. `coverage.json` — is the design complete?

One row per requirement in `design.md` (give every requirement an id there), showing what carries it through the layers — and stays hidden, because it is a list of answers.

```json
{"coverage": [
  {"requirement": "R-01", "business": ["record ids"], "bian": ["record ids"], "application": ["record ids"],
   "technology": ["record ids"], "evidence": "source or decision", "met_by": "design|procedure|not met — why"}
]}
```

A requirement met by a procedure rather than by technology is recorded as such; none is left out.

### 7. `SOURCES.md`

Every source you opened: title, URL, version, date read, and what you used it for. Then a list of everything marked **S?**, and anything in this brief you could not do.

## Before you hand it over

Check that every id used in files 3–6 exists in file 2; that every S item has a location someone could open; that `design.md` contains no expected lists, questions, mutations or coverage table — it necessarily states the design's facts, but never how they will be scored, what must not exist, or what will be broken; and that nothing reproduces specification text.

## For the owner — after the files are written

1. Review them as an architect. Do not correct them from anything you know from work — only from the public sources.
2. Keep all seven somewhere the SDEM session is not pointed at (not this repository).
3. Freeze: `shasum -a 256 design.md expected-records.json expected-links.json answer-key.json mutations.json coverage.json SOURCES.md > FROZEN.txt`, with the date.
4. Give the SDEM session **`design.md` only**. The other files are revealed at scoring.
