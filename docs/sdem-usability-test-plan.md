# SDEM first-time architect usability test — plan and recording template

> **Status: ready to run (v0.18.0); no sessions run yet — no results exist.** For a facilitator running a pilot. It tests whether an architect who has never used SDEM can understand it, explore the synthetic Payments architecture, trace a dependency, tell proposals from approved connections, and explain where the architecture lives. Passing SDEM's automated tests shows the software works as designed; only sessions like these show whether people can use it.

## Who and how

- **Participants:** 3–5 enterprise or solution architects with **no prior knowledge of SDEM** (not people who built or reviewed it). One at a time, 45 minutes each.
- **Set-up (before the session, by the facilitator):** a machine with SDEM v0.18.0 installed, a terminal open in an empty folder, a browser. The Payments data is **synthetic** — made up; no real organisation's data is used, and none is collected.
- **The participant may use** the README, the documentation and SDEM's own output. **The facilitator** reads each scenario aloud, then watches; does not hint; notes every question and where the participant hesitated. If the participant is stuck for 3 minutes, the facilitator may give the **smallest** help and records it.
- **Assistance levels:** **0** none · **1** pointed to a document or page · **2** told which command or tab · **3** did it for them (the scenario counts as not completed).

## The five scenarios

| # | Scenario | The facilitator says | Success criterion | Time limit |
|---|---|---|---|---|
| S1 | **Explain SDEM** | "Read the start of the README for two minutes. Then tell me what SDEM is for, and what its main parts are." | Explains its purpose (one governed architecture model connecting business, BIAN, applications and technology — to see what exists, how it connects, what a change affects) and names the **four core components** — metamodel, workspace, CLI, knowledge graph and pages — each roughly right | 2 min reading + 2 min talking |
| S2 | **Explore the architecture** | "Open the Payments example and show me its four layers." | Without help, reaches SDEM Home (`sdem new … --example payment-initiation --explore`, then the page), opens the workspace dashboard and the architecture graph, and points at A1, A2, A3 and A4 | 10 min |
| S3 | **Trace dependencies** | "Which application and which technology support the business capability *Initiate Payment*?" | Names **Payments Hub** and the **Managed Kubernetes — payments (production)** platform (UAT also acceptable), found by trace in the graph, the dashboard or `sdem trace` | 8 min |
| S4 | **Review relationships** | "Is the connection between *Payments Hub* and its production platform approved? Is there anything proposed but not approved?" | States that Payments Hub's links are **approved** (with who/evidence, or that the graph shows only approved links), and — after the facilitator runs step 11 of *Explore your architecture* — that *Payment Notifications* → the platform is **proposed**, shown in Review, not yet architecture | 8 min |
| S5 | **Explain persistence** | "Where is this architecture stored? If you closed everything and came back tomorrow — or a colleague asked their AI assistant — where would it come from? How would someone change it properly?" | Says the architecture is in the **workspace** (files in the repository), the graph and pages are **generated** from it, an AI conversation is not where it lives, and changes go through the **CLI** (change sets, approvals by a person) | 5 min |

## What to record — per participant

Copy this block once per participant.

```
Participant: P__        Date: ____    Role: enterprise / solution architect    Years in architecture: __
SDEM version: 0.18.0    Facilitator: ____    Prior SDEM knowledge: none (confirm)

| Scenario | Completed (yes / partly / no) | Time (mm:ss) | Assistance (0–3) and what | Errors (what they did wrong) | Confusion (what they asked or hesitated on) | Recommended improvement |
|---|---|---|---|---|---|---|
| S1 Explain SDEM        | | | | | | |
| S2 Explore architecture| | | | | | |
| S3 Trace dependencies  | | | | | | |
| S4 Review relationships| | | | | | |
| S5 Explain persistence | | | | | | |

Quotes worth keeping (verbatim):
-
Overall, in one sentence: what would have helped most?
```

## Summarising the sessions

| Scenario | Completed without help (of N) | Median time | Most common confusion | Change recommended | Owner |
|---|---|---|---|---|---|
| S1 | | | | | |
| S2 | | | | | |
| S3 | | | | | |
| S4 | | | | | |
| S5 | | | | | |

**A scenario passes** when at least 4 of 5 participants (or all of 3) complete it with assistance 0 or 1 within its time limit. Record the results in `docs/evidence/` with the date and SDEM version; keep participants anonymous (P1, P2 …). Changes that follow go into a later release, and the scenario is run again.
