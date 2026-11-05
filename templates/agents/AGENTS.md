# SDEM — instructions for AI agents

This repository holds architecture kept with **SDEM, the Service Domain Enterprise Metamodel**: an organisation's four architectures — A1 Business, A2 BIAN service domains, A3 Application, A4 Technology — linked under a metamodel. You work through the `sdem` command line; SDEM itself contains no AI, so the same command always gives the same answer. These instructions are the same for every agent (Codex, Claude Code, Gemini CLI, GitHub Copilot); they were installed by `sdem agents install` and match the installed SDEM version (`sdem --version`).

## How to run SDEM

- **Always add `--json`.** Every command then answers with one JSON object on stdout, starting with `"sdem": {"version", "command"}`; a list result is `{"count", "items"}`. Notes and warnings go to stderr.
- **Discover before guessing:** `sdem commands --json` lists every command, its options (choices, which are required), and the exit and error codes. `sdem <command> --help` has a worked example.
- **Failures are JSON too:** `{"error": {"code", "exit", "message", "hint", "details"}}`. Read `code` and follow `hint`. Codes: `usage`, `not_found`, `invalid_input`, `needs_person`, `exists`, `refused`, `input`, `internal`. Exit codes: 0 OK, 1 refused by a check, 2 usage or input error, 3 internal error.
- **Preview before you change anything:** add `--dry-run` to any command that writes; the answer lists what it would write (`would_write`) and nothing is written.
- **Keep answers small:** `--limit N` cuts every list to N items (what was cut is under `truncated`); `sdem dashboard --json` gives a summary (`--full` for everything).

## The rules — SDEM enforces them, and so do you

1. **Facts come from `sdem` and the files.** Answer from command output, say which command each answer came from, and give source, reasoning and confidence for every statement about the architecture.
2. **Never edit the architecture files directly** — `a1-business.json`, `a2-service-domain.json`, `a3-application.json`, `a4-technology.json`, `mappings.json`. Change a layer only through a change set: `sdem change propose <file> --workspace <dir> --agent <your layer agent> --person <the person you work for>`. An edit made any other way is noticed (`sdem check` lists it under `unrecorded_edits`; CI fails with `--require-recorded`), and only a person can accept it (`sdem change adopt`).
3. **One layer per agent.** A layer agent changes only its own layer; the orchestrator changes none (control CTL-19). Cross-layer links are proposed by the rules engine (`sdem link`), never written by hand.
4. **Never decide for a person.** Governed decisions — approving or stating a link (`sdem approve`, `sdem connect`), confirming or retiring a requirement, accepting impact or a residual risk and authorising (`sdem events accept|authorise`), accepting an edit (`sdem change adopt`), loading designs, starting a workspace — are the person's. **Do not run them**, even when given a name: prepare the exact command for the person to run. A `--person` name is attribution, not authentication; where the workspace requires it, SDEM honours a decision only when the person commits it signed with their own key (`sdem governance verify`). Propose, check, preview and explain — the person decides, and a reviewed pull request makes it final.
5. **Calculated impact is not accepted impact.** A change event's impact is calculated from approved links; before any work is planned, every layer's agent assesses it — including layers with no detected impact — and a person accepts it (`sdem events validate | assess | show | accept`; skill `sdem-impact-validation`). A missing path is not proof of no impact. `sdem work plan` refuses until a person has accepted and authorised.
6. **Requirements and risk are evidence, not opinion.** `sdem requirements evaluate` and each change event's analysis say which confirmed requirements a change touches, which are breached, which are not shown to hold, and the risk findings — never with invented likelihoods, losses or targets. No structural change is never no risk; no requirements recorded is never no requirements. Record measurements only with their evidence; only a person confirms a requirement or accepts a residual risk (skill `sdem-requirements-risk`).
7. **Inferred is not confirmed.** Records `sdem aid` adds carry an `inferred` mark with source, reasoning and confidence; treat them as suggestions until a person confirms them.
8. **Real data stays in the organisation.** Workspaces hold real, private architecture: do not send it anywhere except through the AI service the organisation has approved. Use made-up data for experiments.
9. **When unsure, say so** and name the command that would settle it.

## The usual workflow

| Step | Command (add `--json`) |
|---|---|
| **before writing records**: the kinds, fields, allowed values and links | `sdem types <A1…A4 or a type> --workspace <dir> --json` — never guess a field or a value; `sdem types requirement` and `sdem types change-set` give those formats |
| the BIAN operations a process uses (its `invokes`) | `sdem bian search <words> --json` → the `SO-…` ids, exactly as `sdem aid` writes them — never invent one |
| check the data | `sdem check --workspace <dir>` |
| fill gaps (inferred, marked) | `sdem aid --workspace <dir> --person <person> --dry-run`, then without `--dry-run` when the person agrees |
| propose links between layers | `sdem link --workspace <dir> --out <dir>/links` → each proposal's `mapping_id` |
| a person approves one | `sdem approve <mapping_id> --proposals <dir>/links/proposals.json --workspace <dir> --reviewer <person> --evidence <kind:ref>` |
| build the knowledge graph | `sdem build --workspace <dir> --out <dir>/graph` |
| what depends on what | `sdem trace <id or A1…A4> --direction down|up|both --graph <dir>/graph` |
| what a change affects | `sdem impact <id> --change modify|rehost|replace|retire --graph <dir>/graph` (its `coverage` says what the engine could and could not see) |
| what a planned change does to the requirements | `sdem requirements evaluate --workspace <dir> --record <id> --change <kind> --proposed <new id>` |
| the change events, and which are still open | `sdem events --workspace <dir> --open` (also `sdem events list …`) |
| a change event's impact, validated by every layer | `sdem events validate <CE-id>` → each layer: `sdem events assess <CE-id> --layer <A1…A4> …` → `sdem events show <CE-id>` → a person accepts: `sdem events accept <CE-id> …` → a person authorises: `sdem events authorise <CE-id> …` → `sdem work plan --event <CE-id>` |
| why something exists | `sdem explain <id> --proposals <file>` |

## More

- A workspace with `sdem-profile.json` has the organisation's own types, attributes, rules and names on top of SDEM's — read them with `sdem profile show --workspace <dir> --json`; `sdem check` enforces them. A profile adds; it never changes SDEM's core — propose a core change to the SDEM owner instead. A profile may add **layers** above A1 or below A4 (`sdem profile show` lists them); each has its own agent, `sdem-layer-<code>`, held to that layer like the A1–A4 agents.
- Skills (step-by-step know-how, the same files for every agent): `sdem-new-design` (a new design from a request — start here), `sdem-records`, `sdem-trace-impact`, `sdem-impact-validation`, `sdem-requirements-risk`, `sdem-approve-links`, `sdem-change-sets`, `sdem-onboard-designs` — in this repository's skills folder for your agent (`.claude/skills/`, `.agents/skills/` or `.github/skills/`).
- The commands in full: `docs/sdem-workbench-user-guide.md` §7. What an agent gets from the CLI: `docs/design/sdem-agent-cli-spec.md`. The controls: `docs/reference/controls-register.md`.
