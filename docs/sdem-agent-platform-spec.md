# SDEM Agent Platform — Specification

> **Status: draft 2026-10-28 — proposed, not approved, not built** (decisions AG-D01…D08 for the owner). Requirements for the design in [`sdem-agent-platform-design.md`](sdem-agent-platform-design.md). Each requirement has an ID (AG-*), a status and how it is accepted. Builds on the workbench spec ([`sdem-workbench-spec.md`](sdem-workbench-spec.md)).

## 1. Purpose and boundary

One agent per architecture (A1–A4) generates and maintains designs in its own layer; a coordinator agent organises the work; they coordinate through the federated graph (change events, impact results, work items); the rules engine proposes cross-layer links; architects approve.

**Out of scope:** direct agent-to-agent messaging; agents approving anything; agents creating cross-layer links; MCP; an AI API inside SDEM; historical design repository (roadmap v0.16).

## 2. Data foundations (what agents read)

| ID | Requirement | Status |
|---|---|---|
| AG-F01 | Each architecture's records and internal links, with their schema, readable by command (`sdem query --json`). | built |
| AG-F02 | The federated graph readable across layers: trace up and down, impact of a change (`sdem trace --json`, `sdem impact --json`). | built |
| AG-F03 | Cross-layer links proposed only by the rules engine (`sdem link`), with rule, reasoning and confidence. | built |
| AG-F04 | Planning projections (AID) kept apart from real data. | built (CTL-16/17) |
| AG-F05 | Real designs loaded from the organisation's sources (ingestion). | not built — roadmap v0.11 |
| AG-F06 | A licensed BIAN catalogue as the A2 agent's only source of BIAN elements. | not built — roadmap v0.15 |

## 3. Coordination records

Stored in the project (Git), validated by a schema (`schema/coordination.schema.json`, new).

| ID | Requirement | Status |
|---|---|---|
| AG-R01 | **Change set**: id, the one layer it changes, the record changes (add / update / retire, with the full record), reason, `agent`, `person`, created at, branch. | not built |
| AG-R02 | **Change event**: id, the change set or merge that caused it, when, by whom. | not built |
| AG-R03 | **Impact result**: the change event, each affected record with level, classification (`design_change_required` / `no_impact` / …), traversal path (link ids), and links to supersede — the output of `sdem impact`, stored. | not built (computed today, not stored) |
| AG-R04 | **Work item**: id, layer, record(s), action, reason (change event + impact path), status `open` → `in_progress` → `done` / `blocked` / `cancelled`, holder (agent + person), round number. | not built |
| AG-R05 | Records are append-only: a status change adds a new state with time and actor; nothing is deleted. | not built |

## 4. Commands (the agents' only interface)

All under the `sdem` CLI, with `--json`, the standard exit codes and `--help` with an example (workbench WB-K04/K05).

| ID | Command | Does | Status |
|---|---|---|---|
| AG-K01 | `sdem change propose <change-set> --layer A? --agent <name> --person <name>` | checks the change set against the rulebook and controls **before** it lands; on success applies it to the layer's dataset on the current branch, records the change event and stores the impact result | not built |
| AG-K02 | `sdem change show <id>` | the change set, its checks and its impact | not built |
| AG-K03 | `sdem events [--open]` | change events with their impact summary | not built |
| AG-K04 | `sdem work create / list / claim / update / done` | work items — create (coordinator), list (by layer, status), claim, update, close | not built |
| AG-K05 | `sdem impact … --record` | computes impact and stores it as an impact result for a change event | not built (impact itself built) |

## 5. Controls

| ID | Requirement | Control | Status |
|---|---|---|---|
| AG-S01 | A change set changes exactly one declared layer; a layer agent's change set only its own layer; the coordinator has no change commands. | **CTL-19** layer ownership (proposed) | not built |
| AG-S02 | Every change set and work item records the agent and the person; nothing lands without both. | **CTL-20** change provenance (proposed) | not built |
| AG-S03 | No agent creates a cross-layer link: a change set may not touch the registry. | CTL-19 | not built |
| AG-S04 | Projected or AI content never lands in real data. | CTL-16 | built |
| AG-S05 | The A2 agent adds BIAN elements only from the catalogue. | CTL-17 (projections); extended to change sets by CTL-19 | partly |
| AG-S06 | Approval only by a person merging a reviewed pull request (reviewer, time, evidence on every approved link). | governance check + review | built (process) |
| AG-S07 | The coordinator stops after a set number of impact rounds (default 3) and asks the architect. | coordinator instruction + work-item round number | not built |

## 6. Agents

| ID | Requirement | Status |
|---|---|---|
| AG-A01 | Four layer agents (A1, A2, A3, A4) and one coordinator, each defined in the project as a GitHub Copilot custom agent (custom chat mode): instructions, layer, allowed commands (design §7.1). | not built — confirm the feature for the organisation's VS Code (AG-Q01) |
| AG-A02 | Layer agent instructions: own layer only; draft through `sdem change propose`; never cross-layer links; never approve; source, reasoning, confidence on every statement; ask the architect when unsure. | not built |
| AG-A03 | Coordinator instructions: read change events and impact results; create one work item per affected layer and record; sequence (e.g. A4 before A3 for a rehost; A1 before A2 for a new capability); track and report; stop after AG-S07's limit. Never change layer data, never decide links, never approve. | not built |
| AG-A04 | Every agent works through the `sdem` CLI only, visibly in the terminal; no MCP; no AI API in SDEM. | built (CLI); agents not built |
| AG-A05 | Every journey also works without agents (the workbench). | built |
| AG-A06 | Later, optional: the same agents on an automated runtime, with the same commands and records, if the organisation allows; approval stays human. | not built |

## 7. Flow

| ID | Requirement | Status |
|---|---|---|
| AG-W01 | A change starts as a change set in one layer, on a branch. | not built |
| AG-W02 | Every applied change set produces a change event and a stored impact result. | not built |
| AG-W03 | The coordinator turns each impact result into work items for the affected layers. | not built |
| AG-W04 | Layer agents answer work items with change sets in their own layer; the rules engine then proposes the cross-layer links. | not built |
| AG-W05 | New impact starts a new round; the flow ends when no new impact remains or the architect stops it. | not built |
| AG-W06 | One pull request per change event carries all its change sets and proposed links for review. | not built |

## 8. Acceptance — use-case example 3

**Method:** as examples 1 and 2 — plan and expected results sealed (committed) before any run; evidence pack with checksums; results table with source, reasoning and confidence.

| ID | Test | Pass when |
|---|---|---|
| AT-AG-01 | A4 agent drafts the rehost of `INF-K8S-PAY-PROD` (payment-initiation) | change set checked; change event and impact stored; impact matches `sdem impact … --change rehost` (APP-PAY-HUB and CMP-PAY-EXEC need design change; PAY-108, PAY-111 to supersede; A2 and A1 unaffected) |
| AT-AG-02 | Coordinator plans the work | work items for A3 (and A4) only; none for A1 or A2 |
| AT-AG-03 | A3 agent answers its work item | change set touches A3 only; the engine proposes the replacement links |
| AT-AG-04 | An agent tries to change another layer | rejected by CTL-19 |
| AT-AG-05 | An agent tries to add a cross-layer link or approve | rejected (CTL-19; approval needs a person's reviewed merge) |
| AT-AG-06 | A change set without agent or person | rejected by CTL-20 |
| AT-AG-07 | A ripple that keeps producing impact | the coordinator stops at the round limit and asks |
| AT-AG-08 | The architect reviews and merges | the graph rebuilds; `sdem trace` shows the new links; every step is traceable in the coordination records |

## 9. Decisions and open questions

Decisions AG-D01…D08 and open questions AG-Q01…Q04: [`sdem-agent-platform-design.md`](sdem-agent-platform-design.md) §11–12.

## 10. Build order (recommended)

1. **Coordination records** (AG-R01…R05) and their schema.
2. **Commands** `sdem change`, `sdem events`, `sdem work`, `sdem impact --record` (AG-K01…K05).
3. **Controls** CTL-19, CTL-20 (AG-S01…S07), tested with good and bad data.
4. **Agent definitions** — four layer agents and the coordinator (AG-A01…A03), after confirming the Copilot feature (AG-Q01).
5. **Use-case example 3** (§8): seal the plan, run, score, evidence pack.
6. Then ingestion (v0.11) and the licensed BIAN catalogue (v0.15) for real designs.
