# From a design to a trace — how SDEM links and traces

> **Status: current (v0.21.13)** — for architects: the question every architect asks first — *how does SDEM know that a business requirement depends on a server?* — answered step by step: how a design gets into SDEM, where every link comes from, what `sdem trace` does with them, and what comes from ArchiMate, TOGAF, BIAN and SDEM itself. Everything in the examples is made up.

## 1. The short answer

SDEM never guesses that a requirement needs a server. A trace from a business requirement to a technology node is a **chain of small links**, and every link in it was either **stated in the architect's design** or **approved by a person**. SDEM joins those links into a knowledge graph (`sdem build`) and walks it with its own declared rules (`sdem trace`) — down from a requirement to what runs it, or up from a server to everything that depends on it. Where a link is missing, the chain stops, and SDEM says so (`sdem trace GAPS`).

| Who | What they contribute |
|---|---|
| **The architect** | the facts: what exists, and how things connect inside each layer |
| **SDEM** (`sdem link`) | *proposes* the links between layers, from the design's own fields and names |
| **AID** (`sdem aid`) | *drafts* what the design leaves out — marked inferred or projected, never a fact |
| **A person** | confirms, rejects and approves — nothing between layers counts until approved |
| **SDEM** (`sdem build`, `sdem trace`) | joins the approved links and walks them; never adds one |

## 2. Getting a design into SDEM

SDEM's commands do not read prose themselves: they are deterministic, with no AI inside, so every record can say exactly where it came from. A design comes in one of three ways — often two of them together:

| Way | Best for | How | Uses AI? |
|---|---|---|---|
| **`sdem transform`** | existing Word, Excel or Confluence designs with inventory tables (applications, servers, interfaces, deployments) | `sdem transform run <export> -o <dir>` reads the tables by fixed rules; each row becomes a candidate citing its row, with an extraction report; a person runs `sdem load` — [Onboarding your existing designs](sdem-onboarding-workflow.md) | no |
| **An AI agent** (Copilot, Claude) | a design document in prose, or a new design from a request | the agent reads the document, maps each statement to a kind of record (`sdem types` says what may be written), and writes one change set per layer — every record citing its section (`document:design.md#4`); what the document does not say is left out and listed | yes — and SDEM checks everything it writes |
| **The architect's own change sets** | small additions and corrections | written in the terminal, or by editing records on DESNRE's workbench (which builds the change set; `sdem desnre pull` applies it) | no |

Whichever way, **nobody edits the layer files directly**: every change is a change set, checked against the metamodel before it is written (`sdem change propose … --dry-run`, then without). Anything the metamodel does not allow is refused, with the field or rule named. Tables through `sdem transform` and prose through an agent can feed the same workspace; `sdem change diff` flags possible duplicates.

## 3. Where each link comes from

There are two kinds of link, and they come from different places.

**Links inside a layer** — a process *realizes* a requirement, a capability *holds* processes, an interface *holds* operations. They come from the design itself (the document says so), each citing its source. SDEM checks that ArchiMate's rules allow the pair — a process may realize a requirement; a server may not.

**Links between layers** — a capability *supported by* a BIAN service domain, a business object *mapped to* a data entity, an application *deployed on* a server. These are the bridges a trace crosses, and they are handled more strictly:

1. **SDEM proposes them** (`sdem link`) from the design's own fields and names — an application that says where it runs, a data entity that says where it is stored. Each proposal says which rule proposed it and why.
2. **A person approves each one** (`sdem approve`), with the evidence its link type requires — usually the section of the design that says it. A proposal that is not approved is not followed by a trace.

**What the design leaves out** — AID (`sdem aid`) drafts it: the BIAN service domains a process implies, the parts a pattern requires, and (with `--complete-draft`) a first placement for what is still open. Everything AID adds is marked *inferred* or *projected*, with its confidence and reasoning, until a person confirms or rejects it. AID never invents a server, a network or an environment — those are design decisions it leaves open and lists. [Designing with AID](sdem-planning-with-aid.md) explains it in full.

## 4. A worked example

A made-up organisation's design says, in its document:

> *Customers must be able to pay online (requirement R-1). The **Take payment** process meets it. The **Payments app** runs that process. The Payments app runs on server **SRV-1**.*

**Step 1 — the records.** One for each thing named, in its layer, as an ArchiMate kind of element:

| Record | Layer | Kind |
|---|---|---|
| R-1 *Pay online* | Business | Requirement |
| PROC-PAY *Take payment* | Business | Business process |
| APP-PAY *Payments app* | Application | Application component |
| SRV-1 | Technology | Node (a server) |

**Step 2 — the links.** Three small ones, from the same sentences:

| Link | Where it comes from | Who checks or decides |
|---|---|---|
| ① PROC-PAY **realizes** R-1 | the document — inside the Business layer | SDEM checks ArchiMate allows *process realizes requirement* |
| ② PROC-PAY **served by** APP-PAY | crosses Business → Application — SDEM **proposes** it | **a person approves it**, citing the document |
| ③ APP-PAY **deployed on** SRV-1 | crosses Application → Technology — **proposed** from the application's "runs on" | **a person approves it** |

**Step 3 — `sdem build`** joins them into one graph:

```
R-1  ←realizes─  PROC-PAY  ─served by→  APP-PAY  ─deployed on→  SRV-1
(Business)       (Business)             (Application)          (Technology)
```

**Step 4 — `sdem trace`** walks it, either way:

- **down from R-1** — what *Pay online* depends on: *Take payment* → *Payments app* → **SRV-1**
- **up from SRV-1** — what depends on SRV-1: *Payments app* → *Take payment* → **R-1**. If SRV-1 fails, the requirement to pay online is at risk.

**If a link is missing** — say nobody has approved ② yet — the trace from R-1 stops at *Take payment*, and `sdem trace GAPS` reports that *Take payment* does not reach the Application or Technology layers. A person approves ②, and the chain is whole.

**If the design says only the first two sentences** — the requirement and the process — AID can draft the middle: with BIAN in the design, the service domain the process implies, one application per service domain (BIAN's pattern) and one deployment per application, each marked *projected*, low confidence. It does **not** draft the server: *runs on what?* stays an open gap until the architect says. The architect accepts each projection under a real name, replaces it or rejects it; only then are the links between layers proposed and approved.

## 5. How the trace walks

`sdem build` turns the design into SDEM's knowledge graph: one graph per layer, and the federated graph that joins them by the approved links between layers. `sdem trace` walks it with SDEM's **declared trace rules** (FT-01 to FT-15, each with its reason, in the metamodel and the [full-trace spec](design/sdem-full-trace-spec.md)). They say how a step is taken, for example:

- a record reaches what **the whole it is part of** reaches — a value stream stage through its value stream, a field through its data entity
- a consumer **depends on what serves it**
- information is followed through **BIAN's control records** (in a design with BIAN)
- a **security control** traces through the records it protects

So a record with no link of its own to another layer is **not** a gap when it reaches every other layer through what it is part of. `sdem trace GAPS` counts how many records reach every other layer, directly or through what they are part of, and lists each gap with the layers it does not reach — the same figures `sdem model integrity` reports for the design as a whole.

## 6. What comes from ArchiMate, TOGAF, BIAN — and what is SDEM's own

ArchiMate and TOGAF give SDEM its **vocabulary**; the **links between layers and the rules that walk them are SDEM's**, because the standards do not define them. Every item in SDEM's metamodel says which it rests on.

| Part | Comes from |
|---|---|
| **The layers** — Business, Data, Application, Technology | **TOGAF**'s four architecture domains (ArchiMate's layers follow them); **BIAN** adds the service-domain layer when a design uses it |
| **The kinds of record** (51) | 27 **ArchiMate 3.2**, 17 **BIAN**, 1 **TOGAF**, 6 SDEM's own — each drawn as an ArchiMate element |
| **The kinds of link inside a layer** (10) | all **ArchiMate 3.2** relationships — composition, aggregation, assignment, realization, serving, access, influence, triggering, flow, association |
| **Which record may link to which, inside a layer** (164 rules) | 103 from **ArchiMate**'s relationship rules, 23 following the Archi tool's implementation of ArchiMate, 6 from **BIAN**'s metamodel, the rest SDEM's own |
| **The link types between layers** (36 — SUPPORTED_BY, MAPPED_TO, DEPLOYED_ON …) | **SDEM's own**, each meaning an ArchiMate relationship (SUPPORTED_BY is *serving*, DEPLOYED_ON is *assignment*), with the evidence a person must give to approve one |
| **How links between layers are proposed** (`sdem link`) | **SDEM's own rules**, run on the design's fields and the BIAN catalogue |
| **How the trace walks** (FT-01 to FT-15) | **SDEM's own rules** — some citing ArchiMate as their reason |
| **The links in a given design** | **the architect's design**, and **the people who approve** |

Why the links between layers are SDEM's own: of 69 pairings of one layer's record with another's that SDEM checked against the published standards, BIAN supports 27 and ArchiMate 5; 31 have no official source at all. The standards do not say how a service domain connects to an application or a server, so SDEM defines those link types — and says which rest on a standard and which are its own.

## 7. A design without BIAN

Since SDEM 0.20, BIAN is an extension, not part of the core. Without it a design has the core's four layers — **A1 Business, A2 Data, A3 Application, A4 Technology** — and everything above holds: links inside each layer are ArchiMate relationships, approved links join the layers directly (*process served by application service*, *business object mapped to data entity*, *application deployed on node*), and SDEM's trace rules walk them, less BIAN's own (FT-07, FT-13). AID's step from a business process to an application rests on BIAN's pattern, so without BIAN, AID leaves that gap open and lists it.

**A known limit in 0.21.13:** for a design without BIAN, `sdem trace GAPS` still expects the BIAN layer and labels the layers by BIAN's numbering, so it counts no record as reaching every layer. The trace itself — which records and links are followed — is right; the gap figure is not. It is to be fixed in the next release.

## 8. The commands, in order

| Step | Command | Who |
|---|---|---|
| bring the design in | `sdem transform run` → `sdem load` · or change sets: `sdem change propose <file> --workspace <ws> --dry-run`, then without | the architect, or an agent for the architect |
| draft what is missing | `sdem aid --workspace <ws> --person <you>` | SDEM, on the architect's request |
| propose the links between layers | `sdem link --workspace <ws> --out <ws>/links` | SDEM |
| decide | `sdem aid confirm\|reject …` · `sdem approve <id> --proposals <ws>/links/proposals.json --workspace <ws> --reviewer <you> --evidence <kind>:<file>#<section>` | **a person only** |
| build the graph | `sdem build --workspace <ws> -o <graph>` | SDEM |
| trace | `sdem trace <record> --graph <graph> --direction down` (or `up`) | anyone |
| find the gaps | `sdem trace GAPS --graph <graph>` | anyone |
| what a change affects | `sdem impact <record> --change retire --workspace <ws>` | anyone |
| the whole design's integrity | `sdem model integrity --workspace <ws> --check` | anyone |

Every option of every command: the [CLI reference](reference/cli-reference.md). The kinds of record and link in plain words: [the metamodel in plain words](sdem-metamodel-guide.md).

## 9. In one paragraph — for whoever asks

*"The architect's design supplies the records and the links inside each layer; the kinds of record and link come from ArchiMate and BIAN, and ArchiMate's rules say which links are allowed. The links between layers are SDEM's own link types: SDEM proposes them from the design, AID drafts what the design leaves out, and a person approves each one. `sdem build` joins only what is stated or approved into a knowledge graph, and `sdem trace` walks it with SDEM's declared rules — down from a requirement to the server that runs it, or up from a server to every requirement that depends on it. Where a link is missing, the chain stops and SDEM reports the gap; it never invents a link."*
