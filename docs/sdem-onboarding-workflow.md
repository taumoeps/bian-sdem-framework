# SDEM onboarding — bringing your existing designs into SDEM

> **One document for design onboarding** (built 2026-10-28): what onboarding is, how to do it — the commands and each step with what you will see — what each step does to the data, and when the data is ready. To **test** it step by step with sealed expected results: [`use-case-example-4.md`](use-case-example-4.md). Technical detail: [`sdem-transform-design.md`](sdem-transform-design.md) (reading the designs), [`sdem-load-design.md`](sdem-load-design.md) (loading, gap records). For architects; no AI needed.

## 1. What onboarding is

**Onboarding** is bringing data from a new source into SDEM until it is **governed and ready for use** — reviewed, checked against the rulebook, connected, approved and built into the knowledge graph. There are two routes:

```mermaid
flowchart LR
    subgraph ON["Onboarding — from a new source to ready for use"]
        direction TB
        D["📄 <b>Design onboarding</b> — built<br/>existing designs (Confluence export)"]
        T["🗄️ <b>Tool onboarding</b> — planned (v0.11)<br/>spreadsheets, CMDB, application portfolio"]
    end
    D -->|"ingestion:<br/>transform → review → load"| E[("Estate<br/>architecture data")]
    T -->|"ingestion:<br/>adapter → check → load"| E
    E -->|"normal processing:<br/>check → link → approve → build"| R(["✅ ready for<br/>queries and changes"])
    classDef built fill:#E8F5E9,stroke:#2E7D32
    classDef next fill:#ECEFF1,stroke:#607D8B
    class D built
    class T next
```

| Term | Means |
|---|---|
| **Onboarding** | the whole process: new source → ready for use |
| **Ingestion** | the first part: getting the data into an estate (for designs: transform → review → load) |
| **Normal processing** | the second part, the same for every estate however its data arrived: check → link → approve → build |
| **Estate** | a project's architecture data, in one folder (here `estates/history/`) |

## 2. The process at a glance

```mermaid
flowchart LR
    E["📄 Your Confluence<br/>export"] --> R["1 · SDEM reads it<br/>(suggestions)"]
    R --> C["2 · You check<br/>the report"]
    C --> K["3 · You keep<br/>the good ones"]
    K --> L["4 · SDEM suggests<br/>connections —<br/>you approve"]
    L --> P["5 · SDEM builds<br/>the picture"]
    P --> Q["6 · You ask questions<br/>and tidy up gaps"]
    classDef you fill:#F3E5F5,stroke:#6A1B9A
    classDef sdem fill:#E3F2FD,stroke:#1565C0
    class C,K,Q you
    class R,L,P sdem
```

How ready the data is after each stage:

```mermaid
flowchart LR
    s1(["raw<br/><i>the export</i>"]) --> s2(["candidate<br/><i>suggested items</i>"]) --> s3(["reviewed<br/><i>you chose</i>"]) --> s4(["loaded<br/><i>in the estate</i>"]) --> s5(["connected<br/><i>links approved</i>"]) --> s6(["✅ ready<br/><i>graph built</i>"])
    classDef r fill:#E8F5E9,stroke:#2E7D32
    class s6 r
```

At the end, your designs are **architecture data** — business capabilities, applications, servers and the links between them — that you can trace, analyse for impact and see on a dashboard. What SDEM could not turn into data (a table of risks, a photo, a PDF) is **kept as a gap** for you to deal with — nothing is lost.

## 3. The commands in plain words

| # | Command | In plain words |
|---|---|---|
| 1 | `sdem transform inspect <export folder>` | **Look before you start.** Shows what is in your export and what SDEM can read. Changes nothing |
| 2 | `sdem transform run <export folder> -o work/history` | **Read the designs.** Turns the pages into a list of *suggested* architecture items, and writes a report for you to read |
| 3 | *(you read `work/history/extraction-report.md`)* | **Check the suggestions.** Decide which are wrong |
| 4 | `sdem load work/history --estate estates/history --person <you> --exclude <wrong ones>` | **Keep the good ones.** Copies the items you accept into your project; whatever did not fit is kept as *gaps*. Add `--dry-run` first to see what would happen |
| 5 | `sdem check --estate estates/history` | **Health check.** Confirms everything follows the rules |
| 6 | `sdem link --estate estates/history --out work/links` | **Suggest connections.** SDEM proposes how items connect across layers (e.g. *this app runs on this server*) |
| 7 | `sdem review work/links/proposals.json` | **See the suggested connections**, weakest first |
| 8 | `sdem approve <id> … --reviewer <you> --evidence <document>` | **Accept a connection.** You confirm it, and name the document that proves it |
| 9 | `sdem build --estate estates/history --out work/graph` | **Make the picture.** Builds the connected view — the knowledge graph — from what you accepted |
| 10 | `sdem trace <item>` · `sdem impact <item> --change retire` | **Ask questions.** *What does this depend on?* · *What breaks if we remove this?* |
| 11 | `sdem dashboard --estate estates/history -o work/dashboard.html` | **See it as a web page** — everything above, clickable, in your browser |
| 12 | `sdem designs --estate estates/history --gaps` | **See the gaps** — what did not fit, still waiting for you |
| 13 | `sdem designs accept` · `resolve <gap id> … --person <you> --note "<why>"` | **Close a gap.** *Accept* = leave it as it is; *resolve* = you have dealt with it |
| 14 | `git add estates/history` → commit → pull request | **Save and share** — your accepted work goes for review |

**In short:** **read** (1–2) → **you check** (3) → **keep** (4–5) → **connect** (6–8) → **picture** (9) → **use** (10–11) → **tidy up** (12–13) → **save** (14). Commands 1–4 are **ingestion**; 5–9 are **normal processing**.

**Remember:**
- `--person` / `--reviewer` is always **your name** — only a person can accept items, connections and gaps.
- `work/` is your **scratch area** — never saved to Git; keep the export there.
- `estates/history/` is **the real result** — that is what you save.
- Any command explains itself: add `--help` (e.g. `sdem load --help`).

## 4. Before you start

1. Open the SDEM project in **VS Code** and open a **terminal** (*Terminal → New Terminal*).
2. Check SDEM works: `python3 -m sdem --help` (or `sdem --help` if it is installed).
3. Start a branch for this work: `git checkout -b onboard/<name>`.
4. **Put your export under `work/`**, e.g. `work/imports/payarch/`. Only `work/`, `private/` and `secrets/` are kept out of Git — anywhere else, your designs could be committed and shared.
5. Have your organisation's **BIAN layer** to hand (an `a2-service-domain.json`) — needed once, so SDEM can connect your designs to BIAN.

> The examples below show what you will see with the made-up export `tests/fixtures/confluence-folder-export`, with `--ocr off` (the same on every machine). Try it first: `cp -r tests/fixtures/confluence-folder-export work/imports/payarch`.

## 5. Step by step

### 1 · Look before you start
```bash
sdem transform inspect work/imports/payarch
```
You see what is in the export and what SDEM will read:
```
6 pages, 6 tables, 7 diagrams read … 3 pictures for a person, 3 provenance files in the root
  [application | purpose | status | support hours] → HT-01     ← read as applications
  [risk | impact | mitigation] → no entity type                  ← SDEM has no place for risks: kept as a gap
Coverage: 80% captured (45 captured, 11 not captured, 4 skipped by design)
```
**If a table or diagram you need shows *no rule* or *unclassified***, SDEM does not know your words yet — copy the rules and add them, then look again:
```bash
cp metamodel/transform-rules.json work/my-rules.json      # e.g. add "system name" as an application column
sdem transform inspect work/imports/payarch --rules work/my-rules.json
```

### 2 · Read the designs
```bash
sdem transform run work/imports/payarch -o work/history          # add --rules work/my-rules.json if you made one
```
```
6 pages read: A1 3 records, A3 6 records, A4 8 records, 7 links inside, 6 candidate links between
check: 1 error(s) — see extraction-report.md
```
These are **suggestions** — nothing is in your project yet.

### 3 · Check the suggestions
Open `work/history/extraction-report.md` (in VS Code: right-click → *Open Preview*). Read, in this order:

| Section | What to look for |
|---|---|
| **Coverage** | how much of each page SDEM understood |
| **Check** | items that break the rules — e.g. *Payment Order: attribute list missing* |
| **Records** | every suggested item, with **the page and place it came from**, how sure SDEM is, and why. Look for wrong names or types |
| **Not captured** | what did not fit — a risks table, a column, a sentence, a PDF |
| **For a person** | pictures and diagrams only you can interpret |

Write down the ids of the items you do **not** want, e.g. `HIS-A3-PAYMENT-ORDER`.
*Tip:* in Copilot Chat, `/sdem-import-review work/history` explains each item and suggests what to reject — you decide.

### 4 · Keep the good ones
Try it first with `--dry-run` (writes nothing), then run it for real:
```bash
sdem load work/history --estate estates/history --person <your name> --exclude HIS-A3-PAYMENT-ORDER \
  --a2 <your BIAN layer>/a2-service-domain.json --dry-run
sdem load work/history --estate estates/history --person <your name> --exclude HIS-A3-PAYMENT-ORDER \
  --a2 <your BIAN layer>/a2-service-domain.json
```
```
loaded (LOAD-001) into estates/history: A1 3 entities, A3 5 entities, A4 8 entities, 7 links inside architectures
gap records: 13 — what did not fit an entity, kept beside the estate
reconciliation: 17 candidates = 16 loaded + 0 already in the estate + 1 excluded
```
The *reconciliation* proves nothing was lost. `--a2` is needed only the first time. **Ingestion is now complete**; the rest is normal processing.

### 5 · Health check
```bash
sdem check --estate estates/history
```
Every line should say `OK`.

### 6 · Suggest and review connections
```bash
sdem link --estate estates/history --out work/links
sdem review work/links/proposals.json
```
```
[0.4] P-RUN-001  Clearing Gateway   DEPLOYED_ON  PAYAPP01    — capped at low: from a document
[0.4] P-RUN-005  Payment Initiation SUPPORTED_BY SD-PI (BIAN)
```
Every connection from a past design is marked **low** — check each against its Confluence page. `sdem designs --estate estates/history --entity <id>` tells you which page an item came from.

### 7 · Accept the right connections
```bash
sdem approve P-RUN-001 --proposals work/links/proposals.json --estate estates/history \
  --reviewer <your name> --evidence deployment_design:<page or document id>
```
For a connection to BIAN, also give the BIAN release: `--bian-release <release>` (SDEM tells you if it is missing). The **evidence** is the document that proves the connection — SDEM tells you which kind each connection needs.

### 8 · Make the picture
```bash
sdem build --estate estates/history --out work/graph
```
```
build 1 accepted: … federated.graph.json (4 nodes, 2 edges), designs.graph.json (24 nodes, 42 edges)
```
**The data is now ready for queries and changes.**

### 9 · Ask questions
```bash
sdem trace HIS-A1-PAYMENT-INITIATION --graph work/graph            # what does this capability depend on?
sdem impact HIS-A4-PAYAPP01 --change retire --graph work/graph      # what breaks if we retire this server?
sdem dashboard --estate estates/history -o work/dashboard.html     # open it in your browser
```
The trace ends with **where the item is documented** — its Confluence pages and their open gaps. The dashboard shows everything, clickable, with a **Designs & gaps** tab.

### 10 · Tidy up the gaps
```bash
sdem designs --estate estates/history --gaps --status open
sdem designs accept  <gap id> --estate estates/history --person <your name> --note "risks stay in the risk register"
sdem designs resolve <gap id> --estate estates/history --person <your name> --note "added by hand as HIS-A3-…"
```
You do not have to close every gap at once — the dashboard keeps showing what is open.

### 11 · Save and share
```bash
git add estates/history
git commit -m "Onboard <design name> (LOAD-001)"
git push -u origin onboard/<name>       # then open a pull request; a reviewer merges it
```
Never add `work/` — it holds the export. **Your approvals become final when the pull request is merged.**

## 6. What each step does to the data

```mermaid
flowchart LR
    C[("Confluence")] -->|"export<br/>(you)"| X[("export folder<br/>pages · diagrams · pictures")]
    X -->|"sdem transform run"| W[("work/history<br/>CANDIDATE data")]
    W -->|"you review<br/>extraction-report.md"| W
    W -->|"sdem load"| E[("estates/history<br/>LOADED data")]
    E -->|"sdem link"| P[("work/links/proposals.json<br/>PROPOSED links")]
    P -->|"sdem approve<br/>(you)"| M[("estates/history/mappings.json<br/>APPROVED links")]
    E -->|"sdem build"| G[("work/graph<br/>KNOWLEDGE GRAPH")]
    M --> G
    G -->|"use"| U(["trace · impact · matrix · dashboard"])
    MM[["metamodel + schemas<br/>(the rulebook)"]] -.->|"checks every step"| W & E & P & M & G
```

**Only two steps create anything new:** the **transform** creates the architecture data; **`sdem build`** creates the graphs. Every other step reviews, moves, proposes or approves.

| Stage | Who | What happens to the data | Produces | Lives in | Stopped by | Data is now |
|---|---|---|---|---|---|---|
| **Export** | you / Confluence | pages, diagrams and pictures leave Confluence | an export folder (any layout) | `work/imports/…` — never committed | — | **raw** |
| **Transform** — `sdem transform run` | SDEM (rules; on-device OCR for pictures) | every item is accounted for — captured, skipped by design, or **not captured** (listed with its place and text); **the architecture data is created**: A1, A3, A4 entities and the links inside each architecture, each with its source | candidate datasets `a1/a3/a4-*.json`, `extraction.json`, `design-index.json`, `extraction-report.md` | `work/history` | nothing is refused — problems are **reported** so you can see them | **candidate**: right format, *not yet* reviewed, *maybe* not valid |
| **Review** | you | you decide what is right — validation cannot tell an OCR misread from a real name | the ids to reject | — | your judgement | **reviewed** |
| **Load** — `sdem load` | you run it | **the data is not changed**: the entities you keep are copied, unchanged, into the estate; the ones you reject are left out; your decision is recorded; what did not fit is kept as **gap records** | the estate's datasets (+ A2 with `--a2`), `designs/design-records.json`, `mappings.json` (empty for a new estate), `loads/LOAD-<n>.json` with the reconciliation | `estates/history` | **refused, nothing written**, if the estate would fail validation, an entity there would change, or the person is not a person | **loaded**: validated *and* reviewed |
| **Link** — `sdem link` | SDEM (rules engine) | links **between** architectures are **proposed**; those touching document-derived entities capped at low (DEC-E-11) | `proposals.json` | `work/links` | — (proposals only) | **proposed links** |
| **Approve** — `sdem approve` | you | a proposal becomes an approved record — your name, the date, the evidence, the BIAN release for BIAN links | records in `mappings.json` | `estates/history/mappings.json` | **refused** if evidence or the BIAN release is missing, or the reviewer is not a person | **approved links** |
| **Build** — `sdem build` | SDEM | **the graphs are created** from the loaded data and approved links | a graph per architecture, `federated.graph.json` (the knowledge graph), `designs.graph.json` (pages and gaps) | `work/graph` | **refused** if any data fails validation, or it is unloaded candidate data (CTL-23) | **ready** |

## 7. Validated and reviewed — both are needed

| | Means | Checked by | Example |
|---|---|---|---|
| **Validated** | follows the schemas and the metamodel (types, required attributes, allowed links) | SDEM, automatically — reported by the transform, **enforced** by the load and the build | "Payment Order" has no attribute list → fails |
| **Reviewed** | correct about the real design | **you** | an OCR misread passes validation but is wrong → you reject it |

The transform produces data that may be neither; the load accepts only data that is **both**. That is why the load exists: `link`, `approve` and `build` work on the estate, and the estate must hold only validated, reviewed data.

## 8. What did not fit — gap records

Nothing is thrown away. What does not fit an architecture entity is kept **beside** the estate — never inside the architectures, never in the knowledge graph — as **gap records** in `estates/history/designs/design-records.json`, with a **design record** for each source page (its facts, coverage and link).

| Kind of gap | Example |
|---|---|
| no entity type | a table of risks — a possible gap in the metamodel, for the owner |
| column not mapped | "Support hours: 24x7" — kept with its application |
| text not read | a sentence with no known name in it |
| needs a person | a photo or sketch |
| file not read | a PDF |
| rejected at load | an item you excluded |

You are told in the transform report, the load's output, `sdem trace` (*N open gap(s)*), `sdem designs`, and the dashboard (*What needs your attention*, the **Designs & gaps** tab). A gap is closed only by a person — `resolve` or `accept`, with a note, on record.

## 9. The metamodel and schemas — the rulebook, not an output

The metamodel (`metamodel/`) and the schemas (`schema/`) are **written and approved before any data**. Onboarding never generates or changes them; every step checks the data against them.

| Rulebook file | Used by | For |
|---|---|---|
| `metamodel/a1…a4-*.json`, `entity-attributes.json` | transform, load, check, build | which entity types exist, their attributes |
| `metamodel/level-relationships.json` | transform, load, check, build | which links are allowed **inside** an architecture |
| `schema/relationship-types.json`, `metamodel/relationship-rules.json` | transform, link | which links may exist **between** architectures; the engine's rules |
| `schema/level-model.schema.json`, `schema/entities/<A>/<Entity>.schema.json` | transform, load, check | the format of a dataset and of each entity |
| `schema/design-records.schema.json` | load, check, build | the format of design and gap records |
| `schema/relationship-registry.schema.json`, `mapping.schema.json` | approve | the format of an approved link |
| `schema/graph-store.schema.json` | build | the format of the graph store |
| `metamodel/transform-rules.json` | transform | how to read tables, diagrams and text (yours to tune) |

## 10. Next time

Repeat the steps for the next export, into the **same** `estates/history`. SDEM adds what is new, skips what is already there, and **stops** if something already there would change — so nothing is overwritten by accident. Gaps you have closed keep their status.

## 11. If something goes wrong

| You see | It means | Do |
|---|---|---|
| `no pages found` | the folder is not the export | point to the folder that holds the pages |
| many tables *no rule* | SDEM does not know your column names | step 1: copy the rules and add your words |
| `load` says `refused — nothing written` | an item breaks the rules, or one already in the estate would change | read the message; `--exclude` the item, or fix it |
| `approve` says `add --bian-release` | a connection to BIAN needs the BIAN release | add `--bian-release <release>` |
| `build` says `CTL-23` | you pointed it at `work/history` (the suggestions) | build from `--estate estates/history` |
| OCR errors on pictures | your Mac's text recognition is not available | add `--ocr off`; the pictures are listed for you as gaps |

## 12. Common questions

| Question | Answer |
|---|---|
| Is my design onboarded after step 11? | Yes, once the pull request is merged: it is in the estate, checked, connected and built — ready for queries and changes. |
| Does the transform produce the graph? | No — it produces the **architecture data** (candidates). The graph comes from `sdem build`. |
| Does the load change the data? | No. It **copies** the entities you keep, unchanged, into the estate, after checking the whole estate, and records your decision. |
| Why not just copy the files? | `sdem build` refuses unloaded candidate data (CTL-23); the load checks the estate as a whole, refuses conflicts instead of overwriting, and records who approved what. |
| Where do links between architectures come from? | `sdem link` proposes them from the loaded data; **you** approve them. The transform's "deployed on" findings are written as data so `sdem link` finds them. |
| Where does the metamodel come from? | It is the rulebook, written and approved beforehand. Nothing generates it from data. |
| Is A2 (BIAN) data taken from the designs? | Never (CTL-17). BIAN names found are listed as hints; your A2 dataset (from the BIAN catalogue) is added once with `--a2`. |
| Is the knowledge graph saved? | No — `work/graph/` is rebuilt from the estate with `sdem build` whenever needed. The estate is what you save. |
