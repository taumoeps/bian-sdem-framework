# Security

## Reporting a problem

Please **do not open a public issue** for a security problem. Report it privately through GitHub: **Security → Report a vulnerability** on this repository (private vulnerability reporting). You will get an acknowledgement within five working days. Say what you found, how to reproduce it, and what it could expose.

## What SDEM is, and what it is not

SDEM is an **offline command-line tool** that reads and writes JSON files on your machine.

- **No network.** SDEM makes no network calls: no server, no AI API client, no MCP server, no API key, and the HTML pages it writes load nothing from the internet. Tests check this on every push (`tests/test_privacy.py`, `tests/test_copilot_setup.py`). The only programs it starts are `git` (to compare with an earlier commit and read the branch name) and the machine's own text recognition (macOS Vision, or Tesseract if installed) to read text in pictures during `sdem transform` — both on your machine; `--ocr off` turns text recognition off. More: [`PRIVACY.md`](PRIVACY.md).
- **No dependencies** beyond the Python standard library — nothing to pull from a package index at run time.
- **AI agents are optional and outside SDEM.** GitHub Copilot, Claude Code, OpenAI Codex or Gemini CLI run under your organisation's agreement with their vendor; SDEM installs instruction files for them (`sdem agents install`) and they use only the SDEM command line, when the architect asks.

## Human decisions and AI agents — the trust boundary

SDEM records architectural decisions with attribution and provenance. Verified human authority requires independently protected signing credentials, authorised signers and repository governance controls. AI-agent instructions prohibit approval actions, but instructions alone are not a security boundary.

- `--person` / `--reviewer` is **attribution, not authentication**. SDEM refuses an agent's name there — a safeguard, not proof of identity: an agent with terminal access can type a person's name.
- In **local evaluation mode** no decision is verified, and SDEM does not claim otherwise.
- **`--dry-run` is a preview, not isolation.** A command that plans its own changes (`load`, `migrate`, `bian update`, `change propose` …) computes them and writes nothing; for the others, SDEM catches its own file writes while the command runs and reports them as `would_write`. Either way it describes what SDEM would do. It is not a sandbox: it does not stop another program, or an agent with terminal access, from writing files. Keep agents' write access limited by the operating system or container, give them their own working copy, and protect `main`.
- In **governed enterprise mode** a decision is verified only by the named approver's SSH-signed commit (`sdem governance verify`), and `sdem work plan` refuses an unverified acceptance or authorisation. That holds only while the approvers' signing keys are out of the agents' reach, `governance.json` and the allowed-signers file are protected by code owners, and `main` is protected. Details: [`docs/design/sdem-governance.md`](docs/design/sdem-governance.md).

## Keeping real data out of this repository

This repository is **public** and holds **made-up data only**.

| Do | Why |
|---|---|
| Keep real workspaces in your team's **private** workspace repository | `workspaces/` and `work/` are ignored here, so they cannot be pushed by mistake |
| Keep design exports (Confluence) in `work/`, on the machine allowed to hold them | the transform reads them where they are; nothing is uploaded |
| Preview PlantUML diagrams **locally** (this project's setting) or on your organisation's server | the public PlantUML server receives the diagram text |
| Never commit tokens, passwords or keys — `.env` and `secrets/` are ignored | |
| Protect `main` in your workspace repository (pull requests, code owners) | so a person's approval is a control — [`docs/sdem-repository-protection.md`](docs/sdem-repository-protection.md) |

## Supported versions

The latest release and `main`. Security fixes are not back-ported.
