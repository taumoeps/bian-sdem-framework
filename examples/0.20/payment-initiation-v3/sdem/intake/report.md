# Intake report — sdem

`sdem intake` by jane.architect. 32 link(s) between layers the design states were approved as authored (`--accept`). What SDEM's rules then inferred is neither confirmed nor approved: it is marked, below.

## What came in

| Layer | Records | Links inside |
|---|---|---|
| A1 | 48 | 72 |
| A3 | 49 | 55 |
| A4 | 28 | 42 |

- SDEM refused nothing (a package with anything refused is not loaded).
- BIAN service domains named: Party Authentication, Payment Order Initiation, Fraud Evaluation; operations: SO-PARTY-AUTHENTICATION-EVALUATE, SO-PAYMENT-ORDER-INITIATION-INITIATE, SO-PAYMENT-ORDER-INITIATION-RETRIEVE.
- Named by the design but not BIAN's (not loaded as service domains): none.
- Links between layers: 32 accepted as authored (`--accept`), each on the design section it cites, under jane.architect's name.

## What the author said the design does not state

- nothing declared

## The draft

Patterns asked before anything was inferred: none fits this design.

```
Completeness: 125 of 125 records connected (100%) — no gaps
Pattern BIAN Transact — a transaction (SD-PAYMENT-ORDER-INITIATION): 9 of 9 parts in place — nothing missing
Pattern Payment initiation (SD-PAYMENT-ORDER-INITIATION): 14 of 14 parts in place — nothing missing
```

*Completeness* counts only what the design states. *Draft* counts as well what SDEM completed by its own written rules (`sdem aid`) — never by an AI. Everything SDEM added is marked inferred or proposed, with the rule that produced it.

**Nothing below needs you for the design to be used.** It is what SDEM inferred, weakest first, for whenever you choose to confirm or reject it.

## Yours to decide — weakest first

### 1. Placed by default — nothing in the design supports these

- none

### 2. Inferred from a name, or by elimination

- none

### 3. Brought in by a pattern

- BIAN service domains: none
- parts added as planned records: none

### 4. Links between layers to approve

`sdem review examples/payment-initiation-v3/sdem/links/proposals.json` lists them with the evidence each needs.

### 5. Gaps left open

- none

### The commands — you run them

```
sdem aid confirm '<source|kind|target>' --workspace examples/payment-initiation-v3/sdem --person <you>      # or: sdem aid reject '<…>' --workspace examples/payment-initiation-v3/sdem --person <you> --reason <why>
sdem aid confirm <record id> --workspace examples/payment-initiation-v3/sdem --person <you>                 # a BIAN domain or a part SDEM brought in
sdem approve <id> --proposals <file> --workspace examples/payment-initiation-v3/sdem --reviewer <you> --evidence <kind>:<ref>
sdem status --workspace examples/payment-initiation-v3/sdem
```
