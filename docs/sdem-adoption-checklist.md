# Adopting SDEM — the checklist for your organisation

> **Status: current (v0.9.12)** — what an organisation should clear before SDEM holds its real architecture: legal and licences, data, security, AI, and the risk of depending on an open-source tool. It lists the questions and the facts behind them; **it is not legal advice** — your legal, risk and security teams decide. Who does what afterwards: the [operating model](sdem-operating-model.md).

## 1. Legal and intellectual property

| Question | The facts | Who decides | ✓ |
|---|---|---|---|
| May we put our architecture designs into a tool we run ourselves? | SDEM runs on your machines and keeps data as files in **your** private repository; nothing goes to the SDEM project or anyone else | legal / IP | ☐ |
| May we use SDEM's licence? | **Apache-2.0** for everything — code, metamodel, documentation, templates (`LICENSE`, `LICENSES.md`); in plain words: [using SDEM](sdem-licence-and-use.md) | legal / open-source review | ☐ |
| May we use the base BIAN? | BIAN's public **Semantic APIs 14.0.0**, published by BIAN e.V. under **Apache-2.0**, ship with SDEM (`bian/`, with BIAN's licence and a statement of what was changed). If you are a BIAN member, check your membership terms too; BIAN® is BIAN's trademark | legal | ☐ |
| Does SDEM claim to be BIAN-endorsed? | No — it is independent and says so (`THIRD_PARTY.md`) | — | ☐ |
| Names from published standards | SDEM's metamodel uses concept names from BIAN, ArchiMate® and TOGAF® (no text copied); ArchiMate and TOGAF are published by The Open Group behind a sign-in. Whether using these names and trademarks needs anything more is a question for your legal team | legal | ☐ |
| Who owns what we create with it? | Your data and the connections your architects approve are yours; SDEM adds no content of its own to them — except the BIAN content you choose to import into your A2 layer, which stays under BIAN's Apache-2.0 licence (keep `bian/LICENSE`) | legal | ☐ |

## 2. Data

| Question | The facts | Who decides | ✓ |
|---|---|---|---|
| How is architecture data classified? | Decide the classification of your workspaces (often *internal* or *confidential*); SDEM supports an `access_classification` on records | data owner | ☐ |
| Where does it live? | A **private** workspace repository in your organisation's GitHub ([template](../templates/workspace-repo/README.md)); design exports only in `work/` on machines allowed to hold them — never committed | data owner, platform | ☐ |
| Who can see the dashboards? | Local HTML files for now; later only behind your sign-in — never public hosting ([operating model](sdem-operating-model.md) §7) | data owner | ☐ |
| How are changes controlled? | Pull requests with named code owners and branch protection ([repository protection](sdem-repository-protection.md)) | platform | ☐ |

## 3. Security

| Question | The facts | Who decides | ✓ |
|---|---|---|---|
| Does SDEM send data anywhere? | **No network** in use: no server, no AI client, no MCP, no API keys; the pages it writes load nothing from the internet — checked by tests on every push ([PRIVACY.md](../PRIVACY.md), [SECURITY.md](../SECURITY.md)) | security | ☐ |
| What does it install? | Python 3.10+ and SDEM itself — **no other dependencies**; pinned to a tagged release in your workspace repository | security, platform | ☐ |
| Reading text in pictures (OCR) during onboarding? | Done **on the machine** (macOS text recognition, or Tesseract if installed); `--ocr off` turns it off | security / data owner | ☐ |
| Diagram previews? | PlantUML previews render **locally** when VS Code's `plantuml.render` setting is `Local` — set in the workspace template's `.vscode/settings.json`; keep it (or use your organisation's own server): the public PlantUML server would receive the diagram text | security | ☐ |
| How are problems reported? | Privately, per [SECURITY.md](../SECURITY.md) | — | ☐ |

## 4. AI

| Question | The facts | Who decides | ✓ |
|---|---|---|---|
| Is AI required? | **No** — every SDEM function works without AI; rules, not AI, propose connections | — | ☐ |
| May architects use GitHub Copilot with it? | Optional. If allowed, `sdem copilot install` adds SDEM's agents, prompts and skills; Copilot never approves (an agent's name is refused as reviewer, CTL-21). Data seen by Copilot is governed by your organisation's Copilot agreement | AI / security policy | ☐ |
| Have the agents been tested in real Copilot? | Not yet — the [spike checklist](sdem-agent-platform-spike.md) is the first step | the SDEM owner, with you | ☐ |

## 5. Depending on an open-source tool

| Risk | The facts | Mitigation | ✓ |
|---|---|---|---|
| **One maintainer** | SDEM is maintained by one person; support is best effort during the pilot (operating model §7) | name an **in-house SDEM lead** ([operating model](sdem-operating-model.md) §2); pin a release; review support after the pilot; Apache-2.0 lets you fork and maintain your own copy if ever needed | ☐ |
| **Lock-in** | Your data is plain JSON files in your repository, in documented formats (`schema/`) — readable without SDEM | nothing to do; keep the repository backed up as usual | ☐ |
| **Quality** | Every release passes the full test suite on Python 3.10–3.13, the installed package is tested, and use-case examples are replayed with sealed expected results | read the release's CHANGELOG before upgrading | ☐ |
| **Changes to the metamodel** | Recorded with a migration; your workspaces move with `sdem migrate`, checked, all-or-nothing | upgrade on a branch, CI green, then merge ([administration](sdem-administration.md#upgrading-sdem)) | ☐ |
| **Procurement** | Open source at no cost; no contract or vendor | your procurement process for open-source software | ☐ |

When every row is ticked, the pilot can start ([pilot plan](sdem-pilot-plan.md), week 0).
