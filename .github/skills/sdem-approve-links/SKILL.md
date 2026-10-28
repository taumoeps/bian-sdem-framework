---
name: sdem-approve-links
description: How a person approves the cross-layer links the SDEM rules engine proposes — reviewing proposals, the evidence each link type requires, superseding old links, and the pull request. Use when reviewing `sdem review` output, preparing an approval, drafting a pull-request description, or when `sdem validate` rejects an approved link. An agent never approves.
---

# Approving SDEM links — done by a person

The rules engine (`sdem link`) **proposes** links; **a person approves** them in the registry (`<estate>/mappings.json`), in a reviewed pull request. An agent may prepare the review and draft the pull-request text — never set a link to `approved` itself.

## Steps

1. **Review:** `sdem review <dir>/proposals.json --estate <estate>` (weakest first) and `sdem explain <P-id> --proposals <dir>/proposals.json` for one link.
2. **The architect approves each accepted link with `sdem approve`** (a person runs it — never an agent; CTL-21 rejects an agent as reviewer):
   ```bash
   sdem approve <P-id> --proposals <dir>/proposals.json --estate <estate> --reviewer <person> --evidence <kind:ref> [--bian-release <release>] [--supersedes <old id>]
   ```
   It writes the record and validates the whole registry first — nothing is written if a check fails. The record gets a new id, `status: "approved"`, the reviewer and date, and the **evidence** — the document that proves it, as `kind:document-reference`; the kinds each link type needs are in [the evidence table](evidence-by-link-type.md). The engine's reasoning alone is not enough. **Never write or edit records in `mappings.json` by hand** — CI refuses an edited approved link.
2a. **A link the engine did not propose** — e.g. the architect knows an application *realises* a BIAN service domain but the designs lack the API detail the rule needs: the architect states it with `sdem connect` (same checks as `sdem approve`, both ends must exist). You may draft the command with its evidence and a one-sentence rationale; the architect runs it:
   ```bash
   sdem connect <source id> <TYPE> <target id> --estate <estate> --reviewer <person> --evidence <kind:ref> --rationale "<why>" [--bian-release <release>]
   ```
3. **Superseding an old link** (e.g. after a rehost): approve the new one with `--supersedes <old id>` — SDEM marks the old one `superseded` and links the two. Never edit an approved link.
4. **Check:** `sdem validate --strict --estate <estate>` and `sdem check --estate <estate>`.
5. **Pull request** on a branch; a reviewer merges — **the merge is the approval**. Then `sdem build … --out <graph>` and `sdem trace …` show the link in use.

## Messages

| Message | Fix |
|---|---|
| `approved mapping requires reviewer_id` / `approved_at` | add who approved and when |
| `evidence missing required kind(s) [...]` | add evidence of that kind (table) |
| a proposal capped at low with **DEC-E-11** in its rationale | an end was read from a past design (`HIS-` record): check it against the page in `design-index.json`; the page can be the evidence reference (e.g. `deployment_design:PAYARCH-55501#notes`) |
| `… mapping requires bian_release` | a link to a BIAN element: add `--bian-release <release>` — the BIAN release the link relies on (the person states it) |
| `duplicate mapping_id` | choose an unused id |
| `superseded mapping has no successor referencing it via previous_mapping_id` | the new link needs `previous_mapping_id` |
| `a link to a projected or design record cannot be approved` (CTL-16) | projections are plans — never approve links to `PRJ-` records |
| `reviewer_id '…' is an agent or a tool` (CTL-21) | a person approves: their own name as reviewer |
