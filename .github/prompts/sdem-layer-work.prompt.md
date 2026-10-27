---
name: sdem-layer-work
description: "Layer agent: do one layer's open work items"
agent: agent
argument-hint: "layer, estate and your name, e.g. A3 work/est jane.architect"
---

Do the open work items of layer ${input:layer:A1, A2, A3 or A4} in estate ${input:estate:work/est} for ${input:person:your name}.

Switch to that layer's agent first if you are not it (sdem-a1-business, sdem-a2-bian, sdem-a3-application or sdem-a4-technology) — only that agent may change the layer.

`sdem work list --estate ${input:estate} --layer ${input:layer} --status open`; claim each item; write one change set for the layer (skill `sdem-change-sets`); propose it with `--work <ids>`; report the change set, the change event and the impact.
