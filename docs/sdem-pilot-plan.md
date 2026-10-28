# SDEM pilot plan — one domain, ten weeks

> **Status: approved by the owner 2026-10-29** (audit phase 4). The domain is chosen by the criteria below when the preconditions are met. A small, real trial of SDEM before wider use: one domain, two or three architects, ten weeks, a go / adjust / stop decision at the end. **The plan works for any domain** — SDEM's rulebook covers the whole bank (A1–A4, every BIAN service domain), and each further domain repeats the same ten weeks with its own estate. How SDEM is run: [`sdem-operating-model.md`](sdem-operating-model.md).

## The question the pilot answers

**Does SDEM make our architecture easier to find, trace and keep current — for an effort architects will accept?**

## Shape

| | |
|---|---|
| Domain | **any one domain**, chosen by the criteria below — the first pilot proves the way of working; later domains repeat it |
| People | 2–3 architects (A1, A3, A4 between them), 1 reviewer, the estate owner (one of the architects), the SDEM owner as maintainer |
| Time | 10 weeks, about half a day a week per architect after set-up |
| Data | 3–5 existing designs onboarded; the domain's changes during the pilot kept in SDEM |
| SDEM | v0.8.0, pinned |

## Choosing the domain

| Criterion | Why it matters |
|---|---|
| Has 3–5 designs in Confluence | there is something real to onboard |
| Has change coming in the next 2–3 months | the pilot needs a real change to test trace and impact |
| Its architects are willing and have half a day a week | the pilot depends on their time more than on the tool |
| Covers A1, A3 and A4 | tests all three layers that need no BIAN licence |
| Mid-sized, not on the critical path | big enough to be real; a slow start hurts no one |
| Designs reasonably consistent | a fair test of the transform's coverage |

A smaller domain with willing architects beats an important one with busy architects.

## Tuning for the domain

SDEM's rules are the same for every domain — the example estates already span seven (payments, cards and fraud, customer onboarding, lending, a core ledger, trade finance, an acquired fintech) with the same rulebook and checks. The design-onboarding test fixtures, though, are payments designs only, so the first pilot in another domain is also the transform's first test on that domain's documents. One thing is worth tuning per domain: the transform's list of words too general to be names (`narrative.ignore_names` in `transform-rules.json` — *system*, *platform*, *customer* …). Add the domain's own general words (for lending: *loan*, *lending*; for cards: *card*, *cards*) in the estate repository's copy and pass it with `sdem transform run … --rules rules/transform-rules.json`. Without it, the transform suggests a few extra candidates named after those words, which reviewers then reject.

## Timeline

```mermaid
gantt
    dateFormat  X
    axisFormat  week %s
    section Before
    Preconditions (legal, Python, repo, hosting)   :p, 0, 1
    section Set up
    Estate repo from template; training (2 h)      :s, 1, 2
    section Onboard
    3–5 designs: transform, review, load, gaps    :o, 2, 6
    section Use
    Real change work: link, approve, trace, impact :u, 6, 9
    section Decide
    Measures, retrospective, decision             :d, 9, 10
```

| Weeks | What happens | Done when |
|---|---|---|
| 0 | **Preconditions** ([operating model §6](sdem-operating-model.md#6-before-starting--what-must-be-true)): legal and IP clearance, Python 3.10+, private repository with protection, hosting decided | all six met — **the pilot does not start without legal clearance** |
| 1 | Estate repository from [`templates/estate-repo`](../templates/estate-repo/README.md); one estate folder for the domain; code owners named; transform tuned for the domain; 2-hour hands-on session with use-case example 4 | each architect has run the checks and an example onboarding |
| 2–5 | Onboard 3–5 designs ([onboarding workflow](sdem-onboarding-workflow.md)); review candidates; load; work the gaps | designs loaded through pull requests; coverage recorded |
| 6–8 | Use SDEM in real change: propose and approve links, trace, impact before a change, keep data current | at least one real change carried through SDEM end to end |
| 9 | Measure, retrospective, decision | decision recorded |

## Measures

| Measure | How | Target |
|---|---|---|
| Coverage | `extraction.json` per load | ≥ 90% of items captured |
| Time to onboard a design | architects' log | ≤ 1 day per design, falling |
| Link quality | proposals approved ÷ proposals reviewed | known and stable (a baseline, not a target, in a first pilot) |
| Gaps | open gaps over time | falling; each new entity-type request decided |
| Usefulness | short survey: *would you keep using it?* (1–5) and one question answered faster | average ≥ 4; at least one real impact question answered |
| Safety | real data outside the private repository; CI failures that reached `main` | **zero** for both |
| Effort | hours per architect per week | ≤ half a day after week 2 |

## Decision at week 10

| Outcome | When |
|---|---|
| **Go** — a second domain, same model | targets met, safety zero |
| **Adjust** — fix the top three problems, pilot again for 6 weeks | usefulness ≥ 3 but targets missed |
| **Stop** — record what was learned | usefulness < 3, or any safety failure that cannot be fixed |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Legal clearance takes longer than planned | medium | start week 0 only when it is granted; prepare everything else meanwhile |
| Designs are less structured than expected (low coverage) | medium | gap records keep everything; tune the domain's copy of `transform-rules.json` on the first design |
| The domain's vocabulary is not yet covered by the transform's word list | medium | the rulebook is domain-neutral; tune the transform's general words (above); review candidates as usual |
| Architects lack time | high | half a day a week, agreed with their manager before starting |
| BIAN ids (A2) unavailable without a licence | high | pilot A1, A3, A4; A2 only from public sources |
| Old Python on work machines | medium | precondition 3 |
