---
name: sdem-scenarios
description: Which SDEM commands to run, in what order, and who decides, for every job — set up an organisation and its first workspace; explore the bundled example; create a new design; onboard existing designs — Confluence, a folder, Word or Excel; a design document into all four layers, with an agent; link the architectures and approve the links; build the knowledge graph and see it; trace dependencies and assess a change's impact; a change event — from change set to accepted, planned work; requirements and risk; the organisation's design spec, standards and patterns; a reference pattern from the organisation's diagram; design documents and narratives; manage the BIAN layer; upgrade SDEM. Use when asked to do any of these jobs, when unsure which command comes next, or before using a command no other skill covers.
---

# SDEM jobs, end to end

> Generated from SDEM's [scenarios guide](../../../docs/sdem-scenarios.md) — the same steps a person reads. Do not edit: SDEM regenerates it.

**How to use it.** Find the job below. Where it names a **skill**, read that skill too — it has the detail. Before you run a command, get its exact options from SDEM, never from memory: `sdem commands <command> --json` (one command, e.g. `sdem commands "events assess" --json`) or `sdem <command> --help`. Add `--json` to every command and `--dry-run` before anything that writes. Every step marked **A person decides** is the architect's: prepare the exact command with their name, explain it, and ask — never run it with an agent's name (CTL-21). End with `sdem handback --workspace <dir> --json`.

**Conventions.** `bank-xyz` is a made-up organisation and `workspaces/ledger` one of its workspaces; `your.name` is your own name — a person's, never an agent's (CTL-21). Add `--json` to any command for one JSON object (agents always do), and `--dry-run` to any command that writes, to see first what it would write.

| # | Scenario | Who |
|---|---|---|
| 1 | [Set up an organisation and its first workspace](#1-set-up-an-organisation-and-its-first-workspace) | architecture owner, architect |
| 2 | [Explore the bundled example](#2-explore-the-bundled-example) | anyone |
| 3 | [Create a new design](#3-create-a-new-design) | architect (with or without an agent) |
| 4 | [Onboard existing designs — Confluence, a folder, Word or Excel](#4-onboard-existing-designs--confluence-a-folder-word-or-excel) | architect |
| 5 | [A design document into all four layers, with an agent](#5-a-design-document-into-all-four-layers-with-an-agent) | agent, then architect |
| 6 | [Link the architectures and approve the links](#6-link-the-architectures-and-approve-the-links) | engine proposes, architect approves |
| 7 | [Build the knowledge graph and see it](#7-build-the-knowledge-graph-and-see-it) | anyone |
| 8 | [Trace dependencies and assess a change's impact](#8-trace-dependencies-and-assess-a-changes-impact) | architect |
| 9 | [A change event — from change set to accepted, planned work](#9-a-change-event--from-change-set-to-accepted-planned-work) | layer agents, orchestrator, architect |
| 10 | [Requirements and risk](#10-requirements-and-risk) | architect |
| 11 | [The organisation's design spec, standards and patterns](#11-the-organisations-design-spec-standards-and-patterns) | architecture owner, architect |
| 12 | [A reference pattern from the organisation's diagram](#12-a-reference-pattern-from-the-organisations-diagram) | pattern owner |
| 13 | [Design documents and narratives](#13-design-documents-and-narratives) | architect, agent |
| 14 | [Manage the BIAN layer](#14-manage-the-bian-layer) | BIAN owner, architect |
| 15 | [Upgrade SDEM](#15-upgrade-sdem) | administrator |

---

## 1. Set up an organisation and its first workspace

**Goal:** the organisation's folder with its design specification (base profile), and a workspace that follows it.

```bash
sdem new --organisation bank-xyz --person your.name                                  # once per organisation
cd bank-xyz
sdem profile check --file profiles/bank-xyz-base.json                                # after the owner adds types, attributes, rules
sdem new --workspace workspaces/ledger --organisation bank-xyz --person your.name --dry-run
sdem new --workspace workspaces/ledger --organisation bank-xyz --person your.name    # each workspace
sdem profile show --workspace workspaces/ledger                                      # base → workspace: what applies
sdem types A3 --workspace workspaces/ledger                                          # what you may write, the profile's fields included
```

**A person decides:** starting the organisation and each workspace. A workspace on its own (no organisation) is `sdem new --workspace workspaces/ledger --person your.name`; an existing workspace takes a profile with `sdem profile adopt` (scenario 11).

## 2. Explore the bundled example

**Goal:** see a complete, made-up Payments architecture — the knowledge graph, dashboard and workbench — in one step.

```bash
sdem new --workspace workspaces/payments --person your.name --example payment-initiation --explore
sdem workbench --workspace workspaces/payments                  # one offline page: designs, data, graph, reviews, documents
sdem trace CAP-PAY-010 --graph workspaces/payments/graph --direction down          # capability → BIAN → application → technology
```

## 3. Create a new design

**Skill (step by step, for an agent):** `sdem-new-design`, `sdem-change-sets`, `sdem-records`.

**Goal:** a new solution, from a business design to approved links across all four layers.

```bash
sdem bian search ledger posting                                 # the BIAN operations a process invokes (SO-… ids)
sdem types A1 --workspace workspaces/ledger                     # the record types and fields
sdem change propose ledger-a1.json --workspace workspaces/ledger --agent architect --person your.name --dry-run
sdem change propose ledger-a1.json --workspace workspaces/ledger --agent architect --person your.name
sdem aid --workspace workspaces/ledger --person your.name --dry-run
sdem aid --workspace workspaces/ledger --person your.name       # infers the BIAN domains, applications, deployments — marked
sdem aid confirm SD-FINANCIAL-ACCOUNTING --workspace workspaces/ledger --person your.name
sdem aid reject APP-LEDGER-X --workspace workspaces/ledger --person your.name --reason "not in scope"
sdem check --workspace workspaces/ledger
sdem handback --workspace workspaces/ledger                     # what is left for a person
```

**Planning without touching the workspace** — a projection in its own folder, then compared with what exists:

```bash
sdem aid project --workspace workspaces/ledger -o workspaces/ledger/plans/ledger-v2
sdem aid check workspaces/ledger/plans/ledger-v2
sdem aid gaps workspaces/ledger/plans/ledger-v2 --workspace workspaces/ledger
```

Then link and approve (scenario 6). A change set put in by mistake is undone with `sdem change revert <id> --workspace workspaces/ledger --agent architect --person your.name --reason "…"` (`sdem change show <id>` first). The format of `ledger-a1.json`: `sdem types change-set`. **A person decides:** every record AID inferred (confirm or reject), and every link.

## 4. Onboard existing designs — Confluence, a folder, Word or Excel

**Skill (step by step, for an agent):** `sdem-onboard-designs`.

**Goal:** past designs become candidate records, reviewed before any enters a workspace.

```bash
sdem transform inspect exports/confluence-space                 # what is there, which rule reads it — changes nothing
sdem transform run exports/confluence-space -o work/history --known workspaces/ledger/a3-application.json
sdem transform run designs/ledger-design.xlsx -o work/ledger-xlsx          # one Excel file: every visible tab
sdem transform run designs/ledger-design.docx -o work/ledger-docx          # one Word file
# read work/history/extraction-report.md; note the HIS-… ids you reject
sdem load work/history --workspace workspaces/ledger --person your.name --exclude HIS-A3-PAYMENT-ORDER --dry-run
sdem load work/history --workspace workspaces/ledger --person your.name --exclude HIS-A3-PAYMENT-ORDER
sdem designs --workspace workspaces/ledger --gaps               # what did not fit an entity
```

Tables, headings and diagrams are read by rules (`sdem transform rules -o rules/transform-rules.json` to tune them for your templates); free text is not — scenario 5. **A person decides:** which candidates are loaded.

## 5. A design document into all four layers, with an agent

**Skill (step by step, for an agent):** `sdem-design-from-document`.

**Goal:** an architect's Markdown or Word design becomes checked change sets for every layer. The agent follows the skill `sdem-design-from-document`; SDEM checks each step.

```bash
sdem transform run designs/ledger-design.docx -o work/ledger-docx           # agent: the tables first, by rules
sdem types A1 --workspace workspaces/ledger --json                          # agent: the allowed types and fields
sdem change diff work/ledger-a1-draft.json --workspace workspaces/ledger -o work/ledger-a1.json
sdem change propose work/ledger-a1.json --workspace workspaces/ledger --agent sdem-a1-business --person your.name --dry-run --json
sdem handback --workspace workspaces/ledger --json                          # agent: what the document did not say
```

**A person decides:** whether each change set is applied (`sdem change propose` without `--dry-run`), and everything in scenario 3's list.

## 6. Link the architectures and approve the links

**Skill (step by step, for an agent):** `sdem-approve-links`.

**Goal:** the links between A1, A2, A3 and A4 — proposed by the rules engine, approved by a person with evidence.

```bash
sdem link --workspace workspaces/ledger --out workspaces/ledger/links
sdem review workspaces/ledger/links/proposals.json --workspace workspaces/ledger          # weakest first
sdem explain P-RUN-003 --proposals workspaces/ledger/links/proposals.json                # why the engine proposed it
sdem approve P-RUN-003 --proposals workspaces/ledger/links/proposals.json --workspace workspaces/ledger \
  --reviewer your.name --evidence deployment_design:DD-LEDGER-1
sdem connect SD-FINANCIAL-ACCOUNTING REALIZED_BY APP-LEDGER-CORE --workspace workspaces/ledger \
  --reviewer your.name --evidence application_architecture_document:LEDGER-HLD#s3 --rationale "the ledger core realises the domain"
```

Each link type needs its own evidence; a link to BIAN also `--bian-release 14.0.0`. `sdem approve` says what is missing and writes nothing. **A person decides:** every link — an agent never approves.

## 7. Build the knowledge graph and see it

```bash
sdem build --workspace workspaces/ledger --out workspaces/ledger/graph
sdem view --graph workspaces/ledger/graph                       # the graph page
sdem dashboard --workspace workspaces/ledger                    # health, review, trace and impact, AID
sdem diagram --workspace workspaces/ledger --template layered -o work/ledger-layered.svg
sdem workbench --workspace workspaces/ledger                    # everything in one offline page
sdem home -o work/sdem                                          # SDEM Home across workspaces
sdem matrix --graph workspaces/ledger/graph                     # capability → BIAN → application → technology, approved links
sdem baseline before-rehost --graph workspaces/ledger/graph     # freeze the graph under a name
sdem diff workspaces/ledger/mappings.json --git HEAD~1          # the approved links: what changed since the last commit
```

The pages are read-only snapshots: run the same commands again after the workspace changes. Only approved links are in the graph.

## 8. Trace dependencies and assess a change's impact

**Skill (step by step, for an agent):** `sdem-trace-impact`.

```bash
sdem trace CAP-GL --graph workspaces/ledger/graph --direction down          # what the capability depends on
sdem trace INF-K8S-FIN --graph workspaces/ledger/graph --direction up --tree
sdem impact INF-K8S-FIN --graph workspaces/ledger/graph --change retire     # what retiring the cluster affects
sdem requirements evaluate --workspace workspaces/ledger --record INF-K8S-FIN --change rehost
```

Read-only: nothing is changed. A planned change goes through scenario 9.

## 9. A change event — from change set to accepted, planned work

**Skill (step by step, for an agent):** `sdem-impact-validation`.

**Goal:** a change to one layer is assessed by every layer before any work is planned (skill `sdem-impact-validation`).

```bash
sdem change propose a4-rehost.json --workspace workspaces/ledger --agent sdem-a4-technology --person your.name   # records event CE-…
sdem events show CE-001 --workspace workspaces/ledger                       # the calculated impact
sdem events validate CE-001 --workspace workspaces/ledger --agent sdem-orchestrator --person your.name
sdem events pending --workspace workspaces/ledger --layer A3                # each layer agent: what waits for it
sdem events assess CE-001 --workspace workspaces/ledger --agent sdem-a3-application --person your.name \
  --layer A3 --status impact_confirmed --recommend design_change_required --evidence design:LEDGER-HLD#s4
sdem events accept CE-001 --workspace workspaces/ledger --person your.name --reason "impact agreed in design review"
sdem events authorise CE-001 --workspace workspaces/ledger --person your.name
sdem work plan --event CE-001 --workspace workspaces/ledger --agent sdem-orchestrator --person your.name
sdem work list --workspace workspaces/ledger --status open
sdem work claim WI-001 --workspace workspaces/ledger --agent sdem-a3-application --person your.name
sdem change propose a3-update.json --workspace workspaces/ledger --agent sdem-a3-application --person your.name --work WI-001
```

Every layer assesses, including those with no calculated impact. A work item can also be blocked, cancelled or reopened: `sdem work block WI-001 …`, `sdem work cancel WI-001 …`, `sdem work reopen WI-001 …` (each with `--workspace`, `--agent`, `--person` and a `--note`). **A person decides:** accepting the impact (and any residual risk, `--accept-risk`) and authorising the work.

## 10. Requirements and risk

**Skill (step by step, for an agent):** `sdem-requirements-risk`.

```bash
sdem requirements propose ledger-requirements.json --workspace workspaces/ledger --person your.name
sdem requirements confirm REQ-GL-AVAIL --workspace workspaces/ledger --person your.name
sdem requirements measure --workspace workspaces/ledger --record APP-LEDGER-CORE --metric availability --value 99.95 --unit percent \
  --evidence monitoring:GL-SLO-2026 --person your.name
sdem requirements list --workspace workspaces/ledger --status confirmed
sdem requirements show REQ-GL-AVAIL --workspace workspaces/ledger            # one requirement, its measurements and status
sdem requirements trace REQ-GL-AVAIL --workspace workspaces/ledger           # where it is allocated, what measures it
sdem requirements evaluate --workspace workspaces/ledger --record APP-LEDGER-CORE --change rehost
sdem requirements check --workspace workspaces/ledger
sdem requirements retire REQ-GL-OLD --workspace workspaces/ledger --person your.name --reason "replaced by REQ-GL-AVAIL"
```

The format of a requirements file: `sdem types requirement`. **A person decides:** confirming and retiring requirements, and accepting a risk (scenario 9).

## 11. The organisation's design spec, standards and patterns

**Goal:** the organisation's own types, attributes and rules (the profile), its standards (security, network …) and reference patterns, checked on every design.

```bash
sdem profile example --out profiles-example                     # a synthetic set to copy from
sdem profile check --file profiles/bank-xyz-base.json           # after each edit — against SDEM's metamodel
sdem profile adopt --workspace workspaces/ledger --person your.name --reason "ledger follows the bank design spec"   # an existing workspace
sdem check --workspace workspaces/ledger                        # the profile's required attributes and rules
sdem comply --workspace workspaces/ledger                       # each standard and pattern: compliant, non-compliant, unresolved …
sdem exception grant --workspace workspaces/ledger --rule NET-07 --records APP-LEDGER-CORE --expires 2026-12-31 \
  --reason "moves to the restricted zone in Q4" --person your.name --dry-run
sdem exception list --workspace workspaces/ledger
```

Standards and patterns are files the profile `includes`; adding one is a profile change, checked by `sdem profile check`. **A person decides:** adopting a profile, and every exception (time-limited).

## 12. A reference pattern from the organisation's diagram

**Goal:** a reference pattern drawn in draw.io, Visio, PlantUML or Mermaid becomes a checked pattern file.

```bash
sdem pattern extract --from diagrams/secure-api-edge.drawio --workspace workspaces/ledger \
  --id PAT-SECURE-API-EDGE --owner "security architecture" --out work/secure-api-edge.json
# the pattern owner reviews work/secure-api-edge.json and its report, then includes it in the profile
sdem profile check --workspace workspaces/ledger
sdem pattern extract --from diagrams/secure-api-edge.drawio --workspace workspaces/ledger \
  --id PAT-SECURE-API-EDGE --owner "security architecture" --compare profiles/patterns/secure-api-edge.json   # after the diagram changes
sdem pattern draw --workspace workspaces/ledger --id PAT-SECURE-API-EDGE --anchor APP-LEDGER-CORE -o work/edge-over-design.svg
sdem comply --workspace workspaces/ledger
```

**A person decides:** including the pattern (an agent may extract and explain, never include).

## 13. Design documents and narratives

**Skill (step by step, for an agent):** `sdem-design-narrative`.

```bash
sdem document --workspace workspaces/ledger --layer A3                         # Markdown, structured
sdem document --workspace workspaces/ledger --layer all --format html -o work/designs/
sdem document --workspace workspaces/ledger --layer A3 --json                  # agent: the facts for a narrative
sdem document verify work/a3-narrative.md --workspace workspaces/ledger        # check the agent's narrative
```

`sdem document` never writes prose; an agent writes the narrative (skill `sdem-design-narrative`), citing `[ID]` for every fact, and `verify` reports invented records or links and unapproved links stated as fact. **A person** reads the narrative before it is shared.

## 14. Manage the BIAN layer

```bash
sdem bian search loan                                           # domains and operations for plain words
sdem bian list --base                                           # all 258 service domains
sdem bian custom --workspace workspaces/ledger --add "Financial Accounting" --person your.name
sdem bian impact --workspace workspaces/ledger                  # before an update: what the new layer drops or renames
sdem bian inference list                                        # inferred asset types and patterns
sdem bian inference show INF-001
sdem bian inference accept INF-001 --person your.name --reason "checked on the BIAN portal"
sdem bian inference challenge INF-002 --person your.name --reason "the portal shows a different pattern"
sdem bian inference change INF-002 --person your.name --reason "per the BIAN portal" --pattern Fulfill
sdem bian inference reject INF-003 --person your.name --reason "not supported by any source"
```

**The organisation's shared BIAN layer** (the BIAN owner, once per release):

```bash
sdem bian pack bian-release-14 -o bian/bian-14.0.0-pack.json                # BIAN's files into one pack
sdem bian import bian/bian-14.0.0-pack.json --all -o bian/a2-service-domain.json
sdem bian update --workspace workspaces/ledger --a2 bian/a2-service-domain.json --person your.name --dry-run
```

**A person decides:** narrowing or updating a workspace's BIAN layer, and accepting, challenging or changing an inference.

## 15. Upgrade SDEM

```bash
sdem releases --since 0.17.0                                    # what changed, and what to do
sdem upgrade check --workspace workspaces/ledger                # run by the NEW version, side by side: migrations, profile, deprecations
sdem migrate --workspace workspaces/ledger --person your.name --dry-run
sdem migrate --workspace workspaces/ledger --person your.name
sdem agents install --dry-run                                   # the agents' instructions and skills for this version
sdem copilot install --dry-run                                  # Copilot's own files only (agents install includes them)
sdem model status                                               # this SDEM's metamodel version and health
```

**A person decides:** migrating each workspace (recorded).
