# The Data Architecture — domains, ownership, read and write, quality and retention

> **Status: approved by the owner (2026-11-22: "approve and build") and built** — metamodel 0.19.0 (RA3-35, RA3-36, AT-A3-52…56), `sdem data lineage`, `sdem data mode`, `sdem connect --access-mode`, `sdem status` (DAR-07), DESNRE's Data plate (DW-75); DAR-09 not yet (below). It extends the Data layer
> ([data layer spec](sdem-data-layer-spec.md), DL-01…) and changes the metamodel (0.18.0 → 0.19.0), so it needs the owner's approval
> (AGENTS.md rule 2). It answers an external review of the A3 plate ("closer to a logical data model than a whole data architecture"),
> keeping SDEM's rule that every link is ArchiMate's own. Made-up data only.

## 1. Why

SDEM's Data layer holds **data entities** (ArchiMate's data object) and their **fields**, with classification, personal data, retention
and where they are stored. On the Payment example that is four tables and their keys: a correct logical data model, but not a data
architecture. Four things an architect expects are missing:

| Missing | What the architect cannot say today |
|---|---|
| **Domains** | that the four ledgers belong to *Payments*, and *Consent* is a subject area inside it (TOGAF's logical data component) |
| **Ownership** | who is accountable for an entity, and who looks after it day to day |
| **Read and write** | which application *writes* the payment ledger and which only *reads* it — so where data comes from (lineage) |
| **Quality and retention rules** | a rule an entity's data must meet, or a retention rule with its basis, that can be checked and approved |

## 2. What is already in SDEM, and stays as it is

The review listed thirteen components. Nine are already in SDEM or belong in another layer; this spec adds none of them:

| The review's component | In SDEM |
|---|---|
| Data entity, data attribute, entity relationship | `data.DataEntity`, `data.DataAttribute`, an association between entities (the foreign-key line) |
| Data classification | `classification` on a field, `personal_information` on an entity and a field — attributes, not records |
| Retention period | `retention_period` on an entity (the *rule* is DAR-06) |
| Physical data component, data store | ArchiMate's artifact and system software on Technology; an entity's `stored_in` names them |
| Data contract | an interface's `contract_format`; an API operation's request and response fields name data fields |
| Data security control | the security extension's S3 layer (one `SecurityControl` type, linked by PROTECTS) |
| Data model | the Data plate itself, or a domain (DAR-01) |

Its link names (`contains`, `stores`, `classified_as`, `governed_by` …) are not adopted: SDEM uses ArchiMate's kinds.

## 3. Rules

| Id | Rule |
|---|---|
| **DAR-01** | **A data domain** — a new Data type, `data.DataDomain`, an ArchiMate **Grouping** (ArchiMate 3.2 §4.4.1): it **aggregates** data entities and other data domains. A domain inside a domain is a *subject area*; the lowest one is TOGAF's *logical data component*. Attribute `domain_kind`: `domain` · `subject_area` · `logical_component` (optional, a label only). An entity may sit in more than one domain (aggregation, not composition). |
| **DAR-02** | **Ownership** — two optional attributes on a data entity and a data domain: `data_owner` (accountable) and `data_steward` (looks after it), each the id of an A1 business role or actor (`refers to`, as `stored_in` refers to Technology). An attribute, not a link between layers, so nothing new to approve. A domain's owner is read by its entities that name none. |
| **DAR-03** | **Read and write on an access link** — `ACCESSED_BY` (DL-04) gains an optional field `access_mode`: `read` · `write` · `read_write`, ArchiMate's own access types (ArchiMate 3.2 §5.2.2). Stated by a person with the link; never inferred. A link without it is an access of unknown mode, as today. The mapping schema gains the field; existing links are unchanged. |
| **DAR-04** | **Lineage, derived, never stored** — `sdem data lineage <entity>`: where an entity's data comes from and where it goes — an application that *reads* entity X and *writes* entity Y gives *X → (application) → Y*. Read-only, from approved links with a stated mode only; a link of unknown mode is listed as *mode not stated*, never guessed. |
| **DAR-05** | **The trace walks a domain** — a domain is a whole (FT-01's aggregation), so an entity's full trace climbs to its domain and never into the domain's other entities (FT-02). Impact of a change to a domain reaches its entities. |
| **DAR-06** | **Quality and retention rules are requirements** — two new requirement categories, `data_quality` and `data_retention`, on an entity or a field (`subject`), with a measurable condition (e.g. `valid_pct >= 99.5`; `retention_years >= 7`) and its evidence, confirmed by a person as any requirement is. No new record type. |
| **DAR-07** | **What `sdem status` says** — a warning, never a failure, and only once the design uses the Data Architecture (a domain, an owner or a stated mode), so a design that has not started is not flooded: a data entity in no domain once the design has a domain; an entity holding personal data with no `data_owner`; an access link to an entity holding personal data with no `access_mode`. |
| **DAR-08** | **The plate shows it** — the Data plate draws a domain as a box round its entities (a subject area nested inside), and an entity's owner on hover. Read and write are written on the access lines between the Data and Application plates (*reads*, *writes*, *reads and writes*). The layout of the workbench views is the DESNRE project's; this spec asks only that these be drawn. |
| **DAR-09** | **Security reaches a domain** *(not yet built: the security extension's link types to a domain would refuse any SDEM before metamodel 0.19.0; added with the next security release that requires it)* — the security extension may PROTECT and THREATEN a data domain (its pack's link types, not SDEM's core); a control on a domain protects its entities for the trace (FT-09). |
| **DAR-10** | **The Payment example shows it** (made-up): a *Payments* domain with subject areas *Consent*, *Payment processing* and *Security audit* (a change set an agent proposes, citing the design's AD-01 and §5–§6); read and write on its ten access links, each as the design document states it (§4–§6) — stated by a person (`sdem data mode`), never by an agent. Owners, and quality and retention rules, are left to a person: the design document names none, so `sdem status` says so (DAR-07). |
| **DAR-11** | **Proved by tests**: a domain is accepted and checked; aggregation to an entity or a domain only; `access_mode` accepted on ACCESSED_BY and refused elsewhere; lineage from read and write, and *mode not stated* otherwise; the trace climbs to a domain and not to its other entities; the two requirement categories accepted; the three status warnings; the 0.19 answers unchanged (BX-31) except where named. (`tests/test_data_architecture.py`) |

## 4. What changes, and what does not

- **Metamodel 0.18.0 → 0.19.0**: one type (`data.DataDomain`), four attributes (`domain_kind`, `data_owner` ×2 types, `data_steward` ×2),
  one mapping field (`access_mode`, and the same on an access link read in 0.19's shape), two requirement categories. Migration: none needed — every addition is optional.
- **SDEM 0.21.0** (the owner, 2026-11-22, MIP-D2: a metamodel change is an SDEM version); the metamodel bump follows SDEM's procedure (migrate examples, rebuild graph
  stores, regenerate, freeze).
- **Not changed**: the existing types, their links, the layer stack, BIAN, the security layer's types.

## 5. Decisions for the owner

| # | Decision | Recommended |
|---|---|---|
| DAR-D1 | Add the data domain, ownership, read/write and the two requirement categories (DAR-01…DAR-07) as metamodel 0.19.0 (released as SDEM 0.21.0, MIP-D2) | **yes** (2026-11-22) |
| DAR-D2 | Ownership as attributes naming an A1 role (DAR-02), not a new link between Business and Data | **yes** (2026-11-22) |
| DAR-D3 | Lineage derived from read/write (DAR-04), not a stored "derived from" link between entities | **yes** (2026-11-22) |
| DAR-D4 | Update the Payment example (DAR-10) and republish it | **yes** (2026-11-22) |
