# Use-case example 3 — the agent platform carries a change across the architectures

> **Status: plan.** The pass criteria are the acceptance tests AT-AG-01…08 of [`sdem-agent-platform-spec.md`](sdem-agent-platform-spec.md) §8, committed on 2026-10-28 (commit `5cbb0ed`) **before** the coordination code was written. They are not changed here. Disclosure: the flow was tried once in a scratch folder while the code was built, so this run is not blind; a test written by someone else is still needed.

## Key words

- **Layer agent** — the agent for one architecture (A1, A2, A3 or A4); changes only its own layer.
- **Orchestrator** — organises the work: turns a change's impact into work items, calls the layer agents, reports. Never changes data, never approves.
- **Change set** — one layer's proposed record changes, checked before they land (`sdem change propose`).
- **Change event** — the record that a change set landed, with its stored impact.
- **Work item** — one task for one layer, from a change event's impact.

## Goal

Show that the agent platform's mechanics carry a technology change through the architectures **safely**: each layer changed only by its own agent, impact decided by SDEM not by agents, cross-layer links proposed by the rules engine, approval by a person — and every step on record.

## The scenario

The payments estate (`examples/payment-initiation`) moves its production workloads from the cluster `INF-K8S-PAY-PROD` to a new cluster `INF-K8S-PAY-PROD2`.

| Round | Who | Does |
|---|---|---|
| 1 | **A4 agent** | change set: add the new cluster; mark the old one as a **rehost**; move the two production deployments to the new cluster |
| — | **Orchestrator** | plans work items from the recorded impact |
| 2 | **A3 agent** | claims its work items; change set: the Payments Hub and the Execution Gateway now run on the new cluster |
| — | **Rules engine** | proposes the new cross-layer links |
| — | **Architect** | approves the new links, supersedes the old ones, merges |

## How it is run

The agents' **commands** are run exactly as the agent files in `.github/agents/` instruct (`scripts/use_case_example_3.py`). Copilot itself is not run here — whether Copilot executes those agent files as designed is checked by the **spike** in your VS Code ([`sdem-agent-platform-spike.md`](sdem-agent-platform-spike.md)). This example tests everything below Copilot: the records, the commands, the controls and the flow.

## Pass criteria (sealed — spec §8)

| ID | Test | Pass when |
|---|---|---|
| AT-AG-01 | A4 agent drafts the rehost of `INF-K8S-PAY-PROD` | change set checked; change event and impact stored; impact matches `sdem impact … --change rehost` (APP-PAY-HUB and CMP-PAY-EXEC need design change; PAY-108, PAY-111 to supersede; A2 and A1 unaffected) |
| AT-AG-02 | Orchestrator plans the work | work items for A3 (and A4) only; none for A1 or A2 |
| AT-AG-03 | A3 agent answers its work item | change set touches A3 only; the engine proposes the replacement links |
| AT-AG-04 | An agent tries to change another layer | rejected by CTL-19 |
| AT-AG-05 | An agent tries to add a cross-layer link or approve | rejected (CTL-19; approval needs a person's reviewed merge) |
| AT-AG-06 | A change set without agent or person | rejected by CTL-20 |
| AT-AG-07 | A ripple that keeps producing impact | the orchestrator stops at the round limit and asks |
| AT-AG-08 | The architect reviews and merges | the graph rebuilds; `sdem trace` shows the new links; every step is traceable in the coordination records |

Controls CTL-19 and CTL-20 are also tested with good data (must be accepted) and bad data (must be rejected), as in example 1.

## Output

A results table per criterion with what happened and the evidence; a controls table (good · bad); an evidence pack in `docs/evidence/use-case-example-3/` with checksums.
