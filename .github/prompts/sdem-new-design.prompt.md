---
name: sdem-new-design
description: "Create a new SDEM design from a short description — A1 business design, requirements, SDEM's inference of A2–A4, and a review list"
agent: agent
argument-hint: "what to design, e.g. a new general ledger system"
---

Create a new SDEM design for: ${input:solution:a new general ledger system}, in workspace ${input:workspace:workspaces/ledger}. The architect is ${input:person:the person running this prompt}.

Follow the skill **sdem-new-design** step by step:
1. Ask SDEM, never guess: `sdem types A1 --json`, `sdem types requirement --json`, `sdem bian search <words> --json`.
2. Write the A1 business design as one change set (capabilities, value stream and stages, processes and activities with the BIAN operations they `invoke`, roles and actors, business objects, the business service, business requirements); dry-run, then propose it as `sdem-a1-business` for the architect.
3. Add the non-functional requirements to the registry with measurable conditions; dry-run, then propose.
4. Let SDEM infer A2–A4 with `sdem aid` (dry-run first), then `sdem link` and `sdem check`.
5. Hand back the review list from the skill — inferred records to confirm or reject (weak ones named), links to approve with their evidence, requirements to confirm, what is still missing — with the exact command for each. Run none of those decisions yourself.
