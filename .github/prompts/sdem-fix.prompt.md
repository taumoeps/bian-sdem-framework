---
name: sdem-fix
description: "Explain an sdem check error and propose the fix"
agent: agent
argument-hint: "paste the error, or leave empty for the last one in the terminal"
---

Take the `sdem check` or `sdem validate` error ${input:error:the error line, or empty for the last one in the terminal}.

1. Explain in plain words which rule it breaks and why (use the `sdem-records` or `sdem-approve-links` skill).
2. Show the exact fix in the file, as a small edit.
3. Give the command to re-check, e.g. `sdem check <estate>/a*.json <estate>/mappings.json`.

Never fix by adding projected (`PRJ-`) content or by setting a link to `approved`.
