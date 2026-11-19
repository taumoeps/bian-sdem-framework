# Metamodel extensions — cross-cutting architectures (security, resilience …) added to SDEM (spec)

> **Status: approved (2026-11-18) — the owner approved MX-D1…MX-D6 as recommended ("commit and start"); being built.** The owner's decision (2026-11-18): cross-cutting architectures such as security and disaster recovery are **not core layers**; they are added as a new kind of SDEM extension, a **metamodel extension**, which extends both the **metamodel** (types, attributes, links, rules that SDEM checks, traces and assesses) and **SDEM** (its own commands, e.g. `sdem security`). This needs one change to SDEM's core (§5), so the metamodel owner's approval (AGENTS.md rule 2). Builds on the [extensions contract](sdem-extensions-spec.md) (EXT-01…EXT-15) and the [profile](sdem-profile-spec.md) merge (PR-01…PR-12).

> **Part 2 (§10–§15), 2026-11-19 — proposed, for the owner's decisions MX-D7…MX-D16 (§15):** three kinds of metamodel extension —
> **vertical** (a layer across A1–A4, as security), **horizontal** (more types inside one layer, e.g. a later network extension for A4)
> and **bridge** (what joins two others) — what the security build taught every future vertical one, and how SDEM tracks them all.
> No horizontal or bridge extension exists yet; the network extension's own spec is not written here.

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
| **MX-16** | **Switched off by a person, archived not lost** (2026-11-19, after the audit's AUD-01). `sdem profile exclude <ref> --workspace … --person … --reason …` is the counterpart of `include`: the layers the part added and **every connection that touches their records** leave the design together, kept whole in `archive/<name>-<date>.json`; the connections' ids are kept in `archive/retired-mappings.json`, so no new link is ever given one (`sdem approve`, `connect`, `reject` count them); the decision is recorded (`exclude_from_profile`). The design passes its checks afterwards. An extension may wrap it (`sdem security remove`). |
| **MX-17** | **Rules an extension computes are rules a person can except** (2026-11-19, AUD-02). A pack may list `computed_rules` (`id`, `message`) — checks its own commands run because SDEM's rule language cannot express them (e.g. SEC-S07, SEC-S08). `sdem exception grant --rule <id>` accepts them like the profile's rules (PR-18), and the extension reads `exceptions.json` to report them as `exception_approved`. |
| **MX-12** | **Provenance shows.** Every aspect type and link carries `evidence_status: aspect_defined` and the aspect's name, so a reviewer tells SDEM's own vocabulary, an organisation's (profile) and an aspect's apart. |

## 4. What it can add to SDEM

| Id | Rule |
|---|---|
| **MX-13** | **Commands** through EXT-15: `sdem security …`, e.g. `sdem security coverage` (which records are protected, by which controls, against which threats), `sdem security review` (a reviewer's list of what is unprotected or unevidenced). Read-only, `--json`, `--dry-run` where it writes (EXT-07, EXT-08). |
| **MX-14** | **Standards and patterns** an aspect ships run in `sdem comply` (PR-13…PR-24), e.g. "every internet-facing zone's interfaces use oauth2 or mutualTLS", "every personal-information entity is protected by an encryption-at-rest control". |
| **MX-15** | **Viewpoints**: an aspect may describe its viewpoint (which of its types and links to draw, and how), so DESNRE draws it as a **vertical plate** beside the A1–A4 stack in the 3D view, with lines into each layer, and as a figure in the Design document — one view model for both, as the [Architecture viewpoint](sdem-architecture-viewpoint-spec.md). |

## 5. The one core change — as built (2026-11-18)

Building it showed SDEM already had most of what an aspect needs: the **layer registry** (LR-01…LR-10, v0.13.0) lets a profile add a layer with its own record file, types, link types, agent and requirements, and trace, impact, check and change sets already work across such layers. So an aspect **is a profile layer**, and the core change is small:

1. **`position: across`** (LR-11): a layer beside the stack whose link types may join any layer, not only its neighbour (`sdem/profile.py` check, `sdem/layers.py`, `schema/profile.schema.json`).
2. **`includes: ["ext:<name>"]`** (MX-01, MX-10): a profile includes an installed metamodel extension's pack — a profile file of its own, named in the extension's manifest (`kind: ["metamodel"]`, `pack`) — folded in, adding only (PR-14); `sdem profile include ext:<name>` is a person's recorded decision.
3. **Refused, never skipped** (MX-11a): the extension not installed, not a metamodel extension, or not supporting this SDEM — every command on the workspace stops with a message naming it.

So the aspect's records live in the layer's own file (e.g. `security.json`), its types are named as profile layer types are (`SEC.S.SecurityControl` — organisation, layer, name), and its links into A1–A4 use ArchiMate kinds SDEM knows (association, realization, …). **SDEM's metamodel files do not change**, so no metamodel version bump (MX-D6 not needed). Not yet built: `sdem extensions check --against <version>` (MX-11b).

## 6. The first two aspects (worked examples)

| Aspect | Types (first version) | Links into A1–A4 | Built on |
|---|---|---|---|
| **Security (`SEC`)** — `sdem-security` | `SecurityControl` (control id from the catalogue, kind: preventive · detective · corrective, implemented: yes · partly · planned, evidence), `Threat`, `TrustBoundary`, `DataClassification` | `PROTECTS` control → any record; `MITIGATES` control → threat; `APPLIES_TO` threat → record; `BOUNDS` trust boundary → zone or component | NIST CSF 2.0 functions; SP 800-53 control families; SDEM's existing `personal_information`, `access_classification`, `security_scheme`, `zone_kind`, `internet_facing`, `encrypted` |
| **Resilience (`RES`)** — `sdem-resilience` | `RecoveryTier` (RTO, RPO), `RecoveryPlan`, `FailoverPair` | `COVERS` plan → A1 process / A3 component / A4 node; `PAIRS` A4 ↔ A4 (different regions) | SDEM's `recovery` and `availability` requirement categories; the DR rules in the profile spec's examples (PR-10, PR-11) |

Each ships synthetic data for SDEM's examples (payment-initiation-v3), tests (EXT-14) and its viewpoint (MX-15). The security aspect's own spec: [`sdem-extensions/metamodel/security/docs/security-aspect-spec.md`](https://github.com/taumoeps/sdem-extensions/blob/main/metamodel/security/docs/security-aspect-spec.md).

## 7. Where they live

In **[sdem-extensions](https://github.com/taumoeps/sdem-extensions)** (public, Apache 2.0), laid out by kind (2026-11-19): `metamodel/<name>/`
for metamodel extensions — vertical, horizontal and bridge alike (the manifest's `scope` and `requires` say which, MX-18, MX-41) —
`publishers/` (e.g. DESNRE's publisher) and `templates/`. Each folder is its own package: the pack, the commands, the tests, the docs.
SDEM's own repository changes only by §5 and the core rules of §10–§14 (MX-44).

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
| MX-D6 | Metamodel version: a minor bump (0.18.0), with migration of nothing (aspects are additive) | *As built: not needed — the metamodel files do not change (§5).* |

## 10. Three kinds of metamodel extension (Part 2)

| Kind | What it adds | Its records live | Example |
|---|---|---|---|
| **Vertical** | a **layer across** A1–A4 (LR-11): its own types, and link types that reach any layer | in its own file (`security.json`) | security (S1–S5) |
| **Horizontal** | **extends the stack** (BX-43, 2026-11-20): **more types inside one core layer**, each extending a type SDEM has there (PR-03), with their attributes, link kinds and rules — or **a layer of its own between core layers** (the reserved A2, LR-01a) | in that layer's file (`a4-technology.json`; `a2-service-domain.json`) | network, for A4 (planned); **BIAN**, A2 ([BIAN extension](sdem-bian-extension-spec.md)) |
| **Bridge** | **only what joins two or more extensions**: link types between their types, rules, viewer features — no records of its own | (its links in `mappings.json`) | network-security (planned) |

| Id | Rule |
|---|---|
| **MX-18** | **An extension states its kind and scope in its manifest**: `"scope": {"across": ["S"]}` (vertical), `{"within": ["A4"]}` (horizontal), or both for a bridge, with `"requires"` (MX-41). SDEM checks the pack against it: a vertical pack adds an `across` layer and no types inside a core layer; a horizontal pack adds no layer and only types that extend a type of the layer it names; a bridge adds no layer and no types. A pack that does more than its scope says is refused. |
| **MX-19** | **No extension changes another or the core** (MX-03, for all three kinds): it adds, never redefines, removes or renames. Type names are namespaced by the extension (`SEC.`, `NET.`); a name another active extension or the core already uses is refused. |

## 11. Vertical metamodel extensions — what the security build taught (Part 2)

Security was the first vertical extension; its two audits (sdem-extensions `metamodel/security/docs/audit-2026-11-19.md`, AUD-01…AUD-36) found what a vertical extension needs beyond §2–§4. Every future one (resilience, privacy, observability) follows these.

| Id | Rule | Learned from |
|---|---|---|
| **MX-20** | **Sub-layers are an attribute, not files.** A vertical layer may divide into views of the core layers (S1–S5 for A1, A2, A3 data, A3 applications, A4) by a required attribute on its types (`security_layer`) — one file, one layer code. | SX-D2 |
| **MX-21** | **One scope, read from the pack.** What the extension's commands cover — coverage, checklists, "unprotected" lists — is the set of types its link types may reach, read from its own pack, never a second list in its code; a test holds them together. | AUD-04, AUD-07 |
| **MX-22** | **Only what can act counts.** A record of the extension that is retired, deprecated or marked not applicable (e.g. `implementation_status: not_applicable`) never counts towards coverage or a check. | AUD-03 |
| **MX-23** | **Its own checks follow SDEM's outcomes**: not decidable yet (a planned subject, a proposed requirement) → `unresolved`, not `non_compliant` (PR-11a); listed as `computed_rules` (MX-17) so a person can except them; a check that names something other than a record (e.g. an empty sub-layer) is reported, not exceptable. | AUD-02, AUD-27 |
| **MX-24** | **It fails clearly, never with a false all-clear.** Its commands stop with a message when SDEM's own answer (e.g. `sdem comply`) fails, is in a form it does not know, or its standard is missing from the profile; findings are taken by the standard's id, never by a name prefix. | AUD-06 |
| **MX-25** | **One meaning for its key words.** Where a word such as *protected* can mean "a control of its own" or "through what holds it", the extension defines it once (its coverage) and every consumer — its document, the viewer, the agent — says which it gives. | AUD-28 |
| **MX-26** | **It publishes its own results.** Read-only commands give `--json` for a publisher (a review, coverage, a checklist) and one gives a readable document (`sdem <name> document`), so a viewer and its agent quote the extension instead of working its findings out. Its manifest's `viewer` (EL-01) lists them. | EL-01, the agent's `security_review` |
| **MX-27** | **Its whole life is commands** (the [extension lifecycle](sdem-extension-lifecycle-spec.md), EL-01…EL-17): `remove`, `restore`, `purge` over SDEM's `profile exclude`, `restore`, `purge`; each says what happens to a published copy. Its records are never deleted by switching off. | AUD-01, EL |
| **MX-28** | **It is tested and documented to one standard**: unit tests of its own logic that run without SDEM; tests with SDEM that make each rule and check fire (never a test that passes on an empty result); CI against SDEM's release tag and `main`, on Linux and Windows; a README with *What you get, and from where*, the two ways to install, and every removal step; an independent audit before its first release. | AUD test gaps, the CI fixes |
| **MX-29** | **Its records are made-up in examples, its catalogues public.** Shipped reference content (a control catalogue) is openly licensed, with its source pinned to a commit and a checksum; proprietary frameworks are cited by identifier only (MX-09). | MX-09, AUD-20 |

## 12. Horizontal metamodel extensions (Part 2)

| Id | Rule |
|---|---|
| **MX-30** | **Types inside one core layer, by inheritance.** Each type `extends` a type SDEM has in the layer the scope names (PR-03) — e.g. a firewall extends `A4.Node`, a subnet `A4.CommunicationNetwork` — and inherits its attributes, link rules, cross-layer link types, impact rules and its place in requirements analysis. It may add attributes (PR-04), link kinds inside the layer mapped to ArchiMate kinds (PR-05), and rules (PR-10…PR-16). |
| **MX-31** | **Cross-layer links come from the parent types**, so the layers above and below need no change: an A3 component already DEPLOYED_ON an `A4.Node` may be DEPLOYED_ON a firewall. A horizontal extension adds a cross-layer link type only to the layer directly above or below (LR-06), never across the stack — that is a vertical or a bridge extension's. |
| **MX-32** | **Other extensions reach its types through their parents.** A link type another extension declares to a core type (security's PROTECTS to `A4.Node`) reaches the horizontal extension's subtypes of it, without either knowing the other. *To be proved by a test before the first horizontal extension (§14): a vertical pack's link type to a core type accepts a horizontal pack's subtype.* |
| **MX-32a** | **An extension's own scope follows inheritance too.** Where an extension's commands decide what is in their scope — coverage, checklists, "unprotected" lists (MX-21) — a subtype of a type in scope is in scope: a vertical extension's coverage of `A4.Node` includes a horizontal extension's `NET.A4.Firewall`. Matching a record's type exactly, as `sdem security` 0.2.0 does, would silently leave such records out although SDEM accepts links to them. The test MX-44 asks for covers the extension's commands, not only SDEM's link check. |
| **MX-33** | **Its records live in the core layer's file**, marked by their type. Switching it off (MX-16) therefore archives **by type**: every record of its types, every link inside the layer and every connection that touches them leave `a4-technology.json` and `mappings.json` together, kept whole in its archive — and a record of a core type it touched is never changed. Restore and purge (EL-06, EL-16) work the same way. *Needs `sdem profile exclude` to archive by type as well as by file (§14).* |
| **MX-34** | **A viewer draws its types as their parents unless told otherwise.** The manifest's `viewer` names, per type, the core shape it is drawn as (a firewall as a node, a subnet as a network) and may name its own; DESNRE's registry (EL-02) gives it features on the layer's existing views — no tab or 3D stack of its own. The design document's section for that layer (e.g. 9.6 Technology architecture) gains its types; there is no new section. |
| **MX-35** | **Its checks and documents are the layer's.** Its rules run in `sdem comply` and `sdem check` like the layer's own; `sdem document --layer A4` shows its types in their own sections. A horizontal extension may also publish its own results (MX-26), e.g. a network document. |

## 13. Bridge metamodel extensions (Part 2)

| Id | Rule |
|---|---|
| **MX-36** | **What a bridge is.** A small metamodel extension that `requires` two or more others, each with a version range (`"requires": {"security": ">=0.2,<0.3", "network": ">=0.1,<0.2"}`), and adds **only what joins them**: link types between their types (a firewall rule ENFORCES a trust boundary), rules across them (every internet-facing subnet is bounded), and viewer features (e.g. firewall rules on the security plates). It has no layer and no records of its own; its links are approved by a person like any other and kept in `mappings.json`. |
| **MX-37** | **Two extensions never join each other directly.** Neither a vertical nor a horizontal extension names another extension's types; anything that would is a bridge's. So each extension can be versioned, switched on and off, and tested alone, and a new extension edits none of the existing ones. |
| **MX-38** | **A person switches a bridge on — SDEM suggests it.** Installing a bridge changes no workspace. `sdem status` in a workspace where everything a bridge requires is on says so and gives the command (`sdem profile include ext:<bridge> …`); SDEM never includes it by itself — it changes what the design is checked against (MX-10). Including a bridge whose requirements are not all on, or not in range, is refused with the reason. |
| **MX-39** | **Switching off respects what depends on it.** Excluding an extension a bridge requires, while the bridge is on, is refused — naming the bridge — unless the person excludes the bridge first, or both together (`sdem profile exclude ext:security ext:network-security`): the bridge's links are archived with it (MX-16). Restoring follows the order the other way. |
| **MX-40a** | **A bridge may ship inference rules for its own link types.** In SDEM's rule form (`metamodel/relationship-rules.json`, AID-…), a bridge pack may add rules that propose its link types — e.g. *a firewall in a zone a trust boundary bounds → propose that the firewall ENFORCES it* — each with its evidence class. `sdem aid` runs them with SDEM's own; every inference is a proposal a person confirms or rejects (CTL-21), and the bridge's document (`sdem <bridge> document`) is the combined view as recorded fact. Without a bridge, AID has no link types between two extensions and infers nothing between them. *Needs: a pack may add inference rules (MX-44).* |
| **MX-40b** | **Without a bridge, reasoning across extensions is inference, said to be one.** An AI agent (the site's design agent) or a tool may read two extensions that no bridge joins and derive how they relate — through inheritance (MX-32), where records sit, and the metamodel — but only as inference: in chat worded as derived ("the design does not record this; from where the records sit…"), in a design document only in *Suggestions (not from the design)*; never written as links, never presented as the design. It names what a bridge would let the design record. With a bridge, such derivations become proposals a person approves (MX-40a). SDEM's own documents stay one per layer and per extension; the joins between them show only as the connections the design holds. |
| **MX-40** | **A bridge has an owner and its own tests**: its manifest names who maintains it; its CI installs every extension it requires at the edges of their ranges. |

## 14. Tracking and managing metamodel extensions (Part 2)

| Id | Rule |
|---|---|
| **MX-41** | **The manifest says what an extension depends on**: `scope` (MX-18); `requires` — other extensions, with ranges (a bridge; a horizontal extension may require another, e.g. network on a cloud-platform extension); `builds_on` — the core types, attributes and link types it extends or names (MX-11b uses it before an upgrade); `enhances` — extensions it works better with but does not need (it says so; it never changes behaviour on its own because of them). |
| **MX-42** | **One view of what is active.** `sdem extensions graph --workspace …` (and `--json`) shows the extensions included in a workspace: kind and scope, version, what each requires and builds on, the types each adds, and the link types between them — and the bridges installed but not included whose requirements are met. DESNRE's Extensions panel (EL-12) shows the same for a published design. |
| **MX-43** | **SDEM enforces it** when a profile is resolved: missing or out-of-range requirements (refused, MX-11a), a type-name collision (refused, MX-19), a pack doing more than its scope (refused, MX-18), and the dependency order on exclude and restore (MX-39). |
| **MX-44** | **Built before the first horizontal or bridge extension** — the core changes this part needs: the scope check (MX-18), namespace collisions (MX-19), archiving by type (MX-33), the inheritance test (MX-32, and an extension's own scope, MX-32a), a pack's inference rules (MX-40a), `requires` and the dependency order (MX-38, MX-39, MX-43), and `sdem extensions graph` (MX-42). Vertical extensions need none of them to keep working. |

## 15. Decisions for the owner (Part 2)

| # | Decision | Recommendation |
|---|---|---|
| MX-D7 | Three kinds — vertical, horizontal, bridge — stated in the manifest's `scope` and checked by SDEM (MX-18) | **yes** |
| MX-D8 | The lessons of the security build (MX-20…MX-29) bind every future vertical extension | **yes** |
| MX-D9 | Horizontal extensions by inheritance inside one layer, archived by type when switched off, drawn as their parents (MX-30…MX-35) | **yes** |
| MX-D10 | Extensions never join each other directly; a bridge does (MX-36, MX-37) | **yes** |
| MX-D11 | A bridge is switched on by a person; SDEM suggests it when its requirements are on, and refuses excluding what it depends on (MX-38, MX-39) | **yes** |
| MX-D12 | `requires` / `builds_on` / `enhances` in the manifest, and `sdem extensions graph` (MX-41, MX-42) | **yes** |
| MX-D13 | Build the core part (MX-44) before the first horizontal extension, and prove MX-32 by a test first | **yes** |
| MX-D14 | An extension's own scope follows inheritance; fix `sdem security`'s exact type match before a horizontal extension ships (MX-32a) | **yes** |
| MX-D15 | A bridge may ship AID inference rules for its own link types; every inference stays a proposal (MX-40a) | **yes** |
| MX-D16 | Without a bridge, an agent's or a tool's reasoning across extensions is inference only, said to be one; SDEM's documents stay one per layer and per extension (MX-40b) | **yes** |

