---
name: sdem-review
description: "Walk through proposed links, weakest first, with the evidence each needs"
agent: agent
argument-hint: "the proposals file, e.g. work/links/proposals.json"
---

Help me review the proposed links in ${input:proposals:work/links/proposals.json}.

1. Run `sdem review ${input:proposals} --json` (and `sdem explain <id> --proposals ${input:proposals}` where I need detail).
2. Go weakest first. For each link: what it says, the rule and its published source, the reasoning, the confidence, and the **evidence kind** an approval needs (skill `sdem-approve-links`).
3. Flag links resting on names only (low confidence) as hints.

I decide. Do not edit the registry and never set a link to approved.
