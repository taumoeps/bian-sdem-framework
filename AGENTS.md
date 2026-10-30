# SDEM — instructions for AI agents working in this repository

This is **SDEM's own repository** (the code, the metamodel, made-up examples). Two kinds of work happen here:

- **Using SDEM** on the examples: follow [`templates/agents/AGENTS.md`](templates/agents/AGENTS.md) — the instructions every agent gets in a workspace repository (`sdem agents install`): always `--json`, `sdem commands --json` to discover, `--dry-run` before writing, never decide for a person, never edit architecture files directly.
- **Changing SDEM**: the rules below.

## Changing SDEM

1. **Tests before every push, with and without an install:** `python -m unittest discover -s tests` (no install — as CI), and `sdem model check` (every generated file current). CI: `.github/workflows/validate.yml`.
2. **The metamodel (`metamodel/`) changes only with the owner's approval**; generated documents are regenerated with `sdem model regenerate`, never edited by hand.
3. **Made-up data only.** No real organisation's architecture, ever; the examples in `examples/` are synthetic.
4. **Every rule has an id** (CTL-…, AF-…, AID-…) in its spec under `docs/design/`; a change cites it, and the CHANGELOG says what changed in plain words.
5. **No new dependencies** — SDEM runs on the Python standard library (`pyproject.toml`: `dependencies = []`).
