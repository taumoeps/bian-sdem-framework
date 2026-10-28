---
name: sdem-onboarding-review
description: "Review a design onboarding with me: explain each candidate's evidence, suggest what to reject, and give me the load command"
agent: agent
argument-hint: "the transform output folder, e.g. work/history"
---

Help me review the onboarding of past designs in ${input:candidates:work/history} (the output of `sdem transform run`). Use skill `sdem-onboard-designs`.

1. Read `${input:candidates}/extraction-report.md` and `${input:candidates}/extraction.json`.
2. Report, in this format:
   - **Summary** — pages, entities per layer (A1, A3, A4), links, check result.
   - **One table per layer** — id, type, name, confidence, the strongest source (page, place, rule), and your note.
   - **Suggest rejecting** — each id with the reason (fails the check, likely OCR misread, typed only by the section default, duplicate name, single weak source).
   - **For me to do by hand** — pictures, diagrams not linked to a page, BIAN names found (hints only — never A2 records).
3. Run `sdem load ${input:candidates} --estate ${input:estate:estates/history} --person ${input:person} --exclude <your suggestions> --dry-run` and show the result.
4. Give me the same command **without** `--dry-run`, for me to run.

I decide what to keep. Never run `sdem load` without `--dry-run`, never edit the datasets, never approve.
