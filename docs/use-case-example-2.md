# Use-case example 2 — testing Architecture Inference Design (AID)

> **Status: plan — expected results sealed 2026-10-27, before any run.**

## Key words

- **AID** — Architecture Inference Design: projects the architecture layers you don't have, from the ones you do.
- **Projected design** — what AID produces: inferred, not real, with a confidence on every element.
- **Gap analysis** — comparing the projected design with the real one.
- **BIAN catalogue** — the list of BIAN service domains AID chooses from.

## Goal

Measure how close AID's projected design is to the real design.

## Method

1. Take an estate where all four layers are known: **payment-initiation**.
2. **Hide** some layers.
3. Let AID **project** them.
4. **Compare** with the hidden real layers.

**BIAN catalogue for the test:** the BIAN layer (A2) of all 7 example estates combined, so AID must *choose* the right service domains from several — not be handed the answer.

## Five runs

| Run | Architect has | AID projects | Real use |
|---|---|---|---|
| 1 | A1 + A2 | A3, A4 | "I've chosen my BIAN domains — what applications and deployments follow?" |
| 2 | A1 only | A2, A3, A4 | "I only have business design — preview everything below" |
| 3 | A4 only | A3, A2, A1 | "I only have infrastructure — what does it support?" |
| 4 | A3 + A4 | A2, A1 | "I have applications and technology — what business do they serve?" |
| 5 | A1 + A3 | A2 | "I have business and applications — fill in the BIAN layer between" |

## What we measure

For each run and layer: ✅ **matched** · ➕ **projected only** · ➖ **real only** · ≠ **differs** — giving precision and recall.

And the safety controls:

- **CTL-16** — a projection put into real data, or approved, is rejected.
- **CTL-17** — every projected element has its provenance; none is above medium confidence; no BIAN element is invented.

## Expected results (sealed)

| Run | Expected |
|---|---|
| 1 | every service domain gets a projected component, and every operation with a REST form an API; **no platform, environment or network invented**; APIs match the real method and path for **at least 2 of 6** (today's level), higher after the qualifier fix (AID-Q04) |
| 2 | **all** real service domains found where the business names its operations; few wrong |
| 3 | **every** application the technology names is projected; BIAN domains suggested at low confidence; the business layer the weakest |
| 4 | BIAN domains correct where the APIs carry BIAN-style operations |
| 5 | at least as accurate as run 2, because both sides agree |
| Safety | CTL-16 and CTL-17 hold **100%** — no exceptions |

## Starting point — honest

Only **run 1** works today (the engine's design mode). Runs 2–5 and the safety controls need AID built. So:

1. **Baseline now:** run 1 gives real numbers; runs 2–5 report *not built*.
2. **Build AID, then re-run** — each re-run shows measured progress against these sealed expectations.

## Output

Per run: a gap-analysis table (element, projected, real, result, confidence), precision and recall per layer, and the safety-control results — with evidence files, as in example 1.

## Limits

Made-up data · a small BIAN catalogue (7 estates), not the full licensed BIAN · AID's rules are tuned on SDEM's own examples, so a test written by someone else is still needed.
