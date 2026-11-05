---
name: sdem-new-design
description: How to create a new SDEM design from an architect's request ("design a new general ledger system") — the A1 business design through a checked change set, measurable requirements, SDEM's inference of A2–A4, and a review list for the person. Use when asked to create, start, draft or design a new solution, system or capability in an SDEM workspace.
---

# Create a new SDEM design

You write the business design (A1) and the requirements from the architect's request; SDEM checks everything and infers the other layers; **the architect decides** — you never confirm, approve or accept. Measured: three agents following this skill made no mistake SDEM refused, inferred only the BIAN domains they chose, and took 18–24 tool calls (docs/evidence/types-search-measurement.md, follow-up).

## 0. Ask SDEM, never guess

| You need | Ask |
|---|---|
| the kinds of A1 record, their fields, allowed values and links | `sdem types A1 --workspace <ws> --json`; one kind in full: `sdem types A1.BusinessProcess --json` |
| the change-set format | `sdem types change-set` |
| the requirement format, categories, operators | `sdem types requirement --workspace <ws> --json` |
| the BIAN operations a process uses | `sdem bian search <words> --json` (add `--all-operations` for every operation of a domain found) |

Use only fields and values `sdem types` lists, and only `SO-…` ids `sdem bian search` returns. Read `sdem types A1` (text — the compact overview), then **`sdem types <type>` for every type you write**: it gives each field's kind (text or a list), the allowed values and what an id field must point to (e.g. a service's `consumers` are role or actor ids, not names). Content is the architect's or made up and marked as such — never a real organisation's.

## 1. Start (if the workspace does not exist)

`sdem new --workspace workspaces/<name> --person <architect>` — a person's decision; if it is missing, prepare the command and ask.

## 2. The A1 design — one change set

Write `workspaces/<name>/coordination/drafts/<name>-a1.json` (format: `sdem types change-set`; a small example: [`example-a1-new-design.json`](example-a1-new-design.json)). Every record `lifecycle_status: "planned"`. Cover, with links from `sdem types` (`links_out`):

| Record | Typical content | Links |
|---|---|---|
| `A1.BusinessCapability` | one top capability, 3–6 under it (`level` 1, 2) | top **composition** sub |
| `A1.ValueStream` + `A1.ValueStreamStage` | the end-to-end stream (e.g. *Record to Report*), 4–6 stages | stream **composition** stage; stage **flow** next stage; capability **serving** stage |
| `A1.BusinessProcess` + `A1.BusinessActivity` | 3–5 processes, 2–3 activities each; **every process and every activity has `invokes`**: the `SO-…` ids from `sdem bian search` | process **composition** activity; process **realization** capability, stage, service, requirement |
| `A1.BusinessActor` + `A1.BusinessRole` | who does the work | actor **assignment** role; role **assignment** process |
| `A1.BusinessObject` | the information handled | process **access** object |
| `A1.BusinessService` | what the solution offers others | process **realization** service |
| `A1.BusinessRequirement` | functional and non-functional statements (`requirement_kind`, `priority`; say *functional* / *non-functional* in the description or the id, unless the organisation profile has a field for it) | process / service / capability **realization** requirement |

**Why every activity needs `invokes`:** an activity without it is matched to BIAN by its *name* — one shared word ("account") can bring in unrelated domains (Savings Account, Current Account …) and hundreds of records. In three measured runs this happened every time an activity was left without `invokes`.

Then:
```
sdem change propose <draft> --workspace <ws> --agent sdem-a1-business --person <architect> --dry-run --json
sdem change propose <draft> --workspace <ws> --agent sdem-a1-business --person <architect> --json
```
`sdem check` will warn that `invokes` names operations not yet in the workspace (LC-08) until step 4 brings them in.

## 3. Measurable requirements

For each non-functional requirement (ids `REQ-…`), one entry in `workspaces/<name>/coordination/drafts/<name>-requirements.json` (`{"requirements": [...]}`, format: `sdem types requirement`): `category`, `scope` (`end_to_end` for the business view), `subject` (a process or service id), `condition` (`metric`, `operator`, `value`, `unit`, `period`), `derived_from` (its `A1.BusinessRequirement` id). Leave `evidence` empty unless the architect gave a document — never invent one. Targets you choose are placeholders: say so.
```
sdem requirements propose <draft> --workspace <ws> --person <architect> --dry-run --json   # then without --dry-run
```

## 4. Let SDEM infer A2–A4 — only if asked

If the request says to infer the other layers (that is the architect's agreement), first `sdem aid --workspace <ws> --person <architect> --dry-run --json`. **Check its `added.A2`: the `SD-…` service domains must be the ones you chose with `sdem bian search`.** If any other domain appears, find where it came from: if a process or activity is missing `invokes`, fix it with an A1 change set (`op: update`) and dry-run again. Domains that only a shared word in an A3 or A4 name points to are not added when your processes name their domains (AID-M03): `sdem aid` lists them as `NOTE: not added — …` (in `--json`: `projection_ends`). Pass those notes on in your review list; do not rename records to avoid them. Only then run `sdem aid` without `--dry-run`. If the request does not ask for inference, stop here and offer it. Then `sdem link --workspace <ws> --out <ws>/links --json` — the one list of proposed connections the architect approves from (AID-W09) — and `sdem check --workspace <ws> --json`.

## 5. Hand back — always this review list

Report in this order, with the exact command for each decision (the architect runs them):

1. **What was created**: A1 records per type, links, requirements; the change set and change event ids.
2. **What SDEM inferred** per layer, with confidence; **name the weak ones** (confidence 0.4, matched on a shared word only) and recommend rejecting the doubtful — `sdem aid confirm <ids>|--all …` / `sdem aid reject <ids> …`.
3. **Links to approve**, grouped by type with the evidence each needs — `sdem approve <id> --proposals <file> --workspace <ws> --reviewer <architect> --evidence <kind:ref> [--bian-release <release>]`.
4. **Requirements to confirm** — after the architect sets real targets and adds evidence: `sdem requirements confirm <ids> …`.
5. **The change event(s)** — impact validation and the architect's acceptance only if work is to be planned from them.
6. **What is still missing**: A4 platforms (`sdem types A4`), business domains above the service domains, anything you assumed.

Never run `sdem aid confirm|reject`, `sdem approve`, `sdem connect`, `sdem requirements confirm`, `sdem events accept|authorise` or `sdem change adopt` — they are the architect's decisions (CTL-21).
