# Updating the BIAN layer in a workspace, and connections a person states — design and specification

> **Status: approved by the owner and built 2026-10-29** ("go ahead"). Found by the fourth new-architect walkthrough. Tests: `tests/test_bian_update_connect.py`.

## The two problems

1. **The shared BIAN layer reached a workspace once and never again.** `sdem load --a2 bian/a2-service-domain.json` adds the BIAN layer only to a workspace that has none. Adding service domains, or moving to a new BIAN release, left existing workspaces on their old copy — silently.
2. **Onboarded designs never connected business to applications.** The only rule that proposes *service domain is realised by application* (S17) needs the application's API operations matched to BIAN's operations first; Confluence designs rarely carry that detail. So onboarded data stopped at BIAN, and the main trace — capability → BIAN → application → technology — never appeared. An architect who *knows* "the Payments Hub realises Payment Order Initiation" had no way to say so except editing `mappings.json` by hand, which the rules forbid.

## The design

```mermaid
flowchart LR
    B["bian/a2-service-domain.json<br/>(shared, updated)"] -- "sdem bian update --root workspaces" --> E1["workspaces/payments"]
    B -- "" --> E2["workspaces/lending"]
    P(["👤 Architect<br/>knows a connection,<br/>has the document"]) -- "sdem connect … --evidence" --> R["mappings.json<br/>approved, checked"]
```

**`sdem bian update`** replaces a workspace's BIAN layer with the shared one, after checking: the whole workspace must pass with the new layer, and **no approved connection may point to a BIAN record that would disappear** — if one does, it is refused and named, and the architect supersedes that connection first. What was added, dropped or renamed is recorded in the workspace (`bian-updates/BU-nnn.json`). One workspace (`--workspace`) or every workspace under a folder (`--root workspaces`), all-or-nothing.

**`sdem connect`** lets a person state a connection the engine did not propose, with the same governance as `sdem approve` — it builds the record and passes it through the same approval: a person as reviewer (CTL-21), the evidence the connection type requires, one of the nine types between the right kinds of record (CTL-05), the BIAN release where needed — and additionally checks that both ends exist in the workspace and the whole workspace passes. The record says it was **stated by a person** (`created_by: sdem connect`), not proposed by the engine.

Neither changes the metamodel.

## Requirements

| ID | Requirement | Accepted by |
|---|---|---|
| BU-01 | `sdem bian update --workspace DIR \| --root DIR --a2 FILE --person NAME [--dry-run]` replaces each workspace's `a2-service-domain.json` with FILE (an A2 dataset). | test |
| BU-02 | Refused, nothing written, if an approved connection in a workspace points to an A2 record not in FILE — the refusal names the connection and the record. | test |
| BU-03 | Refused, nothing written, if a workspace would not pass its checks with FILE. With `--root`, every workspace is checked before any is written (all-or-nothing). | test |
| BU-04 | Each workspace updated gets `bian-updates/BU-nnn.json`: who, when, FILE, and the A2 ids added, dropped and renamed. A workspace already identical to FILE is reported unchanged and not rewritten. | test |
| BU-05 | `--person` must be a person. `--dry-run` reports and writes nothing. | test |
| SC-01 | `sdem connect SOURCE RELATIONSHIP TARGET --workspace DIR --reviewer NAME --evidence KIND:REF … --rationale TEXT [--bian-release R] [--id ID] [--date D] [--dry-run]` writes one approved connection. | test |
| SC-02 | It passes the same checks as `sdem approve` (a person; the required evidence kinds; a catalogued connection type; the BIAN release where the type needs it) and is refused, nothing written, if any fails. | tests: a missing evidence kind; an agent as reviewer; a type that is not one of the nine |
| SC-03 | Both ends must exist in the workspace, of the types the connection needs; the whole workspace must pass with the new connection. | test |
| SC-04 | An already-approved identical connection is refused. The record carries `created_by: sdem connect`, the reviewer's rationale, and is otherwise an ordinary approved record (it can be superseded, traced and built). | test: connect, build, trace |
