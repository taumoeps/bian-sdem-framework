# Architecture Inference Design (AID) — Specification

> **Status: approved 2026-10-27 (design decisions AID-D01…07); §12 (AI suggestion layer, AID-D08) proposed, not approved.** Requirements for the design in [`aid-design.md`](aid-design.md). Each requirement has an ID (AID-*), a status, and how it is accepted. **Built 2026-10-27, completed 2026-10-28** in `sdem/aid.py` (command `sdem aid`), `schema/projection.schema.json` and the graph view and trace; tested by [use-case example 2](use-case-example-2.md). Every requirement in §2–§9 is built; §12 (AI) is proposed only.

## 1. Purpose and boundary

AID projects the missing architecture layers from the architecture datasets an architect has, for **planning** — scope, impact, upstream and downstream alignment, gaps. Its output is a **projected design** within stated inference confidence, **not** a validated design.

**Out of scope:** approving projected links; generating real architecture datasets; inventing BIAN content; projecting anything a rule or pattern does not support.

## 2. Inputs

| ID | Requirement | Status |
|---|---|---|
| AID-I01 | Accept any non-empty subset of the four architecture datasets (A1–A4), each passing the dataset check (controls CTL-01…03). | built — inputs must pass the dataset check |
| AID-I02 | Accept a **BIAN reference catalogue**: an A2 architecture dataset of BIAN service domains, operations, business objects, asset types and behaviour qualifiers, used as the only source of A2 elements. | built |
| AID-I03 | Accept the approved links already known (a Relationship Registry), and use them before inferring anything. | built — used by F1 and R2 (the engine reads it) |
| AID-I04 | Read the rulebook (entity types, allowed links, relationship types, mapping rules) exactly as the engine does. | built (engine) |

## 3. Forward projection (downstream)

| ID | Requirement | Confidence | Status |
|---|---|---|---|
| AID-F01 | **A1 → A2.** Project the service domains a business architecture needs: (a) domains of BIAN operations an A1 process or activity names (`invokes`); (b) otherwise by verb + noun matching of activity names to operations (rule S06) and of capability and process descriptions to domains (step 5, bounded). Each projected domain is a **reference** to the BIAN catalogue, never a new A2 element. | (a) medium, (b) low | built |
| AID-F02 | **A2 → A3.** For each projected or given service domain: one component; one API per service operation, method and path from BIAN's REST mapping; payload from the operation's attributes (BIAN container pattern). | low | built — with the qualifier fix (AID-Q04) |
| AID-F03 | **A3 → A4.** One deployment per projected component. No platform, environment, network or location is projected. | low | built |
| AID-F04 | Projected links between layers use only the nine relationship types, between the right entity types. | as the element | built |

## 4. Reverse projection (upstream)

| ID | Requirement | Confidence | Status |
|---|---|---|---|
| AID-R01 | **A4 → A3.** Project an application component for every A3 id an A4 record names (`hosts`, `component_id`, `of_component`); carry only the id and the A4 evidence. | medium (existence) | built |
| AID-R02 | **A3 → A2.** Map A3 elements to the BIAN catalogue with the engine's rules: API ↔ operation (step 2), data entity ↔ business object (S30), component ↔ domain (S17 and its fallbacks). Projected domains reference the catalogue. | medium → low | built — plus a low-confidence fallback from id words when A4 gives only an application id |
| AID-R03 | **A2 → A1.** Suggest capabilities and processes a domain typically supports, from the domain's name, description and operations. Each suggestion is a low-confidence candidate, never a named A1 record of the institution. | low | built — a capability candidate per domain (from its name) and a process candidate per BIAN service group (from its operations) |
| AID-R04 | Stop at the first layer with no basis; report *projection ends at <level>* with the reason. | — | built |

## 5. Middle gap

| ID | Requirement | Status |
|---|---|---|
| AID-M01 | With layers above and below a missing layer, project the missing layer from both sides (forward and reverse) and keep elements both sides support; an element supported by both is one band higher than either alone (still capped by AID-S04). | built |

## 6. Output — the projection package

| ID | Requirement | Status |
|---|---|---|
| AID-O01 | A projection is written as a **projection package** — a folder, separate from architecture datasets, the registry and graph stores: `projection.json` (metadata), one projected architecture dataset per projected layer, and `projected-links.json`. | built |
| AID-O02 | `projection.json`: projection id, mode (forward / reverse / middle), the datasets and catalogue used (with checksums), rulebook version, created by, created at, and per layer a summary (elements projected, by confidence). | built |
| AID-O03 | Every projected record: id `PRJ-<…>`; the normal record fields for its entity type; and a `projection` object — `{step, rule, inferred_from, reasoning, confidence}`. | built |
| AID-O04 | Every projected link: the relationship-record fields, status `projected`, plus the `projection` object. | built |
| AID-O05 | The package validates against `schema/projection.schema.json` (new); projected records also pass the per-entity schemas apart from fields AID cannot know, which are omitted. | built — `schema/projection.schema.json`, checked first by CTL-17 |
| AID-O06 | The graph view and trace can load a projection package alongside real data, labelling every projected element **PROJECTED** and showing its confidence. | built — `sdem view --projection` (dashed, labelled PROJECTED with confidence and provenance) and `sdem trace --projection` |

## 7. Gap analysis

| ID | Requirement | Status |
|---|---|---|
| AID-G01 | Compare a projection package with real architecture datasets and registry, per layer and per link: **matched**, **projected only**, **real only**, **differs**. | built — `sdem aid gaps` |
| AID-G02 | Matching: A2 by BIAN `canonical_id`; A3 components by the BIAN operations their APIs implement, then by name; APIs by method and path; deployments by component; A1 by the domains they use, then by name. Each match states the rule that matched it. | built — every result states the rule that matched it; A2 by BIAN `canonical_id`; a name-only resemblance is reported as *similar name*, not counted as a match |
| AID-G03 | Report precision and recall per layer and per relationship type, and list every unmatched element with its reason. | built — per layer, per relationship type, and every unmatched element with its reason |

## 8. Safety rules and their controls

| ID | Requirement | Control (proposed) |
|---|---|---|
| AID-S01 | A projection never enters an architecture dataset, the Relationship Registry or a real graph store. | **CTL-16** (built): the dataset check, the registry validator and the store build reject `PRJ-` (and design-mode `DSN-`) records, approval of links to them, and projection datasets |
| AID-S02 | A projected link is never approved. | **CTL-16** (status `projected` is not a registry status) |
| AID-S03 | Every projected element carries its projection provenance. | **CTL-17** (built): `sdem aid check`, run before every projection is written |
| AID-S04 | No projected element above **medium** confidence; pattern-derived elements are **low**. | **CTL-17** |
| AID-S05 | No BIAN element is invented: every projected A2 element references the catalogue. | **CTL-17** |
| AID-S06 | Nothing beyond the rule or pattern: no platforms, environments, owners or names without a basis. | acceptance tests (§9) |
| AID-S07 | Name-only evidence — an engine fallback (e.g. S17 fallback B), a description match, a verb-and-noun or id-word match — never gives a projected element more than **low** confidence, so a strong projection can be told from a weak one (finding AID-B6). | **CTL-17** (built) |

CTL-16 and CTL-17 are in the controls register, tested with good and bad data in use-case example 2 (15 of 15 pass).

## 9. Acceptance

**Method:** take example estates where all four layers are known, **hide** layers, run AID, and run gap analysis against the hidden real layers.

| ID | Run | Given | Projected | Pass when |
|---|---|---|---|---|
| AT-AID-01 | Forward from A1 + A2 | A1, A2 | A3, A4 | every given domain has a component and its operations APIs; no platform invented; the existing M2 case still passes |
| AT-AID-02 | Forward from A1 only | A1 + BIAN catalogue | A2, A3, A4 | projected domains include every real domain whose operations A1 names; precision and recall reported per layer |
| AT-AID-03 | Reverse from A4 only | A4 + catalogue | A3, A2, A1 | every application A4 names is projected; A2 suggestions reported with confidence; A1 marked low |
| AT-AID-04 | Reverse from A3 + A4 | A3, A4 + catalogue | A2, A1 | projected domains match the real domains for every component whose APIs carry BIAN operations |
| AT-AID-05 | Middle gap | A1, A3 + catalogue | A2 | domains supported from both sides are matched; precision at least that of AT-AID-02 |
| AT-AID-06 | Safety | any | — | CTL-16 rejects a projected record in a dataset, a projected link in the registry, and approval of a projected link |

The accuracy reached is **reported, not assumed**: each run states its precision and recall per layer — the "inference accuracy" an architect plans with.

## 10. Commands

```
sdem aid project --have a1.json [a2.json …] --catalogue bian.json [--registry approved.json] --out projection/
sdem aid check   projection/ [--catalogue bian.json]
sdem aid gaps    projection/ --actual a*.json mappings.json
sdem view  --graph graph/ --projection projection/
sdem trace <id> --graph graph/ --projection projection/
```

## 11. Open questions

| ID | Question | Recommendation |
|---|---|---|
| AID-Q01 | Where does the BIAN catalogue come from? | A2 dataset built from the public portal for testing; an institution's licensed copy in practice |
| AID-Q02 | Should AID project data entities (A3) from BIAN business objects? | Yes, low confidence, as an option — the pattern does not give them; off by default |
| AID-Q03 | How far should reverse projection go above A2 (R3)? | Candidates only, low; revisit when BIAN publishes its capability-to-domain mapping |
| AID-Q04 | Should F2 put a create-type operation with a behaviour qualifier (e.g. *Evaluate … Validation*) on a qualifier sub-resource (`POST …/{id}/validation`)? Found in the design illustration: today it uses the collection. | Yes — align with check 3 of step 2. **Done 2026-10-27**: APIs matched rose from 2 to 3 of 5 |
| AID-Q05 | Should AID use AI where rules have no basis? | Proposed as AID-D08 (design §8) — through the architect's Copilot, never an AI SDEM calls: rules first, closed questions only for gaps, every answer checked, marked and capped; requirements in §12 |

## 12. AI suggestion layer through Copilot (proposed — AID-D08, **not approved, not built**)

Revised 2026-10-28 to the SDEM workbench: the AI is the architect's GitHub Copilot Chat in VS Code; SDEM calls no AI, holds no key, uses no MCP ([`sdem-workbench-spec.md`](sdem-workbench-spec.md) §8).

| ID | Requirement | Status |
|---|---|---|
| AID-AI01 | Rules run first. `sdem aid project --ask` then writes `ai/questions.json`, one question per gap the rules left (a layer where projection ended, or an element found only by name evidence): the record, its neighbours' names and descriptions, the BIAN catalogue choices, and the answer format. | not built |
| AID-AI02 | The answer format is closed: `{question_id, choice, evidence, reasoning}` where `choice` is an id from the question's list or `none`. Prompt file `.github/prompts/aid-suggest.prompt.md` tells Copilot to answer only in this format into `ai/answers.json`. | not built |
| AID-AI03 | `sdem aid ai-import` rejects (and logs) any answer whose choice is not in the list, whose evidence ids do not exist in the inputs, or that is not in the format. | not built |
| AID-AI04 | Every accepted answer becomes an element with id `PRJ-AI-<…>`, rule `AI suggestion`, source reference "GitHub Copilot (model as stated)" plus the checksums of both files, reasoning prefixed **UNVERIFIED (AI)**, confidence **0.2**. | not built |
| AID-AI05 | `questions.json` and `answers.json` are kept in the projection package's `ai/` folder; re-importing the same answers gives the same result. | not built |
| AID-AI06 | Gap analysis reports AI elements separately: precision and recall for rules only, and for rules + AI. | not built |
| AID-AI07 | Acceptance: use-case example 2 with and without the answers; AI is kept only if recall rises without precision falling below a limit recorded before the run. Automated tests use saved answers. | not built |

**Control (proposed): CTL-18** — AI suggestions are marked `PRJ-AI-`, carry the stated model and both files' checksums, are at most 0.2, choose only from the BIAN catalogue, and are reported separately in gap analysis. Added to the controls register only when approved and built.
