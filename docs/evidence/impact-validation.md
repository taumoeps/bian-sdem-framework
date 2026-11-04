# Four-layer impact validation — what was built and how it was tested

> **Status: released in v0.10.0 (2026-11-01).** Made-up data only. Requirements: [agent platform spec §11](../design/sdem-agent-platform-spec.md#11-four-layer-impact-validation-owners-requirement-2026-11-01) (AG-V01…V10).

## The problem (found in real GitHub Copilot testing of v0.9.14)

On the synthetic payments workspace, the A4 agent rehosted the production Kubernetes cluster (`INF-K8S-PAY-PROD` → `INF-K8S-PAY-PROD2`; change set CS-001, change event CE-001). The deterministic engine classified APP-PAY-HUB and CMP-PAY-EXEC (A3) as *design change required* and A2 and A1 as *no impact*. The orchestrator then planned work from that classification alone. No layer agent checked it — least of all the layers with *no impact* — though a missing or unapproved link can hide an impact.

## What changed

| | Before | Now |
|---|---|---|
| The calculation | classifications and paths | the same classifications and rules, plus per-layer **coverage** — reached or not, the rule behind each record, links not followed, records with no approved link, evidence complete or not — and the **basis** (rules version, dataset and registry checksums, approved links). *No impact detected* is never *confirmed* |
| Before work is planned | nothing | **every layer's agent assesses** its layer — including the no-impact layers — and **a person accepts** the final assessment and authorises implementation |
| `sdem work plan` | planned from the calculation | **refuses** until authorised; plans from the **accepted** assessment, including design changes a specialist found that the engine did not reach |
| Each follow-on change event | planned directly | validated again |
| The orchestrator | planned, then delegated | **two phases**: impact assurance (all four layers assess, read-only; it stops for the architect), then implementation |

New commands — extending `sdem events`, not a new command group:

| Command | Who | Does |
|---|---|---|
| `sdem events validate <CE>` | orchestrator or a person | opens the validation, all four layers |
| `sdem events pending [--layer]` | a layer agent | what waits for its assessment |
| `sdem events assess <CE> --layer … --status …` | that layer's agent | `impact_confirmed`, `no_impact_confirmed` (evidence required; uncertainty required where links are incomplete), `impact_disputed` (evidence and a recommendation; records for a design change), `further_investigation_required` |
| `sdem events show <CE>` | anyone | calculated against assessed, per layer; what still stops acceptance |
| `sdem events accept <CE> … [--authorise]` · `sdem events authorise <CE>` | **a person only** | the final assessment, with disputed layers decided and explained; authorising implementation |

Data: one validation record per event in `<workspace>/coordination/validations/IV-….json` (schema `coordination.schema.json#/$defs/validation`), append-only, every step with agent and person. Existing records are untouched; events from v0.9.14 and earlier stay readable — validating one recomputes its coverage from the current graph and says so; nothing is accepted for it unless a person does it now. Code: `sdem/validation.py`, `sdem/agents.py`, `sdem/graph.py` (`impact_coverage`).

## The rehost, end to end

[Transcript](impact-validation/transcript.txt) — every command and its output, on a fresh copy of the payments example:

1. The A4 agent's change set lands; CE-001 records A3 *design change*, A1/A2 *no impact by rule* — and **evidence incomplete** in every layer (records with no approved link).
2. `sdem work plan` **refuses** (AG-V08): no validation yet.
3. The orchestrator opens the validation; four layers pending.
4. The A2 agent's *no impact* without evidence is **refused** ("a missing path is not proof of no impact"); the A3 agent assessing A2 is **refused** (CTL-19).
5. A4 and A3 confirm the impact; A2 confirms none with evidence and states its uncertainty; **A1 asks for further investigation** (10 A1 records without links; the cutover may affect the payment process).
6. Acceptance without deciding A1 is **refused**; acceptance by the orchestrator is **refused** (CTL-21).
7. The architect accepts — A1 as *review required*, with the reason — and authorises. Only now does `sdem work plan` create the two A3 work items, and it lists A1 for the architect's review.
8. `sdem check` passes, the validation record included.

## Tests

| Criterion | Test (`tests/test_impact_validation.py`) | Result |
|---|---|---|
| T1 the rehost's calculation: A3 design change, A1/A2 no detected impact; coverage, rules, basis | `test_t1_the_calculation_and_its_coverage` | pass |
| T2 the orchestrator requests validation from all four layers | `test_t2_the_orchestrator_opens_all_four_layers` | pass |
| T3 each specialist assesses independently | `test_t3_each_specialist_assesses_its_own_layer` | pass |
| T4 A2 challenges *no impact* with evidence → an A2 work item from the accepted assessment | `test_t4_a_specialist_disputes_no_impact_with_evidence` | pass |
| T5 a missing link is uncertainty, not confirmation | `test_t5_missing_links_are_uncertainty_not_confirmation` | pass |
| T6 no implementation while assessments are missing, disputed or not accepted and authorised | `test_t6_no_implementation_before_acceptance_and_authorisation` | pass |
| T7 agents cannot accept, authorise or assess another layer | `test_t7_agents_cannot_accept_or_act_as_a_person` | pass |
| T8 after acceptance, the layer agent's change set lands | `test_t8_after_acceptance_the_layer_agents_change_their_layer` | pass |
| T9 the follow-on event needs its own validation | `test_t9_a_follow_on_event_is_validated_again` | pass |
| T10 a v0.9.14 event stays readable; validating it fabricates nothing | `test_t10_events_from_before_validation_stay_readable` | pass |
| T11 `sdem check` reads validation records and flags tampering | `test_t11_check_reads_validation_records_and_flags_tampering` | pass |
| T12 the CLI shows everything behind each final classification | `test_t12_the_cli_shows_everything_behind_the_final_classification` | pass |
| The real-agent scenario's grader checks task 8 (validation before work) | `tests/test_agent_eval.py` | pass |
| Use-case example 3 (the agent platform's sealed criteria), now validating before each plan | `tests/test_use_case_example_3.py` | 8 of 8 criteria; controls 19 of 19 |
| **The full suite** — with and without an install | `python -m unittest discover -s tests` | **all pass** |

## Known limitations

- **Live Copilot behaviour is not verified** by these tests: whether the orchestrator really calls all four layer agents, stops for the architect and never plans first. `sdem` enforces the outcome — it refuses to plan, refuses an agent's acceptance — but the agents' behaviour needs a real run (below).
- **SDEM cannot tell who typed a person's name.** An agent could run `sdem events accept --person <a person>`; the defence is the reviewed pull request and branch protection, as for approvals.
- **Coverage's *records with no approved link* is layer-wide**, not limited to the changed path; it flags where impact could hide, not where it does.
- **A layer's assessment is the agent's judgement**: SDEM checks that it is complete (status, evidence, reasoning) and from the right agent, not that it is right.

## Retest in GitHub Copilot

1. `sdem agents install` in your test folder (or `sdem copilot install`) — the agents, prompts and the new skill `sdem-impact-validation`.
2. Run spike steps S3 and **S12** ([checklist](../sdem-agent-platform-spike.md)): the A4 agent rehosts; then `/sdem-process-events <workspace> <your name>`. Expect `sdem events validate`, **four** `sdem events assess` calls (one per layer agent, the no-impact layers included), `sdem events show` — and a stop for your decision. Then run `sdem events accept CE-001 … --authorise` yourself and ask it to continue.
3. Or, in a checkout: `python scripts/agent_eval.py prepare <folder>`, give the agent `TASKS.md` (task 8 is this), then `python scripts/agent_eval.py grade <folder>`.

