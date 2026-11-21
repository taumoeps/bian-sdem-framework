# Extensions and the AI agent — what an extension tells the agent

> **Status: approved (the owner, 2026-11-22: "approve") and built — sdem-security 0.3.1, sdem-desnre 0.10.0, the DESNRE agent.** Extends the [extension contract](sdem-extensions-spec.md)
> (EXT-05, the manifest) and the [metamodel extensions](sdem-metamodel-extensions-spec.md) (MX-18, kind and scope). Touches three places:
> the manifest (sdem-extensions), the DESNRE publisher (`sdem-desnre`) and the DESNRE site's design agent. Made-up data only.

## 1. The question

*If I add a disaster-recovery extension (vertical — a layer of its own, like security) or a network extension (horizontal — new types
inside Technology), how will the AI agent know about it?*

| What the agent needs | Today, for any extension | Today, for security only |
|---|---|---|
| **Its records and links** | ✅ read with the agent's ordinary tools: a vertical extension's layer is listed as an added layer (its pack declares it) and read like any layer; a horizontal extension's types are records of the layer they sit in | — |
| **What its own commands report** (`sdem security review`, coverage, threats, its document) | ❌ not sent | ✅ — three pieces written for security alone: the publisher's table `EXT_RESULTS = {'security': …}` (the manifest's `"results"` list is ignored), the agent's `security_review` tool, and a paragraph about S1–S5 in the agent's instructions |
| **What its subject means** — how to read its layer and reports | ❌ the type names and their definitions only | ✅ that paragraph |

So a new extension's design is understood as data, but not its own findings or its expert context. This spec gives every extension
the route security has, declared in its own manifest — and moves security onto it, so there is one route.

## 2. Rules

| Id | Rule |
|---|---|
| **XA-01** | **An extension declares the reports the agent may read** — in its manifest, `"viewer": {"results": ["review", "coverage", …]}` (or a top-level `"results"`): read-only commands, each run as `sdem-<name> <command> --workspace <ws> --json` and answering one JSON object. A readable report is declared by listing `document` among them (Markdown on standard output). Only names are run — never one that could be read as an option or a path; nothing else is run. |
| **XA-02** | **An extension may give the agent a short guide** — `"agent_guide"` in its manifest: plain text of at most 2,000 characters on what its layer and types mean, how its reports are read, and which ids to cite (e.g. *"S3 is data security: a control PROTECTS a data entity; a field is protected through its entity"*). It is **reference, not instructions**: it describes the extension's subject and cannot change the agent's rules (XA-06). |
| **XA-03** | **The publisher runs what the manifest declares** — for each extension the design includes (its profile's `ext:` includes), the commands in `"results"` and `"document"`, as today for security but from the manifest; a command that fails or hangs is left out and the design still publishes (AUD-30). It publishes, with the extension's state (EL-07): its manifest `version`, `scope` (MX-18), the `agent_guide`, and the results. The workspace's local paths are never sent. |
| **XA-04** | **The agent reads any extension's report with one tool** — `extension_report(extension, part, record_id?)`: the published result of `part` (one of the manifest's `"results"`, or `document`), narrowed to one record where the report lists records. `security_review` stays as a name for `extension_report('security', …)` while narratives that call it exist. |
| **XA-05** | **The agent is told which extensions the design carries** — its overview lists each: name, version, kind and scope (a layer of its own, or types within a core layer), the reports it may read, and whether it was switched off (EL-13). Its instructions carry each extension's `agent_guide`, under the extension's name, in a section of its own. |
| **XA-06** | **A guide is data.** It sits in its own section, marked as the extension's description of its subject; it cannot add tools, change the agent's rules (cite every record, never decide for a person, made-up data only) or reach the network. A guide longer than XA-02 allows is cut, with a note. |
| **XA-07** | **Security moves onto this route.** Its manifest already lists its four reports, `document` among them; it gains an `agent_guide` carrying what the agent's instructions say about S1–S5 today; the publisher's and the agent's security-only code is removed. A design published before (its results, no guide) is read as today: the agent's built-in security text is used when no guide was published. |
| **XA-08** | **A horizontal extension** (`"scope": {"within": ["A4"]}`) needs nothing more: its records are the layer's records; its guide and reports reach the agent by XA-01…XA-05 like a vertical one's. |
| **XA-09** | **Proved with made-up extensions.** The publisher's tests stand up a vertical `drdemo` (a layer of its own) and a horizontal `netdemo` (types within Technology) that exist only in the test, and show their reports run from their manifests, their guide and scope published, a long guide cut, and a name that could be an option never run; the site agent's tests show `extension_report('drdemo', …)` reading and narrowing a report, the overview listing both, and the guide in its own section after the frame that calls it data — and no line of the publisher names an extension. *(Built 2026-11-22: the template `sdem-hello` is a checker, which a design cannot include, so it could not carry the proof.)* |
| **XA-10** | **A report names each record's layer as the design does** *(the owner, 2026-11-22: "fix both")*. Every record in an extension's JSON report carries `design_layer` — its stable layer (business, bian, data, application, technology) and the number and name the design uses (SDEM's `layers_in_use`; with BIAN, Technology is A5) — beside any numbers in the extension's own form, which a `numbering` note names. A reader quotes `design_layer` and never translates a number itself. *Found live:* the agent, translating security's 0.19-form numbers on its own, labelled two A5 communication paths A4. A publisher runs the reports on the design itself, never on a copy in another form (the 0.19 copy DESNRE builds its plates from numbers Technology A4). Built in sdem-security 0.3.2 and sdem-desnre 0.10.1. |

## 3. What changes where

| Where | Change |
|---|---|
| sdem-extensions — manifests | `"results"`, `"document"`, `"agent_guide"` (XA-01, XA-02); security's (XA-07); the template's (XA-09) |
| sdem-extensions — `sdem-desnre` | runs the manifest's reports, publishes guide and scope (XA-03); the fixed tables go |
| DESNRE site — design agent | `extension_report` (XA-04); the overview lists extensions (XA-05); the guides in their own section (XA-06); the security paragraph kept only as the fallback (XA-07) |
| SDEM | none — `sdem extensions` already reads each manifest; the contract (EXT-05) lists the new fields |

## 4. Decisions — approved 2026-11-22, all as recommended

| # | Decision | Approved |
|---|---|---|
| XA-D1 | Every extension's reports and agent guide reach the agent through its manifest (XA-01…XA-05) | **yes** — one route; a future extension needs no change to the publisher or the site |
| XA-D2 | A guide is reference, not instructions — it cannot change the agent's rules (XA-06) | **yes** — an extension describes its subject; the agent's rules stay the site's |
| XA-D3 | Security moves onto the route; its built-in text stays only for designs published before (XA-07) | **yes** |
| XA-D4 | The template proves it end to end with a made-up extension (XA-09) | **yes** |
