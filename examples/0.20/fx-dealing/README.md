# Synthetic FX dealing: trade capture, confirmation and settlement

**Everything here is synthetic.** Harbourline Bank, its applications (Aurora, ClearView, Ledgerline, ConfirmHub, FX Settlement Manager, CRDS, Contributor Rates Gateway), the vendors ("Synthetic Vendor A/B"), the people's roles, the hosts and the document references are all made up. The BIAN layer is the only real content: seven service domains copied from BIAN's Semantic API release 14.0.0 with `sdem bian import --base --no-inferences`.

The answer key (`b1-gold-mappings.json`) was written from the architect's own judgement **without seeing SDEM's inference rules, its proposals or any other gold file**, and without running any inference command.

## What the bank does

Harbourline's FX desk sells spot and forward FX to corporate treasurers and runs the resulting position against other banks.

1. **Price.** A client asks for a rate on the ClearView portal (vendor-hosted) or by phone. The Aurora Pricing Engine builds a price from contributor rates (fed by the Contributor Rates Gateway), adds the client's margin and issues a firm quote that holds for a few seconds. Before quoting, the sales trader's workflow checks in CRDS that the client may trade that product.
2. **Deal.** The client accepts; Ledgerline FX Booking books the deal, puts it on the trader's blotter and updates the desk's net open position. The interbank dealer watches that position and covers it with other banks, inside per-dealer limits that Ledgerline also holds.
3. **Confirm.** Ledgerline publishes `FxDealBooked`; ConfirmHub (a vendor package on a VM) sends the bank's confirmation, matches the counterparty's, and queues breaks that analysts chase and escalate.
4. **Settle.** FX Settlement Manager enriches each leg with the counterparty's standing settlement instructions (from CRDS), releases the pay leg on value date through the interbank payment gateway, and books the incoming nostro advice against the expected receive leg.

## The design

| File | Records | Contents |
|---|---|---|
| `a1-business.json` | 42 | 8 capabilities (1 level-1, 7 level-2), a value stream with 4 stages, 4 processes with 13 activities, 6 roles, 6 business objects |
| `a2-service-domain.json` | 261 | 7 BIAN service domains — Currency Exchange, Dealer Desk, Trader Position Operations, Trade Confirmation Matching, Trade Settlement, Counterparty Administration, Market Data Switch Operation — with their 29 service groups, 185 operations, 7 control records, 22 behaviour qualifiers, 7 asset types and 4 functional patterns, as BIAN 14.0.0 publishes them |
| `a3-application.json` | 54 | 7 components, 7 interfaces, 26 API operations, 12 data entities, 2 events |
| `a4-technology.json` | 23 | 2 environments, 2 Kubernetes clusters, 4 databases, 3 nodes (2 VMs, 1 physical co-location server), 2 technology services, 2 networks, 8 deployments |
| `mappings.json` | 0 | the empty registry: no cross-layer link is approved yet |
| `b1-gold-mappings.json` | 63 | the architect's answer key |

`invokes` is recorded where the process model names an operation, and only there, as in a real model. Some activities have none: 01d (blotter), 02b (dealer limit) and 04a (standing settlement instructions). Processes PRC-FX-02, -03 and -04 have no process-level `invokes`. The answer key still holds the domain usage those steps imply.

Some parts are left without a link on purpose. ClearView is a vendor SaaS channel: it realises no BIAN domain and has no deployment of ours. Aurora's indicative-rate ladder, the nostro-break list, the SSI lookup and the rate snapshot implement no operation in the key. The databases hold data but host no component.

## How the answer key was decided

All links have the status `approved`, carry a one-line rationale and give evidence in the `kind:ref` form that `schema/relationship-types.json` asks for.

| Link | Count | How it was decided |
|---|---|---|
| `SUPPORTED_BY` (capability → domain) | 9 | A level-2 capability is supported by a domain when part of its responsibility is that domain's scope. The level-1 capability has none of its own. |
| `USES_DOMAIN` (process → domain) | 8 | One link per domain that any activity of the process calls, whether or not the call is written in `invokes`. |
| `REALIZED_BY` (domain → component) | 8 | The component implements operations of that domain in this design. Ledgerline realises three domains; Currency Exchange is split between Aurora (Quote) and Ledgerline (FX Transaction Capture). |
| `IMPLEMENTED_BY` (operation → API) | 22 | Each API is matched to the BIAN operation whose behaviour qualifier and action term it exposes. Most APIs have one operation. |
| `DEPLOYED_AS` (component → deployment) | 8 | One per deployment record. |
| `DEPLOYED_ON` (component → node or system software) | 8 | The platform each deployment runs on: the Kubernetes clusters, the two VMs and the co-location server. |

The key has no `ALIGNED_TO` or `MAPPED_TO` links. The base BIAN that ships with SDEM has no business scenarios and no Business Object Model objects, and none were invented. So no value stream or business object has a BIAN target, and no BIAN object has a data entity.

## Links I was unsure about and left out

- **CAP-FX-000 Foreign Exchange → any domain** (`SUPPORTED_BY`). The level-1 capability is supported through its level-2 children. Whether to repeat the links at level 1 is a modelling convention, not a fact of the design.
- **CAP-FX-100 FX Client Pricing → Market Data Switch Operation** and **→ Trader Position Operations** (`SUPPORTED_BY`). Pricing depends on rates, and BIAN gives Trader Position Operations a "Trade Quote and Pricing" partition. Sourcing rates is its own capability here (CAP-FX-700), and client quoting is Currency Exchange.
- **PRC-FX-01 → Market Data Switch Operation** (`USES_DOMAIN`). The pricing engine consumes the rate feed, but no step of the business process calls the switch.
- **PRC-FX-03 → Counterparty Administration** (`USES_DOMAIN`). ConfirmHub may look up counterparty details to route confirmations. The process model does not say so.
- **Trader Position Operations → APP-AURORA** (`REALIZED_BY`). This depends on whether Aurora's dealer-facing pricing counts as BIAN's "Trade Quote and Pricing" partition.
- **API-AUR-03 indicative rate ladder → SO-CURRENCY-EXCHANGE-RETRIEVE-QUOTE** (`IMPLEMENTED_BY`). Indicative rates are not a quote instance, so the link is probably not true.
- **API-CRD-04 standing settlement instructions → SO-COUNTERPARTY-ADMINISTRATION-RETRIEVE or SO-COUNTERPARTY-ADMINISTRATION-RETRIEVE-COUNTERPARTY-ENTITY-REFERENCE** (`IMPLEMENTED_BY`). The domain is right, but I could not choose the operation.
- **API-RGW-02 rate snapshot → SO-MARKET-DATA-SWITCH-OPERATION-RETRIEVE-DISTRIBUTION or …-RETRIEVE-FEED-UPLOAD** (`IMPLEMENTED_BY`). Same problem: the domain is right, the operation is not clear.
- **API-CNF-02 run matching** is in the key as *Execute* on Transaction Confirmation Affirmation, because matching is an automated task. *Exchange* (accept or reject) was the alternative. I judged it confident enough to keep.

## Run it

```bash
sdem check --workspace examples/fx-dealing
sdem validate --strict examples/fx-dealing/b1-gold-mappings.json
```

*When the case was added to SDEM (2026-11-10), the attribute `automation_level` was removed from 9 business activities: the metamodel does not define it. Nothing else was changed; the answer key is as its author wrote it.*
