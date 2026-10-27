# SDEM Agent Platform — Specification

> **Status: approved by the owner 2026-10-28 (AG-D01…D09); Level 1 built and tested** — [use-case example 3](use-case-example-3.md): 8 of 8 criteria, controls 14 of 14. Still to confirm in the owner's VS Code: the spike ([`sdem-agent-platform-spike.md`](sdem-agent-platform-spike.md)). Requirements for the design in [`sdem-agent-platform-design.md`](sdem-agent-platform-design.md). Each requirement has an ID (AG-*), a status and how it is accepted. Builds on the workbench spec ([`sdem-workbench-spec.md`](sdem-workbench-spec.md)).

## 1. Purpose and boundary

One agent per architecture (A1–A4) generates and maintains designs in its own layer; an orchestrator agent organises the work; they coordinate through the federated graph (change events, impact results, work items); the rules engine proposes cross-layer links; architects approve.

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

Stored with the estate in `<estate>/coordination/` (Git), one file per record: `change-sets/`, `events/`, `work-items/`; change sets validated by `schema/coordination.schema.json`. Built in `sdem/agents.py`.

| ID | Requirement | Status |
|---|---|---|
| AG-R01 | **Change set**: id, the one layer it changes, the record changes (add / update / retire, with the full record), reason, `agent`, `person`, created at, branch. | built — `coordination/change-sets/`; also `work_items` answered and the branch |
| AG-R02 | **Change event**: id, the change set or merge that caused it, when, by whom. | built — `events.json` |
| AG-R03 | **Impact result**: the change event, each affected record with level, classification (`design_change_required` / `no_impact` / …), traversal path (link ids), and links to supersede — the output of `sdem impact`, stored. | built — stored in each event (`impact`), from `sdem impact` per changed record, strongest classification kept |
| AG-R04 | **Work item**: id, layer, record(s), action, reason (change event + impact path), status `open` → `in_progress` → `done` / `blocked` / `cancelled`, holder (agent + person), round number. | built — `work-items.json` |
| AG-R05 | Records are append-only: a status change adds a new state with time and actor; nothing is deleted. | built — every status change appends a state with time, agent and person |
| AG-R06 | Ids cannot clash between branches, and parallel work never edits the same file: one file per record; ids scoped to the Git branch they were made on (`CS-<branch>-001`; plain `CS-001` on main or outside Git). | built 2026-10-28 (D1) |
| AG-R07 | `sdem check` also checks an estate's coordination records: schema, file name = id, references resolve, work-item histories follow the allowed steps, agent and person on every step. | built 2026-10-28 (D2) |

## 4. Commands (the agents' only interface)

All under the `sdem` CLI, with `--json`, the standard exit codes and `--help` with an example (workbench WB-K04/K05).

| ID | Command | Does | Status |
|---|---|---|---|
| AG-K01 | `sdem change propose <change-set> --estate DIR --agent <name> --person <name>` | checks the change set against the rulebook and controls **before** it lands; on success applies it to the layer's dataset on the current branch, records the change event and stores the impact result | built — `sdem change propose <file> --estate DIR --agent … --person … [--work WI…] [--catalogue …]` |
| AG-K02 | `sdem change show <id>` | the change set, its checks and its impact | built — `sdem change show <CS-id> --estate DIR` |
| AG-K03 | `sdem events [--open]` | change events with their impact summary | built — `sdem events --estate DIR [--open]` |
| AG-K04 | `sdem work plan / list / claim / block / cancel / reopen` | work items — create (orchestrator), list (by layer, status), claim, update, close | built — `sdem work plan / list / claim / block / cancel / reopen`; *done* is set by `sdem change propose --work` |
| AG-K05 | impact stored with each change event | computes impact for every changed record and stores it as the event's impact result | built — inside `sdem change propose` (impact stored with the event) |
| AG-K06 | `sdem change revert <CS-id> --estate DIR --agent … --person …` | reverses a change set (restores the records it changed) and records the reversal as a change event, with its impact | proposed — not built ([principles](sdem-agent-platform-principles.md) #3) |
| AG-K07 | `sdem change adopt --estate DIR --layer A? --person … --reason …` | records a person's direct edit of a layer as a change set (the diff against the last snapshot, with its impact), so the chain is whole again; refuses agent names and edits that break the rulebook | built 2026-10-28 (AG-S08) |

## 5. Controls

| ID | Requirement | Control | Status |
|---|---|---|---|
| AG-S01 | A change set changes exactly one declared layer; a layer agent's change set only its own layer; the orchestrator has no change commands. | **CTL-19** layer ownership (proposed) | built |
| AG-S02 | Every change set and work item records the agent and the person; nothing lands without both. | **CTL-20** change provenance (proposed) | built |
| AG-S03 | No agent creates a cross-layer link: a change set may not touch the registry. | CTL-19 | built — relationships may not leave the layer; the change-set format has no registry field |
| AG-S04 | Projected or AI content never lands in real data. | CTL-16 | built |
| AG-S05 | The A2 agent adds BIAN elements only from the catalogue. | CTL-17 (projections); extended to change sets by CTL-19 | built — A2 additions need `--catalogue` and must be in it |
| AG-S06 | Approval only by a person merging a reviewed pull request (reviewer, time, evidence on every approved link). | governance check + review | built — `sdem approve` (a person) and **CTL-21** in the governance check: a reviewer that is an agent or a tool is rejected |
| AG-S07 | The orchestrator stops after a set number of impact rounds (default 3) and asks the architect. | orchestrator instruction + work-item round number | built — `sdem work plan` answers `STOP: round limit …` (default 3) |
| AG-S08 | Detect dataset changes that did not come through a change set (a direct edit by an agent or a person): compare the datasets with the result of the recorded change sets since the last baseline. | proposed — CTL-20 extension | built 2026-10-28 — each change set records its dataset's checksum before and after and a snapshot; `sdem check` verifies the chain; a person records a direct edit with `sdem change adopt` |

## 6. Agents

| ID | Requirement | Status |
|---|---|---|
| AG-A01 | Four layer agents (A1, A2, A3, A4) and one orchestrator, each defined in the project as a GitHub Copilot custom agent (custom chat mode): instructions, layer, allowed commands (design §7.1). | built — `.github/agents/*.agent.md`; to confirm in the organisation's VS Code (spike S1, S2) |
| AG-A02 | Layer agent instructions: own layer only; draft through `sdem change propose`; never cross-layer links; never approve; source, reasoning, confidence on every statement; ask the architect when unsure. | built |
| AG-A03 | Orchestrator instructions: read change events and impact results; create one work item per affected layer and record; sequence (e.g. A4 before A3 for a rehost; A1 before A2 for a new capability); track and report; stop after AG-S07's limit. Never change layer data, never decide links, never approve. | built |
| AG-A04 | Every agent works through the `sdem` CLI only, visibly in the terminal; no MCP; no AI API in SDEM. | built |
| AG-A05 | Every journey also works without agents (the workbench). | built |
| AG-A06 | Later, optional: the same agents on an automated runtime, with the same commands and records, if the organisation allows; approval stays human. | not built |

## 7. Flow

| ID | Requirement | Status |
|---|---|---|
| AG-W01 | A change starts as a change set in one layer, on a branch. | partly — `sdem change propose` records the branch and warns on `main` |
| AG-W02 | Every applied change set produces a change event and a stored impact result. | built |
| AG-W03 | The orchestrator turns each impact result into work items for the affected layers. | built — `sdem work plan` |
| AG-W04 | Layer agents answer work items with change sets in their own layer; the rules engine then proposes the cross-layer links. | built — tested in example 3 |
| AG-W05 | New impact starts a new round; the flow ends when no new impact remains or the architect stops it. | built |
| AG-W06 | One pull request per change event carries all its change sets and proposed links for review. | process — the architect opens one pull request per change event |

## 7a. Triggers (AG-D09)

| ID | Requirement | Status |
|---|---|---|
| AG-T01 | **Level 1, on request:** the architect starts the orchestrator or a layer agent in Copilot Chat; the orchestrator calls the layer agents as subagents (`agent` tool, `agents` allowlist); layer agents cannot call any agent (`agents: []`). | built (agent files) — to confirm with the spike (S6, S7) |
| AG-T02 | **Level 2, queue prompts:** no listener; the durable work queue is the trigger — `sdem change propose` prints the next command for the orchestrator; `sdem events --open` shows anything waiting; optional Git hook or VS Code task to print open work. | partly — prompts built; hook / task not built |
| AG-T03 | **Level 3, automated — only with the organisation's approval:** a GitHub Actions workflow runs Copilot CLI programmatically (`copilot -p … --agent sdem-orchestrator --no-ask-user --allow-tool 'shell(sdem:*)'`) on an event, or an issue is assigned to Copilot's cloud agent with the orchestrator; the result is a pull request a person merges. Same agent files and commands. | not built — needs approval |

## 7b. Proof and audit of the agents themselves

| ID | Requirement | Status |
|---|---|---|
| AG-E01 | **Score the agents:** after the spike, run use-case example 3 with the real Copilot agents (not scripted) several times; score how often each run drafts change sets that pass and match the expected impact, plans the right work items, and stops correctly; report the rate per agent. | proposed — not built ([principles](sdem-agent-platform-principles.md) #2) |
| AG-O01 | **Session record:** with each change event, keep a short summary of the agent session that produced it — who asked what, which `sdem` commands ran — for audit. | proposed — not built ([principles](sdem-agent-platform-principles.md) #4) |

## 8. Acceptance — use-case example 3

**Method:** as examples 1 and 2 — plan and expected results sealed (committed) before any run; evidence pack with checksums; results table with source, reasoning and confidence.

| ID | Test | Pass when |
|---|---|---|
| AT-AG-01 | A4 agent drafts the rehost of `INF-K8S-PAY-PROD` (payment-initiation) | change set checked; change event and impact stored; impact matches `sdem impact … --change rehost` (APP-PAY-HUB and CMP-PAY-EXEC need design change; PAY-108, PAY-111 to supersede; A2 and A1 unaffected) |
| AT-AG-02 | Orchestrator plans the work | work items for A3 (and A4) only; none for A1 or A2 |
| AT-AG-03 | A3 agent answers its work item | change set touches A3 only; the engine proposes the replacement links |
| AT-AG-04 | An agent tries to change another layer | rejected by CTL-19 |
| AT-AG-05 | An agent tries to add a cross-layer link or approve | rejected (CTL-19; approval needs a person's reviewed merge) |
| AT-AG-06 | A change set without agent or person | rejected by CTL-20 |
| AT-AG-07 | A ripple that keeps producing impact | the orchestrator stops at the round limit and asks |
| AT-AG-08 | The architect reviews and merges | the graph rebuilds; `sdem trace` shows the new links; every step is traceable in the coordination records |

**Result (2026-10-28):** 8 of 8 met, controls 14 of 14 — [`use-case-example-3.md`](use-case-example-3.md). The Copilot side is the spike.

## 9. Decisions and open questions

Decisions AG-D01…D09 and open questions AG-Q01…Q04: [`sdem-agent-platform-design.md`](sdem-agent-platform-design.md) §11–12.

## 10. Build order

1. **Spike in the owner's VS Code** — [`sdem-agent-platform-spike.md`](sdem-agent-platform-spike.md): the agent files load, the terminal tool's name, a layer agent proposes a change set, the orchestrator calls a subagent, layer agents cannot call each other.
2. ~~Coordination records (AG-R01…R05) and their schema~~ — **built 2026-10-28**.
3. ~~Commands `sdem change`, `sdem events`, `sdem work` (AG-K01…K05)~~ — **built**.
4. ~~Controls CTL-19, CTL-20 (AG-S01…S07), tested with good and bad data~~ — **built**.
5. ~~Agent definitions (AG-A01…A03)~~ — **built**, `.github/agents/`; adjust after the spike.
6. ~~Use-case example 3~~ — **run: 8 of 8**.
7. Next ([principles](sdem-agent-platform-principles.md)): ~~AG-S08~~ (built), AG-E01 (score the agents after the spike), AG-K06 (undo), AG-O01 (session record); AG-T02's Git hook or VS Code task; then ingestion (v0.11) and the licensed BIAN catalogue (v0.15) for real designs; AG-T03 only with the organisation's approval.
