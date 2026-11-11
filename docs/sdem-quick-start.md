# SDEM quick start — ten commands for everyday design work

> **Status: current.** A first design, end to end, with the ten commands an architect uses most (CR-05). Every command here is checked against the CLI by a test (`tests/test_scenarios_doc.py`). Everything else SDEM does: the [scenarios](sdem-scenarios.md) (15 jobs, in order) and the [CLI reference](reference/cli-reference.md) (every command and option). The data is made up.

**Conventions.** `bank-xyz` is a made-up organisation and `workspaces/ledger` one of its workspaces; `your.name` is your own name. **👤 marks a person's decision:** SDEM records the name you give — your own, never an agent's (CTL-21) — so an agent prepares these commands and asks you; it never runs them for you.

| Command | What it does |
|---|---|
| `sdem new` | start a workspace (or an organisation) for a design |
| `sdem status` | where the design is: what blocks it, what waits on you, and what to do next |
| `sdem aid` | infer the missing layers from the business design — marked inferred until 👤 you confirm them |
| `sdem check` | is the design well-formed? — against the metamodel |
| `sdem comply` | does it meet the organisation's standards and reference patterns? |
| `sdem approve` | 👤 approve a proposed link between layers, with its evidence |
| `sdem trace` | what a record depends on, or what depends on it |
| `sdem impact` | what a change to a record affects: modify, rehost, replace or retire |
| `sdem document` | the design as a readable document — from the records, nothing invented |
| `sdem workbench` | everything about the design on one offline page |

## 1. Start

Once per organisation, then once per design:

```bash
sdem new --organisation bank-xyz --person your.name
cd bank-xyz
sdem new --workspace workspaces/ledger --person your.name
cd workspaces/ledger
```

**Inside a workspace folder, `--workspace` is found for you** (SDEM says which on the first line). Everything below runs in `workspaces/ledger`; from anywhere else, add `--workspace <folder>`.

## 2. Write the business design, and see where you are

Write the business layer — capabilities, value streams, processes and the BIAN operations they use — through a checked change set: [create a new design](sdem-new-design.md) shows how, or ask your agent to (skill `sdem-new-design`). Then:

```bash
sdem status
```

`status` sorts everything SDEM finds into **blocking** (must be fixed), **unresolved** (a value nobody knows, a decision waiting on a person) and **warnings**, and lists the **next** commands with who runs each. Run it whenever you are unsure what to do next.

## 3. Let SDEM infer the rest — then decide

```bash
sdem aid --person your.name --dry-run
sdem aid --person your.name
```

AID brings in the BIAN service domains your processes use and the applications and technology they imply — every record **marked inferred**, with its source, reasoning and confidence. Nothing inferred counts as decided until 👤 you confirm it (or reject it):

```bash
sdem aid confirm SD-FINANCIAL-ACCOUNTING --person your.name
```

## 4. Check it, and check it against your standards

```bash
sdem check
sdem comply
```

`check` is the metamodel: is every record well-formed and every link allowed. `comply` is your organisation's own standards and reference patterns: each rule and record **compliant**, **not met**, **unresolved** (a value is unknown — never counted compliant) or under an exception.

## 5. Approve the links between layers

SDEM proposes links between the layers — a capability to its service domain, a service domain to the applications that implement it, an application to its platform. A proposal is not a fact until 👤 a person approves it, with the evidence it needs:

```bash
sdem link --out work/links
sdem approve P-RUN-001 --proposals work/links/proposals.json --reviewer your.name --evidence business_architecture_document:LEDGER-BA#capabilities
```

## 6. Trace, and assess a change

```bash
sdem build -o graph
sdem trace CAP-LEDGER-010 --graph graph
sdem impact APP-LEDGER --change replace --graph graph
```

`trace` follows **approved** links down from a record (or up, with `--direction up`). `impact` names the record that changes and how — `modify`, `rehost`, `replace` or `retire` — and classifies everything it touches. Both read the knowledge graph `build` writes; rebuild after every approved change.

## 7. Write it up, and see it all

```bash
sdem document --layer all
sdem workbench
```

`document` writes each layer's design as a structured document — from the records, with their sources and gaps; nothing invented. For readable prose, an agent writes the narrative from it and SDEM checks every citation (`sdem document verify`; skill `sdem-design-narrative`). `workbench` writes one offline page: the designs, the data, the knowledge graph, trace and impact, reviews and changes.

**Then:** `sdem status` again. When it says **CLEAR**, nothing blocks the design and nothing waits on a person.
