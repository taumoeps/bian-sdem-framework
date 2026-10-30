# SDEM pilot plan — one domain, ten weeks

> **Status: current (v0.9.11)**. The domain is chosen by the criteria below when the preconditions are met. A small, real trial of SDEM before wider use: one domain, two or three architects, ten weeks, a go / adjust / stop decision at the end. **The plan works for any domain** — SDEM's metamodel covers the whole enterprise (A1–A4, every BIAN service domain), and each further domain repeats the same ten weeks with its own workspace. How SDEM is run: [`sdem-operating-model.md`](sdem-operating-model.md).

## The question the pilot answers

**Does SDEM make our architecture easier to find, trace and keep current — for an effort architects will accept?**

## Shape

| | |
|---|---|
| Domain | **any one domain**, chosen by the criteria below — the first pilot proves the way of working; later domains repeat it |
| People | 2–3 architects (A1, A3, A4 between them), 1 reviewer, the workspace owner (one of the architects) who is also the **in-house SDEM lead**, and the upstream SDEM maintainer for questions |
| Time | 10 weeks, about half a day a week per architect after set-up |
| Data | 3–5 existing designs onboarded; the domain's changes during the pilot kept in SDEM |
| SDEM | v0.9.11 (or later), pinned |

## Choosing the domain

| Criterion | Why it matters |
|---|---|
| Has 3–5 designs in Confluence | there is something real to onboard |
| Has change coming in the next 2–3 months | the pilot needs a real change to test trace and impact |
| Its architects are willing and have half a day a week | the pilot depends on their time more than on the tool |
| Covers business, applications and technology | business connects to applications only through the BIAN layer — start it from the **base BIAN** that ships with SDEM (`sdem bian import --base`), see the [onboarding workflow](sdem-onboarding-workflow.md#your-bian-a2-layer) |
| Mid-sized, not on the critical path | big enough to be real; a slow start hurts no one |
| Designs reasonably consistent | a fair test of the transform's coverage |

A smaller domain with willing architects beats an important one with busy architects.

## No per-domain settings

SDEM needs **no settings per domain**. The metamodel and checks are the same everywhere — the example workspaces span seven domains (payments, cards and fraud, customer onboarding, lending, a core ledger, trade finance, an acquired fintech) — and design onboarding has been tested on two (payments and lending — the lending design run with no lending-specific rules: 18 of 18 records found, nothing lost, no records made from general words like *loan* or *credit*).

What may need tuning depends on **how your organisation writes designs**, not on the domain: if your designs use table headings or column names SDEM does not recognise (e.g. *Platform* for an application, or a column like *Data classification*), those items become gap records. Add the headings to the workspace repository's copy of `transform-rules.json` (`tables`) and run `sdem transform run … --rules rules/transform-rules.json`. Do this once, on the first design, and keep the copy for every domain.

## Timeline

```mermaid
gantt
    dateFormat  X
    axisFormat  week %s
    section Before
    Preconditions (legal, Python, repo, hosting)   :p, 0, 1
    section Set up
    Workspace repo from template; training (2 h)      :s, 1, 2
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
| 1 | Workspace repository from [`templates/workspace-repo`](../templates/workspace-repo/README.md); one workspace folder for the domain; code owners named; a first design transformed to see which of your table headings SDEM does not yet recognise; 2-hour hands-on session with use-case example 4 | each architect has run the checks and an example onboarding |
| 2–5 | Onboard 3–5 designs ([onboarding workflow](sdem-onboarding-workflow.md)); review candidates; load; work the gaps | designs loaded through pull requests; coverage recorded |
| 6–8 | Use SDEM in real change: propose and approve links, trace, impact before a change, keep data current | at least one real change carried through SDEM end to end |
| 9 | Measure, retrospective, decision | decision recorded |

## Measures

| Measure | How | Target |
|---|---|---|
| Coverage — tables and diagrams | `sdem transform run` prints it; `coverage.by_kind` in `extraction.json` | ≥ 90% captured (payments and lending test designs: 95%) |
| Coverage — nothing lost | load reconciliation | **every** item captured or kept as a gap record — plain text and pictures are not read without AI or a person, so they are measured by being kept, not by being captured |
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
| Designs are less structured than expected (low coverage) | medium | gap records keep everything; tune your copy of the transform rules (`sdem transform rules`, shared by every domain) on the first design |
| Your designs use table headings SDEM does not recognise | medium | those items become gap records, so nothing is lost; add the headings to your copy of the rules (above) |
| Architects lack time | high | half a day a week, agreed with their manager before starting |
| No BIAN (A2) layer — then business never connects to applications | medium | build it in week 1 from the base BIAN (`sdem bian import --base --all`, or `--only` the domain's service domains) |
| Old Python on work machines | medium | precondition 3 |
