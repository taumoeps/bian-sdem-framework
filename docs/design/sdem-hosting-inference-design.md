# Hosting — cloud first by default, on premises by evidence, a person decides

> **Status: approved and built — the owner approved H1–H8 (2026-11-14); metamodel 0.11.0, SDEM 0.18.0.** Built: `metamodel/hosting-signals.json` (HS-01…HS-09), attributes `site`, `cloud_provider`, `region` (AT-A4-37…39), the `inferred` mark on links, the profile's `hosting` (PR-32), `sdem new --hosting` (WS-12), zone proposals in `sdem aid` with `sdem aid confirm|reject <shape>` (AID-Z01…Z04), LC-19, LC-20, the zone connections ZC-01…ZC-04 (`sdem/hosting.py`) and `sdem zones`; tests `tests/test_hosting.py`. One change from §2, made while building: without `--hosting` a new workspace starts with no zones, and `sdem aid` proposes them from the default — so no zone is written that nobody chose. It follows network zones (metamodel 0.10.0; [design](sdem-network-zones-design.md)): every A4 shape is in a zone, and a level-0 zone is on premises or cloud. This page says how a shape's zone is **proposed** — from the organisation's default and the evidence in the records — and how a person **decides** it. A metamodel change: it needs the owner's approval, a new `metamodel_version` and a migration.

## 1. The problem

SDEM can check that every shape is in a zone (LC-16), but it cannot say which zone a shape *should* be in. Today a person places every shape by hand. Most designs follow the organisation's hosting policy — often *cloud first* — with exceptions: a mainframe, a physical device, a system the bank keeps in its own data centre. SDEM should propose the placement and say why; it must never decide it (CTL-21, the AID principle).

## 2. The organisation's default (H1, agreed)

The organisation profile states its hosting policy and the zone templates it uses (proposed **PR-32**):

```json
"hosting": {
  "default": "cloud",
  "templates": {
    "cloud":       ["cloud", ["dmz", "internal", ["private"]]],
    "on_premises": ["on_premises", ["dmz", "internal"]],
    "hybrid":      ["cloud", "on_premises"]
  }
}
```

With no profile setting, SDEM's default is **cloud**. `sdem new --workspace … --hosting cloud | on_premises | hybrid` (proposed **WS-12**) creates the template's empty zones; without `--hosting`, the profile's default.

## 3. The evidence (H4, agreed: this list first; organisations add their own)

A table of signals, as data (`metamodel/hosting-signals.json`, reviewable like the transform rules), each with an id, what it reads, which way it points and how strongly. An organisation's profile adds its own (its product names, naming conventions, CMDB fields).

| Id | Signal | Points to | Confidence |
|---|---|---|---|
| HS-01 | a `site` or `data_centre` value on the shape (new attribute AT-A4-37) | on premises | high |
| HS-02 | the name or product says mainframe, LPAR, z/OS, AS/400, IBM i, iSeries | on premises | high |
| HS-03 | the shape is an `A4.Device` — physical computing hardware | on premises | medium |
| HS-04 | the name or product says vSphere, ESXi, bare metal | on premises | medium |
| HS-05 | its environment's `cloud_deployment_model` (AT-A4-17, NIST SP 800-145) is `public` | cloud | high |
| HS-06 | a `cloud_provider` or `region` value (new attributes AT-A4-38, AT-A4-39) | cloud | high |
| HS-07 | the name or product is a provider's managed service (e.g. EKS, AKS, GKE, RDS, Cloud SQL) | cloud | high |
| HS-08 | a technology service delivered as IaaS, PaaS or SaaS (`cloud_service_model`, AT-A4-19) | cloud | medium |
| HS-09 | the name says *managed* | cloud | low |
| HS-10 | no signal: the organisation's default (H1) | the default | low |

Provider and product names are used only to recognise what a record names; SDEM claims no affiliation with them.

## 4. The proposal (H2, agreed: always a proposal; a person confirms)

`sdem aid` (proposed **AID-Z01…AID-Z04**) proposes a zone for each A4 shape that is in none:

- **AID-Z01 level 0** — from the strongest signals: on premises or cloud. Signals on both sides at medium or above: **unresolved**, both cited, never guessed.
- **AID-Z02 level 1** — `internet_facing: true` → the DMZ; otherwise internal.
- **AID-Z03 level 2** — never proposed: a private network is a design decision.
- **AID-Z04 only what is not hosted** — a deployment, an artifact or software on a node is in its host's zone (RA4-38); only its host gets a proposal.

Each proposal is a placement link (RA4-38) **marked inferred** — source (the signal ids and the values read), reasoning, confidence — and creates the template's zones if the workspace has none. `sdem status` lists what waits; `sdem aid confirm` or `sdem aid reject` decides, by a person (CTL-16, CTL-21).

## 5. A system on both sides (H3, agreed)

Each platform is placed on its own: cloud production with on-premises disaster recovery is two platforms in two level-0 zones, connected because both exist (zones design §2). There is no "hybrid shape".

## 6. Checks

| Id | Rule | Severity |
|---|---|---|
| LC-19 | an inferred zone placement not yet confirmed or rejected | warning (as CTL-16 for inferred records) |
| LC-20 | a shape in a zone that its own evidence contradicts at high confidence (a mainframe in a cloud zone) | warning |

## 7. Decisions for the owner

| # | Question | Recommendation |
|---|---|---|
| H5 | An inferred placement is a **link** carrying an `inferred` mark (a metamodel change: a within-layer link may carry `inferred`, as a record does), or a separate proposals file that becomes links on confirmation? | **the link, marked** — one source of truth, as AID's inferred records |
| H6 | New attributes: `site` (AT-A4-37), `cloud_provider` (AT-A4-38), `region` (AT-A4-39) on A4 platforms? | **yes** — explicit data beats name matching |
| H7 | The examples: legacy-core-ledger's LPAR proposed on premises (HS-02); payment-initiation proposed cloud (HS-09 + the default); and payment-initiation made hybrid — a made-up on-premises core ledger the Execution Gateway posts to, so Cloud ↔ On premises is drawn | **yes** — all made up |

Version: metamodel **0.11.0** — the signal table, three attributes, the `inferred` mark on links (H5), checks LC-19 and LC-20; profile PR-32; `sdem new --hosting` (WS-12); AID-Z01…AID-Z04.

## 8. Zone connectivity (H8, approved)

The connections between zones are SDEM's rules, worked out from the zone structure — never records — in one place (`sdem/hosting.py`), read by `sdem zones`, the checks and the pictures:

| Id | Rule |
|---|---|
| ZC-01 | level-0 zones are connected with each other (on premises ↔ cloud) when a workspace has both |
| ZC-02 | the level-1 zones of one level 0 are connected with each other (DMZ ↔ internal) |
| ZC-03 | a zone is connected with the zone it is part of |
| ZC-04 | a shape reaches another through their zones — `sdem zones path A B` names the route |
| ZC-05 | what a lost zone connection cuts off — `sdem zones cut A B`: the A4 links with one end on each side, and everything that depends on their ends up to A1 (trace up). Nesting is containment, not a way round a firewall: cutting ZC-03 puts the inner zone against the rest, cutting ZC-01 or ZC-02 the one zone against the other (the owner, 2026-11-14) |
