# Use-case example 1 — testing the rulebook

> **Status: plan — not yet run.**

## Key words

- **Metamodel** — the rulebook: what records may exist, what they hold, how they may link.
- **Architecture dataset** — a file of one layer's records: business, BIAN, application or technology.
- **Rejected** — SDEM refuses data that breaks a rule, and says why.
- **Trace** — following the links from a server up to the business.

## Goal

Prove the rulebook works:

1. good data is **accepted**, bad data is **rejected**;
2. the four datasets get **linked** correctly;
3. you can **trace** from server to business.

## Test data

Payment-initiation example: 4 datasets, 68 records, **no links between them**, and an answer key of **18 links**.

## What we test

| # | Rule | Example |
|---|---|---|
| 1 | Record types | only 44 known kinds of record |
| 2 | Record information | criticality must be high, medium or low |
| 3 | Links inside a layer | a process may contain activities, not a capability |
| 4 | Links between layers | only 9 kinds, e.g. *application runs on server* |
| 5 | Finding links | 69 rules for working out the links |
| 6 | Approving links | approved links can't be changed |
| 7 | Sources | every rule says where it comes from |

## Two runs

**Run 1 — good data.** Expect: all accepted · 18 of 18 links correct · trace complete.

**Run 2 — planted mistakes.** Expect each one caught:

| Mistake | Expect |
|---|---|
| unknown kind of record | rejected |
| criticality "urgent" | rejected |
| process contains a capability | rejected |
| link between the wrong kinds of record | rejected |
| application doesn't say its server | no link made |
| edit an approved link | rejected |
| rule with no source | test fails |

Expected results are written down before the run.

## Output

| Rule | Data | Should | Did | ✅/❌ |
|---|---|---|---|---|
| 2 | criticality "urgent" | be rejected | *(when run)* | |

Plus: the 18 links found, the trace, and any gaps.

## Gaps already known

- **G-A** — the link-finding rules and the engine's code aren't checked against each other.
- **G-B** — limits on how many links of a kind may exist aren't checked.

## Limits

Made-up data · rules tuned on this example · approval by hand for now.
