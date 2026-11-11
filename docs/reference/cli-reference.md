# SDEM CLI reference

> **Generated** from the code by `sdem model regenerate` (`sdem/clidoc.py`), from the same catalogue as `sdem commands --json`; `sdem model check` fails in CI when it is stale — **do not edit by hand**. Each command's `--help` has the same options and a worked example. For *when* to use which command, in order, see the [scenarios](../sdem-scenarios.md); for what each does to your data, the [user guide](../sdem-workbench-user-guide.md#7-command-reference).

116 commands and subcommands.

## Every command takes

| Option | What it does |
|---|---|
| `--json` | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--limit N` | with --json: every list cut to N items, listed under "truncated" |
| `--dry-run` | nothing written; what would be written is listed under "would_write" |

**Exit codes:** `0` ok · `1` refused by a check · `2` usage or input error · `3` internal error. **Error codes** (with `--json`, in `{"error": {"code", …}}`): `exists`, `input`, `internal`, `invalid_input`, `needs_person`, `not_found`, `refused`, `usage`.

**A person's decision:** approve, load, new, aid confirm/reject and other recorded decisions take --person/--reviewer: a person's own name, never an agent's (CTL-21). Commands below marked 👤 take such a name.

## Index

### J9 · Start and onboard

*start a workspace or an organisation, bring in designs, upgrade*

| Command | What it does |
|---|---|
| [`sdem bian`](#cmd-bian) | the BIAN (A2) layer: from the base BIAN that ships with SDEM, your own BIAN pack, or BIAN's files |
| [`sdem bian custom`](#cmd-bian-custom) 👤 | narrow one workspace's BIAN layer to the service domains it uses |
| [`sdem bian impact`](#cmd-bian-impact) | before an update: what in each workspace points at BIAN records the new layer drops, renames or changes |
| [`sdem bian import`](#cmd-bian-import) | write an A2 dataset for the service domains you choose |
| [`sdem bian inference`](#cmd-bian-inference) | SDEM's record of inferred BIAN asset types and functional patterns: list, show, accept, challenge, change or reject an entry. Every change names a person and a  |
| [`sdem bian inference accept`](#cmd-bian-inference-accept) 👤 | accept an entry |
| [`sdem bian inference challenge`](#cmd-bian-inference-challenge) 👤 | question an entry |
| [`sdem bian inference change`](#cmd-bian-inference-change) 👤 | give new values |
| [`sdem bian inference list`](#cmd-bian-inference-list) | the entries, with values, confidence and status |
| [`sdem bian inference reject`](#cmd-bian-inference-reject) 👤 | reject an entry |
| [`sdem bian inference show`](#cmd-bian-inference-show) | one entry: values, sources, reasoning, history |
| [`sdem bian list`](#cmd-bian-list) | the service domains in the base, a pack or a folder; writes nothing |
| [`sdem bian pack`](#cmd-bian-pack) | pack a folder of BIAN-format files into one file |
| [`sdem bian search`](#cmd-bian-search) | BIAN service domains and operations for plain words |
| [`sdem bian update`](#cmd-bian-update) 👤 | replace a workspace's BIAN layer with your shared one |
| [`sdem designs`](#cmd-designs) | design records and gap records: the pages onboarded designs came from, and what did not fit an entity |
| [`sdem load`](#cmd-load) 👤 | load reviewed candidate entities from sdem transform into a workspace |
| [`sdem new`](#cmd-new) 👤 | start a workspace: the four layers (A2 your BIAN layer) and an empty registry of connections |
| [`sdem releases`](#cmd-releases) | what each SDEM release changed: migrations, breaking changes, deprecations and the actions to take |
| [`sdem transform`](#cmd-transform) | transform past designs |
| [`sdem transform inspect`](#cmd-transform-inspect) | what is in the export and which rules read it |
| [`sdem transform rules`](#cmd-transform-rules) | write a copy of SDEM's transform rules to tune for your organisation's designs (then pass it with --rules) |
| [`sdem transform run`](#cmd-transform-run) | transform the export: write candidate datasets, extraction.json, design-index.json and extraction-report.md |
| [`sdem upgrade`](#cmd-upgrade) | before you switch SDEM versions: run the new version, installed side by side, against your workspaces |
| [`sdem upgrade check`](#cmd-upgrade-check) | what upgrading to this version means for your workspaces: migrations, profile, deprecations, agent files, actions |

### J1 · Check and specify

*check the data; the organisation's profile, standards and patterns*

| Command | What it does |
|---|---|
| [`sdem check`](#cmd-check) | check architecture datasets and registry against the metamodel |
| [`sdem comply`](#cmd-comply) | the organisation's standards and reference-architecture patterns over a workspace: per rule and record compliant, non-compliant, unresolved or under an exceptio |
| [`sdem pattern`](#cmd-pattern) | reference-architecture patterns as structures |
| [`sdem pattern draw`](#cmd-pattern-draw) | draw a pattern (PR-25) |
| [`sdem pattern extract`](#cmd-pattern-extract) | a diagram → a DRAFT pattern file and a report; nothing enters the profile until a person includes it (PR-30) |
| [`sdem profile`](#cmd-profile) | the organisation's design specification on top of SDEM's metamodel |
| [`sdem profile adopt`](#cmd-profile-adopt) 👤 | put the workspace under its sdem-profile.json: the layers it adds start empty, and the adoption is recorded |
| [`sdem profile check`](#cmd-profile-check) | check the workspace's profile (and the base it extends) against SDEM's metamodel |
| [`sdem profile example`](#cmd-profile-example) | write a synthetic bank base profile, team profiles that extend it (one adds layers), and a team profile with the bank's standards and secure API pattern |
| [`sdem profile show`](#cmd-profile-show) | the merged profile: every type, attribute, rule, link kind and name it adds |
| [`sdem types`](#cmd-types) | what you may write: each layer's kinds of record, their fields (type, required, allowed values) and allowed links; the requirement and change-set formats |
| [`sdem validate`](#cmd-validate) | validate a relationship document (registry or proposals) |

### J2 · Link the architectures

*propose links between the layers*

| Command | What it does |
|---|---|
| [`sdem link`](#cmd-link) | run the inference engine: propose links between the architectures, and show them weakest first for review (--no-review: just write them) |

### J3 · Review and approve

*a person decides on proposed links*

| Command | What it does |
|---|---|
| [`sdem approve`](#cmd-approve) 👤 | a person approves proposed links into the registry |
| [`sdem connect`](#cmd-connect) 👤 | a person states a connection the engine did not propose |
| [`sdem exception`](#cmd-exception) | a person's time-limited exception to one of the organisation's rules for named records |
| [`sdem exception grant`](#cmd-exception-grant) 👤 | record a person's exception |
| [`sdem exception list`](#cmd-exception-list) | the workspace's exceptions, active or expired |
| [`sdem governance`](#cmd-governance) | governed decisions |
| [`sdem governance verify`](#cmd-governance-verify) | every decision record: verified by a signed commit from its approver, or why not |
| [`sdem handback`](#cmd-handback) | what a workspace leaves open for a person |
| [`sdem review`](#cmd-review) | list proposed links for review, weakest first |

### J4 · Build the knowledge graph

*the graph store, queries and baselines*

| Command | What it does |
|---|---|
| [`sdem baseline`](#cmd-baseline) | freeze the current graph store under a name |
| [`sdem build`](#cmd-build) | check the inputs and write the graph store (knowledge graph) |
| [`sdem query`](#cmd-query) | find records in a graph store |

### J5 · Trace, impact and requirements

*what depends on what, what a change affects*

| Command | What it does |
|---|---|
| [`sdem impact`](#cmd-impact) | classify what a change to a record affects |
| [`sdem matrix`](#cmd-matrix) | business → BIAN → application → technology matrices from approved links |
| [`sdem requirements`](#cmd-requirements) | requirements and constraints the workspace must keep meeting, their measurements, and what a change does to them: in scope, satisfied, breached, not evaluable |
| [`sdem requirements check`](#cmd-requirements-check) | the registry against its schema and the workspace |
| [`sdem requirements confirm`](#cmd-requirements-confirm) 👤 | a person confirms proposed requirements |
| [`sdem requirements evaluate`](#cmd-requirements-evaluate) | what a change does to the requirements: in scope, satisfied, breached, not evaluable |
| [`sdem requirements list`](#cmd-requirements-list) | the requirements, with status and subject |
| [`sdem requirements measure`](#cmd-requirements-measure) 👤 | record measurements |
| [`sdem requirements propose`](#cmd-requirements-propose) 👤 | add requirements, or new versions, as proposed |
| [`sdem requirements retire`](#cmd-requirements-retire) 👤 | a person retires requirements |
| [`sdem requirements show`](#cmd-requirements-show) | one requirement: condition, evidence, history and its measurements |
| [`sdem requirements trace`](#cmd-requirements-trace) | a requirement through the layers: its subject and allocations, what they depend on and serve, and the requirements it derives from |
| [`sdem trace`](#cmd-trace) | trace what a record depends on (down) or what depends on it (up) |

### J6 · Infer with AID

*fill the gaps, confirm or reject*

| Command | What it does |
|---|---|
| [`sdem aid`](#cmd-aid) 👤 | Architecture Inference Design: fill a workspace's gaps |
| [`sdem aid check`](#cmd-aid-check) | — |
| [`sdem aid confirm`](#cmd-aid-confirm) 👤 | Confirm inferred records: you agree with them; the mark stays, with your name. |
| [`sdem aid gaps`](#cmd-aid-gaps) | — |
| [`sdem aid project`](#cmd-aid-project) | — |
| [`sdem aid reject`](#cmd-aid-reject) 👤 | Reject inferred records: removed with their links inside the layer, and remembered so they are not inferred again. |

### J7 · See it

*pages, diagrams, documents*

| Command | What it does |
|---|---|
| [`sdem dashboard`](#cmd-dashboard) | one read-only HTML dashboard for a workspace: health, attention, review, trace & impact, matrices, changes, AID, controls |
| [`sdem diagram`](#cmd-diagram) | ArchiMate diagrams of a workspace from SDEM's templates |
| [`sdem document`](#cmd-document) | a layer's design as a structured, readable document (Markdown or HTML), generated from the workspace |
| [`sdem document verify`](#cmd-document-verify) | Check a narrative an agent wrote from `sdem document --json` against the workspace (UX-D09…D11): every [ID] it cites is a record or an approved connection, ever |
| [`sdem home`](#cmd-home) | the main dashboard: the metamodel (entities, links inside and between architectures, engine rules), its picture, health, configuration |
| [`sdem view`](#cmd-view) | write the HTML picture of a graph store, optionally with a projection |
| [`sdem workbench`](#cmd-workbench) | the workbench for one workspace: one offline page |

### J8 · Explain

*why a record or link exists*

| Command | What it does |
|---|---|
| [`sdem explain`](#cmd-explain) | explain one element or link: why it exists, from what, how sure |

### AG · Agents and change

*change sets, events, work items, agent setup*

| Command | What it does |
|---|---|
| [`sdem agents`](#cmd-agents) | put SDEM's instructions and skills for AI agents into your workspace repository |
| [`sdem agents install`](#cmd-agents-install) | write AGENTS.md, CLAUDE.md, .claude/skills, .agents/skills, .gemini/settings.json and .github/ (Copilot) |
| [`sdem change`](#cmd-change) | agent platform: propose a change set to one layer |
| [`sdem change adopt`](#cmd-change-adopt) 👤 | record a person's direct edit of a layer as a change set (AG-S08) |
| [`sdem change diff`](#cmd-change-diff) | compare an incoming layer file with the workspace and write the change set it implies |
| [`sdem change propose`](#cmd-change-propose) 👤 | check and apply a change set to its layer; records the change event and its impact |
| [`sdem change revert`](#cmd-change-revert) 👤 | undo the latest change set of a layer |
| [`sdem change show`](#cmd-change-show) | a change set with its event and impact |
| [`sdem copilot`](#cmd-copilot) | put SDEM's Copilot instructions, agents, prompts and skills into your workspace repository, matching this SDEM version |
| [`sdem copilot install`](#cmd-copilot-install) | write .github/copilot-instructions.md, agents/, prompts/, skills/ into a repository |
| [`sdem events`](#cmd-events) | agent platform: change events, their impact and open work |
| [`sdem events accept`](#cmd-events-accept) 👤 | a person accepts the final impact assessment (and, with --authorise, authorises implementation) |
| [`sdem events analyse`](#cmd-events-analyse) 👤 | recompute the requirements evaluation and risk findings after new evidence, links or requirements (assessments made against other evidence become stale) |
| [`sdem events assess`](#cmd-events-assess) 👤 | a layer agent records its layer's assessment of the calculated impact |
| [`sdem events authorise`](#cmd-events-authorise) 👤 | a person authorises implementation of an accepted assessment |
| [`sdem events pending`](#cmd-events-pending) | layers still to assess |
| [`sdem events show`](#cmd-events-show) | the calculated impact, every assessment, and what still stops acceptance |
| [`sdem events validate`](#cmd-events-validate) 👤 | orchestrator or architect: open the impact validation of a change event |
| [`sdem work`](#cmd-work) | agent platform: plan, list and claim work items |
| [`sdem work block`](#cmd-work-block) 👤 | a work item cannot proceed |
| [`sdem work cancel`](#cmd-work-cancel) 👤 | drop a work item |
| [`sdem work claim`](#cmd-work-claim) 👤 | a layer agent takes a work item |
| [`sdem work list`](#cmd-work-list) | work items |
| [`sdem work plan`](#cmd-work-plan) 👤 | orchestrator: turn a change event's impact into work items |
| [`sdem work reopen`](#cmd-work-reopen) 👤 | return a work item to open |

### — · SDEM maintenance

*the owner's commands in SDEM's own repository*

| Command | What it does |
|---|---|
| [`sdem diff`](#cmd-diff) | compare two versions of a relationship document |
| [`sdem migrate`](#cmd-migrate) 👤 | move a workspace to the current metamodel version |
| [`sdem model`](#cmd-model) | maintainers: regenerate and check generated files, acceptance, evaluation, examples |
| [`sdem model accept`](#cmd-model-accept) | engine acceptance cases |
| [`sdem model baseline-pack`](#cmd-model-baseline-pack) | write the metamodel baseline review pack |
| [`sdem model calibrate`](#cmd-model-calibrate) | how often each confidence band and evidence class is right on the acceptance cases (AID-E03) |
| [`sdem model check`](#cmd-model-check) | fail if any generated file differs from a fresh generation |
| [`sdem model eval`](#cmd-model-eval) | score proposals against approved links |
| [`sdem model examples`](#cmd-model-examples) | re-run use-case examples 1 and 2 (evidence packs and results) |
| [`sdem model freeze`](#cmd-model-freeze) | record the core after an approved, versioned change |
| [`sdem model regenerate`](#cmd-model-regenerate) | regenerate every generated document, diagram and schema |
| [`sdem model stability`](#cmd-model-stability) | the core against its last freeze (as CI) |
| [`sdem model status`](#cmd-model-status) | every part of SDEM's metamodel not yet settled, with its source and what would settle it |
| [`sdem model usage`](#cmd-model-usage) | what the given workspaces use, and what no workspace uses |

## Commands

### sdem agents

<a id="cmd-agents"></a>

put SDEM's instructions and skills for AI agents into your workspace repository — one AGENTS.md for Codex, Claude Code, Gemini CLI and Copilot, the same skills in each one's folder

Subcommands: [`sdem agents install`](#cmd-agents-install)

### sdem agents install

<a id="cmd-agents-install"></a>

write AGENTS.md, CLAUDE.md, .claude/skills, .agents/skills, .gemini/settings.json and .github/ (Copilot)

```
sdem agents install [--to TO] [--platform {copilot,claude,codex,gemini} …] [--workspace WORKSPACE] [--dry-run] [--force]
```

*JSON: native · dry run: native*

| Argument | Required | What it is |
|---|---|---|
| `--to` |  | the repository (default: the current folder) |
| `--platform` {copilot, claude, codex, gemini} |  | which agents (default: all four) |
| `--workspace` |  | also a layer agent for each layer this workspace's profile adds (repeatable) |
| `--dry-run` |  | show what would change; write nothing |
| `--force` |  | also replace files your team has changed since the last install |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem aid

<a id="cmd-aid"></a>

Architecture Inference Design: fill a workspace's gaps — inferred records marked with source, reasoning and confidence; confirm, reject (also project, check, gaps for file-based planning)

Subcommands: [`sdem aid check`](#cmd-aid-check) · [`sdem aid gaps`](#cmd-aid-gaps) · [`sdem aid project`](#cmd-aid-project)

```
sdem aid --workspace WORKSPACE --person PERSON [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--person` | yes | your name — a person |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem aid --workspace workspaces/payments --person jane.architect
```

### sdem aid check

<a id="cmd-aid-check"></a>

```
sdem aid check <projection> [--catalogue CATALOGUE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<projection>` | yes | — |
| `--catalogue` |  | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem aid confirm

<a id="cmd-aid-confirm"></a>

Confirm inferred records: you agree with them; the mark stays, with your name.

```
sdem aid confirm [<ids>] --workspace WORKSPACE --person PERSON [--all] [--reason REASON]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<ids>` |  | — |
| `--workspace` | yes | — |
| `--person` | yes | your name — a person |
| `--all` |  | every inferred record not yet confirmed |
| `--reason` |  | why — kept |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem aid gaps

<a id="cmd-aid-gaps"></a>

```
sdem aid gaps <projection> [--workspace WORKSPACE] [--actual ACTUAL …]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<projection>` | yes | — |
| `--workspace` |  | compare with a workspace's real layers and approved connections |
| `--actual` |  | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem aid project

<a id="cmd-aid-project"></a>

```
sdem aid project [--workspace WORKSPACE] [--have HAVE …] [--catalogue CATALOGUE] [--registry REGISTRY] [-o O]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | plan from a workspace: its business layer (and any applications and technology), its BIAN layer and its approved connections |
| `--have` |  | — |
| `--catalogue` |  | — |
| `--registry` |  | — |
| `-o`, `--out` |  | where the planned design goes (default with --workspace: <workspace>/plans/PLAN-nnn) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem aid reject

<a id="cmd-aid-reject"></a>

Reject inferred records: removed with their links inside the layer, and remembered so they are not inferred again.

```
sdem aid reject [<ids>] --workspace WORKSPACE --person PERSON [--all] --reason REASON
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<ids>` |  | — |
| `--workspace` | yes | — |
| `--person` | yes | your name — a person |
| `--all` |  | every inferred record not yet confirmed |
| `--reason` | yes | why — kept |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem approve

<a id="cmd-approve"></a>

a person approves proposed links into the registry — reviewer, date, required evidence, validated first

```
sdem approve <ids> --proposals PROPOSALS [--workspace WORKSPACE] [--registry REGISTRY] --reviewer REVIEWER [--evidence EVIDENCE] [--supersedes SUPERSEDES] [--id ID] [--bian-release BIAN_RELEASE] [--date DATE] [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<ids>` | yes | proposal id(s) from `sdem review` |
| `--proposals` | yes | — |
| `--workspace` |  | workspace folder (its mappings.json) |
| `--registry` |  | the registry, if not <workspace>/mappings.json |
| `--reviewer`, `--person` | yes | your name — a person (CTL-21); --person works too, as in the other commands |
| `--evidence` |  | the document that proves the link (repeatable) |
| `--supersedes` |  | the approved link this one replaces (it becomes superseded) |
| `--id` |  | the new link id (default: the next in the registry's style) |
| `--bian-release` |  | for a link to a BIAN element: the BIAN release it relies on (required by the registry rules) |
| `--date` |  | approval date (default today) |
| `--dry-run` |  | show the record; write nothing |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem approve P-RUN-001 --proposals work/links/proposals.json --workspace work/est --reviewer jane.architect --evidence deployment_design:PAY-REHOST#cutover
```

### sdem baseline

<a id="cmd-baseline"></a>

freeze the current graph store under a name

```
sdem baseline <name> --graph GRAPH
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<name>` | yes | — |
| `--graph` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem baseline release-1 --graph work/graph
```

### sdem bian

<a id="cmd-bian"></a>

the BIAN (A2) layer: from the base BIAN that ships with SDEM, your own BIAN pack, or BIAN's files — list, import the service domains you choose (checked), pack

Subcommands: [`sdem bian custom`](#cmd-bian-custom) · [`sdem bian impact`](#cmd-bian-impact) · [`sdem bian import`](#cmd-bian-import) · [`sdem bian inference`](#cmd-bian-inference) · [`sdem bian list`](#cmd-bian-list) · [`sdem bian pack`](#cmd-bian-pack) · [`sdem bian search`](#cmd-bian-search) · [`sdem bian update`](#cmd-bian-update)

### sdem bian custom

<a id="cmd-bian-custom"></a>

narrow one workspace's BIAN layer to the service domains it uses — checked; never strands an approved connection

```
sdem bian custom [<folder>] [--base BASE] --workspace WORKSPACE [--add ADD …] [--only ONLY …] [--from FROM] [--all] [--patterns PATTERNS] [--inferences INFERENCES] [--no-inferences] --person PERSON [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<folder>` |  | a folder of BIAN-format files (e.g. a release downloaded from BIAN's GitHub) |
| `--base` |  | the base BIAN that ships with SDEM — or, with FILE, your own packed BIAN |
| `--workspace` | yes | — |
| `--add` |  | add these service domains from the catalogue to what the workspace holds |
| `--only` |  | service domains by name — exactly these |
| `--from` |  | a file of names, one per line |
| `--all` |  | back to every service domain |
| `--patterns` |  | — |
| `--inferences` |  | — |
| `--no-inferences` |  | — |
| `--person` | yes | your name — a person |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian impact

<a id="cmd-bian-impact"></a>

before an update: what in each workspace points at BIAN records the new layer drops, renames or changes — read-only

```
sdem bian impact [--workspace WORKSPACE] [--root ROOT] --a2 A2
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | — |
| `--root` |  | every workspace in a folder |
| `--a2` | yes | the new shared BIAN layer, e.g. bian/a2-service-domain.json |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian import

<a id="cmd-bian-import"></a>

write an A2 dataset for the service domains you choose — checked first

```
sdem bian import [<folder>] [--base BASE] -o O [--only ONLY …] [--from FROM] [--all] [--patterns PATTERNS] [--inferences INFERENCES] [--no-inferences] [--descriptions] [--objects] [--previous PREVIOUS]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<folder>` |  | a folder of BIAN-format files (e.g. a release downloaded from BIAN's GitHub) |
| `--base` |  | the base BIAN that ships with SDEM — or, with FILE, your own packed BIAN |
| `-o`, `--out` | yes | — |
| `--only` |  | service domains by name (or file name) |
| `--from` |  | a file of service-domain names, one per line |
| `--all` |  | every service domain in the release (about 3,000 records for release 14) |
| `--patterns` |  | service domain, asset type, functional pattern — overrides the derived values |
| `--inferences` |  | your own copy of the inference record (default: the one that ships with SDEM for the release) |
| `--no-inferences` |  | do not apply SDEM's accepted inferences (bian/inferences-<release>.json) |
| `--descriptions` |  | include BIAN's descriptions (left out by default) |
| `--objects` |  | also write BIAN business objects (many) |
| `--previous` |  | a previous A2 dataset: report what was added, dropped or renamed |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian inference

<a id="cmd-bian-inference"></a>

SDEM's record of inferred BIAN asset types and functional patterns: list, show, accept, challenge, change or reject an entry. Every change names a person and a reason and is kept in the entry's history; the import applies accepted entries only.

Subcommands: [`sdem bian inference accept`](#cmd-bian-inference-accept) · [`sdem bian inference challenge`](#cmd-bian-inference-challenge) · [`sdem bian inference change`](#cmd-bian-inference-change) · [`sdem bian inference list`](#cmd-bian-inference-list) · [`sdem bian inference reject`](#cmd-bian-inference-reject) · [`sdem bian inference show`](#cmd-bian-inference-show)

### sdem bian inference accept

<a id="cmd-bian-inference-accept"></a>

accept an entry — the import applies it

```
sdem bian inference accept <id> --person PERSON [--reason REASON] [--dry-run] [--file FILE]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--person` | yes | your name — a person |
| `--reason` |  | why — kept in the history |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--file` |  | the record (default: bian/inferences-14.0.0.json in this folder, or the installed one to read) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian inference challenge

<a id="cmd-bian-inference-challenge"></a>

question an entry — the import stops applying it

```
sdem bian inference challenge <id> --person PERSON --reason REASON [--dry-run] [--file FILE]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--person` | yes | your name — a person |
| `--reason` | yes | why — kept in the history |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--file` |  | the record (default: bian/inferences-14.0.0.json in this folder, or the installed one to read) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian inference change

<a id="cmd-bian-inference-change"></a>

give new values — the entry becomes proposed

```
sdem bian inference change <id> --person PERSON --reason REASON [--asset-type ASSET_TYPE] [--pattern PATTERN] [--confidence {high,medium,low}] [--source SOURCE] [--reasoning REASONING] [--dry-run] [--file FILE]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--person` | yes | your name — a person |
| `--reason` | yes | why — kept in the history |
| `--asset-type` |  | — |
| `--pattern` |  | — |
| `--confidence` {high, medium, low} |  | — |
| `--source` |  | — |
| `--reasoning` |  | — |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--file` |  | the record (default: bian/inferences-14.0.0.json in this folder, or the installed one to read) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian inference list

<a id="cmd-bian-inference-list"></a>

the entries, with values, confidence and status

```
sdem bian inference list [--status {open,proposed,accepted,challenged,rejected}] [--file FILE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--status` {open, proposed, accepted, challenged, rejected} |  | — |
| `--file` |  | the record (default: bian/inferences-14.0.0.json in this folder, or the installed one to read) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian inference reject

<a id="cmd-bian-inference-reject"></a>

reject an entry — the import does not apply it

```
sdem bian inference reject <id> --person PERSON --reason REASON [--dry-run] [--file FILE]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--person` | yes | your name — a person |
| `--reason` | yes | why — kept in the history |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--file` |  | the record (default: bian/inferences-14.0.0.json in this folder, or the installed one to read) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian inference show

<a id="cmd-bian-inference-show"></a>

one entry: values, sources, reasoning, history

```
sdem bian inference show <id> [--file FILE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--file` |  | the record (default: bian/inferences-14.0.0.json in this folder, or the installed one to read) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian list

<a id="cmd-bian-list"></a>

the service domains in the base, a pack or a folder; writes nothing

```
sdem bian list [<folder>] [--base BASE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<folder>` |  | a folder of BIAN-format files (e.g. a release downloaded from BIAN's GitHub) |
| `--base` |  | the base BIAN that ships with SDEM — or, with FILE, your own packed BIAN |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian pack

<a id="cmd-bian-pack"></a>

pack a folder of BIAN-format files into one file — your own base

```
sdem bian pack <folder> -o O
```

*JSON: wrapped · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<folder>` | yes | — |
| `-o`, `--out` | yes | — |

### sdem bian search

<a id="cmd-bian-search"></a>

BIAN service domains and operations for plain words — with the ids to use in a process's invokes

```
sdem bian search <words> [--base BASE] [--folder FOLDER] [--top TOP] [--all-operations]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<words>` | yes | e.g. ledger posting |
| `--base` |  | the base BIAN (default) — or your own pack |
| `--folder` |  | a downloaded BIAN release instead |
| `--top` |  | how many service domains (default 5) |
| `--all-operations` |  | every operation of each domain found, not only those matching the words |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem bian update

<a id="cmd-bian-update"></a>

replace a workspace's BIAN layer with your shared one — checked; never strands an approved connection

```
sdem bian update [--workspace WORKSPACE] [--root ROOT] --a2 A2 --person PERSON [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | one workspace |
| `--root` |  | every workspace in a folder, e.g. workspaces |
| `--a2` | yes | your shared BIAN layer, e.g. bian/a2-service-domain.json |
| `--person` | yes | your name — a person |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem build

<a id="cmd-build"></a>

check the inputs and write the graph store (knowledge graph)

```
sdem build <paths> -o O [--check]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<paths>` | yes | architecture datasets and relationship registries |
| `-o`, `--out` | yes | graph store directory |
| `--check` |  | fail if the stored graph files differ from a fresh build (CI) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem build --workspace examples/card-fraud-alerts --out work/graph
```

### sdem change

<a id="cmd-change"></a>

agent platform: propose a change set to one layer — checked, then its impact recorded

Subcommands: [`sdem change adopt`](#cmd-change-adopt) · [`sdem change diff`](#cmd-change-diff) · [`sdem change propose`](#cmd-change-propose) · [`sdem change revert`](#cmd-change-revert) · [`sdem change show`](#cmd-change-show)

### sdem change adopt

<a id="cmd-change-adopt"></a>

record a person's direct edit of a layer as a change set (AG-S08)

```
sdem change adopt --workspace WORKSPACE --layer {A1,A2,A3,A4,registry,requirements} --person PERSON --reason REASON
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--layer` {A1, A2, A3, A4, registry, requirements} | yes | — |
| `--person` | yes | who made the edit |
| `--reason` | yes | — |

### sdem change diff

<a id="cmd-change-diff"></a>

compare an incoming layer file with the workspace and write the change set it implies — nothing is applied (AG-K09)

```
sdem change diff <incoming> --workspace WORKSPACE [--complete] [-o O]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<incoming>` | yes | a layer dataset (JSON with 'level', 'instances', 'relationships') — e.g. records an agent drafted from a document |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--complete` |  | the file is the whole layer: records it leaves out become retirement candidates (listed, never applied) and its records are compared field by field |
| `-o`, `--out` |  | write the change set here, for sdem change propose |

### sdem change propose

<a id="cmd-change-propose"></a>

check and apply a change set to its layer; records the change event and its impact

```
sdem change propose <change_set> --workspace WORKSPACE --agent AGENT --person PERSON [--work WORK …] [--catalogue CATALOGUE]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<change_set>` | yes | change set file (JSON): layer, reason, changes[, relationships] |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--work` |  | work item(s) this change set answers (claimed by the same agent) |
| `--catalogue` |  | BIAN catalogue (A2 dataset) — required when an A2 change set adds records |

### sdem change revert

<a id="cmd-change-revert"></a>

undo the latest change set of a layer — recorded as a new change set (T5)

```
sdem change revert <id> --workspace WORKSPACE --agent AGENT --person PERSON [--reason REASON]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--reason` |  | — |

### sdem change show

<a id="cmd-change-show"></a>

a change set with its event and impact

```
sdem change show <id> --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem check

<a id="cmd-check"></a>

check architecture datasets and registry against the metamodel

```
sdem check [<paths>] [--graph GRAPH] [--status STATUS] [--require-recorded]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<paths>` |  | architecture datasets and mapping documents, any order (or use --graph) |
| `--graph` |  | read a graph store (sdem build) instead of architecture datasets |
| `--status` |  | mapping statuses to treat as arrows |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--require-recorded` |  | fail if a layer file or the registry changed since SDEM last wrote it (an edit not made through sdem, not accepted with sdem change adopt) — for CI where agents edit (AF-07) |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem check --workspace examples/payment-initiation
```

### sdem comply

<a id="cmd-comply"></a>

the organisation's standards and reference-architecture patterns over a workspace: per rule and record compliant, non-compliant, unresolved or under an exception — separate from sdem check (PR-19)

```
sdem comply --workspace WORKSPACE [--as-of AS_OF]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--as-of` |  | evaluate dates (effective dates, expiries, `today`) as of this date |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem comply --workspace examples/payment-initiation
```

### sdem connect

<a id="cmd-connect"></a>

a person states a connection the engine did not propose — the same checks as approve, both ends in the workspace

```
sdem connect <source> <relationship> <target> --workspace WORKSPACE --reviewer REVIEWER [--evidence EVIDENCE] --rationale RATIONALE [--bian-release BIAN_RELEASE] [--id ID] [--date DATE] [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<source>` | yes | the record the connection starts from, e.g. a BIAN service domain id |
| `<relationship>` | yes | one of the nine connection types, e.g. REALIZED_BY, SUPPORTED_BY, DEPLOYED_ON |
| `<target>` | yes | the record it goes to |
| `--workspace` | yes | — |
| `--reviewer`, `--person` | yes | your name — a person (CTL-21) |
| `--evidence` |  | the document that proves it (repeatable; every kind the type needs) |
| `--rationale` | yes | one sentence: why this connection is true |
| `--bian-release` |  | for a connection resting on BIAN guidance: the BIAN release (e.g. 14.0.0) |
| `--id` |  | — |
| `--date` |  | — |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem connect SD-PAYMENT-ORDER-INITIATION REALIZED_BY HIS-A3-PAYMENTS-HUB --workspace workspaces/payments --reviewer jane.architect --evidence application_architecture_document:PAYHUB-HLD#s2 --rationale "…"
```

### sdem copilot

<a id="cmd-copilot"></a>

put SDEM's Copilot instructions, agents, prompts and skills into your workspace repository, matching this SDEM version

Subcommands: [`sdem copilot install`](#cmd-copilot-install)

### sdem copilot install

<a id="cmd-copilot-install"></a>

write .github/copilot-instructions.md, agents/, prompts/, skills/ into a repository

```
sdem copilot install [--to TO] [--dry-run] [--force]
```

*JSON: native · dry run: native*

| Argument | Required | What it is |
|---|---|---|
| `--to` |  | the repository (default: the current folder) |
| `--dry-run` |  | show what would change; write nothing |
| `--force` |  | also replace files your team has changed since the last install |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem dashboard

<a id="cmd-dashboard"></a>

one read-only HTML dashboard for a workspace: health, attention, review, trace & impact, matrices, changes, AID, controls

```
sdem dashboard --workspace WORKSPACE [-o O] [--proposals PROPOSALS] [--projection PROJECTION] [--catalogue CATALOGUE] [--graph GRAPH] [--view VIEW] [--title TITLE] [--full]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `-o`, `--out` |  | default <workspace>/dashboard.html |
| `--proposals` |  | show these proposals (default: run the rules engine now) |
| `--projection` |  | an AID projection package to show beside the real design |
| `--catalogue` |  | the BIAN catalogue the projection used (for its check) |
| `--graph` |  | a graph store of this workspace — warn when it is out of date (default: <workspace>/graph when built) |
| `--view` |  | the graph viewer (sdem view) to link to — default <graph>/view.html; linked only when it shows the current graph |
| `--title` |  | — |
| `--json` |  | print a summary of the computed data instead of writing the page |
| `--full` |  | with --json: everything the page shows, every record's trace and impact (large) |

Example:

```bash
sdem dashboard --workspace examples/payment-initiation -o work/dashboard.html
```

### sdem designs

<a id="cmd-designs"></a>

design records and gap records: the pages onboarded designs came from, and what did not fit an entity

```
sdem designs [--workspace WORKSPACE] [--graph GRAPH] [--entity ENTITY] [--gaps] [--category CATEGORY] [--status {open,resolved,accepted}]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | — |
| `--graph` |  | — |
| `--entity` |  | an entity's pages and the gaps about it or found in them |
| `--gaps` |  | list gap records, not design records |
| `--category` |  | only gaps of this category, e.g. "no entity type" |
| `--status` {open, resolved, accepted} |  | only gaps with this status |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem designs --workspace workspaces/history --entity HIS-A3-PAYMENTS-HUB
```

### sdem diagram

<a id="cmd-diagram"></a>

ArchiMate diagrams of a workspace from SDEM's templates — capabilities and value stream, business process, BIAN service domains, application cooperation, technology and deployment, layered — only stored, approved links drawn

```
sdem diagram [--workspace WORKSPACE] [--template TEMPLATE] [--focus FOCUS] [--format {svg,html,json}] [-o O] [--list] [--check]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | — |
| `--template` |  | the template (sdem diagram --list); default layered |
| `--focus` |  | draw only this record, what it contains and is inside, and what is linked to them |
| `--format` {svg, html, json} |  | default from the -o extension, else svg |
| `-o`, `--out` |  | write here (default: print) |
| `--list` |  | the templates |
| `--check` |  | check the templates against the metamodel (as sdem model check) |
| `--json` |  | with --list or --check: JSON |

Example:

```bash
sdem diagram --workspace examples/payment-initiation --template layered -o work/layered.svg
```

### sdem diff

<a id="cmd-diff"></a>

compare two versions of a relationship document

```
sdem diff <new> [--old OLD] [--git GIT]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<new>` | yes | current mapping document(s) |
| `--old` |  | previous version (file); use with a single document |
| `--git` |  | compare each document against this git revision, e.g. HEAD~1 |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem diff --git HEAD~1 examples/payment-initiation/mappings.json
```

### sdem document

<a id="cmd-document"></a>

a layer's design as a structured, readable document (Markdown or HTML), generated from the workspace — nothing invented, sources and gaps shown; verify checks an agent's narrative against it

```
sdem document --workspace WORKSPACE [--layer LAYER] [--format {md,html}] [-o O]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--layer` |  | A1, A2, A3, A4 (or a layer the profile adds), or all (default) |
| `--format` {md, html} |  | — |
| `-o`, `--out` |  | a file (one layer) or a folder (all layers); without it, Markdown goes to the screen |
| `--json` |  | the structured document instead |

Example:

```bash
sdem document --workspace examples/payment-initiation --layer A3
```

### sdem document verify

<a id="cmd-document-verify"></a>

Check a narrative an agent wrote from `sdem document --json` against the workspace (UX-D09…D11): every [ID] it cites is a record or an approved connection, every link it states ([SOURCE KIND TARGET]) exists and is approved, every record it names is cited, inferred records are said to be inferred, gaps are mentioned. Read-only. Exit 1 when it finds an error.

```
sdem document verify <file> --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<file>` | yes | the narrative (Markdown) an agent wrote |
| `--workspace` | yes | the workspace the narrative describes |
| `--json` |  | the findings as JSON |

### sdem events

<a id="cmd-events"></a>

agent platform: change events, their impact and open work

Subcommands: [`sdem events accept`](#cmd-events-accept) · [`sdem events analyse`](#cmd-events-analyse) · [`sdem events assess`](#cmd-events-assess) · [`sdem events authorise`](#cmd-events-authorise) · [`sdem events pending`](#cmd-events-pending) · [`sdem events show`](#cmd-events-show) · [`sdem events validate`](#cmd-events-validate)

```
sdem events --workspace WORKSPACE [--open]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--open` |  | only events not yet validated, planned or done |

Example:

```bash
sdem events --workspace work/est --open
```

### sdem events accept

<a id="cmd-events-accept"></a>

a person accepts the final impact assessment (and, with --authorise, authorises implementation)

```
sdem events accept <event> --workspace WORKSPACE --person PERSON --reason REASON [--final FINAL …] [--resolve RESOLVE …] [--authorise] [--accept-risk ACCEPT_RISK …]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<event>` | yes | — |
| `--workspace` | yes | — |
| `--person` | yes | your name — a person; never an agent |
| `--reason` | yes | — |
| `--final` |  | your final classification for a layer (required where a specialist disputed or asked for more investigation) |
| `--resolve` |  | how you resolved a layer you decided |
| `--authorise` |  | also authorise implementation now |
| `--accept-risk` |  | accept a confirmed requirement breach as a residual risk, with your reason (required for every confirmed breach) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem events analyse

<a id="cmd-events-analyse"></a>

recompute the requirements evaluation and risk findings after new evidence, links or requirements (assessments made against other evidence become stale)

```
sdem events analyse <event> --workspace WORKSPACE --agent AGENT --person PERSON
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<event>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem events assess

<a id="cmd-events-assess"></a>

a layer agent records its layer's assessment of the calculated impact

```
sdem events assess <event> --workspace WORKSPACE --agent AGENT --person PERSON --layer {A1,A2,A3,A4} --status {impact_confirmed,no_impact_confirmed,further_investigation_required,impact_disputed} [--recommend {design_change_required,review_required,no_impact}] [--evidence EVIDENCE …] [--mapping MAPPING …] [--record RECORD …] [--missing MISSING …] [--uncertainty UNCERTAINTY] [--confidence {high,medium,low}] --reasoning REASONING
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<event>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--layer` {A1, A2, A3, A4} | yes | — |
| `--status` {impact_confirmed, no_impact_confirmed, further_investigation_required, impact_disputed} | yes | — |
| `--recommend` {design_change_required, review_required, no_impact} |  | your classification for the layer (implied for the two *_confirmed statuses) |
| `--evidence` |  | what you checked — a record, a document, a design (required to confirm no impact or to dispute) |
| `--mapping` |  | the approved links (mapping ids) you relied on |
| `--record` |  | records of your layer that are affected (required for a disputed design change) |
| `--missing` |  | links or records that should exist but do not |
| `--uncertainty` |  | what you could not establish, and why it does or does not change your conclusion |
| `--confidence` {high, medium, low} |  | — |
| `--reasoning` | yes | why — in a sentence or two |

### sdem events authorise

<a id="cmd-events-authorise"></a>

a person authorises implementation of an accepted assessment

```
sdem events authorise <event> --workspace WORKSPACE --person PERSON
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<event>` | yes | — |
| `--workspace` | yes | — |
| `--person` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem events pending

<a id="cmd-events-pending"></a>

layers still to assess — for a layer agent: its own

```
sdem events pending --workspace WORKSPACE [--layer {A1,A2,A3,A4}] [--event EVENT]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--layer` {A1, A2, A3, A4} |  | — |
| `--event` |  | — |

### sdem events show

<a id="cmd-events-show"></a>

the calculated impact, every assessment, and what still stops acceptance

```
sdem events show <event> --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<event>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem events validate

<a id="cmd-events-validate"></a>

orchestrator or architect: open the impact validation of a change event — all four layers

```
sdem events validate <event> --workspace WORKSPACE --agent AGENT --person PERSON
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<event>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem exception

<a id="cmd-exception"></a>

a person's time-limited exception to one of the organisation's rules for named records — a governed decision; list shows them active or expired (PR-18)

Subcommands: [`sdem exception grant`](#cmd-exception-grant) · [`sdem exception list`](#cmd-exception-list)

### sdem exception grant

<a id="cmd-exception-grant"></a>

record a person's exception — never an agent's

```
sdem exception grant --workspace WORKSPACE --rule RULE --records RECORDS … --expires EXPIRES --reason REASON --person PERSON [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--rule` | yes | — |
| `--records` | yes | — |
| `--expires` | yes | — |
| `--reason` | yes | — |
| `--person` | yes | — |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem exception list

<a id="cmd-exception-list"></a>

the workspace's exceptions, active or expired

```
sdem exception list --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem explain

<a id="cmd-explain"></a>

explain one element or link: why it exists, from what, how sure

```
sdem explain <id> [--projection PROJECTION] [--proposals PROPOSALS …] [--graph GRAPH] [--names NAMES …] [--workspace WORKSPACE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | a record id, projected id (PRJ-…), or link id |
| `--projection` |  | an AID projection package |
| `--proposals` |  | proposals file(s) from `sdem link` |
| `--graph` |  | graph store to show record names |
| `--names` |  | architecture datasets to show record names |
| `--workspace` |  | workspace folder — show record names from its datasets |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem explain SD-PI --projection work/prj
```

### sdem governance

<a id="cmd-governance"></a>

governed decisions — who was named, and whether a signed commit by that approver verifies it (a typed --person is attribution, not authentication)

Subcommands: [`sdem governance verify`](#cmd-governance-verify)

### sdem governance verify

<a id="cmd-governance-verify"></a>

every decision record: verified by a signed commit from its approver, or why not

```
sdem governance verify --workspace WORKSPACE [--require-verified]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--require-verified` |  | exit 1 unless every decision is verified |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem handback

<a id="cmd-handback"></a>

what a workspace leaves open for a person — values nobody knows, unconfirmed inferences and the strength of their evidence, links to review, possible duplicates, unsourced records — with the commands the person runs (AG-H01)

```
sdem handback --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem handback --workspace examples/payment-initiation
```

### sdem home

<a id="cmd-home"></a>

the main dashboard: the metamodel (entities, links inside and between architectures, engine rules), its picture, health, configuration — and every project

```
sdem home [-o O] [--root ROOT] [--workspace WORKSPACE] [--full]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `-o`, `--out` |  | output folder (default work/sdem) |
| `--root` |  | a folder of workspaces (repeatable; default examples/) |
| `--workspace` |  | one more workspace (repeatable) |
| `--json` |  | print a summary: health, configuration, every workspace (the page is written too) |
| `--full` |  | with --json: everything, including the whole metamodel and the drawings (large) |

Example:

```bash
sdem home -o work/sdem
```

### sdem impact

<a id="cmd-impact"></a>

classify what a change to a record affects

```
sdem impact <entity> [<paths>] [--graph GRAPH] [--status STATUS] --change {modify,rehost,replace,retire} [--report REPORT]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<entity>` | yes | instance id to start from |
| `<paths>` |  | architecture datasets and mapping documents, any order (or use --graph) |
| `--graph` |  | read a graph store (sdem build) instead of architecture datasets |
| `--status` |  | mapping statuses to treat as arrows |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--change` {modify, rehost, replace, retire} | yes | — |
| `--report` |  | also write a printable impact report (Markdown) |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem impact INF-CLOUD-K8S-PROD --change rehost --graph examples/card-fraud-alerts/graph
```

### sdem link

<a id="cmd-link"></a>

run the inference engine: propose links between the architectures, and show them weakest first for review (--no-review: just write them)

```
sdem link [<paths>] [--graph GRAPH] [-o O] [--threshold THRESHOLD] [--baseline]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<paths>` |  | architecture datasets and the approved registry (or use --graph) |
| `--graph` |  | read a graph store (sdem build) — the normal path |
| `-o`, `--out` |  | also write candidates, the inference log and any target-design architecture datasets here |
| `--threshold` |  | baseline only |
| `--json` |  | with --out (sdem link): the proposals, weakest first, as JSON — without --out the output is JSON already |
| `--baseline` |  | the name-overlap baseline engine instead of the rules engine |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem link --workspace examples/payment-initiation --out work/links
```

### sdem load

<a id="cmd-load"></a>

load reviewed candidate entities from sdem transform into a workspace — selected, checked first, recorded (the L of the ETL)

```
sdem load <candidates> --workspace WORKSPACE --person PERSON [--all] [--only ONLY …] [--exclude EXCLUDE …] [--keep KEEP] [--a2 A2] [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<candidates>` | yes | the folder `sdem transform run` wrote |
| `--workspace` | yes | the workspace to load into — started with `sdem new`; for past designs a separate historical workspace is recommended |
| `--person` | yes | who reviewed and loads — a person, never an agent |
| `--all` |  | load every candidate |
| `--only` |  | load only these |
| `--exclude` |  | load all but these |
| `--keep` |  | load the ids listed in a file (one per line, # comments) |
| `--a2` |  | your organisation's A2 dataset (BIAN catalogue), added if the workspace has none |
| `--dry-run` |  | check and show what would be loaded; write nothing |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem load work/history --workspace workspaces/history --person jane.architect --exclude HIS-A3-X
```

### sdem matrix

<a id="cmd-matrix"></a>

business → BIAN → application → technology matrices from approved links

```
sdem matrix [<paths>] [--graph GRAPH] [--md MD]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<paths>` |  | architecture datasets and the registry (or --workspace / --graph) |
| `--graph` |  | — |
| `--md` |  | write Markdown to FILE |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem matrix --workspace examples/payment-initiation --md work/matrix.md
```

### sdem migrate

<a id="cmd-migrate"></a>

move a workspace to the current metamodel version — recorded migrations applied, checked, written all-or-nothing, recorded

```
sdem migrate --workspace WORKSPACE --person PERSON [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--person` | yes | your name — a person |
| `--dry-run` |  | check and show what would change; write nothing |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem migrate --workspace workspaces/history --person jane.architect --dry-run
```

### sdem model

<a id="cmd-model"></a>

maintainers: regenerate and check generated files, acceptance, evaluation, examples

Subcommands: [`sdem model accept`](#cmd-model-accept) · [`sdem model baseline-pack`](#cmd-model-baseline-pack) · [`sdem model calibrate`](#cmd-model-calibrate) · [`sdem model check`](#cmd-model-check) · [`sdem model eval`](#cmd-model-eval) · [`sdem model examples`](#cmd-model-examples) · [`sdem model freeze`](#cmd-model-freeze) · [`sdem model regenerate`](#cmd-model-regenerate) · [`sdem model stability`](#cmd-model-stability) · [`sdem model status`](#cmd-model-status) · [`sdem model usage`](#cmd-model-usage)

### sdem model accept

<a id="cmd-model-accept"></a>

engine acceptance cases

```
sdem model accept
```

*JSON: wrapped · dry run: sandbox*

### sdem model baseline-pack

<a id="cmd-model-baseline-pack"></a>

write the metamodel baseline review pack

```
sdem model baseline-pack
```

*JSON: wrapped · dry run: sandbox*

### sdem model calibrate

<a id="cmd-model-calibrate"></a>

how often each confidence band and evidence class is right on the acceptance cases (AID-E03)

```
sdem model calibrate
```

*JSON: wrapped · dry run: sandbox*

### sdem model check

<a id="cmd-model-check"></a>

fail if any generated file differs from a fresh generation

```
sdem model check
```

*JSON: wrapped · dry run: sandbox*

### sdem model eval

<a id="cmd-model-eval"></a>

score proposals against approved links

```
sdem model eval
```

*JSON: wrapped · dry run: sandbox*

### sdem model examples

<a id="cmd-model-examples"></a>

re-run use-case examples 1 and 2 (evidence packs and results)

```
sdem model examples
```

*JSON: wrapped · dry run: sandbox*

### sdem model freeze

<a id="cmd-model-freeze"></a>

record the core after an approved, versioned change

```
sdem model freeze
```

*JSON: wrapped · dry run: sandbox*

### sdem model regenerate

<a id="cmd-model-regenerate"></a>

regenerate every generated document, diagram and schema

```
sdem model regenerate
```

*JSON: wrapped · dry run: sandbox*

### sdem model stability

<a id="cmd-model-stability"></a>

the core against its last freeze (as CI)

```
sdem model stability
```

*JSON: wrapped · dry run: sandbox*

### sdem model status

<a id="cmd-model-status"></a>

every part of SDEM's metamodel not yet settled, with its source and what would settle it

```
sdem model status
```

*JSON: wrapped · dry run: sandbox*

### sdem model usage

<a id="cmd-model-usage"></a>

what the given workspaces use, and what no workspace uses

```
sdem model usage
```

*JSON: wrapped · dry run: sandbox*

### sdem new

<a id="cmd-new"></a>

start a workspace: the four layers (A2 your BIAN layer) and an empty registry of connections — checked, recorded

```
sdem new [--workspace WORKSPACE] [--organisation ORGANISATION] --person PERSON [--bian BIAN] [--no-bian] [--example {payment-initiation}] [--from FROM] [--profile PROFILE] [--explore] [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | the folder to start, e.g. workspaces/payments — inside an organisation, a path from its folder |
| `--organisation` |  | alone: start an organisation — the folder NAME with a starter base profile (profiles/NAME-base.json) and workspaces/ (WS-08); with --workspace: start the workspace inside that organisation, its profile extending the base (WS-09, WS-10). Inside an organisation's folder it is found without this |
| `--person` | yes | your name — a person |
| `--bian` |  | start with exactly this BIAN layer in A2 (default: A2 empty; sdem aid brings in the domains your design needs from bian/a2-service-domain.json if it exists, else the base BIAN) |
| `--no-bian` |  | start without a BIAN layer (add it later); business then does not connect to applications |
| `--example` {payment-initiation} |  | start with a synthetic example that ships with SDEM as the baseline (made-up data, for learning) — the same as --from its folder |
| `--from` |  | start with this content as the baseline: the four layers, mappings.json and requirements.json found in DIR — checked first, recorded in the ledger and as a decision; only when the workspace is created (a baseline is never re-taken) |
| `--profile` |  | start with this organisation profile (kept as sdem-profile.json; its base is still found): its types, rules and names apply, and the layers it adds above A1 or below A4 start empty beside the core four |
| `--explore` |  | also build the knowledge graph and write the pages to explore it — the graph page, the workspace dashboard and SDEM Home (work/sdem/index.html) — in one step; derived outputs only, the workspace is not changed (EX-01) |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem new --workspace workspaces/payments --person jane.architect
```

### sdem pattern

<a id="cmd-pattern"></a>

reference-architecture patterns as structures — extract a draft pattern from the organisation's diagram (draw.io, Visio, PlantUML, Mermaid), compare it with the included one, draw it over a design (PR-21…PR-31)

Subcommands: [`sdem pattern draw`](#cmd-pattern-draw) · [`sdem pattern extract`](#cmd-pattern-extract)

### sdem pattern draw

<a id="cmd-pattern-draw"></a>

draw a pattern (PR-25) — with --workspace and --anchor, over that design: which part is there, which is missing

```
sdem pattern draw [--file FILE] [--id ID] [--workspace WORKSPACE] [--profile PROFILE] [--anchor ANCHOR] [--format {svg,html,json}] [-o O]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--file` |  | — |
| `--id` |  | a pattern the workspace's profile includes |
| `--workspace` |  | — |
| `--profile` |  | — |
| `--anchor` |  | draw over the design from this record |
| `--format` {svg, html, json} |  | — |
| `-o`, `--out` |  | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem pattern extract

<a id="cmd-pattern-extract"></a>

a diagram → a DRAFT pattern file and a report; nothing enters the profile until a person includes it (PR-30)

```
sdem pattern extract --from FROM [--profile PROFILE] [--workspace WORKSPACE] --id ID [--title TITLE] [--version VERSION] --owner OWNER [--anchor ANCHOR] [--out OUT] [--compare COMPARE] [--dry-run]
```

*JSON: native · dry run: native*

| Argument | Required | What it is |
|---|---|---|
| `--from` | yes | — |
| `--profile` |  | — |
| `--workspace` |  | — |
| `--id` | yes | — |
| `--title` |  | — |
| `--version` |  | — |
| `--owner` | yes | who owns the pattern (it is theirs to approve) |
| `--anchor` |  | the part the pattern applies to (its label or role id) |
| `--out` |  | write the draft here (otherwise only the report) |
| `--compare` |  | what changed against this pattern file (PR-31) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |

### sdem profile

<a id="cmd-profile"></a>

the organisation's design specification on top of SDEM's metamodel — its own types, attributes, rules, link kinds and names (sdem-profile.json, optionally extending a shared base): check, show, example

Subcommands: [`sdem profile adopt`](#cmd-profile-adopt) · [`sdem profile check`](#cmd-profile-check) · [`sdem profile example`](#cmd-profile-example) · [`sdem profile show`](#cmd-profile-show)

### sdem profile adopt

<a id="cmd-profile-adopt"></a>

put the workspace under its sdem-profile.json: the layers it adds start empty, and the adoption is recorded — a person's decision

```
sdem profile adopt --workspace WORKSPACE --person PERSON --reason REASON [--dry-run]
```

*JSON: native · dry run: native · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--person` | yes | your name — a person |
| `--reason` | yes | — |
| `--dry-run` |  | nothing written; what would be written is listed under "would_write" |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem profile check

<a id="cmd-profile-check"></a>

check the workspace's profile (and the base it extends) against SDEM's metamodel

```
sdem profile check [--workspace WORKSPACE] [--file FILE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | — |
| `--file` |  | a profile file instead of a workspace |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem profile example

<a id="cmd-profile-example"></a>

write a synthetic bank base profile, team profiles that extend it (one adds layers), and a team profile with the bank's standards and secure API pattern

```
sdem profile example --out OUT
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--out` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem profile show

<a id="cmd-profile-show"></a>

the merged profile: every type, attribute, rule, link kind and name it adds

```
sdem profile show [--workspace WORKSPACE] [--file FILE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | — |
| `--file` |  | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem query

<a id="cmd-query"></a>

find records in a graph store

```
sdem query --graph GRAPH [--level {A1,A2,A3,A4}] [--type TYPE] [--where WHERE] [--neighbours NEIGHBOURS] [--kind KIND] [--direction {in,out,both}] [--unmapped {A1,A2,A3,A4}]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--graph` | yes | — |
| `--level` {A1, A2, A3, A4} |  | — |
| `--type` |  | entity type; subtypes included |
| `--where` |  | core field or attribute equals value (repeatable) |
| `--neighbours` |  | within-level neighbours of a record |
| `--kind` |  | with --neighbours: only this relationship kind |
| `--direction` {in, out, both} |  | — |
| `--unmapped` {A1, A2, A3, A4} |  | records with no approved cross-level link where the catalogue expects one |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem query --graph examples/card-fraud-alerts/graph --level A3
```

### sdem releases

<a id="cmd-releases"></a>

what each SDEM release changed: migrations, breaking changes, deprecations and the actions to take

```
sdem releases [--since SINCE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--since` |  | only releases after this one, e.g. the version you use |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem releases --since 0.15.0
```

### sdem requirements

<a id="cmd-requirements"></a>

requirements and constraints the workspace must keep meeting, their measurements, and what a change does to them: in scope, satisfied, breached, not evaluable — and the risk findings

Subcommands: [`sdem requirements check`](#cmd-requirements-check) · [`sdem requirements confirm`](#cmd-requirements-confirm) · [`sdem requirements evaluate`](#cmd-requirements-evaluate) · [`sdem requirements list`](#cmd-requirements-list) · [`sdem requirements measure`](#cmd-requirements-measure) · [`sdem requirements propose`](#cmd-requirements-propose) · [`sdem requirements retire`](#cmd-requirements-retire) · [`sdem requirements show`](#cmd-requirements-show) · [`sdem requirements trace`](#cmd-requirements-trace)

### sdem requirements check

<a id="cmd-requirements-check"></a>

the registry against its schema and the workspace

```
sdem requirements check --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem requirements confirm

<a id="cmd-requirements-confirm"></a>

a person confirms proposed requirements — only confirmed requirements are evaluated as obligations

```
sdem requirements confirm <id> --workspace WORKSPACE --person PERSON [--note NOTE]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--person` | yes | — |
| `--note` |  | — |

### sdem requirements evaluate

<a id="cmd-requirements-evaluate"></a>

what a change does to the requirements: in scope, satisfied, breached, not evaluable — and the risk findings

```
sdem requirements evaluate --workspace WORKSPACE [--event EVENT] [--record RECORD] [--change {modify,rehost,replace,retire}] [--proposed PROPOSED]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--event` |  | a change event (its stored impact and the change set it came from) |
| `--record` |  | or: a record you plan to change |
| `--change` {modify, rehost, replace, retire} |  | with --record: the kind of change |
| `--proposed` |  | with --record: the record that will replace it (e.g. the new platform) |

### sdem requirements list

<a id="cmd-requirements-list"></a>

the requirements, with status and subject

```
sdem requirements list --workspace WORKSPACE [--layer {A1,A2,A3,A4}] [--status STATUS]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--layer` {A1, A2, A3, A4} |  | — |
| `--status` |  | — |

### sdem requirements measure

<a id="cmd-requirements-measure"></a>

record measurements — stated values with their evidence, current or proposed

```
sdem requirements measure --workspace WORKSPACE [--from FROM] [--record RECORD] [--metric METRIC] [--value VALUE] [--unit UNIT] [--state {current,proposed}] [--evidence EVIDENCE …] --person PERSON [--agent AGENT]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--from` |  | measurements from a file (a list, or {"measurements": [...]}: record, metric, value, unit, state, evidence) — each recorded against you |
| `--record` |  | — |
| `--metric` |  | — |
| `--value` |  | — |
| `--unit` |  | — |
| `--state` {current, proposed} |  | — |
| `--evidence` |  | — |
| `--person` | yes | — |
| `--agent` |  | — |

### sdem requirements propose

<a id="cmd-requirements-propose"></a>

add requirements, or new versions, as proposed

```
sdem requirements propose <file> --workspace WORKSPACE --person PERSON [--agent AGENT]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<file>` | yes | a JSON requirement, a list of them, or a registry ({"requirements": [...]}) — version and history are set here |
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--person` | yes | — |
| `--agent` |  | — |

### sdem requirements retire

<a id="cmd-requirements-retire"></a>

a person retires requirements

```
sdem requirements retire <id> --workspace WORKSPACE --person PERSON --reason REASON
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--person` | yes | — |
| `--reason` | yes | — |

### sdem requirements show

<a id="cmd-requirements-show"></a>

one requirement: condition, evidence, history and its measurements

```
sdem requirements show <id> --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem requirements trace

<a id="cmd-requirements-trace"></a>

a requirement through the layers: its subject and allocations, what they depend on and serve, and the requirements it derives from

```
sdem requirements trace <id> --workspace WORKSPACE
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | — |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem review

<a id="cmd-review"></a>

list proposed links for review, weakest first

```
sdem review <proposals> [--graph GRAPH] [--names NAMES …] [--workspace WORKSPACE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<proposals>` | yes | proposals file(s), e.g. from `sdem link --out` |
| `--graph` |  | graph store to show record names |
| `--names` |  | architecture datasets to show record names |
| `--workspace` |  | workspace folder — show record names from its datasets |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem review work/links/proposals.json
```

### sdem trace

<a id="cmd-trace"></a>

trace what a record depends on (down) or what depends on it (up)

```
sdem trace <entity> [<paths>] [--graph GRAPH] [--status STATUS] [--direction {down,up,both,downstream,upstream,all}] [--tree] [--only-gaps] [--to {A1,A2,A3,A4}] [--csv CSV] [--follow-composition] [--projection PROJECTION]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<entity>` | yes | instance id to start from — or a whole layer: A1, A2, A3 or A4 |
| `<paths>` |  | architecture datasets and mapping documents, any order (or use --graph) |
| `--graph` |  | read a graph store (sdem build) instead of architecture datasets |
| `--status` |  | mapping statuses to treat as arrows |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--direction` {down, up, both, downstream, upstream, all} |  | down: what it depends on; up: what depends on it; both (also: downstream, upstream, all) |
| `--tree` |  | a whole layer: one tree per record (default: summary, gaps and a table of chains) |
| `--only-gaps` |  | a whole layer: only the records with no connection in that direction |
| `--to` {A1, A2, A3, A4} |  | a whole layer: stop the chains at this layer |
| `--csv` |  | a whole layer: also write the chains as CSV |
| `--follow-composition` |  | continue a chain through within-level part-whole links — composition and aggregation (part -> whole downstream, whole -> parts upstream) |
| `--projection` |  | also follow the links of an AID projection package, labelled PROJECTED (AID-O06) |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem trace CAP-310 --graph examples/card-fraud-alerts/graph
```

### sdem transform

<a id="cmd-transform"></a>

transform past designs — a Confluence export, a folder, or one Word, Excel, Markdown or CSV file — into candidate architecture entities: inspect it, extract (rules; on-device OCR for pictures)

Subcommands: [`sdem transform inspect`](#cmd-transform-inspect) · [`sdem transform rules`](#cmd-transform-rules) · [`sdem transform run`](#cmd-transform-run)

### sdem transform inspect

<a id="cmd-transform-inspect"></a>

what is in the export and which rules read it — structure only

```
sdem transform inspect <export> [--rules RULES] [--anonymous] [--ocr {auto,vision,tesseract,off}]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<export>` | yes | — |
| `--rules` |  | your copy of the rules (make one with `sdem transform rules -o FILE`) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--anonymous` |  | folder layout only, names replaced by F1, F2 … — safe to describe to others |
| `--ocr` {auto, vision, tesseract, off} |  | read text in pictures: macOS Vision (built in), Tesseract (if installed), auto, or off |

### sdem transform rules

<a id="cmd-transform-rules"></a>

write a copy of SDEM's transform rules to tune for your organisation's designs (then pass it with --rules)

```
sdem transform rules -o O
```

*JSON: wrapped · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `-o`, `--out` | yes | e.g. rules/transform-rules.json in your workspace repository |

### sdem transform run

<a id="cmd-transform-run"></a>

transform the export: write candidate datasets, extraction.json, design-index.json and extraction-report.md

```
sdem transform run <export> -o O [--rules RULES] [--known KNOWN …] [--model-id MODEL_ID] [--ocr {auto,vision,tesseract,off}]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<export>` | yes | — |
| `-o`, `--out` | yes | — |
| `--rules` |  | your copy of the rules (make one with `sdem transform rules -o FILE`) |
| `--known` |  | existing SDEM datasets: their names are found in the text and flagged as the same record |
| `--model-id` |  | name for the candidate datasets (default: the Confluence space) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--ocr` {auto, vision, tesseract, off} |  | read text in pictures: macOS Vision (built in), Tesseract (if installed), auto, or off |

### sdem types

<a id="cmd-types"></a>

what you may write: each layer's kinds of record, their fields (type, required, allowed values) and allowed links; the requirement and change-set formats — your profile's included with --workspace

```
sdem types [<what>] [--workspace WORKSPACE]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<what>` |  | a layer (A1), a type (A1.BusinessProcess), requirement or change-set; nothing: the overview |
| `--workspace` |  | include the workspace's organisation profile |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem types A1.BusinessProcess
```

### sdem upgrade

<a id="cmd-upgrade"></a>

before you switch SDEM versions: run the new version, installed side by side, against your workspaces — migrations, profile, deprecations, agent files, actions; writes nothing

Subcommands: [`sdem upgrade check`](#cmd-upgrade-check)

### sdem upgrade check

<a id="cmd-upgrade-check"></a>

what upgrading to this version means for your workspaces: migrations, profile, deprecations, agent files, actions — writes nothing

```
sdem upgrade check [--workspace WORKSPACE] [--root ROOT] [--repo REPO] [--from FROM]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` |  | — |
| `--root` |  | every workspace in a folder |
| `--repo` |  | your workspace repository (requirements.txt, AGENTS.md); default the current folder |
| `--from` |  | the version you use now (default: read from requirements.txt) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

### sdem validate

<a id="cmd-validate"></a>

validate a relationship document (registry or proposals)

```
sdem validate <paths> [--registry REGISTRY] [--catalogue CATALOGUE] [--strict]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `<paths>` | yes | mapping JSON file(s) |
| `--registry` |  | relationship registry (default: bundled) |
| `--catalogue` |  | entity catalogue JSON; every endpoint must exist in it |
| `--strict` |  | treat warnings as errors (except draft warnings on proposed records) |
| `--json` |  | emit a JSON report instead of text |
| `--workspace` |  | the workspace folder, in place of the list of files (its layer datasets and mappings.json) |

Example:

```bash
sdem validate --strict --workspace examples/payment-initiation
```

### sdem view

<a id="cmd-view"></a>

write the HTML picture of a graph store, optionally with a projection

```
sdem view --graph GRAPH [-o O] [--projection PROJECTION] [--dashboard DASHBOARD] [--home HOME]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--graph` | yes | — |
| `-o`, `--out` |  | default <DIR>/view.html |
| `--projection` |  | overlay an AID projection package, drawn dashed and labelled PROJECTED (AID-O06) |
| `--dashboard` |  | the workspace dashboard to link back to (default: <workspace>/dashboard.html when the store is the workspace's own graph and that page exists) |
| `--home` |  | SDEM Home (index.html written by sdem home) to link back to |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |

Example:

```bash
sdem view --graph examples/card-fraud-alerts/graph -o work/view.html
```

### sdem work

<a id="cmd-work"></a>

agent platform: plan, list and claim work items

Subcommands: [`sdem work block`](#cmd-work-block) · [`sdem work cancel`](#cmd-work-cancel) · [`sdem work claim`](#cmd-work-claim) · [`sdem work list`](#cmd-work-list) · [`sdem work plan`](#cmd-work-plan) · [`sdem work reopen`](#cmd-work-reopen)

### sdem work block

<a id="cmd-work-block"></a>

a work item cannot proceed — say why

```
sdem work block <id> --workspace WORKSPACE --agent AGENT --person PERSON [--note NOTE]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--note` |  | — |

### sdem work cancel

<a id="cmd-work-cancel"></a>

drop a work item — say why

```
sdem work cancel <id> --workspace WORKSPACE --agent AGENT --person PERSON [--note NOTE]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--note` |  | — |

### sdem work claim

<a id="cmd-work-claim"></a>

a layer agent takes a work item

```
sdem work claim <id> --workspace WORKSPACE --agent AGENT --person PERSON [--note NOTE]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--note` |  | — |

### sdem work list

<a id="cmd-work-list"></a>

work items

```
sdem work list --workspace WORKSPACE [--layer {A1,A2,A3,A4}] [--status {open,in_progress,done,blocked,cancelled}]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--layer` {A1, A2, A3, A4} |  | — |
| `--status` {open, in_progress, done, blocked, cancelled} |  | — |

### sdem work plan

<a id="cmd-work-plan"></a>

orchestrator: turn a change event's impact into work items

```
sdem work plan --event EVENT --workspace WORKSPACE --agent AGENT --person PERSON [--max-rounds MAX_ROUNDS]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `--event` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--max-rounds` |  | stop and ask the architect after this many rounds (default and most 3; only the architect may raise it) |

### sdem work reopen

<a id="cmd-work-reopen"></a>

return a work item to open

```
sdem work reopen <id> --workspace WORKSPACE --agent AGENT --person PERSON [--note NOTE]
```

*JSON: native · dry run: sandbox · 👤 a person's own name*

| Argument | Required | What it is |
|---|---|---|
| `<id>` | yes | — |
| `--workspace` | yes | the workspace folder (a1…a4 datasets, mappings.json) |
| `--agent` | yes | the agent: sdem-a1-business, sdem-a2-bian, sdem-a3-application, sdem-a4-technology, sdem-orchestrator, or 'architect' for a person working without an agent |
| `--person` | yes | the person behind the agent (CTL-20) |
| `--json` |  | the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}} |
| `--note` |  | — |

### sdem workbench

<a id="cmd-workbench"></a>

the workbench for one workspace: one offline page — the solution workspace (designs, data, knowledge graph, trace and impact, reviews and changes, documents and evidence) and the SDEM framework (metamodel, configuration, rules, health)

```
sdem workbench --workspace WORKSPACE [-o O]
```

*JSON: native · dry run: sandbox*

| Argument | Required | What it is |
|---|---|---|
| `--workspace` | yes | — |
| `-o`, `--out` |  | the page to write (default work/workbench.html) |
| `--json` |  | print a summary of what the page shows (the page is written too) |

Example:

```bash
sdem workbench --workspace examples/payment-initiation -o work/workbench.html
```
