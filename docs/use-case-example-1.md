# Use-case example 1

> **Status: plan — not yet run.**

## Goal

Show that SDEM can take four **separate** architecture datasets — A1 Business, A2 Service Domain, A3 Application, A4 Technology — and **link them together**, so you can trace from a server all the way up to a business capability.

## The data

The **payment-initiation** example (synthetic):

- 4 architecture datasets, **68 records**
- **No links between them** at the start
- An **answer key** of the 18 links that should be found

## Two runs

| Run | Data | Why |
|---|---|---|
| **1 — Clean** | the datasets as they are | shows SDEM finds every link when the data is right |
| **2 — Imperfect** | the same datasets with **8 deliberate mistakes** | real data is never perfect — shows SDEM refuses or flags bad links instead of guessing |

For run 2, the expected result of each mistake is **written down before the run**, so the test is honest.

## What happens in each run

1. **Check** the four datasets — bad data is rejected.
2. **Engine** proposes the links between them.
3. **Score** the proposals against the answer key.
4. **Approve** the links (by hand for now).
5. **Trace** from the production server up to the capability, and back down.

## The output

A results table — one row per link:

| From | Link | To | Why (rule and evidence) | Confidence | Result |
|---|---|---|---|---|---|
| Retrieve Payment Instruction | implemented by | API `POST /payment-instructions/{id}` | rule S24: payload matches, but Retrieve should be GET, not POST | medium | ✅ correct, flagged |

**Result** is one of: ✅ correct · ⚠️ correct but flagged · ❌ wrong · ➖ missed · 🚫 refused (with the reason).

Below the table: the totals, and whether the trace worked.

## Expected

- **Run 1:** 18 of 18 links found, none wrong.
- **Run 2:** each mistake caught as written down beforehand — rejected, refused or flagged; nothing invented.

## Limits

- The data is synthetic, not real.
- The engine was built while this example's answers were visible, so this doesn't prove it works on unseen data — that needs a test written by someone else.
- Approval is done by hand until the approve command exists.
