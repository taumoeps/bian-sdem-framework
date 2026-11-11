# SDEM's command line, built for agents

> **Status: built (AF-01…AF-06 in v0.9.12; AF-07…AF-11 in v0.9.13)** — what every `sdem` command gives an AI agent (GitHub Copilot, Claude Code, OpenAI Codex, Gemini CLI — any agent that runs commands), so it can drive SDEM reliably without reading prose. Owner's decisions, 2026-10-31; AF-07…AF-11 follow the [readiness assessment](../evidence/agent-cli-readiness.md). Code: `sdem/agent.py`, `sdem/errors.py`, `sdem/files.py` (the ledger), `sdem/copilot.py` (the installer); tests: `tests/test_agent.py`, `tests/test_agent_eval.py`.

SDEM is an **agent-friendly command line**: it contains no AI itself — the same input always gives the same output — and an agent can run every step. Decisions on record (approve, load, start a workspace, confirm or reject an inferred record) still take a person's own name (CTL-21); an agent can propose, check, preview and explain, never decide.

## What an agent gets

| Id | Requirement | Verified by |
|---|---|---|
| AF-01 | **`--json` on every command.** The result is one JSON object on stdout (AF-08), carrying `"sdem": {"version", "command"}` first, so an agent knows what produced it. Notes (`baseline:`, `WARN:`, `NOTE:`) stay on stderr; a `WARN` line is also given under `"warnings"`. | tests |
| AF-02 | **Small by default.** `sdem dashboard --json` and `sdem home --json` give a summary (about 9 KB and 13 KB, down from 313 KB and 254 KB); `--full` gives everything. `--limit N` with `--json` cuts every list to N items and lists what was cut under `"truncated"`. | tests |
| AF-03 | **Every workflow command has JSON of its own** — including `link` (the proposals weakest first, with a `next` step), `build` (errors in the result), `baseline`, `aid confirm`/`reject`, `bian inference`. A command without (maintainers' tools: `model …`, `transform rules`, `bian pack`) is wrapped: `{"ok", "exit", "output": [its lines], "wrote": [files]}`. | tests |
| AF-04 | **`--dry-run` on every command.** A command with its own dry run uses it; any other runs with every file write, folder made or file removed caught and listed under `"would_write"` — only the temporary files the command makes itself are written. | tests: the workspace is byte-for-byte unchanged |
| AF-05 | **Failures are JSON too:** `{"sdem": …, "error": {"code", "exit", "message", "hint", "details"}}`. Codes: `usage`, `not_found`, `invalid_input`, `needs_person`, `exists`, `refused`, `input`, `internal`. The code comes from where the error happened (`sdem/errors.py`: a missing file is `not_found`, a file that is not JSON `invalid_input`, an unknown command `usage`); older error messages are classified by a pattern table. **Every error has a hint**: the command's own advice, else the usual next step (e.g. *`sdem query --graph <dir> --json` lists the record ids*). Exit codes unchanged: 0 OK, 1 refused by a check, 2 usage or input error, 3 internal error. | tests |
| AF-06 | **`sdem commands --json`** lists every command and subcommand: what it does, an example, its positionals and options (with choices and which are required), and whether its JSON and dry run are its own or given by `sdem`; plus the exit codes, error codes and the rule that decisions need a person. | tests |

| AF-07 | **Edits made outside `sdem` are noticed.** Every SDEM write to a workspace's layer files or registry is noted in `sdem-ledger.json` (file, checksum, which command, when). `sdem check` lists any file changed since under `unrecorded_edits` (a note — a person may edit by hand); `sdem check --require-recorded` fails on it (for CI where agents write files). Only a person accepts such an edit: `sdem change adopt` (an agent's name is refused). A workspace started before the ledger has none: nothing is reported until SDEM next writes. | tests |
| AF-08 | **Every result is an object.** A command whose result is a list (`query`, a whole-layer `trace`, `review`, `approve`, `explain`) answers `{"sdem": …, "count", "items"}`. Proposals and approvals are identified by `mapping_id` everywhere. | tests |
| AF-09 | **One set of instructions for every agent.** `sdem agents install` writes `AGENTS.md` (read by Codex, and by Gemini CLI through `.gemini/settings.json`), `CLAUDE.md` (one line: `@AGENTS.md`, for Claude Code), SDEM's one set of skills into `.claude/skills/` and `.agents/skills/`, and Copilot's own files (`sdem copilot install`). Doc links are pinned to the installed version; a file the team changed is kept (`--force` replaces it) — for a kept `.gemini/settings.json` it says what to add. | tests |
| AF-10 | **Runs on Windows too:** output is UTF-8 on every console; CI runs the suite on Windows. | CI |
| AF-11 | **The real-agent evaluation is the same for every platform:** `scripts/agent_eval.py prepare <dir>` sets up made-up data, the agent files and seven tasks (`TASKS.md`); after the agent has worked, `grade <dir>` checks the files — one approval, by the person who asked; the A3 change through a change set; the A4 change refused; no edit outside `sdem`. A careless agent's work fails it (tested). | tests; [evidence](../evidence/agent-cli-readiness.md) |
| AG-S01 | **Agents know when to use every command.** Each command and subcommand except the owner's `sdem model …` is named in `AGENTS.md` or a skill — the generated `sdem-scenarios` skill covers every job end to end; a command no instruction names fails the test. `AGENTS.md` has a *Which skill for which job* index. | `test_every_command_is_named_for_agents` |
| AG-S02 | **One source for people and agents:** the skill `sdem-scenarios` is generated from `docs/sdem-scenarios.md` by `sdem model regenerate` (`sdem/scenarioskill.py`) into every agent's skills folder and shipped by `sdem agents install`; `sdem model check` fails when it is stale. Links to SDEM's docs, which are not in an agent's repository, are written as plain references. | `test_the_scenarios_skill_is_generated_and_installed` |
| AG-S03 | **One command's details on request:** `sdem commands <command> [--json]` (e.g. `sdem commands "events assess" --json`) gives that command's entry and its subcommands — about 4 KB instead of about 130 KB for all; a mistyped name gets the closest matches. Agents fetch a command's options this way before running it, never from memory. | `test_one_command_on_request` |

## Why no MCP

Every target platform runs shell commands, and `sdem commands --json` already tells an agent what it can run. An MCP server would add a second interface to secure and keep in step with the CLI, for no capability the CLI lacks — and the organisation prohibits MCP in Copilot. Revisit only if an agent platform that cannot run commands is needed.

## Not changed

- Output shapes: existing JSON keeps its keys; the `"sdem"` marker is added. Since AF-08 a list result is wrapped as `{"count", "items"}` — the one change that affects existing scripts (v0.9.13).
- Without `--json`, `--dry-run` or `--limit`, every command behaves exactly as before.

## Sources

The conventions follow the public *Command Line Interface Guidelines* (clig.dev): machine-readable output with `--json`, results on stdout and messages on stderr, `--dry-run` for commands that change things, no prompts. **Confidence: medium** — the guidelines were not re-read for this change; the requirements above are measured by the test.
