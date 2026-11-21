# Brief for the author of the second reference design (Model A, scenario 2)

> For the assistant the owner asks to write the reference for the public twin's **second scenario** — see the [plan](sdem-public-twin-benchmark-plan.md) and the [first run's report](../evidence/payment-initiation-v3/report.md). Complete on its own: the owner can hand this over without anything else. It replaces the [first brief](sdem-public-twin-reference-brief.md) for new work and is stricter, because of what the first run showed (section "What changed since the first brief"). It contains none of the answers.
>
> **Status: proposed — the owner chooses the scenario (below) before handing it over.**

## What this is for

SDEM is a tool that holds a solution design as records in four layers — A1 business, A2 BIAN service domains, A3 application, A4 technology — with links inside and between the layers; it checks the design, proposes links for an architect to approve, and answers questions about it. We test whether SDEM gets a realistic design right by comparing it with a design, and the right answers about it, written by someone who is **not** SDEM and not the session operating SDEM. That is you. Your files are frozen before SDEM sees any of them; SDEM's operator is given your design document only.

Two things follow, as before: **do not write towards SDEM** — do not look for its data model; write what a careful solution architect would, in ArchiMate 3.2 and BIAN terms. And **a wrong reference makes every score meaningless** — where a statement comes from a standard, open the standard and cite the place; where you could not verify, say so.

## The scenario

The same made-up New Zealand retail bank as the first scenario, a **new, self-contained design** — do not assume the reader has the first one.

**Recommended (the owner decides): the decoupled authorisation flow with an enduring payment consent.** A customer sets up a standing arrangement with a merchant's payment provider: the provider asks the bank for an enduring payment consent (limits on amount and frequency, an expiry); the customer authorises it on their own device in the bank's app — the standard's decoupled flow, not a redirect; later the provider initiates payments under the consent without the customer present; the bank checks each against the consent's limits, validates, screens and debits; the customer can see and revoke the consent. Cover the unhappy paths: the customer does not respond, declines, or revokes; a payment exceeds a limit; the consent has expired; the same payment is submitted twice.

*Why this one:* it is the other authorisation flow the regulated standard requires, it is documented in the same public standard (v2.3.3), and it brings what the first scenario did not — a long-lived consent with limits, a second channel (the bank's app), notifications, and state that changes over time.

**In scope:** everything inside the bank, through all four layers. **Out of scope** (name as boundaries only): the redirect flow, bulk files, direct debits, cards, cross-border, and clearing and settlement with other banks.

## Sources

Open each one you cite; record its URL, version and the date you read it.

| Layer | Source |
|---|---|
| A3 and the information | **NZ Banking Data API Specification, Payment Initiation API (including enduring payment consents) and Security Profile (decoupled flow) — v2.3.3**, public at `paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards`. v2.3.3 is the version MBIE's *Customer and Product Data (Banking and Other Deposit Taking) Standards 2025* incorporate; read that document for any modifications that touch this scenario |
| A2 | **BIAN 14.0.0** semantic API files, `github.com/bian-official/public`, `release14.0.0`. Choose the service domains the scenario needs and justify each |
| A4 | Reserve Bank of New Zealand — BS11 Outsourcing Policy, Guidance on Cyber Resilience — as expectations; the deployment is your design decision |
| Notation | ArchiMate 3.2 |

**Cite, never copy:** name a resource, field or status and cite where it is defined; reproduce no specification text, schema, table or diagram. **Nothing from any real bank.**

## What changed since the first brief — seven rules

The first reference found real faults in SDEM, but a quarter of it could not be scored. These rules fix that.

1. **A closed world.** Every record in your expected lists is **named in `design.md` by its id**, in the sentence or table that introduces it — `the consent service (APP-CONSENT)`. If a thing is not worth naming in the design, it is not in the expected records. *(First run: 44 of 196 expected records appeared nowhere in the design document — services, functions, events, artifacts.)* Before you hand over, check it mechanically: every id in `expected-records.json` occurs in `design.md`.
2. **A full design names what carries each process.** Name the application **services** (what each application offers) and, where it matters, functions; say which service serves which business process, and which component realises each service. In ArchiMate a process is served by an application *service*, never directly by a component. *(First run: the design named components only, so nothing could link the business layer to the software, and no "which process is affected?" question could be answered by any tool.)*
3. **Say where things run — or say it is not decided.** For every deployment: the node it runs on. For every piece of platform software (database, key store, messaging, monitoring): the node it runs on. For every node: its zone. Where the design has not decided, write "not decided" — that is a valid answer and will be scored as one.
4. **Say how the zones are arranged.** Either flat (a list of zones) or nested (which zone is inside which), and whether the estate is cloud, on premises or not stated.
5. **`in_design` means what it says, and is checked.** *stated*: one sentence or one table row of `design.md` names both ends and the relationship — a table's columns are *stated* to belong to the table. *implied*: it follows from two or more statements, none of which says it. Go through every link twice. *(First run: 18 of 212 links were marked stated; the tables' own columns were marked implied.)*
6. **A fixed vocabulary for links.** Inside a layer, ArchiMate's relationship names only: composition, aggregation, assignment, realization, serving, access, flow, triggering, association, specialization. Between layers, one of: `uses BIAN domain`, `supported by BIAN domain`, `realized by`, `served by`, `automated by`, `maps to` (object to table), `field maps to`, `stored in`, `deployed as`, `deployed on`, `exposed through`, `built as`. Anything that is not a direct relationship — "depends on, through …" — goes in a separate list, `derived`, with the chain of direct links it follows from.
7. **Questions and mistakes stay inside the design.** Every expected answer is a set of record ids from `expected-records.json`, or a value those records hold. Every planted mistake changes a record, a field or a link that exists in your expected files, and says exactly which. *(First run: one question and four mistakes needed records the design did not contain.)*

## Mark every statement S or D

**S — standards-derived:** checkable against a source; give the source, version and exact location. **D — design decision:** the made-up bank's own choice; give the reason in a few words. **S?** — you believe it is standard but could not open the source: never plain S. Give every requirement an id (`R-01` …) and measurable targets where they apply, marked D.

## The seven files

Write them in this order. The first is what SDEM's operator is given: it must stand alone, and must not contain the other files' content.

1. **`design.md`** — the solution design, as a document for people: scope and actors; requirements; the business process, its events and the information it handles (name the business objects); the BIAN alignment; applications, their services, interfaces and API operations with paths; the data — entities and fields with types, keys, which are personal, and the permitted values of every status; how the API's fields, BIAN's fields and the bank's columns correspond; the deployment — nodes, platform software, zones, locations, paths with their two ends and protocol; the unhappy paths; decisions and reasons.
2. **`expected-records.json`** — `{"records": [{"id", "layer": "A1|A2|A3|A4", "kind": "the ArchiMate element or BIAN term", "name", "basis": "S|S?|D", "source", "section": "the design.md section that names it", "fields": {…}, "acceptable_alternatives": "optional"}]}`
3. **`expected-links.json`** — `{"links": [{"from", "relationship": "from rule 6's lists", "to", "scope": "within-layer|between-layers", "basis", "source", "in_design": "stated|implied", "section": "where", "needed": "mandatory|optional"}], "derived": [{"from", "to", "follows_from": ["the direct links, in order"]}], "must_not_exist": [{"from", "to", "why"}]}` — 10–20 `must_not_exist`, each something a careless tool might plausibly propose.
4. **`answer-key.json`** — 30–50 questions: `{"id", "type": "lineage|trace|impact|standards|governance", "question", "expected": {"record_ids": […]} or {"value": "…"}, "basis", "source"}`. At least eight *impact* questions ("what is affected if … is retired / moves zone / is unavailable?"), each answerable by following the links in file 3.
5. **`mutations.json`** — 15–25 planted mistakes: `{"id", "category": "structure|standards|data|placement|governance|resilience", "change": {"op": "set_field|delete_link|add_link|move|duplicate_record|delete_record", …exact ids and values…}, "why_wrong", "a_tool_should": "refuse|warn|cannot-know", "basis", "source"}`. Use `cannot-know` honestly.
6. **`coverage.json`** — one row per requirement: what carries it in each layer (record ids), the evidence, and `met_by`: design, procedure, or not met.
7. **`SOURCES.md`** — every source opened (title, URL, version, date read, what for); every S?; anything in this brief you could not do.

## Before you hand it over — run these checks and report the result in `SOURCES.md`

- Every id in files 2–6 exists in file 2; every id in file 2 occurs in `design.md` (rule 1).
- Every relationship name is from rule 6's lists.
- Every link marked *stated* has a section where one sentence or row says it.
- `design.md` contains no expected lists, questions, mistakes or coverage table.
- Nothing reproduces specification text.

## For the owner — after the files are written

1. Review them as an architect; correct only from the public sources, never from anything known from work.
2. Keep all seven **outside this repository**, where the SDEM session is not pointed.
3. Freeze: `shasum -a 256 design.md expected-records.json expected-links.json answer-key.json mutations.json coverage.json SOURCES.md > FROZEN.txt`.
4. Give the SDEM session **`design.md` only** — the file itself, not the folder.
