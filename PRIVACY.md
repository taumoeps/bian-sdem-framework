# SDEM — Privacy and Data Handling

> **Status: current (v0.9.14)** — how the SDEM software handles the information you give it, as verified against the v0.9.14 code. It describes the software's behaviour; it is not a privacy policy of any organisation or platform, and it makes no claim of compliance with any privacy law or industry regulation. Plain-words licence page: [`docs/sdem-licence-and-use.md`](docs/sdem-licence-and-use.md).

## 1. Overview

SDEM is a command-line tool. It reads files you point it at, checks them against its metamodel, and writes files into folders you choose: architecture records for the four layers (A1 business, A2 BIAN service domains, A3 applications, A4 technology), the connections between them, knowledge graphs, reports and HTML pages.

**Where your information goes is decided by where you run SDEM and where you keep its files** — your machine, your organisation's private repository, any optional services you connect. SDEM itself sends nothing anywhere.

## 2. Local data processing

Every SDEM command runs on the machine where you type it.

| Component | Reads | Writes |
|---|---|---|
| `sdem check`, `validate`, `trace`, `impact`, `matrix`, `query` | the workspace's layer files (`a1-business.json` … `a4-technology.json`) and `mappings.json` | the terminal; a report file only when you ask (`--report`) |
| `sdem link` | the workspace | proposals in a folder you name (usually `work/`) |
| `sdem approve`, `sdem connect` | the workspace and the proposal | the workspace's `mappings.json` |
| `sdem transform` (onboarding) | a design export you downloaded — pages, diagrams, pictures | *candidate* records in a folder you name |
| `sdem load` | the candidates | the workspace's layer files, `designs/` and `loads/` |
| `sdem build`, `view`, `dashboard`, `home` | the workspace | a graph store, HTML pages — in folders you name |
| `sdem bian import`, `pack`, `update` | a BIAN release you downloaded, or the bundled base BIAN | an A2 file; `bian-updates/` records in each workspace |
| `sdem copilot install` | files bundled with SDEM | `.github/` in the folder you name |

**Programs SDEM starts on your machine** — and nothing else:

- **`git`** — to compare data with an earlier commit (`sdem validate`/`diff` against a revision) and to read the current branch name (agents' work items).
- **Text recognition in pictures**, during `sdem transform`: macOS's built-in Vision framework (through `osascript`), or Tesseract if installed. Both run on the machine. `--ocr off` turns text recognition off.

## 3. Data collection and telemetry

Verified in the v0.9.14 code:

| Does SDEM collect … | Answer |
|---|---|
| Usage analytics or telemetry | **No.** There is no analytics or telemetry code. |
| Architecture data | **No.** It is read and written in your folders only. |
| Device information | **No.** |
| Credentials | **No.** SDEM asks for no account, password, token or API key. |
| Personal information | **Not collected — but recorded where you put it.** SDEM writes the names you give it into your records: the person who approves or states a connection (`--reviewer`/`--person`), who loaded designs, who adopted a change, and dates. Design exports you onboard may themselves contain names. These stay in your files. |

## 4. Data storage

SDEM stores everything as ordinary files in the folders you choose; it keeps no database, cache or hidden store elsewhere.

| What | Where |
|---|---|
| Architecture records (A1–A4) | the workspace folder: `a1-business.json` … `a4-technology.json` |
| Connections (approved, superseded) and their evidence | the workspace's `mappings.json` |
| Onboarding records, load records, BIAN updates, migrations, agent coordination | the workspace's `designs/`, `loads/`, `bian-updates/`, `migrations/`, `coordination/` |
| Imported design exports and candidate records | where you put them — by convention `work/`, which Git ignores |
| Knowledge graphs | the graph store you name (JSON Graph Format files, a load record, frozen baselines) |
| Dashboards and views | HTML files you name; each is self-contained (data, script and style inside) and loads nothing from the internet |
| Temporary files | a write goes to a temporary file in the same folder and is moved into place; text recognition uses a temporary folder removed when SDEM exits |
| Logs | none — SDEM writes messages to the terminal only |

The full list of what is inside a workspace, and what writes each file: [the architecture page](docs/sdem-architecture.md#inside-a-workspace).

## 5. External data transmission

**Core SDEM makes no network requests.** It imports no networking library, and the HTML pages it writes load nothing from the internet (both checked by `tests/test_privacy.py` on every push). It depends only on the Python standard library.

Optional tools and services around SDEM are **not** covered by this — each has its own behaviour and terms:

| Around SDEM | What leaves your machine |
|---|---|
| **Installing SDEM** (`pip install` from GitHub) | a download from GitHub; nothing about your data |
| **GitHub Copilot** (optional) | what you and Copilot put in the chat, under your organisation's agreement with GitHub. SDEM's agents and prompts only run SDEM commands, when you ask |
| **Other AI services** | SDEM calls none. If you use one alongside SDEM, its terms apply |
| **Text recognition** | none — macOS Vision and Tesseract run on the machine |
| **Diagram previews** | Mermaid previews render in VS Code. PlantUML previews render locally in this project's setting; a public PlantUML server would receive the diagram text |
| **Repository hosting and CI** (GitHub or your own) | whatever you commit and push, to the host you choose — keep real workspaces in a **private** repository |
| **VS Code and its extensions** | under their own terms; this project only recommends three (Python, Copilot Chat, Mermaid preview) |
| **Future integrations** (planned: reading from EA tools and CMDBs) | not in v0.9.14; each will state its own behaviour when built |

## 6. Organisation data ownership

The SDEM licence (Apache License 2.0) covers SDEM's software and documentation. It **does not give the SDEM project, or anyone else, any right to your organisation's architecture data**, and SDEM does not send that data anywhere. Your organisation remains responsible for its data classification, access control, retention and records management.

## 7. Confidential architecture information

- Keep organisation-specific workspaces, design exports and outputs in **systems your organisation approves** — a private workspace repository and approved machines. The [workspace repository template](templates/workspace-repo/README.md) and the [protection guide](docs/sdem-repository-protection.md) set this up.
- SDEM **never requires** you to contribute data, configurations or changes to the public SDEM repository. The public repository holds made-up data only and ignores `workspaces/` and `work/`, so they cannot be pushed to it by mistake.

## 8. Data retention and deletion

- **SDEM deletes nothing automatically**, apart from its own temporary files (§4). Files it writes stay until you delete them.
- **Approved connections are kept by design**: SDEM does not edit or delete an approved connection — a replacement *supersedes* it, and both remain. Retired records are marked `retired`, not removed. This keeps the history auditable; it also means that removing information from a workspace (for example, a person's name) is a change you make in the files and in your repository's history, under your organisation's policies.
- Anything committed to a Git repository also stays in its history and its copies.

## 9. Security responsibilities

SDEM is provided as is (Apache License 2.0, §7–§8). It has not been independently audited or certified. Each organisation assesses SDEM — and any service connected to it — against its own security requirements before use with real data: where it runs, who can read the workspace repository, branch protection and code owners, the SDEM version it pins, and its Copilot and text-recognition policy. Reporting a vulnerability: [`SECURITY.md`](SECURITY.md).

## 10. Policy scope

This document describes **the SDEM software's behaviour** in v0.9.14. It does not describe, and cannot vouch for, the practices of GitHub, Microsoft, Apple, the Tesseract project, PlantUML or any other platform you use with SDEM; their own terms apply. It is not legal advice and makes no claim of compliance with any law or regulation.
