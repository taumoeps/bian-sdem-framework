# Designing with AID

> **Status: current (v0.9.14)** — for architects: designing a new solution with SDEM's *Architecture Inference Design* (AID). You write what you know; `sdem aid` fills in what is missing, marked so you can see — and decide on — every record it added.

## What you give it, what it gives you

**You give it whatever you have**, in your workspace: any of the four layers — often just the business design (A1): a few capabilities, a process and its activities, named *verb + thing* (*Initiate payment order*, *Execute payment*). BIAN's service domains are the catalogue AID chooses from — the workspace will hold only the ones your design needs.

**It gives you the rest**, written into the same layer files:

| From | AID infers | How |
|---|---|---|
| your activities and capabilities (A1) — or your applications and their APIs (A3) | the **BIAN service domains** they need, copied from the catalogue into your A2 layer with their operations and control records | an activity's verb and thing match a BIAN operation and cover the domain's subject (*Initiate payment order* → Payment Order Initiation); or a capability's description shares the domain's words |
| each service domain | an **application** and one **API per BIAN operation** (A3) | BIAN's container pattern: one component per domain; method and path from BIAN's REST mapping |
| each application | a **deployment** (A4) | one per application — no servers, platforms or locations are guessed |
| your technology or applications (A4, A3), if that is what you have | the applications (named from their deployments), the BIAN domains above them, and *suggested* capabilities | upwards, by the same rules: an application's APIs, data or a name that says what it does (*Term Deposit Engine* → Term Deposit). A name that doesn't say (*Payments Hub*) gets no guessed domain — AID stops and tells you what to add |

**Every record it adds is marked `inferred`**, with its **source, reasoning and confidence** and the rule used — so you can always tell what a person wrote from what SDEM inferred. The connections between layers are only **proposed**: you approve them, with evidence, as always.

## Step by step — a real example

**1. Start the workspace** — all four layers empty; BIAN's 258 service domains are read from the catalogue, not copied:
```bash
sdem new --workspace workspaces/payments --person jane.architect
```

**2. Write what you know** in `workspaces/payments/a1-business.json` — here a capability *Payment Initiation*, a process *Make a payment* and two activities, *Initiate payment order* and *Execute payment*. `sdem check --workspace workspaces/payments` confirms the file is well formed.

**3. Fill the gaps:**
```bash
sdem aid --workspace workspaces/payments --person jane.architect
```
```
added (AID-001) to workspaces/payments: A2 67 inferred record(s), A3 40 inferred record(s), A4 2 inferred record(s); 45 connection(s) proposed in workspaces/payments/aid/AID-001-proposals.json — checked
```
From four business records, AID found the two BIAN service domains a payment needs — **Payment Order Initiation** and **Payment Rail** — and brought only those into the workspace's BIAN layer (67 records, with their operations and control records — not all 258 domains), then added their applications, APIs and deployments. Confirming a domain confirms its operations with it; rejecting one removes what was built on it. An inferred record looks like this:
```json
{ "id": "AID-APP-SD-PAYMENT-ORDER-INITIATION", "name": "Payment Order Initiation service (inferred)", "lifecycle_status": "planned",
  "attributes": { "inferred": { "by": "sdem aid", "run": "AID-001", "rule": "BIAN container pattern",
    "source": "S17: [SAPG] §3.4 p. 52 (functional partition)", "reasoning": "one component per service domain",
    "confidence": "0.4", "from": "SD-PAYMENT-ORDER-INITIATION" } } }
```

**4. Review and decide.** Read the inferred records in the layer files (or on the dashboard — it lists them under *needs attention*), then:
```bash
sdem aid confirm AID-APP-SD-PAYMENT-ORDER-INITIATION --workspace workspaces/payments --person jane.architect   # you agree
sdem aid reject  AID-DEP-SD-PAYMENT-RAIL --workspace workspaces/payments --person jane.architect --reason "runs on the shared platform"
```
A confirmed record keeps its mark, with your name. A rejected one is removed — and remembered, so AID never adds it again. You can also edit any inferred record's values first, then confirm it; you can never simply delete the mark (`sdem check` refuses that).

**5. Approve the connections** AID proposed — weakest first:
```bash
sdem review workspaces/payments/aid/AID-001-proposals.json
sdem approve AID-001-P001 --proposals workspaces/payments/aid/AID-001-proposals.json --workspace workspaces/payments \
     --reviewer jane.architect --evidence process_model:PM-PAY-2026
```
Until a connection is approved, `trace` and `impact` do not follow it.

**6. Carry on as usual** — `sdem check`, `sdem link` for further connections, `sdem build`, `trace`, `impact`, dashboards. As you learn more, write it in; run `sdem aid` again whenever you like — it adds only what is still missing, never touches what you wrote, and never brings back what you rejected.

## Good to know

- **Confidence is honest and low.** Inferred records are a starting point (most are 0.4): BIAN's container pattern gives one application per domain, which your organisation may not follow. That is why every record waits for you.
- **It works better when activities are named verb + thing** (*Initiate payment order*, not *Payments*), or name the BIAN operation they use (`invokes`).
- **AID chooses from all of BIAN** and brings in only the best-matching domains; add one it missed with `sdem bian custom --add`.
- **It never guesses from fragments** of ids or names: a domain needs a name that covers what the domain is about, or matching APIs or data. No AI is used — written rules, the same result every time.
- **It infers only from what you wrote or confirmed** — never from its own unconfirmed records — so running it again does not pile guesses on guesses.
- **For existing designs too:** after `sdem load`, run `sdem aid` — the domains your designs point to come in, from the business side or the application side.
- **File-based planning still works** — `sdem aid project --have <files> --catalogue <A2 file> --out <folder>` (or `--workspace`, into `<workspace>/plans/`) writes a separate plan that never touches your files; `sdem aid gaps` compares a plan with the real design.
- **Rules and controls:** [AID specification](design/aid-spec.md) — *Filling a workspace* (AID-W01…W07) and control CTL-16.
