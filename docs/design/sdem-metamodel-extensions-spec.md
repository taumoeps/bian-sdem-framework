# Metamodel extensions — cross-cutting architectures (security, resilience …) added to SDEM (spec)

> **Status: approved (2026-11-18) — the owner approved MX-D1…MX-D6 as recommended ("commit and start"); being built.** The owner's decision (2026-11-18): cross-cutting architectures such as security and disaster recovery are **not core layers**; they are added as a new kind of SDEM extension, a **metamodel extension**, which extends both the **metamodel** (types, attributes, links, rules that SDEM checks, traces and assesses) and **SDEM** (its own commands, e.g. `sdem security`). This needs one change to SDEM's core (§5), so the metamodel owner's approval (AGENTS.md rule 2). Builds on the [extensions contract](sdem-extensions-spec.md) (EXT-01…EXT-15) and the [profile](sdem-profile-spec.md) merge (PR-01…PR-12).

## 1. Why

SDEM's core is four layers, A1 Business to A4 Technology, joined by nine cross-layer link types. Some architectures are not a layer: **security, resilience (disaster recovery), privacy, observability** cut across all four. A security control protects a business process, a service domain's data, an interface and a network zone at once.

Today neither mechanism can hold them:

| | Can add record types | Can link into every layer | Can add commands |
|---|---|---|---|
| Extension (EXT-01…EXT-15) | no — uses SDEM only through its commands (EXT-02) | no | yes (`sdem <name>`, EXT-15) |
| Profile (PR-01…PR-12) | yes — but each type extends a type **of one layer** (PR-03) | no — the nine link types are fixed (PR-02) | no |
| **Metamodel extension (this spec)** | **yes, in its own cross-cutting aspect** | **yes, through link types it declares** | **yes** |

Kept outside SDEM's data, a security model would not be checked, traced, approved or seen by the agent and the Design document — two sources of truth. A metamodel extension keeps it **in the design**, so every viewpoint is drawn from one dataset.

## 2. What a metamodel extension is

| Id | Rule |
|---|---|
| **MX-01** | A metamodel extension is an SDEM extension (EXT-01) whose manifest declares `"kind": ["metamodel", …]` and ships an **aspect**: a data file (`aspect.json`, format `sdem-aspect/1`) that adds to the metamodel. It may also ship commands, run as `sdem <name> …` (EXT-15). One package, installed like any extension (`pip install sdem-security`). |
| **MX-02** | **An aspect is a cross-cutting architecture**, not a layer: it has an id (`SEC`, `RES`), a name ("Security architecture") and its own record types, named `<ASPECT>.<Name>` (`SEC.SecurityControl`, `SEC.Threat`, `RES.RecoveryPlan`). Its records live in the workspace in their own file, `aspect-<id>.json` (`aspect-sec.json`), beside `a1-…`–`a4-…`. |
| **MX-03** | **Adds, never changes** (as PR-02): an aspect cannot redefine, remove or rename an SDEM type, attribute, link type, impact rule or requirement disposition; it cannot change A1–A4. `sdem extensions check` refuses one that tries. |
| **MX-04** | **Its types** declare attributes (the profile's attribute kinds, PR-04), required or optional, and rules (PR-10, PR-11, PR-15, PR-16 forms). `sdem check` enforces them as SDEM's own. |
| **MX-05** | **Its links into the layers**: an aspect declares its own **cross-cutting link types** — e.g. `PROTECTS` (SEC.SecurityControl → any A1–A4 record, or named types), `MITIGATES` (control → threat), `APPLIES_TO` (threat → A1–A4 record) — each with the types allowed at each end, the evidence an approval needs, and an ArchiMate relationship it maps onto (`influence`, `realization`, `association`). They are proposed and approved like SDEM's own links (`sdem link`, `sdem approve`), never written by an agent (CTL-21). |
| **MX-06** | **Inside the aspect**, links between its own types are declared like a profile's link kinds (PR-05), each mapped to an ArchiMate kind. |
| **MX-07** | **Requirements**: an aspect may add requirement categories (PR-12) and say which of its types realise a category (`SEC.SecurityControl` realises `security` requirements), so `sdem requirements evaluate` covers it. |
| **MX-08** | **Trace and impact follow it**: `sdem trace` and `sdem impact` follow the aspect's approved links, and an aspect declares its impact rules (retiring a protected record leaves its control without a target; retiring a control leaves its records unprotected). |
| **MX-09** | **Sources, not copies.** An aspect's reference catalogue (e.g. a control catalogue) cites its public source and licence; only openly licensed text is shipped. The security aspect uses **NIST CSF 2.0 and NIST SP 800-53** (US government works, public domain); proprietary catalogues (ISO/IEC 27001 Annex A text, CIS Controls) are cited by identifier only, never reproduced. |

## 3. How it is switched on

| Id | Rule |
|---|---|
| **MX-10** | **Installed is not active.** A workspace uses an aspect only when its profile includes it — `sdem profile include ext:security --workspace … --person …` (as `sdem:` standards today, PR-13) — a person's decision, recorded. A workspace without it is unaffected. |
| **MX-11** | **Versioned like SDEM's metamodel.** An aspect has a version and declares the SDEM and metamodel versions it supports (EXT-04); `workspace.json` records which aspects, at which versions, a workspace uses; a graph store keeps them (as PR-07). A newer aspect version that changes a type ships a migration, as SDEM's own do. |
| **MX-11a** | **Never silently dropped.** A workspace that includes an aspect which is not installed, or whose supported range does not cover the installed SDEM or metamodel, is **refused** by every command that reads it, with a message naming the aspect, its range and what to install or upgrade — never checked as if the aspect's records were not there (as a failing profile refuses, PR-07). |
| **MX-11b** | **Upgrades say what they break.** An aspect names the core types, attributes and link types it builds on (`builds_on` in `aspect.json`). Before an upgrade, `sdem extensions check --against <version>` reads SDEM's metamodel migrations and reports, per installed aspect, anything it names that the new version renames or removes — so an aspect is released for the new version before the workspace moves, and the workspace's aspect data is never left unreadable. |
| **MX-12** | **Provenance shows.** Every aspect type and link carries `evidence_status: aspect_defined` and the aspect's name, so a reviewer tells SDEM's own vocabulary, an organisation's (profile) and an aspect's apart. |

## 4. What it can add to SDEM

| Id | Rule |
|---|---|
| **MX-13** | **Commands** through EXT-15: `sdem security …`, e.g. `sdem security coverage` (which records are protected, by which controls, against which threats), `sdem security review` (a reviewer's list of what is unprotected or unevidenced). Read-only, `--json`, `--dry-run` where it writes (EXT-07, EXT-08). |
| **MX-14** | **Standards and patterns** an aspect ships run in `sdem comply` (PR-13…PR-24), e.g. "every internet-facing zone's interfaces use oauth2 or mutualTLS", "every personal-information entity is protected by an encryption-at-rest control". |
| **MX-15** | **Viewpoints**: an aspect may describe its viewpoint (which of its types and links to draw, and how), so DESNRE draws it as a **vertical plate** beside the A1–A4 stack in the 3D view, with lines into each layer, and as a figure in the Design document — one view model for both, as the [Architecture viewpoint](sdem-architecture-viewpoint-spec.md). |

## 5. The one core change

SDEM loads the metamodel as **core + active profile** today (`Metamodel.load()`, PR-06). This adds a third source and the cross-cutting rules:

1. `Metamodel.load()` merges **core + aspects the profile includes + profile**; `Metamodel.base()` stays SDEM's own (PR-06).
2. Record files `aspect-<id>.json` are read with the layer files (`sdem check`, `load`, the graph store).
3. Cross-layer link checking accepts an aspect's declared link types between its types and A1–A4 records (MX-05); the nine core link types are unchanged.
4. `sdem trace` / `sdem impact` follow approved aspect links (MX-08).
5. `sdem extensions check` validates an aspect file (MX-03).

No change to A1–A4, to the nine link types, to inference (`sdem aid` infers nothing for an aspect in the first version — §9, MX-D4) or to existing workspaces.

## 6. The first two aspects (worked examples)

| Aspect | Types (first version) | Links into A1–A4 | Built on |
|---|---|---|---|
| **Security (`SEC`)** — `sdem-security` | `SecurityControl` (control id from the catalogue, kind: preventive · detective · corrective, implemented: yes · partly · planned, evidence), `Threat`, `TrustBoundary`, `DataClassification` | `PROTECTS` control → any record; `MITIGATES` control → threat; `APPLIES_TO` threat → record; `BOUNDS` trust boundary → zone or component | NIST CSF 2.0 functions; SP 800-53 control families; SDEM's existing `personal_information`, `access_classification`, `security_scheme`, `zone_kind`, `internet_facing`, `encrypted` |
| **Resilience (`RES`)** — `sdem-resilience` | `RecoveryTier` (RTO, RPO), `RecoveryPlan`, `FailoverPair` | `COVERS` plan → A1 process / A3 component / A4 node; `PAIRS` A4 ↔ A4 (different regions) | SDEM's `recovery` and `availability` requirement categories; the DR rules in the profile spec's examples (PR-10, PR-11) |

Each ships synthetic data for SDEM's examples (payment-initiation-v3), tests (EXT-14) and its viewpoint (MX-15). The security aspect's own spec: [`sdem-extensions/security/docs/security-aspect-spec.md`](https://github.com/taumoeps/sdem-extensions/blob/main/security/docs/security-aspect-spec.md).

## 7. Where they live

In **[sdem-extensions](https://github.com/taumoeps/sdem-extensions)** (public, Apache 2.0), one folder each (`security/`, `resilience/`), beside the DESNRE publisher: the aspect file, the commands, the tests. SDEM's own repository changes only by §5.

## 8. Tests

- An aspect that redefines an SDEM type, or a link type that names an unknown type, is refused (MX-03).
- A workspace without the aspect is byte-for-byte unaffected; with it, `sdem check` enforces its rules, `sdem link`/`approve` handle its links with evidence, trace and impact follow them (MX-05, MX-08).
- The payment-v3 example with the security aspect: every PII entity has a `PROTECTS` from an encryption control; the two paths with `encrypted` not given are reported unresolved, not compliant.

## 9. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| MX-D1 | A new extension kind `metamodel`, adding to the metamodel and to SDEM's commands | **yes** — the owner's direction, 2026-11-18 |
| MX-D2 | The core change in §5 (aspects merged into the metamodel; aspect link types accepted; trace and impact follow them) | **yes** — the smallest change that lets a cross-cutting architecture be checked, traced and approved like the layers |
| MX-D3 | Switched on per workspace by the profile (`sdem profile include ext:<name>`) | **yes** — installed is not active (MX-10) |
| MX-D4 | No inference for aspects in the first version | **yes** — every aspect record and link comes from a person or a source; inference rules later, by spec |
| MX-D5 | Security first, on NIST (public domain) | **yes**; resilience second |
| MX-D6 | Metamodel version: a minor bump (0.18.0), with migration of nothing (aspects are additive) | **yes** — the usual bump: migrate the examples, rebuild their graph stores, regenerate, freeze |
