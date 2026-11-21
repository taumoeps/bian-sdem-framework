# SDEM 0.20 step 5 — BIAN on the default: five layers

> **Status: built and approved — BD-D1 decided by the owner (2026-11-21).** Step 5 of the [0.20 plan](sdem-0.20-plan.md) (PL-D4: *this spec decides, link by link,
> how service domain → application connections cross the Data layer*). Made-up data only.

## 1. What it is

With BIAN on, a workspace in SDEM 0.20's form has five layers — **A1 Business, A2 BIAN, A3 Data, A4 Application, A5 Technology** — the
default four (Business, Data, Application, Technology; [Data layer spec](sdem-data-layer-spec.md)) with BIAN between Business and Data
(BX-04: BIAN sits where 0.19 had it, after Business). Step 4 built it: the stack is computed from the layers in use (DL-06), BIAN's types and
link types come from `ext:bian` or `sdem-bian` (step 1, 2), and every example with BIAN is migrated into it (DL-20).

## 2. The links between BIAN and the layers below it

Five of 0.19's link types join BIAN to the layers that were A3. With Data its own layer, two now end in Data — BIAN's neighbour — and
three end in Application, with Data between.

| Id | Link type | From → to | In five layers | Rule |
|---|---|---|---|---|
| **BD-01** | `BIAN_OBJECT_MAPPED_TO_DATA_ENTITY` | `bian.BusinessObject` MAPPED_TO `data.DataEntity` | BIAN → Data, neighbours | unchanged |
| **BD-02** | `BIAN_ATTRIBUTE_FIELD_MAPPED_TO_DATA_ATTRIBUTE` | `bian.BusinessObjectAttribute` FIELD_MAPPED_TO `data.DataAttribute` | BIAN → Data, neighbours | unchanged |
| **BD-03** | `DOMAIN_REALIZED_BY_COMPONENT` | `bian.ServiceDomain` REALIZED_BY `application.ApplicationComponent` | BIAN → Application, over Data | **unchanged — a direct link** |
| **BD-04** | `OPERATION_IMPLEMENTED_BY_API` | `bian.ServiceOperation` IMPLEMENTED_BY `application.APIOperation` | BIAN → Application, over Data | **unchanged — a direct link** |
| **BD-05** | `NOTIFY_OPERATION_IMPLEMENTED_BY_EVENT` | `bian.ServiceOperation` IMPLEMENTED_BY `application.Event` | BIAN → Application, over Data | **unchanged — a direct link** |

**Why BD-03…BD-05 stay direct.** What each says is between a service domain or operation and the application that carries it out — a
service domain is realised by an application component, not by data; routing it through a data entity would change what it means and lose
which component realises the domain. SDEM's rule for links between layers is that they point **down** the stack (KG-F-03), not that they join
neighbours: 0.19 already has links that pass over a layer (a business process SERVED_BY an application service passes over BIAN). The Data
layer between is not on these links' path; what a service domain's records hold is said by BD-01 and BD-02.

**BD-06 — Nothing is re-written.** No 0.19 link is moved, split or re-typed by step 5; a workspace's approved links stay as they were
(the access links inside Application become `ACCESSED_BY` in step 4's migration, DL-13 — not here).

## 3. The proof — P4

**P4: BIAN on the default is 0.19.** 0.19's answers, translated by `metamodel/identity.json` (P2), match the five-layer payment example
(`examples/0.20/payment-initiation`), except where the Data layer — not BIAN — explains the difference, each named
(`tests/test_data_layer.py`, `NAMED`). No difference is about BD-03…BD-05: the traces and impacts through service domain → application are
0.19's. And every example with BIAN reconciles record by record (`Reconciled`).

## 4. Decision

| # | Decision | Recommended |
|---|---|---|
| BD-D1 | The three links from BIAN to Application (BD-03…BD-05) stay direct links, over the Data layer, as in 0.19 | **yes** — the owner, 2026-11-21 ("Yes, stay direct"): their meaning is BIAN → application; nothing to migrate |
