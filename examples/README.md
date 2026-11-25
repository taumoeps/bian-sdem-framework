# Examples

> **Status: current (v0.22)** — made-up designs to try, copy and learn from. **Everything here is synthetic**: no real organisation's architecture.

SDEM's core is industry-neutral, and so are its own examples. The banking designs — the Payment design in its versions, lending, fraud, FX, trade finance, onboarding, an acquired fintech, a legacy ledger — use BIAN, and since SDEM 0.22 they ship with the [`sdem-bian` extension](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/bian/sdem_bian/examples) (R-D6). With it installed, `sdem new --example` offers them too.

## Where to start

| You want to | Start with | How |
|---|---|---|
| A design without BIAN — any industry | [`0.20/library-holds`](0.20/library-holds/) | `sdem new --workspace workspaces/library --person <you> --example library-holds` |
| The metamodel exercised — one relationship per rule inside a layer | [`0.20/reference-structure`](0.20/reference-structure/) | `sdem check --workspace examples/0.20/reference-structure` |
| Practise bringing in existing designs | [`designs/`](designs/) | a made-up Confluence export: `sdem transform run examples/designs/confluence-folder-export -o work/transform` |
| An organisation's own rules, standards and patterns | [`profiles/`](profiles/) | profiles to include: `sdem profile include …` |
| A finished banking design, explored | sdem-bian's [`payment-initiation`](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/bian/sdem_bian/examples/payment-initiation) | with sdem-bian installed: `sdem new --workspace workspaces/payments --person <you> --example payment-initiation --explore` |
| A complete design — every layer, BIAN and the Security extension, 0 gaps | sdem-bian's [`0.20/payment-initiation-v4`](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/bian/sdem_bian/examples/0.20/payment-initiation-v4) | with sdem-bian installed |

## The two forms

SDEM 0.20 changed how a design is held: Data a layer of its own, and the layer files named for their layer (`business.json`, `data.json`, `application.json`, `technology.json`, and `bian.json` where a design uses BIAN). [`0.20/`](0.20/) holds the examples in that form; [`reference-structure/`](reference-structure/) keeps 0.19's form (`a1-business.json` …), which `sdem migrate` reads.
