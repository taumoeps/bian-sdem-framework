---
name: sdem-process-events
description: "Orchestrator: process the open change events of a workspace"
agent: sdem-orchestrator
argument-hint: "workspace folder and your name, e.g. work/est jane.architect"
---

Process the open change events in workspace ${input:workspace:work/est} for ${input:person:your name}.

Follow your instructions, in two phases.

**Phase A — impact assurance:** `sdem events --workspace ${input:workspace} --open`; for each event, `sdem events validate`; call **all four** layer agents as subagents to assess their layer (read-only, `sdem events assess`, skill sdem-impact-validation); then `sdem events show` and report to me — calculated against assessed, disagreements, gaps, uncertainty — and **stop for my decisions** — accepting the impact (`sdem events accept …`) and, separately, authorising implementation (`sdem events authorise …`), which I run. Run the shared analysis once and give each specialist its layer's extract, not the whole event.

**Phase B — only for events I have accepted and authorised:** `sdem work plan`; call the layer agent for each layer's work items as a subagent (workspace, work item ids, person); every new change event goes through Phase A again; stop at the round limit; then ask the rules engine for the new links (`sdem link`, `sdem review`) and report to me. Never change data, never accept, never approve.
