# SDEM — instructions for GitHub Copilot

Architects here use **SDEM, the Service Domain Enterprise Metamodel**: it links an organisation's four architectures — A1 Business, A2 BIAN service domains, A3 Application, A4 Technology — under a rulebook, and keeps them as a knowledge graph. They run it from the VS Code terminal with the `sdem` command; you **support** them. Start with `docs/sdem-workbench-user-guide.md`.

**Which repository this is.** In an **estate repository** (the usual case), the architecture data is in `estates/<domain>/` — real, private data: never paste it outside the organisation's approved Copilot — and SDEM is installed (`sdem --version`). In the **SDEM project** itself, the data is the made-up examples in `examples/`.

## Ground rules

1. **Facts come from SDEM's CLI and files.** Answer architecture questions from `sdem` output and the project's files, not from memory, and say which command or file each answer came from.
2. **Suggest the exact command.** When an answer needs SDEM to run, give the exact `sdem …` command. Run it only when the architect asks, in the terminal, so the command and its output are visible.
3. **Rules first.** The rules engine (`sdem link`) proposes cross-layer links and `sdem impact` decides what a change affects; never invent links or impact.
4. **Never write projected or AI content into real data** — the architecture datasets (`a1-…a4-*.json`), the registry (`mappings.json`) or a graph store. Projections (`PRJ-` ids) stay in their own folder.
5. **Never approve, never load.** A person approves a link with `sdem approve` (their name, the date, the evidence its type requires) and a reviewed pull request; CTL-21 rejects an agent as reviewer. A person loads onboarded designs with `sdem load`. Never run `sdem approve`, `sdem connect`, `sdem bian update`, `sdem change adopt`, `sdem load` or `sdem designs resolve|accept|reopen` yourself (`--dry-run` is fine). You may draft a `sdem connect` command, with its evidence and rationale, for the architect to run. You may draft the review, the load command or the pull-request text.
6. **Source, reasoning and confidence** on every statement about the architecture.
7. **No MCP, no API keys**, and no data sent anywhere except through the organisation's approved Copilot.
8. **When unsure, say so** and name the command that would settle it.

## Where things are

| Need | Where / command |
|---|---|
| every command and journey | `sdem --help`; `sdem <command> --help` has a worked example; the full list: `docs/sdem-workbench-user-guide.md` §7 |
| SDEM and every project on one page | `sdem home -o work/sdem` (main dashboard: metamodel, health, configuration, projects) · `sdem dashboard --estate <estate> -o <file.html>` (one project) — suggest them to architects who prefer a page to the terminal |
| matrices, impact report | `sdem matrix --estate <estate>` · `sdem impact <id> --change <kind> --estate <estate> --report <file.md>` |
| the architecture data | `estates/<domain>/` in an estate repository: `a1-…a4-*.json`, `mappings.json` (approved links), `designs/` (design and gap records), `loads/`, `coordination/` |
| check data | `sdem check --estate <estate>` |
| propose and review links | `sdem link … --out <dir>` · `sdem review <dir>/proposals.json` |
| trace and impact | `sdem trace <id> --graph <dir>` · `sdem impact <id> --change <kind> --graph <dir>` |
| why something exists | `sdem explain <id> --proposals <file>` or `--projection <dir>` |
| plan missing layers | `sdem aid project …` |
| onboard past designs (Confluence) | `sdem transform inspect` · `sdem transform run` → review → `sdem load` (the architect); skill `sdem-onboard-designs`; `docs/sdem-onboarding-workflow.md` |
| agent platform | `.github/agents/` (orchestrator and A1–A4 layer agents), `sdem change` · `sdem events` · `sdem work` |
| the rulebook | `metamodel/`, `schema/`; the governing spec `docs/design/architecture-metamodel-detail-level-spec.md` |
| your BIAN layer | `sdem bian list --base` · `sdem bian import --base --only <names> -o <file>` (the architect); the onboarding workflow's *Your BIAN (A2) layer* |
| example estates (SDEM project only) | `examples/` — public, made-up data only |
