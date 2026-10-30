---
name: sdem-pr
description: "Draft a pull-request description for SDEM changes"
agent: agent
---

Draft a pull-request description for the SDEM changes on this branch.

- List the change sets and change events (`sdem events --workspace <workspace>`), the work items they answered, and the links added, approved or superseded in `mappings.json` with their evidence.
- Say which checks were run (`sdem check`, `sdem validate --strict`) and their result.
- State that approval is the reviewer's merge — not mine, not an agent's.
