---
name: sdem-impact-note
description: "Draft an impact note from sdem impact output"
agent: agent
argument-hint: "record id and change kind, e.g. INF-K8S-PAY-PROD rehost"
---

Draft an impact note for changing ${input:record:record id} (${input:kind:modify, rehost, replace or retire}).

1. If there is no impact output in the terminal, give me the command: `sdem impact ${input:record} --change ${input:kind} --graph <graph>`.
2. From the output, write: the change; each affected record (layer, id, name, classification, path of link ids, why); the links to supersede; what is unaffected.
3. End with: "Classification is structural; an architect confirms before any design changes."

Use the `sdem-trace-impact` skill. Cite the link ids as sources.
