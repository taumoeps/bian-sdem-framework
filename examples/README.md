# Examples

> **Status: current (v0.21.14)** — made-up designs to try, copy and learn from. **Everything here is synthetic**: no real organisation's architecture.

## Where to start

| You want to | Start with | How |
|---|---|---|
| See a finished design, explored | [`payment-initiation`](payment-initiation/) | `sdem new --workspace workspaces/payments --person <you> --example payment-initiation --explore` |
| A complete design in SDEM 0.20's form — every layer, BIAN and the Security extension, 0 gaps | [`0.20/payment-initiation-v4`](0.20/payment-initiation-v4/) | `sdem model integrity --workspace examples/0.20/payment-initiation-v4/sdem --check` — it is the Payment example on [DESNRE](https://desnre.vercel.app/example/payment) |
| A design without BIAN — any industry | [`0.20/library-holds`](0.20/library-holds/) | `sdem new --workspace workspaces/library --person <you> --core --from examples/0.20/library-holds` |
| Practise bringing in existing designs | [`designs/`](designs/) | a made-up Confluence export: `sdem transform run examples/designs/confluence-folder-export -o work/transform` |
| An organisation's own rules, standards and patterns | [`profiles/`](profiles/) | profiles to include: `sdem profile include …` |

## The two forms

SDEM 0.20 changed how a design is held: BIAN became an extension, Data a layer of its own, and the layer files are named for their layer (`business.json`, `bian.json`, `data.json`, `application.json`, `technology.json`). **`0.20/` holds every example in that form — use these.** The folders at this level are the same designs in the earlier form (`a1-business.json` … `a4-technology.json`), kept because SDEM's tests and migration (`sdem migrate`) use them.

| Example | What it shows |
|---|---|
| [`payment-initiation`](0.20/payment-initiation/) | a brownfield payment design (use case M1) |
| [`payment-initiation-v2`](0.20/payment-initiation-v2/) · [`v3`](0.20/payment-initiation-v3/) · [`v4`](0.20/payment-initiation-v4/) | the same payment design grown to a full design, traced from its plan to its data, then completed to every layer |
| [`digital-lending`](0.20/digital-lending/) | greenfield — where mapping ends and design begins (M2) |
| [`legacy-core-ledger`](0.20/legacy-core-ledger/) | reverse mapping of a legacy system (H1) |
| [`acquired-fintech`](0.20/acquired-fintech/) | an acquired company with hostile naming (H2) |
| [`card-fraud-alerts`](0.20/card-fraud-alerts/) | a change event and its impact |
| [`customer-onboarding`](0.20/customer-onboarding/) · [`fx-dealing`](0.20/fx-dealing/) · [`trade-finance`](0.20/trade-finance/) | mapping and coverage cases |
| [`library-holds`](0.20/library-holds/) | a design with no banking content and no BIAN |
| [`reference-structure`](0.20/reference-structure/) | one relationship per rule inside a layer — the metamodel exercised |

`acceptance-cases.json` and `blind-cases.json` are the evaluation cases SDEM's tests run against these designs.
