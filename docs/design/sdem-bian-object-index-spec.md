# BIAN's business objects without a download — an index, suggestions, a person decides

> **Status: approved by the owner (2026-11-22: "write spec and then implement") and built** — `bian/objects-14.0.0.json`, `sdem bian objects suggest`, `--object` from the base, the `sdem status` warning; sdem-bian 1.0.2. Revises [BB-D2](sdem-bian-base-design.md)
> for business objects only (descriptions stay out). Builds on the [BIAN import](sdem-full-design-metamodel-design.md) (IM-09: typed
> fields), the link types BD-01 / BD-02 ([BIAN on by default](sdem-bian-on-default-spec.md)) and SDEM's rule S30. Made-up data only.

## 1. Why

A service domain has business objects (BIAN's Business Object Model); SDEM maps them to the Data layer (`MAPPED_TO`, `FIELD_MAPPED_TO`).
But the BIAN that ships with SDEM leaves them out (BB-D2), so a design built from it has none, and its BIAN → Data connections stay
empty unless someone downloads BIAN's files and knows `--objects`. On `payment-v3-020` the gap was invisible. And when the objects were
imported, all of its domains' 80 objects and 620 fields, SDEM still proposed nothing: the design's columns (`payment_id`,
`debtor_account`) are not BIAN's names (`PaymentTransactionIdentification`, `PayerReference`). Having the objects is necessary;
deciding which one a table *is* takes a person.

So: ship the objects as a **lookup**, suggest candidates with their reasons, and let a person bring in only the one they choose and state
the link.

## 2. Rules

| Id | Rule |
|---|---|
| **BO-01** | **The index ships with the base.** `bian/objects-<release>.json` beside `base-<release>.json`: for every service domain of the release, its business objects (its control record is in the base already) with their typed fields as IM-09 reads them — `name`, `data_type`, `required`, `many`, `identifier`, `allowed_values`, `refers_to`. Each distinct definition is stored once (BIAN defines 521 objects differently in different domains; each domain keeps its own). **No descriptions, examples or other BIAN prose** — BB-D2's reason holds for those. Built by `scripts/build_bian_base.py` from the same release folder as the base; BIAN 14.0.0: 1,089 objects, 7,602 fields, 1.9 MB. |
| **BO-02** | **The index is a source, never a design.** Nothing in it enters a workspace by itself — only what a person asks for, record by record (BO-03). |
| **BO-03** | **`--objects` / `--object NAME` work with the base.** `sdem bian add` and `sdem bian import` read a domain's business objects from the index of the base's release, as they would from BIAN's files (BB-C04 is lifted for objects; `--descriptions` with the base is still refused). `--object` is the way to use it — a few named objects, not a domain's dozens. A pack of the organisation's own (`--base FILE`) has no index: refused as before, with the message to import from BIAN's files. |
| **BO-04** | **`sdem bian objects suggest --workspace W`** — read-only: for each data entity, up to three BIAN business objects it may be, each with its evidence: the entity's columns whose words match one of the object's fields (the object's own name taken off the field: `PaymentTransactionAmount` → *amount*), and the words the entity's name shares with the object's. Objects of the design's own service domains first. Each suggestion gives the two commands for the person: bring the object in (`sdem bian add "<domain>" --object <Object>`), and state the link (`sdem connect <object> MAPPED_TO <entity> --evidence … --rationale …`). Every suggestion is marked *a suggestion — not a link*. `--json` for an agent. |
| **BO-05** | **Words, plainly matched.** Names are split into lowercase words (snake_case and CamelCase); a short fixed list of equivalents is read as one word — *id = identification = identifier = reference = ref*, *datetime = date = time = at*, *amount = value* — and words that say nothing about meaning (*the, of, type*) are ignored. The list is in the code and this spec; nothing is learned or guessed beyond it. A score is the share of the entity's columns matched; the name's shared words break ties. |
| **BO-06** | **The gap is said.** `sdem status` warns when a design holds BIAN service domains but no BIAN business object — *"its BIAN → Data connections are empty"* — and names `sdem bian objects suggest` as a next step. A warning, never a failure: a design may decide not to map them. |
| **BO-07** | **The link stays a person's.** Suggesting writes nothing. A `MAPPED_TO` comes from `sdem connect` (or `sdem approve` of what S30 proposes), by a named person, with its evidence (CTL-21). An agent may run the suggestion and hand the commands over; it never runs them. |
| **BO-08** | **The BIAN package carries the index.** `sdem-bian`'s catalogue is SDEM's `bian/` folder (BP-02), so it gains the index in its next release (1.0.2); with an older package SDEM reads its own copy. |
| **BO-09** | **Proved by tests**: the index holds every domain of the release, no description anywhere, and the same typed fields BIAN's files give (checked against the downloaded files when present); `--object` with the base brings in exactly the named object with its typed fields; `suggest` ranks, for a made-up ledger with payment columns, BIAN's Payment Transaction first and writes nothing; `sdem status` says the gap; a pack of one's own is still refused. |

## 3. Decision

| # | Decision | The owner's choice |
|---|---|---|
| BO-D1 | Ship BIAN's business objects — names and typed fields, no descriptions — as an index; suggest, a person brings in and links (revises BB-D2 for objects) | **yes** (2026-11-22) |
