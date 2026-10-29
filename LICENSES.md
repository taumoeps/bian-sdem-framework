# Licensing

SDEM is published under the **Apache License 2.0** (`LICENSE`). This page says which licence covers each part of the repository and what is *not* covered by it. In plain words: [`docs/sdem-licence-and-use.md`](docs/sdem-licence-and-use.md). It is not legal advice.

## What is licensed, and by whom

| Category | Licensing and ownership |
|---|---|
| **SDEM core framework** — the tool (`sdem/`), tests, scripts, CI and Copilot files (`.github/`), templates (`templates/`), made-up examples (`examples/`) | Apache License 2.0 (`LICENSE`), as granted by its contributors, to the extent of their rights in what they contributed |
| **SDEM documentation, metamodel and schemas** — `docs/`, `README.md` and the other Markdown files, `metamodel/`, `schema/` | Apache License 2.0, except third-party content identified in `THIRD_PARTY.md` |
| **BIAN Semantic APIs** — the base BIAN in `bian/` (`base-*.json`) | BIAN e.V.'s Apache License 2.0 (`bian/LICENSE`); what was changed is stated in `bian/README.md` |
| **SDEM's inference record** — `bian/inferences-*.json` | SDEM's own work (Apache License 2.0, `LICENSE`): values inferred from BIAN's public sources, each citing them |
| **Your organisation's architecture data** — estates, design exports, outputs | **not part of SDEM** and not licensed by it; controlled by your organisation's own intellectual-property and confidentiality arrangements |
| **Your organisation's configurations** — transform rules, BIAN selections, code owners, CI settings | ownership governed by the agreements that apply to the people who make them |
| **Your organisation's modifications to SDEM** | ownership governed by authorship, employment and contractual arrangements; the Apache License 2.0 lets you make and keep them |
| **External tools and integrations** — GitHub, Copilot, VS Code, Tesseract, PlantUML, others | their own licences and terms |

Trademarks — BIAN®, ArchiMate®, TOGAF® — belong to their owners and are not licensed here (`THIRD_PARTY.md`; Apache License 2.0 §6).

## What the Apache License 2.0 permits

- **Commercial use** — permitted.
- **Internal use in any organisation**, across any number of teams — permitted.
- **Private modifications and extensions** — permitted.
- **Not publishing your modifications** — permitted; there is no obligation to share or contribute them.
- **Redistribution** — permitted, under the licence's conditions (§4): give recipients a copy of the licence, mark files you changed, and keep the copyright, patent, trademark and attribution notices (for the base BIAN, `bian/LICENSE` and `bian/README.md`).

## What the licence does not do

- **It does not override employment agreements or confidentiality obligations.** Whether a person may install SDEM on an employer's device, use it at work, or publish a change made at work is decided by their employer's policies and their contract, not by this licence.
- **It does not decide who owns a modification.** That depends on applicable law, who wrote it, and the agreements they work under.
- **It grants no rights in your organisation's data**, to the SDEM project or anyone else.

## Ownership of SDEM itself

Before promoting SDEM widely, the publisher confirms they have the right to license all of it (for example, under their employment terms). A contribution to the public repository is offered under the Apache License 2.0 (§5); contributors confirm they have the right to offer it (`CONTRIBUTING.md`).
