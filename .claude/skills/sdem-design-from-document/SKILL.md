---
name: sdem-design-from-document
description: How to turn an architect's solution design document (Markdown or Word) into SDEM records in all four layers — reading it, mapping each statement to a record type, drafting one change set per layer, citing the section every record came from, letting SDEM infer the rest, and handing back what the document did not say. Use when the architect gives you a design document, a .md or .docx file, or asks to "import", "model" or "load" a design from a document.
---

# A design document into SDEM

The document is the architect's; SDEM checks everything you draft; **the architect decides** — you never confirm, approve or accept (AGENTS.md rule 4). SDEM itself does not read documents: you read it, and you write change sets through the `sdem` command line like any other change. Past designs exported from Confluence go through `sdem transform` instead (skill `sdem-onboard-designs`).

## 1. Read the document

- **Markdown** (`.md`): read it directly.
- **Word** (`.docx`): convert it to text with what your platform has — e.g. `textutil -convert txt <file>` (macOS), `pandoc -t plain <file>`, or read `word/document.xml` from the file (a `.docx` is a zip) with Python's standard library. Keep the headings: you cite them.
- Number the sections as the document does (`#2`, `#4.1`) — every record you write cites one.

## 2. Map what it says to records — and only what it says

| The document says | Layer | Record type (check with `sdem types <layer>`) |
|---|---|---|
| capabilities, value streams and stages, processes, activities, roles, information handled, business requirements | A1 | `A1.BusinessCapability`, `A1.ValueStream`, `A1.ValueStreamStage`, `A1.BusinessProcess`, `A1.BusinessActivity`, `A1.BusinessRole`, `A1.BusinessObject`, `A1.BusinessRequirement` |
| measurable targets (availability, response time, region) | requirements | `sdem types requirement` |
| BIAN service domains, by name or implied by the business | A2 | **do not write A2** — give every process and activity `invokes` from `sdem bian search`; `sdem aid` brings the domains in. Look up **everything the business relies on**, not only what it does: a statement such as *the customer must be authenticated* or *the credit is checked* is a BIAN operation too (`sdem bian search authenticate customer`) — put it in the `invokes` of the activity it belongs to |
| applications and components, services, interfaces and API operations, data entities, events | A3 | `A3.ApplicationComponent`, `A3.ApplicationService`, `A3.ApplicationInterface`, `A3.APIOperation`, `A3.DataEntity`, `A3.Event` |
| platforms, databases, technology services, environments, deployments, networks, images | A4 | `A4.SystemSoftware`, `A4.Node`, `A4.TechnologyService`, `A4.DeploymentEnvironment`, `A4.Deployment`, `A4.CommunicationNetwork`, `A4.Artifact` |

- Use the document's own names for records, exactly as written (`loan_application` stays `loan_application`). Do not invent what it does not say (API paths, fields, versions); where SDEM needs a value the document lacks, **leave it out and mark the record `planned`** — never write a placeholder: `sdem check` reads `TBD`, `unknown`, `/TBD` or an empty string as missing and fails an active record (LC-04), and words in paths and names are matched to BIAN domains. `sdem handback` lists every value left out, for step 5.
- Fields that point to another layer (an A3 component's `deployed_on`, a data entity's `stored_in`, an A4 deployment's `component_id`) may name records that do not exist yet; SDEM accepts that and `sdem link` connects them once both layers exist.
- **Every record cites its section** in `attributes.source_id`: `"document:<file>#<section>"`, e.g. `"document:DESIGN.md#4"` — the same field design onboarding uses for Confluence pages (`confluence:<page>`). A record built from two sections cites both, comma-separated. A value stated in another section than the record cites that section in `attributes.sources` (`{"deployed_on": "document:DESIGN.md#6"}`).
- Links inside a layer (a process *composition* activity, a component *access* data entity …) come from what the document says, with kinds from `sdem types <type>` (`links_out`). Links **between** layers are never written — `sdem link` proposes them. Cite the section on each link too: `"source_id": "document:<file>#<section>"`.

## 3. One change set per layer, each by its layer's agent

Draft each layer's change set in `<workspace>/coordination/drafts/` (format: `sdem types change-set`; the change set's `reason` names the document) — or draft the layer as a dataset and let `sdem change diff <drafted.json> --workspace <ws> -o <draft>` write the change set, with any possible duplicates of existing records (AG-K09) — then:

```
sdem change propose <draft> --workspace <ws> --agent sdem-a1-business --person <architect> --dry-run --json   # then without --dry-run
sdem change propose <draft> --workspace <ws> --agent sdem-a3-application --person <architect> --dry-run --json
sdem change propose <draft> --workspace <ws> --agent sdem-a4-technology --person <architect> --dry-run --json
sdem requirements propose <draft> --workspace <ws> --person <architect> --dry-run --json
```

Each layer's change set goes under that layer's agent (CTL-19); if your platform has no separate layer agents, you write them in turn under each agent's name. Fix what a dry run refuses before going on — the message names the field or rule.

## 4. Let SDEM infer and propose

```
sdem aid --workspace <ws> --person <architect> --dry-run --json      # check added.A2: the domains your invokes name
sdem aid --workspace <ws> --person <architect> --json                # only if the architect asked for inference
sdem link --workspace <ws> --out <ws>/links --json                   # the one list of proposed connections (AID-W09)
sdem check --workspace <ws> --require-recorded --json
```

`NOTE: not added — …` lines from `sdem aid` (in `--json`: the list `projection_ends`) are domains only names or descriptions pointed to (AID-M03, AID-E02): pass them on, do not act on them. Every inferred record and proposed link says what kind of evidence it rests on (`evidence_class`: `attribute_join`, `structural`, `pattern`, `name_token`, `text` — strongest first); call out those resting on `name_token` or `text`.

## 5. Hand back — always this review list

Run `sdem handback --workspace <ws> --json` and build the list from it — it is read from the workspace, so it is complete whichever agent did the work (AG-H01): values nobody knows, unconfirmed inferences with their evidence class, links to review, possible duplicates, unsourced records, failing checks. Add what only you know (items 1 and 3).

1. **What you created**, per layer, each record with the section it came from; the change sets and events.
2. **What the document did not say** that SDEM needs or would use — `missing_values` from `sdem handback` (each one left out on a `planned` record), with the section where it belongs.
3. **Where you interpreted** — a statement you mapped to a type the document did not name, or two statements you merged.
4. **What SDEM inferred** (with confidence and evidence class — weak ones first) and the **NOTE** lines; any **possible duplicates**; the architect's commands: `sdem aid confirm|reject …`.
5. **Connections to approve**, grouped by type with the evidence each needs — the document section is a good evidence reference; a link type that needs two kinds of evidence takes `--evidence` twice; preview each with `--dry-run` (allowed) to see whether it also needs `--bian-release`: `sdem approve <id> --proposals <ws>/links/proposals.json --workspace <ws> --reviewer <architect> --evidence <kind>:<file>#<section>`.
6. **Requirements to confirm** once the targets are real: `sdem requirements confirm …`.

Never run `sdem approve`, `sdem connect`, `sdem aid confirm|reject`, `sdem requirements confirm`, `sdem events accept|authorise` or `sdem change adopt` — they are the architect's (CTL-21).
