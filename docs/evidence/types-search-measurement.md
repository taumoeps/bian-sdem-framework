# Measurement — `sdem types` and `sdem bian search` (2026-11-02)

> **Status: done.** Decides whether SDEM 0.16.0 improves an agent's ability to create a new design (owner's criterion: build only if it improves both users and agents). The user side is measured separately by a person (a 15-minute trial).

## Method

Three independent agents (fresh, no knowledge of SDEM's code or of this work) were given the same request — *"Create a new SDEM design for a new general ledger system: the full A1 business design — capabilities, a value stream with its stages, processes and activities, roles and actors, business objects, the business service, and business requirements (functional and non-functional, the non-functional ones measurable in the requirements registry). Then let SDEM infer the other layers."* — each in its own repository set up with `sdem agents install` and an empty workspace. Every `sdem` call went through a recorder that logged the command, its exit code and output, and kept a copy of every file submitted. The figures below are counted from those logs and the files left behind — not from the agents' reports. Run first on SDEM 0.15.0 (baseline), then on the 0.16.0 code with the updated agent instructions (after). Synthetic content only.

## Results

| | Baseline 1 | 2 | 3 | After 1 | 2 | 3 |
|---|---|---|---|---|---|---|
| Change sets and requirements submitted (incl. dry runs) | 13 | 10 | 12 | 7 | 6 | 7 |
| **…refused by SDEM** | **7** | **3** | **5** | **0** | **0** | **0** |
| **Distinct wrong fields, values or links submitted** | **4** | **4** | **11** | **0** | **0** | **0** |
| BIAN operation ids invented | 0 | 0 | 0 | 0 | 0 | 0 |
| Lookups (help, discovery; incl. `sdem types` / `bian search`) | 20 | 21 | 21 | 32 (24) | 25 (16) | 20 (10) |
| Agent tool calls (all tools) | 35 | 34 | 44 | 26 | 22 | 25 |
| Minutes | 4.9 | 4.2 | 6.6 | 4.5 | 4.1 | 4.6 |
| A1 records in the finished design | 45 | 34 | 55 | 53 | 49 | 52 |
| `sdem check` on the finished design | ok | ok | ok | ok | ok | ok |
| A person's decision taken by the agent | 0 | 0 | 0 | 0 | 0 | 0 |

The baseline's wrong submissions were all fields, allowed values or links no command listed (e.g. `requirement_kind: functional`, `frequency: monthly and quarterly`, a capability *realising* a stage); the agents found the right ones by submitting wrong values to read the error messages. After: every agent asked `sdem types` first and took its BIAN operation ids from `sdem bian search`; nothing was refused.

## Against the pass mark

| Criterion | Result |
|---|---|
| At least half as many refused submissions | **met** — 15 → 0 |
| No wrong field or value reaching a change set | **met** — 19 distinct → 0 |
| Fewer lookups | **not met as worded** — lookups rose (62 → 77), because the agents now ask `sdem types` and `sdem bian search` instead of probing with failed submissions; total tool calls fell by about a third (113 → 73) |

## Found by the measurement and fixed

- `sdem commands --json` showed `sdem link` with a required `engine` argument that `sdem link` fills in itself — removed; `--baseline` listed.
- `sdem bian search` showed only the operations matching the words — `--all-operations` lists every operation of each domain found.

## Follow-up — the `sdem-new-design` skill (v0.16.1)

The same request and set-up, three fresh agents each time, with the new-design skill and prompt installed.

| | 0.16.0, no skill | First skill | **Revised skill (shipped)** |
|---|---|---|---|
| Submissions refused | 0 · 0 · 0 | 2 · 1 · 1 | **0 · 0 · 0** |
| Distinct wrong fields or values | 0 · 0 · 0 | 1 · 0 · 0 | **0 · 0 · 0** |
| BIAN service domains inferred | 4 · 3 · 3 | 10 · 10 · 10 | **3 · 3 · 3** — exactly the ones the agent chose |
| Processes and activities without `invokes` | 0 · 0 · 0 | 6 · 2 · 2 | **0 · 0 · 0** |
| Agent tool calls | 26 · 22 · 25 | 45 · 34 · 27 | **24 · 18 · 20** |
| A1 records in the design | 53 · 49 · 52 | 55 · 55 · 56 | 60 · 58 · 56 |
| Review list for the architect | varied | yes | yes, the same structure in all three |

**The first version failed** and was not shipped: it stressed `invokes` for processes, and agents left some activities without it; AID then matched those activities to BIAN by name, and one common word ("account") brought in seven unrelated service domains — about 500 inferred records — in every run. **The revision** requires `invokes` on every process and activity, says why, has the agent compare `sdem aid --dry-run`'s service domains with the ones it chose before running it, and tells it to read each type in full (`sdem types <type>`); `sdem types requirement` now states the id rule (`REQ-…`).

**Open, for the owner:** AID's name match (step S06) accepts one common shared word. The skill now keeps agents from triggering it; tightening the rule itself would change inference results.
