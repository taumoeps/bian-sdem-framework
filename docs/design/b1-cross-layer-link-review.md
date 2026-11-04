# B1 — review of the cross-layer link types (draft for the owner's decision)

> **Status: applied — items 1–5 approved by the owner ("approve B1: 1, 2, 3, 4, 5", 2026-11-02); metamodel 0.8.0, SDEM 0.15.0. Item 6 open (needs an Open Group login).** Applied with one refinement for the stability policy (MS-06): the old DEPLOYED_ON row is **deprecated, not removed** — a connection only it allows passes with a warning until metamodel 0.9.0 removes it, and the migration gives every connection that named the supertype its record's own type. DEPLOYED_AS is marked `sdem_definition_grounded` (SDEM's own, grounded in a checked ArchiMate pattern) so its confidence is derived as high.
>
> Originally: **DRAFT, 2026-11-02 — nothing in the metamodel has changed.** Owner's approval of B1 (2026-11-02): review the six cross-layer link types that are not verified, against public sources, and propose for each: confirm, correct, or keep as SDEM's own. Applied only as approved, with a new metamodel version, a migration and a freeze (docs/design/sdem-metamodel-stability.md).

## Sources read for this review

| Key | Source | Read? |
|---|---|---|
| [RN14] | BIAN v14.0.0 Release Notes v1.0 (Final), © 2026 BIAN e.V., bian.org — §1, §1.1, §1.2, §3, §8 | **read** (downloaded 2026-11-02) |
| [ARCHI] | Archi's implementation of the ArchiMate 3.2 relationship tables — `com.archimatetool.model/model/relationships.xml`, `<relationships version="3.2">`, github.com/archimatetool/archi (master, 2026-11-02) | **read** |
| [AM] | ArchiMate 3.2 specification, pubs.opengroup.org | not read — login required |
| [AM-BIAN] | The Open Group, BIAN in ArchiMate (digital portfolio) | not read — login required |
| [W135] | The Open Group White Paper W135, *Integrating the TOGAF Standard with the BIAN Service Landscape* | not read — login required |
| [BCM23] | BIAN, *BCM Relationship with BIAN Service Landscape* (2023) | not read — removed from bian.org (404); a third-party copy shows no body text. Search summaries describe it as saying most capability–domain mappings are many-to-many and that scenarios relate to value streams — **secondary, not relied on** |

## Proposals

| # | Link type | Today | Proposal | Change | Confidence |
|---|---|---|---|---|---|
| 1 | `A3.ApplicationComponent DEPLOYED_ON A4.InfrastructureComponent` (S33) | SDEM's own, medium | **Correct, then verify.** Narrow the target to the ArchiMate types that host an application: `A4.Node`, `A4.Device`, `A4.SystemSoftware` (and their subtypes, e.g. a profile's MacBook). Mark verified against ArchiMate 3.2. | metamodel (registry): one row → three; verification `verified_against_archi`, confidence high | **High** |
| 2 | `A3.ApplicationComponent DEPLOYED_AS A4.Deployment` (S32) | SDEM's own, medium | **Keep as SDEM's own; ground it.** The target is SDEM's Deployment record; ArchiMate supports the pattern it records. Raise confidence to high; reasoning cites [ARCHI]. | metamodel (text, confidence) | High |
| 3 | `A1.ValueStream ALIGNED_TO A2.BusinessScenario` (S02) | authority `bian_alignment_guidance`, verification SDEM's own | **Correct the authority** to `enterprise_rule`: no BIAN guidance was found or is cited; [RN14] §3 says BIAN's value-stream work is "not yet modelled". Keep as SDEM's own. | metamodel (authority, text) | High |
| 4 | `A1.BusinessCapability SUPPORTED_BY A2.ServiceDomain` (S01) | BIAN intent only, medium | **Keep.** Re-cite: [RN14] §3 (read) confirms BIAN's capability–domain structure is "still work in progress" and not yet in its repository. Cardinality stays many-to-many. | metamodel (text) | High (that it stays intent-only) |
| 5 | `A1.BusinessObject ALIGNED_TO A2.BusinessObject` (S12) | BIAN target only, medium | **Keep.** Re-cite: [RN14] §1.2 and §8 (read) — BIAN publishes the Business Object Model in UML as the target; no method for aligning an organisation's own objects. | metamodel (text) | High (that it stays target-only) |
| 6 | `A1.BusinessProcess USES_DOMAIN A2.ServiceDomain` (S04) | unverified — [W135] unread, medium | **Keep unverified.** [W135] is still behind a login. [RN14] §1 says BIAN expresses Service Domains in ArchiMate 3.2, but the element it uses is in [AM-BIAN], also login-gated — so ArchiMate's process rules cannot be applied yet. To settle: someone with a (free) Open Group account reads [W135] and [AM-BIAN]. | none | — |

**Net effect:** one link moves to verified (1); one false authority claim is corrected (3); three keep their status with better, read citations (2, 4, 5); one stays open with what would settle it (6). `sdem model status` would show 5 of 9 unsettled instead of 6.

## The evidence for proposal 1

[ARCHI] — what ArchiMate 3.2 allows *towards* an Application Component, per A4 type:

| A4 type (ArchiMate concept) | Allowed to the Application Component | Hosts it? |
|---|---|---|
| Node, Device, System Software | realization, serving, flow, triggering, association | **yes** — realization: the component runs here |
| Artifact | realization, association | the deployed file — that is DEPLOYED_AS's Deployment |
| Communication Network, Path | realization, serving, … | ArchiMate allows a derived realization, but an application is not "deployed on" a network — **excluded** |
| Technology Service, Technology Interface | serving, flow, triggering, association — **no realization** | no — the application *uses* it; not a deployment |
| Deployment, Deployment Environment, Infrastructure Component | SDEM's own types | — |

And the deployment pattern itself: Artifact **realization** Application Component; Node and System Software **assignment** Artifact.

**Data impact of proposal 1:** a DEPLOYED_ON connection to any other A4 type no longer passes `sdem check`. In SDEM's synthetic examples: 12 to System Software, 3 to Node, 1 to Device (all fine) and **4 to the abstract `A4.InfrastructureComponent`** — those four are re-pointed in the migration. In an organisation's workspaces, the migration lists any such connection for a person to re-point; nothing is changed silently.

## If approved — how it is applied

1. Metamodel `0.7.0 → 0.8.0`; a migration in `metamodel/migrations.json` (approved by the owner) whose step reports DEPLOYED_ON connections to a type that no longer qualifies.
2. The registry rows as above; the four synthetic example connections re-pointed; generated documents regenerated.
3. `sdem model stability` passes; `sdem model freeze --person "the SDEM owner"`.
4. Released as SDEM 0.15.0, with the change explained in the CHANGELOG.

## Decision

Approve all, or by number — e.g. "approve B1: 1, 2, 3, 4, 5" (6 needs no change).
