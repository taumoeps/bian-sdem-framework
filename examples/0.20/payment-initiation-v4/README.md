# Payment Initiation v4 — the v3 design, completed to every layer

> **Made-up data only.** The same invented New Zealand retail bank as [v3](../payment-initiation-v3/); the standards it cites are public. Nothing here comes from any real organisation.

v4 is [v3](../payment-initiation-v3/)'s design (its [narrative](narrative/design.md) is the same document), taken in SDEM's 0.20 form to a design in which **every record reaches every other layer** — the metamodel integrity design's MID-05, checked on a real design (docs/design/metamodel-integrity-design.md §6). v3 stays as it is: it is the migration twin of the 0.19 example, record for record.

```
sdem check  --workspace examples/0.20/payment-initiation-v4/sdem          # OK — without the security extension installed (its pack is carried as a file)
sdem status --workspace examples/0.20/payment-initiation-v4/sdem          # Completeness 148 of 148 (100%), both patterns in place
sdem build  --workspace examples/0.20/payment-initiation-v4/sdem -o /tmp/g && sdem trace GAPS --graph /tmp/g   # 327 of 327, 0 design gaps, 0 rule gaps
```

## What v4 adds to v3 — every change a person's decision, recorded

| | What | Basis |
|---|---|---|
| Data architecture | Domains *Payments*, *Consent*, *Payment processing*, *Security audit*; read and write on each access link | the Data Architecture spec (DAR-10) |
| Security layer | S1–S5: controls, threats, trust boundaries — the security extension's pack carried as a file (`security-pack.json`) | sdem-security 0.4.3 |
| New tables | **AuthenticationResult** (written by Identity), **RiskDecision** (written by the Fraud service, read by the Payments hub), **LedgerPosting** (written by the Account ledger) — each in the bank's one database (AD-01) | design §4–§7; R-08, R-09 |
| BIAN alignment | Business objects *PartyAuthentication*, *ProductionTransaction* (Fraud Evaluation), *FinancialTransactionCapture* (Position Keeping, a domain added for posting) — each held by its domain's control record, mapped to its table; IdempotencyRegistry and ConsentLedger mapped from *Payment Transaction* | BIAN 14.0.0's published schemas; R-05 |
| Applications | Consent processing realises Party Authentication (design §4); the Outbound connector realises Payment Order Initiation and writes the hand-off id; the Account ledger realises Position Keeping | design §4–§5, R-10 |
| Channels, technology | Each channel associated with the service it exposes (FT-15); a *Restricted storage service* the stores share (design §6) | ArchiMate 3.2 §8.2.3 |
| Removed | The Notification service and its deployment — an existing, non-critical system the payment journey never uses — **retired** through a change event whose impact the owner accepted (CE-013) | design §1, §5 |

Each record and link cites its section of the narrative or BIAN's file and says *the owner's decision 2026-11-22* where the narrative does not state it; the change sets, the change event and the decisions are in [`sdem/coordination/`](sdem/coordination/) and [`sdem/decisions/`](sdem/decisions/). It is the design published at DESNRE as the Payment example.
