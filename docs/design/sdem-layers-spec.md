# SDEM layer registry — specification

> **Status: built (v0.13.0, 2026-11-02).** Owner's request (2026-11-02): design teams add layers "up and down stream" of SDEM's four, and which layers differs from team to team. Code: `sdem/layers.py` (the registry), `sdem/profile.py` (declaring layers); tests `tests/test_layers.py`; synthetic example `examples/profiles/strategy-and-sites-team.json`. Builds on organisation profiles ([`sdem-profile-spec.md`](sdem-profile-spec.md)).

## The idea, plainly

SDEM's four layers — A1 Business, A2 Service Domain (BIAN), A3 Application, A4 Technology — are the **core every team shares**; that is what lets traces, impact and dashboards join up across teams. A team's profile may add **its own layers at either end**: above A1 (e.g. strategy: goals and outcomes) or below A4 (e.g. physical: sites and equipment). Each added layer has its own record file, its own types, and link types to the layer next to it. From then on every SDEM command works across all the workspace's layers — a trace runs from a strategy outcome down to a data centre, and retiring the data centre shows its impact all the way up.

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| LR-01 | **Layers at the ends only.** A profile's `layers` each have a `code` (e.g. `A0`, `A5` — never A1–A4), a `name`, a `position` (`above` A1 or `below` A4; on one side, listed nearest the core first) and a `file`. A layer cannot be inserted between core layers or redefine one; `sdem profile check` refuses it. Each added layer declares at least one type (`<ORG>.<code>.<Name>`); a type of an added layer may stand alone (no `extends`) or extend another type of that layer. | `test_a_profile_cannot_put_a_layer_between_or_leave_it_unlinked` |
| LR-02 | **One registry, read everywhere.** The layers of a workspace — the core four plus its profile's, in order — come from `sdem/layers.py`; every command that works layer by layer reads them there. The profile is activated from `--workspace` or `--graph` before a command's options are read, so an added layer is a valid `--layer`. | all tests below |
| LR-03 | **Files on record.** `sdem new --profile FILE` starts a workspace with every layer, the profile kept as `sdem-profile.json` (its base still found). `sdem profile adopt --workspace … --person … --reason …` puts an existing workspace under its profile: each added layer's empty file is written and recorded in the ledger, `workspace.json` notes the profile, and an `adopt_profile` decision is recorded (attributed). Existing records are never changed. | `test_adopting_a_profile_adds_its_layers_on_record`, `test_a_new_workspace_starts_with_every_layer` |
| LR-04 | **Trace and impact across every layer.** Layer order is the registry's; `sdem trace <id>` and `sdem trace <layer>` follow approved links through added layers; impact classification counts steps along links (schema/impact-rules.json), so it needs no rule per layer. | `test_trace_runs_through_every_layer`, `test_impact_reaches_every_layer` |
| LR-05 | **Graph store**: one graph file per layer (`<code>.graph.json` for an added layer); the store keeps the profile it was built with. | `test_trace_runs_through_every_layer` |
| LR-06 | **Link types to the neighbour.** A profile's `link_types` join a type of one layer to a type of the layer directly below it, at least one of them an added layer, each with the evidence it requires. They join SDEM's link-type registry while the profile is active (authority `organisation_profile`), so `sdem connect` states such links with the same checks as SDEM's nine. Links between two core layers stay SDEM's nine; an added layer with no link type is refused. | `test_a_profile_cannot_put_a_layer_between_…` and the class set-up |
| LR-07 | **An agent per layer.** An added layer's agent is `sdem-layer-<code>`; CTL-19 holds it to its own layer for change sets and assessments, as for the core agents. The four-layer impact validation covers every layer. `sdem agents install --workspace DIR` writes a Copilot agent file for each added layer and adds it to the orchestrator's agents. | `test_each_layer_has_its_own_agent_and_validation`, `test_agents_install_writes_an_agent_per_profile_layer` |
| LR-08 | **Requirements** can sit on an added layer (`owner_layer`, `subject`). | `test_a_requirement_can_sit_on_a_profile_layer` |
| LR-09 | **Names**: an added layer's name shows in traces, impact, the dashboard and the graph view. | `test_trace_runs_through_every_layer` |
| LR-10 | **Nothing changes without a profile**: a workspace with no added layers has exactly the four, as before. | `test_a_workspace_without_layers_is_unchanged` |

## What stays on the core four

- **AID** (Architecture Inference Design) infers from BIAN through A1–A4; it does not infer into added layers.
- **Design onboarding** (`sdem transform`, `sdem load`) recognises A1–A4 records in past designs.
- **The rules engine** proposes links only for SDEM's nine link types; links to and from an added layer are stated by a person (`sdem connect`, with evidence).
- **SDEM's own reference documents** (the metamodel guide, catalogue, diagrams) describe SDEM's metamodel; a workspace's profile is shown by `sdem profile show`.

## Synthetic example

`examples/profiles/strategy-and-sites-team.json` extends the bank base profile with **A0 Strategy** (Goal, Outcome — ArchiMate 3.2 Motivation and Strategy) and **A5 Physical** (Facility, Equipment — ArchiMate 3.2 Physical); link types `BANK.A0.Outcome REALIZED_BY A1.BusinessCapability` (evidence `strategy_document`) and `A4.InfrastructureComponent HOUSED_IN BANK.A5.Facility` (evidence `site_register`).
