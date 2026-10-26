# Use-case example 1 — testing the metamodel

> **Status: plan — not yet run.**

## First, the words

| Word | Plain meaning |
|---|---|
| **Architecture** | a description of how a bank is put together. SDEM uses four, one per layer: **A1 Business** (what the bank does), **A2 Service Domain** (the standard BIAN building blocks of banking), **A3 Application** (the software), **A4 Technology** (the servers and platforms). |
| **Architecture dataset** | a file holding one architecture's information — e.g. a list of the bank's business processes, or its servers. There are four: one per layer. |
| **Record** | one thing in a dataset — one process, one application, one server. |
| **Link** | a connection between two records, e.g. *"the Payments Hub application runs on the production server"*. |
| **Metamodel** | **the rulebook.** It says what kinds of record may exist, what information each must hold, and which links are allowed. It is the brain of SDEM: everything else follows its rules. |
| **Control** | an automatic check that enforces a rule of the rulebook. |
| **Accepted / rejected** | when data follows the rules, SDEM **accepts** it and loads it. When it breaks a rule, SDEM **rejects** it — refuses to load it and says why — like an online form that won't submit until a wrong field is fixed. |
| **Engine** | the program that reads the four datasets and uses the rulebook to work out the links **between** the layers. |
| **Knowledge graph** | all the records and links joined together, so you can follow them. |
| **Trace** | following the links, e.g. from a server up to the business capability that depends on it. |

## Goal

**Test the rulebook (the metamodel).** Prove that:

1. every rule is **enforced** — good data is accepted, bad data is rejected;
2. using the rules, the four separate datasets can be **linked together** correctly;
3. the result can be **traced** from the bottom layer to the top.

The engine and the trace are only how we see the rulebook at work. The rulebook is what is under test, because it is complex and brittle: a rule that nothing enforces can be broken without anyone noticing.

The rulebook is written down in [`architecture-metamodel-detail-level-spec.md`](architecture-metamodel-detail-level-spec.md).

## The test data

The **payment-initiation** example — made-up data for a bank's payments area:

- four datasets (business, BIAN, application, technology), **68 records**;
- each dataset has links **inside** it, but there are **no links between the layers** at the start;
- an **answer key**: the 18 links between the layers that should be found.

## The seven parts of the rulebook we test

| # | Rule area | In plain words | The control that enforces it |
|---|---|---|---|
| 1 | Record types | every record must be a known kind of thing (one of 44, e.g. *business process*, *server*) | the dataset check |
| 2 | Record information | each kind of record holds set information, in set formats — e.g. a process's *criticality* must be *high*, *medium* or *low* | the dataset check |
| 3 | Links inside a layer | only certain links are allowed inside each layer — e.g. a process may contain activities, but may not contain a capability | the dataset check |
| 4 | Links between layers | only 9 kinds of link may join the layers, each between named kinds of record — e.g. *an application runs on a server* | the link checker |
| 5 | Rules for finding links | 69 rules say how to work out each link between layers from the data | the acceptance tests only |
| 6 | Approving links | a found link is only *proposed* until an architect approves it; once approved it can never be edited | the link checker and the change guard |
| 7 | Sources | every rule says where it comes from (e.g. BIAN, ArchiMate), why, and how sure we are | the completeness and confidence tests |

## Two test runs

### Run 1 — good data

The four datasets exactly as they are, with no mistakes.

| What we do | What should happen |
|---|---|
| check the four datasets against the rulebook | all **accepted** — no rule broken |
| let the engine work out the links between the layers | it finds **18 links, all matching the answer key, none wrong** |
| approve the links | allowed |
| trace from the production server up to the business capability, and back down | every step of the way is there, each with the link that justifies it |

### Run 2 — bad data, on purpose

The same datasets with **mistakes planted deliberately**, one or more for each part of the rulebook. Examples:

| Mistake planted | Rule area | What should happen |
|---|---|---|
| a record of a kind that does not exist | 1 | **rejected** |
| a process with criticality "urgent" | 2 | **rejected** — "urgent" is not high, medium or low |
| a process that "contains" a capability | 3 | **rejected** — not allowed in the business layer |
| a link between the wrong kinds of record | 4 | **rejected** |
| an application that does not say which server it runs on | 5 | **no link made** — the engine does not guess |
| two APIs that fit one operation equally well | 5 | **no link made** — both named, for a person to decide |
| an approved link edited afterwards | 6 | **rejected** |
| a rule with its source removed | 7 | **fails** the completeness test |

The expected result of every mistake is **written down before the run**, so nobody can adjust it afterwards to fit.

## What you get when the test is run

A **results report**, added to this document:

**1. The results table** — one row per test: what data we gave SDEM, what the rulebook says should happen, what actually happened, and ✅ if they match or ❌ if they don't.

| Rule area | Data given | Should | Did | ✅ / ❌ |
|---|---|---|---|---|
| 2 Record information | a process with criticality "urgent" | be rejected | *(filled in when run)* | |

A ❌ means a rule is wrong or is not enforced, and must be fixed.

**2. The links found** in run 1 — each with the rule that found it, why, how sure, and whether it matches the answer key.

**3. The gaps** — any part of the rulebook that nothing enforces.

**4. The trace** — the path from the server to the business capability, link by link.

**5. A one-line verdict** — e.g. *"all rule areas enforced; 18 of 18 links correct; trace complete; 2 gaps."*

## Gaps already found while planning

| Gap | What is not enforced | Why it matters |
|---|---|---|
| **G-A** | Rule area 5: the rulebook describes each link-finding rule in words, but the engine holds its own copy of the logic; nothing checks the two still agree | the rulebook and the engine could quietly drift apart |
| **G-B** | Rule area 4: each kind of link says how many may exist (e.g. one-to-many), but this is not checked | a link breaking that limit would be accepted |

The test will confirm these and look for others.

## Limits

- The data is made up, not real bank data.
- The link-finding rules were tuned while this example's answers were visible, so passing does not prove they work on new data; a test written by someone else is still needed.
- Approving is done by hand until an approve command exists.
