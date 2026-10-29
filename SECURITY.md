# Security

## Reporting a problem

Please **do not open a public issue** for a security problem. Report it privately through GitHub: **Security → Report a vulnerability** on this repository (private vulnerability reporting). You will get an acknowledgement within five working days. Say what you found, how to reproduce it, and what it could expose.

## What SDEM is, and what it is not

SDEM is an **offline command-line tool** that reads and writes JSON files on your machine.

- **No network.** SDEM makes no network calls: no server, no AI API client, no MCP server, no API key, and the HTML pages it writes load nothing from the internet. Tests check this on every push (`tests/test_privacy.py`, `tests/test_copilot_setup.py`). The only programs it starts are `git` (to compare with an earlier commit and read the branch name) and the machine's own text recognition (macOS Vision, or Tesseract if installed) to read text in pictures during `sdem transform` — both on your machine; `--ocr off` turns text recognition off. More: [`PRIVACY.md`](PRIVACY.md).
- **No dependencies** beyond the Python standard library — nothing to pull from a package index at run time.
- **Copilot is optional and outside SDEM.** If your organisation uses GitHub Copilot, its data handling is your organisation's agreement with GitHub; SDEM's agents only run the SDEM CLI, and only when the architect asks.

## Keeping real data out of this repository

This repository is **public** and holds **made-up data only**.

| Do | Why |
|---|---|
| Keep real estates in your team's **private** estate repository | `estates/` and `work/` are ignored here, so they cannot be pushed by mistake |
| Keep design exports (Confluence) in `work/`, on the machine allowed to hold them | the transform reads them where they are; nothing is uploaded |
| Preview PlantUML diagrams **locally** (this project's setting) or on your organisation's server | the public PlantUML server receives the diagram text |
| Never commit tokens, passwords or keys — `.env` and `secrets/` are ignored | |
| Protect `main` in your estate repository (pull requests, code owners) | so a person's approval is a control — [`docs/sdem-repository-protection.md`](docs/sdem-repository-protection.md) |

## Supported versions

The latest release and `main`. Security fixes are not back-ported.
