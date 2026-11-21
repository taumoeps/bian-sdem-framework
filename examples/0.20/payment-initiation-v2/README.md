# Payment Initiation v2 — a full design (made-up)

**Not a bank.** A synthetic design: no real organisation's architecture. It extends the starter example
[`payment-initiation`](../payment-initiation/) (kept as it is — its records are the sealed evaluation set the engine is scored against)
into a **full A1–A4 design** for metamodel 0.17.0 — the test of [Metamodel 0.15.0–0.17.0: a full design](../../../docs/design/sdem-full-design-metamodel-design.md) (V2-01…V2-07).

## What it holds

- **A1:** capabilities, the value stream and its stages, processes and activities with their triggers, outcomes and automation; three
  **business events** (an instruction received, a 16:00 cut-off, a payment executed); the retail customer; the *Make a payment*
  **business service**; the *Domestic payment* **product**; two **channels** (the mobile app, the open-banking API); the payment
  instruction, payee and account; the instant-confirmation requirement.
- **A2:** the payment domains, with **BIAN 14.0.0's own business objects** for payment initiation — payment transaction, payer, payee,
  their banks, account, funding and compliance checks — each with its **typed fields** (BIAN's types, required fields, allowed values,
  references between objects).
- **A3:** the Payments Hub, its components, service, validation function, interface and APIs; every data table with **typed fields,
  primary and foreign keys**; every API naming its **request and response fields**; the payments building block.
- **A4:** the cloud and on-premises zones, platforms, a payments HSM, the API gateway's HTTPS interface, a network path that carries
  payment data, and **locations** (a country, its cloud region, a data centre).
- **Between the layers:** BIAN objects mapped to tables **field by field**; the business served and automated by the application
  (direct A1→A3, the owner's decision D9); the event and channel realised by the software; where each table is stored; the platform
  services the application uses.

## How it was built — the SDEM CLI only

The record is in [`docs/evidence/payment-initiation-v2/`](../../../docs/evidence/payment-initiation-v2/):

1. `sdem bian import <BIAN 14.0.0 folder> --only "Payment Order Initiation" --object …` — BIAN's own typed objects (the extract:
   `bian-14.0.0-payment-objects.json`; BIAN, Apache-2.0).
2. `sdem change propose` — one change set per layer (`cs-a2-objects.json` with `--catalogue`, `cs-a1.json`, `cs-a3.json`, `cs-a4.json`).
3. `sdem aid` — inferred 9 data tables with typed fields and keys and proposed 90 links (AID-001).
4. **The owner's review** — [`review-v2.sh`](../../../docs/evidence/payment-initiation-v2/review-v2.sh): `sdem aid confirm|reject`,
   `sdem approve`, `sdem connect`. The owner accepted the recommendations in that script as the owner's decisions without reviewing each line
   (2026-11-16); the approvals are recorded under the owner's name.
5. `sdem check` — clean (two advisory warnings: the starter's own made-up BIAN objects list field names without field records, LC-24).

The data files here are the result; the change sets, AID run and decisions stay with the evidence, so this folder is plain design data
like the other examples.
