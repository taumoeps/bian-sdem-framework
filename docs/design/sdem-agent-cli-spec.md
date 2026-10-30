# SDEM's command line, built for agents

> **Status: built (v0.9.12, unreleased)** — what every `sdem` command gives an AI agent (Copilot, Claude Code, any agent that runs commands), so it can drive SDEM reliably without reading prose. Owner's decision, 2026-10-31. Code: `sdem/agent.py`; test: `tests/test_agent.py`.

SDEM is an **agent-friendly command line**: it contains no AI itself — the same input always gives the same output — and an agent can run every step. Decisions on record (approve, load, start a workspace, confirm or reject an inferred record) still take a person's own name (CTL-21); an agent can propose, check, preview and explain, never decide.

## What an agent gets

| Id | Requirement | Verified by |
|---|---|---|
| AF-01 | **`--json` on every command.** The result is JSON on stdout. An object carries `"sdem": {"version", "command"}` first, so an agent knows what produced it. Notes (`baseline:`, `WARN:`, `NOTE:`) stay on stderr; a `WARN` line is also given under `"warnings"`. | tests |
| AF-02 | **Small by default.** `sdem dashboard --json` and `sdem home --json` give a summary (about 9 KB and 13 KB, down from 313 KB and 254 KB); `--full` gives everything. `--limit N` with `--json` cuts every list to N items and lists what was cut under `"truncated"`. | tests |
| AF-03 | **Every workflow command has JSON of its own** — including `link` (the proposals weakest first, with a `next` step), `build` (errors in the result), `baseline`, `aid confirm`/`reject`, `bian inference`. A command without (maintainers' tools: `model …`, `transform rules`, `bian pack`) is wrapped: `{"ok", "exit", "output": [its lines], "wrote": [files]}`. | tests |
| AF-04 | **`--dry-run` on every command.** A command with its own dry run uses it; any other runs with every file write, folder made or file removed caught and listed under `"would_write"` — only the temporary files the command makes itself are written. | tests: the workspace is byte-for-byte unchanged |
| AF-05 | **Failures are JSON too:** `{"sdem": …, "error": {"code", "exit", "message", "hint", "details"}}`. Codes: `usage`, `not_found`, `invalid_input`, `needs_person`, `exists`, `refused`, `input`, `internal`. The hint is the command's own advice when it gives one, else the usual next step (e.g. *`sdem query --graph <dir> --json` lists the record ids*). Exit codes unchanged: 0 OK, 1 refused by a check, 2 usage or input error, 3 internal error. | tests |
| AF-06 | **`sdem commands --json`** lists every command and subcommand: what it does, an example, its positionals and options (with choices and which are required), and whether its JSON and dry run are its own or given by `sdem`; plus the exit codes, error codes and the rule that decisions need a person. | tests |

## Not changed

- Output shapes: existing JSON keeps its keys; the `"sdem"` marker is added to objects. A result that is a list (a whole-layer `trace`, `review`) stays a list; `--limit` and dry-run notes for it go to stderr.
- Without `--json`, `--dry-run` or `--limit`, every command behaves exactly as before.

## Sources

The conventions follow the public *Command Line Interface Guidelines* (clig.dev): machine-readable output with `--json`, results on stdout and messages on stderr, `--dry-run` for commands that change things, no prompts. **Confidence: medium** — the guidelines were not re-read for this change; the requirements above are measured by the test.
