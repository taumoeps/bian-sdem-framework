# Use-case example 1 — testing the metamodel

> **Status: plan — not yet run.**

## Goal

Test the **metamodel** — the brain of SDEM — part by part, against its specification ([`architecture-metamodel-detail-level-spec.md`](architecture-metamodel-detail-level-spec.md)).

| | Role in this test |
|---|---|
| **Metamodel** | **what is being tested** |
| Engine | the processor — it applies the metamodel's rules |
| Trace | the output — proof that the parts work together |

The metamodel is complex and brittle: a rule nothing enforces can be broken without anyone noticing. So every part is tested with **good data** (accepted, and used as the spec says) and **bad data** (rejected by its control) — and any part **without a control** is reported as a gap.

## The metamodel's parts and what we test

| # | Part | The spec says (detail §) | Control | Good-data test → expected | Bad-data test → expected |
|---|---|---|---|---|---|
| 1 | **Entity types** | every record is one of 44 types; types inherit (is-a) (§3, §5) | dataset check | all 68 records typed correctly → **accepted** | unknown type; abstract type → **rejected** |
| 2 | **Attributes** | each type's fields, data types, allowed values, required fields (§16) | dataset check, schemas | every value valid → **accepted** | criticality "urgent"; text where a number is due; missing required field → **rejected** |
| 3 | **Links within an architecture** | only the 132 allowed links, with their counts (§6.1) | dataset check | 69 links all allowed → **accepted** | a link A1 does not allow; too many links where the max is one → **rejected** |
| 4 | **Link types between architectures** | 9 types, each only between named entity types, adjacent levels (§6.2) | registry validator | proposed links all of the 9 types → **valid** | wrong entity type; skipping a level → **rejected** |
| 5 | **Mapping rules** | 69 rules say how each link is found (§15) | acceptance tests only | engine finds the 18 expected links → **18 of 18, none wrong** | (see gap G-A) |
| 6 | **Mapping record and approval** | statuses, approval fields, approved links never edited (§6.4) | validator, change guard | proposed → approved → **allowed** | editing an approved link → **rejected** |
| 7 | **Provenance and confidence** | every part has source, reasoning, confidence by one rule (§17) | completeness and confidence tests | all present and consistent → **pass** | a missing source; a rating that breaks the rule → **fail** |

**Output check (all parts together):** trace from the production server up to the business capability, and back down → every hop present, each showing the link that justifies it.

## Control gaps found while planning

| Gap | What is not controlled | Risk |
|---|---|---|
| **G-A** | Mapping rules (#5): how a rule matches is written in the engine's code; the rule records describe it in plain text, which nothing checks against the code | a rule's record and the engine can drift apart unnoticed; only the acceptance tests would catch it |
| **G-B** | Link types (#4): each type's cardinality (e.g. one-to-many) is recorded but not enforced on actual links | a link that breaks a type's cardinality is accepted |

The test will confirm both, and look for any others.

## The data

The **payment-initiation** example (synthetic): four separate architecture datasets, 68 records, **no links between them** at the start; an answer key of the 18 links that should be found.

## The output — what you will get when the test is run

The test produces a **results report** added to this document. It has four parts.

### 1. The results table — did each part of the metamodel behave as the spec says?

Each row is **one test**: we feed the metamodel some data (good or deliberately bad) and record what happened.

| Column | Means |
|---|---|
| **Part** | which part of the metamodel is being tested (one of the seven above) |
| **Test** | the data we fed in |
| **Expected** | what the spec says should happen |
| **Actual** | what really happened, copied from the tool's output |
| **Control that acted** | the check that stopped (or allowed) it |
| **Result** | ✅ pass — actual matches expected · ❌ fail — it doesn't |

*Illustration (not yet run):*

| Part | Test | Expected | Actual | Control that acted | Result |
|---|---|---|---|---|---|
| 2 Attributes | a process with criticality "high" | accepted | *accepted* | dataset check | *✅* |
| 2 Attributes | a process with criticality "urgent" (not an allowed value) | rejected | *rejected — "criticality: 'urgent' is not one of high, medium, low"* | dataset check | *✅* |
| 3 Links within an architecture | a process "composes" a capability (not allowed in A1) | rejected | *rejected — "does not match the A1 rows"* | dataset check | *✅* |
| 6 Mapping record | an approved link is edited afterwards | rejected | *rejected — "approved record changed"* | change guard | *✅* |

A ❌ means the metamodel or its control is wrong and must be fixed.

### 2. The links the metamodel produced

The engine applies the mapping rules (part 5) to the four datasets. This table shows each link it found — and why — so you can see the rules at work:

| From | Link | To | Rule | Why | Confidence | Matches answer key? |
|---|---|---|---|---|---|---|
| *Payments Hub (application)* | *deployed on* | *production Kubernetes cluster* | *S33* | *the application names the cluster as its platform* | *high* | *✅* |

Expected: 18 links, all matching the answer key.

### 3. The control gaps

A list of every part of the metamodel that nothing enforces (G-A, G-B above, plus any the test finds), with the risk of each.

### 4. The trace — proof the parts work together

The end result in practice: starting from the production server, follow the links up through the four architectures.

*Illustration:*

```
production Kubernetes cluster          (A4 Technology)
  ← deployed on — Payments Hub          (A3 Application)   link PAY-108
    ← realised by — Payment Initiation  (A2 BIAN domain)    link PAY-106
      ← uses — Capture and validate payment instruction (A1 process)   link PAY-003
      ← supported by — Initiate Payment (A1 capability)    link PAY-001
```

Expected: every hop present, each with the link that justifies it.

### The verdict

A summary line, for example: *"7 of 7 parts behave as specified; 2 parts have no control (G-A, G-B); trace complete."*

## Limits

- The data is synthetic.
- The mapping rules were tuned while this example's answers were known; a test written by someone else is still needed to prove they work on unseen data.
- Approval is done by hand until the approve command exists.
