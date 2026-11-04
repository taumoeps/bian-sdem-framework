# Create a new design

> **Status: current (v0.18.0)** — for architects: from "I need a design for a new general ledger" to a checked business design, its requirements and SDEM's inference of the other layers — ready for you to review and decide. The steps are the ones three agents followed in the [measurement](evidence/types-search-measurement.md) without a single refused submission. Synthetic examples only.

## The idea

You decide; something else does the typing. Your business design (A1) and your requirements go into the workspace through **checked change sets**; SDEM infers the BIAN, application and technology layers; nothing counts until **you** confirm and approve it.

| Step | Who | Command |
|---|---|---|
| 1. Start a workspace | you | `sdem new --workspace workspaces/ledger --person <you>` |
| 2. Write the business design (A1) | your agent, or you | a change set → `sdem change propose` |
| 3. Add the measurable requirements | your agent, or you | `sdem requirements propose` |
| 4. Infer A2, A3, A4 | SDEM (`sdem aid`), when you ask | `sdem aid --workspace … --person <you>` |
| 5. Review and decide | **you** | `sdem aid confirm|reject`, `sdem approve`, `sdem requirements confirm` |

## Route 1 — with your agent (recommended)

In VS Code, open your workspace repository (with `sdem agents install` done) and in Copilot Chat:

```
/sdem-new-design a new general ledger system
```

(With Claude Code, Codex or Gemini CLI: *"Create a new SDEM design for a new general ledger system in workspaces/ledger; then let SDEM infer the other layers."* — they follow the same skill, `sdem-new-design`.)

The agent asks SDEM what may be written (`sdem types`), finds the BIAN operations your processes use (`sdem bian search`), writes and checks the change set and the requirements, runs `sdem aid` if you asked for it, and hands back **a review list**: what it created; what SDEM inferred, with the weak inferences named; the links to approve with the evidence each needs; the requirements to confirm; what is still missing — each with the command **you** run. It never runs those decisions itself.

**Review before you decide:** the change set is in `workspaces/ledger/coordination/drafts/`, the inferred records are marked `inferred` with their confidence, the proposed links are in `workspaces/ledger/aid/` and `workspaces/ledger/links/`. `sdem dashboard --workspace workspaces/ledger` shows it all on one page.

## Route 2 — by hand

1. **What may be written:** `sdem types A1` (kinds, fields, allowed values, links), `sdem types change-set`, `sdem types requirement`.
2. **The BIAN operations** your processes use: `sdem bian search ledger posting` → `SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING`, …
3. **Write the change set** — start from the example in the skill (`.github/skills/sdem-new-design/example-a1-new-design.json`: a capability, a value stream, a process with its BIAN operation, a role, an object, a service, a requirement, and their links) and extend it.
4. **Check, then land it:**
   ```
   sdem change propose ledger-a1.json --workspace workspaces/ledger --agent architect --person <you> --dry-run
   sdem change propose ledger-a1.json --workspace workspaces/ledger --agent architect --person <you>
   ```
   A refusal names the field, value or link and what is allowed.
5. **Requirements:** a file `{"requirements": [...]}` in the format `sdem types requirement` shows → `sdem requirements propose <file> --workspace workspaces/ledger --person <you>`.
6. **Infer:** `sdem aid --workspace workspaces/ledger --person <you> --dry-run`, then without `--dry-run`; then `sdem link --workspace workspaces/ledger --out workspaces/ledger/links`.
7. **Decide** as below.

## How SDEM chooses the BIAN service domains

You do not pick the service domains for the A2 layer — SDEM works them out from your business design, and you confirm them.

1. **Each business process and activity names the BIAN operations it uses** — its `invokes` attribute. Find them with `sdem bian search <words>`:
   ```json
   {"id": "PRC-GL-POST", "type": "A1.BusinessProcess", "name": "Post journal entries",
    "attributes": {"invokes": ["SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING"]}}
   ```
2. **`sdem aid` follows each operation to the one service domain that owns it** in the BIAN catalogue — here *Financial Accounting* — and **copies** that domain into the A2 layer with what it needs: its operations, control record, asset type, functional pattern and service groups. Nothing is invented; every record comes from the catalogue.
3. **Each copied record is marked `inferred`**, with the rule, the reasoning and a confidence — e.g. *"PRC-GL-POST invokes SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING; all 1 processes of the capability use the domain"*, confidence 0.6.
4. **AID also proposes the connections** — the capability and process to the domain. They are proposals until a person approves them.
5. **You decide:** `sdem aid confirm` or `sdem aid reject` for the domains; `sdem approve` for the connections.

**Good to know**

- **The domains come only from your business design.** A process or activity without `invokes` leaves AID to match on names; such evidence is capped at low confidence (0.4) and can bring in unrelated domains. Give every process and activity its operations.
- **Several operations, several domains** — a process that uses operations of different domains gets all of them.
- **Want a particular domain?** Find one of its operations (`sdem bian search`) and add it to the process's `invokes`.
- **Don't want one?** `sdem aid reject <id>` — it is removed with its links and not inferred again.

## Deciding

| What | Command |
|---|---|
| inferred records you agree with — or not | `sdem aid confirm <ids> | --all …` · `sdem aid reject <ids> …` (reject the weak ones you doubt — confidence 0.4, matched on a shared word only) |
| a proposed link, with its evidence | `sdem approve <id> --proposals <file> --workspace … --reviewer <you> --evidence <kind:ref>` — `sdem types A1.BusinessProcess` lists the evidence each link type needs |
| a requirement, once its target is real and its evidence given | `sdem requirements confirm <ids> --workspace … --person <you>` |

Then the technology you know and SDEM cannot infer (platforms: `sdem types A4`), and — before any work is planned from the change — the impact validation (`sdem events validate`).
