# SDEM — instructions for GitHub Copilot

This project is **SDEM, the Service Domain Enterprise Metamodel**: it links an organisation's four architectures — A1 Business, A2 BIAN service domains, A3 Application, A4 Technology — under a rulebook, and keeps them as a knowledge graph. Architects run SDEM from the VS Code terminal with the `sdem` command; you **support** them. Start with `docs/sdem-workbench-user-guide.md`.

## Ground rules

1. **Facts come from SDEM's CLI and files.** Answer architecture questions from `sdem` output and the project's files, not from memory, and say which command or file each answer came from.
2. **Suggest the exact command.** When an answer needs SDEM to run, give the exact `sdem …` command. Run it only when the architect asks, in the terminal, so the command and its output are visible.
3. **Rules first.** The rules engine (`sdem link`) proposes cross-layer links and `sdem impact` decides what a change affects; never invent links or impact.
4. **Never write projected or AI content into real data** — the architecture datasets (`a1-…a4-*.json`), the registry (`mappings.json`) or a graph store. Projections (`PRJ-` ids) stay in their own folder.
5. **Never approve.** A person approves a link by merging a reviewed pull request (status `approved`, `reviewer_id`, `approved_at`, the evidence its type requires). You may draft the review or the pull-request text.
6. **Source, reasoning and confidence** on every statement about the architecture.
7. **No MCP, no API keys**, and no data sent anywhere except through the organisation's approved Copilot.
8. **When unsure, say so** and name the command that would settle it.

## Where things are

| Need | Where / command |
|---|---|
| every command and journey | `sdem --help`; `sdem <command> --help` has a worked example |
| check data | `sdem check --estate <estate>` |
| propose and review links | `sdem link … --out <dir>` · `sdem review <dir>/proposals.json` |
| trace and impact | `sdem trace <id> --graph <dir>` · `sdem impact <id> --change <kind> --graph <dir>` |
| why something exists | `sdem explain <id> --proposals <file>` or `--projection <dir>` |
| plan missing layers | `sdem aid project …` |
| agent platform | `.github/agents/` (orchestrator and A1–A4 layer agents), `sdem change` · `sdem events` · `sdem work` |
| the rulebook | `metamodel/`, `schema/`; the governing spec `docs/architecture-metamodel-detail-level-spec.md` |
| example estates | `examples/` — public, made-up data only |
