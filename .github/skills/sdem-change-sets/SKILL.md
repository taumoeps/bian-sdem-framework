---
name: sdem-change-sets
description: How to write and propose an SDEM change set — the only way a layer agent (or a person) changes an architecture dataset. Use when drafting, fixing or proposing changes to A1, A2, A3 or A4 records, or when `sdem change propose` rejects a change set.
---

# SDEM change sets

A **change set** is a JSON file with the changes to **one** architecture layer. `sdem change propose` checks it against the metamodel and the controls **before** anything lands; if it is accepted it is applied to the layer's dataset and a **change event** with its impact is recorded in `<estate>/coordination/`.

## Format

```json
{
  "layer": "A4",
  "reason": "why — one sentence a reviewer understands",
  "changes": [
    { "op": "add",    "record": { "id": "…", "type": "A4.…", "version": "…", "name": "…", "lifecycle_status": "active", "attributes": { } } },
    { "op": "update", "kind": "rehost", "record": { …the full record, with its changes… } },
    { "op": "retire", "record": { "id": "…", "type": "…", "version": "…", "name": "…" } }
  ],
  "relationships": { "add": [ { "source": "…", "kind": "association", "target": "…" } ], "remove": [ ] }
}
```

- `op`: `add` (a new record), `update` (replace the record — give the **whole** record, same `id` and `type`), `retire` (sets `lifecycle_status` to `retired`).
- `kind` (optional, for impact): `modify` (default for update), `rehost`, `replace`, `retire`. Use `rehost` when only hosting changes, `replace` when the record is replaced.
- `relationships`: links **inside** the layer only (composition, aggregation, association, assignment …). Never a cross-layer link — those come from the rules engine (`sdem link`).
- Keep `version` as it is unless the real version changed: approved links name the version they point to.

Worked examples (the rehost in use-case example 3): [A4 rehost](example-a4-rehost.json) · [A3 re-point](example-a3-repoint.json).

## Propose

```bash
sdem change propose <estate>/coordination/drafts/<file>.json --estate <estate> --agent <your agent name> --person <the architect's name> [--work WI-001 WI-002] [--catalogue <bian.json>]
```

Then read the output: the change set id (`CS-…`), the change event (`CE-…`), the records in other layers that need a design change, and the links to supersede. The orchestrator plans the follow-on work.

## Undo

`sdem change revert <CS-id> --estate <estate> --agent <your agent> --person <name> --reason "…"` restores the layer exactly as it was before that change set, recorded as a new change set and change event; open work from the undone change is cancelled. Only the **latest** change set of a layer can be reverted, and only if nobody edited the file since.

## When it is rejected — what each message means

| Message | Fix |
|---|---|
| `CTL-19: agent … may change only A3, not A4` | you are not the owner of that layer — only that layer's agent may change it |
| `CTL-19: change N: … has type … — not a A4 record` | a record from another layer is in the change set — remove it; the orchestrator plans other layers' work |
| `CTL-19: relationship … leaves layer …` | a cross-layer link — remove it; `sdem link` proposes those |
| `CTL-19: an A2 change set that adds records needs --catalogue` | A2 elements come only from the BIAN catalogue — pass `--catalogue` |
| `CTL-20: … needs both the agent and the person` | add `--agent` and `--person` |
| `CTL-20: WI-… is not claimed by …` | `sdem work claim WI-… --estate … --agent … --person …` first |
| `CTL-16: … is a projected or design record` | `PRJ-` / `DSN-` records are plans, never real data |
| `the change set breaks the metamodel — nothing was changed:` + errors | fix each listed error (missing field, wrong type, a link the metamodel does not allow) — the `sdem-records` skill explains the fields |
| `change set format: …` | the JSON does not match the format above |
| `CTL-20 (AG-S08): … was changed outside a change set` (from `sdem check`) | someone edited the dataset file directly — agents never do; a **person** records their own edit with `sdem change adopt --estate … --layer … --person <their name> --reason …` |
