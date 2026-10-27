---
name: sdem-process-events
description: "Orchestrator: process the open change events of an estate"
agent: sdem-orchestrator
argument-hint: "estate folder and your name, e.g. work/est jane.architect"
---

Process the open change events in estate ${input:estate:work/est} for ${input:person:your name}.

Follow your instructions: `sdem events --estate ${input:estate} --open`; plan each event with `sdem work plan`; call the layer agent for each layer's work items as a subagent (give it the estate, the work item ids and the person); after each change set check for new impact; stop at the round limit; then ask the rules engine for the new links (`sdem link`, `sdem review`) and report to me. Never change data, never approve.
