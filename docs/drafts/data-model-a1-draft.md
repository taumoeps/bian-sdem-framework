# A1 Business Architecture data model — DRAFT for review

> **Status: draft, 2026-10-24.** Nothing here is in the model yet. Review each proposed field; approved fields move into `metamodel/entity-attributes.json` and the generated documents. Record: `metamodel/drafts/a1-descriptive-attributes.json`.

## How this draft was built

1. For each entity, the **design questions** architects ask of it.
2. One field per question, taken from the **highest available source**: BIAN → open public standards readable without login (Dublin Core, W3C ORG, W3C SKOS, public legislation) → ArchiMate concepts (meaning only) → SDEM-defined.
3. **Not used:** TOGAF and the ArchiMate text (login), ISO 11179 / ISO 22301 / ITIL (paid), vendor schemas, your employer's model.
4. **Confidence** uses the same rule as the rest of the model: **high** = a public standard defines the field and it was checked; **medium** = built on a standard concept as SDEM chose to model it; **low** = SDEM-defined, no standard behind it.

## Summary

| | Proposed fields | High | Medium | Low |
|---|---|---|---|---|
| Common set (every entity, all four architectures) | 11 | 9 | 2 | 0 |
| `A1.BusinessCapability` | 4 | 0 | 1 | 3 |
| `A1.ValueStream` | 2 | 0 | 2 | 0 |
| `A1.ValueStreamStage` | 3 | 0 | 1 | 2 |
| `A1.BusinessProcess` | 6 | 0 | 3 | 3 |
| `A1.BusinessActivity` | 1 | 0 | 1 | 0 |
| `A1.BusinessService` | 4 | 0 | 1 | 3 |
| `A1.BusinessActor` | 5 | 4 | 0 | 1 |
| `A1.BusinessRole` | 2 | 1 | 1 | 0 |
| `A1.BusinessObject` | 2 | 2 | 0 | 0 |
| `A1.BusinessRequirement` | 3 | 1 | 1 | 1 |
| **Total** | **43** | **17** | **13** | **13** |

| Source | Fields |
|---|---|
| SDEM-defined (no open standard) | 13 |
| ArchiMate 3.2 concept (confirmed via the Archi oracle; specification text login-gated) | 12 |
| Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20) | 11 |
| W3C Organization Ontology (W3C Recommendation 2014-01-16) | 5 |
| W3C SKOS Reference (W3C Recommendation 2009-08-18) | 1 |
| EU GDPR Art. 4(1) and NZ Privacy Act 2020 s 7 (public legislation) | 1 |

## 1. Common fields — proposed for every entity

Today every entity already has: `id`, `type`, `version`, `name`, `lifecycle_status`, `canonical_id`, `description`, `definition_uri`, `attributes`. Proposed in addition, for **all four architectures** (A2–A4 will reuse this set):

| ID | Field | Type | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| DA1-01 | `source_id` | string | Which record in the source tool is this? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:identifier` | The record's own key in the tool it came from, so any node can be traced back to its system of record. Distinct from SDEM `id`, which may be the same value. | **high** |
| DA1-02 | `created` | date | How old is this? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:created` | Date the thing was created in the source. | **high** |
| DA1-03 | `modified` | date | What changed recently? Is this stale? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:modified` | Date of the last change in the source; lets reviews spot stale entries. | **high** |
| DA1-04 | `valid_from` | date | Is this in force on a given date? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:valid` | Start of the validity period. Dublin Core defines `valid` as a date or range; SDEM stores the range as two dates. | **high** |
| DA1-05 | `valid_to` | date | Is this in force on a given date? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:valid` | End of the validity period (empty = open). | **high** |
| DA1-06 | `replaces` | reference (same entity type) | What did this replace? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:replaces` | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | **high** |
| DA1-07 | `replaced_by` | reference (same entity type) | What replaced this? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:isReplacedBy` | The later instance that supersedes this one. | **high** |
| DA1-08 | `conforms_to` | list of text | Which standard, framework or policy does this follow? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:conformsTo` | E.g. "BIAN BCM 14.0", an internal policy id. Makes alignment claims explicit and queryable. | **high** |
| DA1-09 | `subject` | list of text | Find everything about a topic (e.g. "payments", "fraud"). | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:subject` | Free topic tags; lets architects slice the graph by theme. | **high** |
| DA1-10 | `owner` | reference → A1.BusinessActor or A1.BusinessRole | Who is accountable for this? | [ArchiMate 3.2 concept (confirmed via the Archi oracle; specification text login-gated)](https://pubs.opengroup.org/architecture/archimate3-doc/): `assignment (active structure assigned to behaviour or object)` | Accountability is the most-asked design question. No public standard defines an "owner" field: Dublin Core's rightsHolder is about rights, not accountability. Built on ArchiMate's assignment of an actor or role. | **medium** |
| DA1-11 | `access_classification` | enum — one of: public, internal, confidential, restricted | Who may see this? How sensitive is it? | [Dublin Core (DCMI Metadata Terms, DCMI Recommendation 2020-01-20)](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:accessRights` | Dublin Core defines the field (access or security status); the four values are SDEM's common banking scale, not a standard. | **medium** |

## 2. `A1.BusinessCapability`

A business ability independent of how it is implemented.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `owner` | string | existing | — | SDEM | Informational field used by one example; no rule reads it. Kept so exports that carry it validate. | low |
| **`level`** | integer ≥ 1 | **proposed DA1-12** | Show the capability map at level 1, 2 or 3. | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Capability composition (hierarchy)` | Depth in the capability hierarchy. The hierarchy itself is the composition link between capabilities; `level` makes the depth queryable without walking it. | **medium** |
| **`strategic_importance`** | enum — one of: core, differentiating, supporting, commodity | **proposed DA1-13** | Which capabilities matter most to strategy? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Common capability heat-map dimension; no open standard defines it or its values. | **low** |
| **`maturity_current`** | integer 1–5 | **proposed DA1-14** | Where do we need to invest? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Current maturity on a 1–5 scale. Maturity scales (e.g. CMMI) are proprietary; SDEM defines only the range. | **low** |
| **`maturity_target`** | integer 1–5 | **proposed DA1-15** | Where do we need to invest? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Target maturity, same scale; the gap to current drives investment questions. | **low** |

## 3. `A1.ValueStream`

The stages by which stakeholders receive value.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `stages` | list<string> | existing | — | ArchiMate relationship | ArchiMate composes a value stream of stages; SDEM keeps them as an ordered list because stage order is what is matched to a BIAN scenario's operation sequence. | medium |
| **`stakeholder`** | text | **proposed DA1-16** | Who is this value stream for? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Stakeholder (motivation)` | The stakeholder the stream delivers value to; ArchiMate has a Stakeholder concept. | **medium** |
| **`value_proposition`** | text | **proposed DA1-17** | What value does it deliver? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Value (motivation)` | The value the stream produces; ArchiMate has a Value concept associated with value streams. | **medium** |

## 4. `A1.ValueStreamStage`

One named segment of a value stream. A kind of `A1.ValueStream`; inherits its fields.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| **`entrance_criteria`** | text | **proposed DA1-18** | When does a stage start? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Condition for entering the stage. Widely used in value-stream mapping, but the source that defines it (BIZBOK) is membership-only. | **low** |
| **`exit_criteria`** | text | **proposed DA1-19** | When is a stage done? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Condition for leaving the stage; as above. | **low** |
| **`value_item`** | text | **proposed DA1-20** | What value does each stage add? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Value (motivation)` | The value a stage contributes; ArchiMate Value concept. | **medium** |

## 5. `A1.BusinessProcess`

Coordinated business behaviour.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `invokes` | list<string> | existing | — | ArchiMate relationship | Records on the process which BIAN operations it uses, so the A1→A2 USES_DOMAIN relationship can be derived by join instead of guessed. ArchiMate expresses this as behaviour served by a service; listing the operation ids on the process is SDEM's encoding. | medium |
| **`level`** | integer ≥ 1 | **proposed DA1-21** | Show processes at level 1, 2, 3 … | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Business Process composition` | Depth in the process hierarchy; the hierarchy itself is the composition link. | **medium** |
| **`triggered_by`** | text | **proposed DA1-22** | What starts this process? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Business Event triggering a process` | The business event that starts it (e.g. "customer submits payment"). | **medium** |
| **`outcome`** | text | **proposed DA1-23** | What result does it produce? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Outcome (motivation)` | The end result the process achieves. | **medium** |
| **`criticality`** | enum — one of: high, medium, low | **proposed DA1-24** | Which critical processes depend on this platform or application? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | The single most useful field for impact analysis. No open standard defines it; business-continuity standards (ISO 22301) are paid. | **low** |
| **`frequency`** | enum — one of: continuous, daily, weekly, monthly, ad hoc | **proposed DA1-25** | How often does it run? What is the blast radius of an outage? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | How often the process runs; informs outage impact. | **low** |
| **`automation_level`** | enum — one of: manual, partly automated, automated | **proposed DA1-26** | Where is manual effort? What is a candidate for automation? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Degree of automation; no standard scale. | **low** |

## 6. `A1.BusinessActivity`

A fine-grained activity within a process. A kind of `A1.BusinessProcess`; inherits its fields.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `invokes` | list<string> | existing | — | ArchiMate relationship | As for the process, at the level where one step calls one operation; makes S06 a step-1 join. | medium |
| **`sequence`** | integer ≥ 1 | **proposed DA1-27** | In what order do the steps run? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `triggering / flow between process steps` | Position of the step in its process; ArchiMate orders steps with triggering and flow. | **medium** |

## 7. `A1.BusinessService`

Business behaviour exposed to consumers.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `inputs` | list<string> | existing | — | SDEM | ArchiMate defines no attributes for a business service. SDEM adds inputs and outputs so a business service can be matched to BIAN operation inputs and outputs (S09). No standard defines them. | medium |
| `outputs` | list<string> | existing | — | SDEM | As for inputs. | medium |
| **`consumers`** | list of references → A1.BusinessActor or A1.BusinessRole | **proposed DA1-28** | Who uses this service? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `serving (service serves actor or role)` | The actors or roles the service serves. | **medium** |
| **`customer_facing`** | boolean | **proposed DA1-29** | Which customer-facing services depend on this? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Whether customers use the service directly; key for customer-impact questions. | **low** |
| **`channels`** | list of enum — one of: branch, online, mobile, contact centre, partner, API | **proposed DA1-30** | Through which channels is it offered? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Delivery channels. ArchiMate models channels as business interfaces; the value list is SDEM's. | **low** |
| **`service_level`** | text | **proposed DA1-31** | What has the bank committed to? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | The service-level target (e.g. "same-day"). Service-management standards that define this (ITIL) are paid. | **low** |

## 8. `A1.BusinessActor`

An individual or organisation capable of business behaviour.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| **`actor_kind`** | enum — one of: formal organisation, organisational unit, person | **proposed DA1-32** | Is this a company, a department or a person? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/): `org:FormalOrganization, org:OrganizationalUnit (persons via foaf:Person, which ORG uses)` | The three kinds of agent ORG distinguishes. | **high** |
| **`external`** | boolean | **proposed DA1-33** | Which external parties (customers, partners, regulators) are involved? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | Whether the actor is outside the bank. ORG does not distinguish internal from external. | **low** |
| **`classification`** | text | **proposed DA1-34** | What category of organisation is this? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/): `org:classification` | A category from a scheme (e.g. regulator, partner, business line). | **high** |
| **`purpose`** | text | **proposed DA1-35** | Why does this unit exist? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/): `org:purpose` | The organisation's or unit's purpose. | **high** |
| **`location`** | text | **proposed DA1-36** | Where is it based? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/): `org:basedAt / org:Site` | The site where the actor is based. | **high** |

## 9. `A1.BusinessRole`

Responsibility for a class of business behaviour.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| **`role_kind`** | enum — one of: role, post | **proposed DA1-37** | Is this a generic role or a specific position? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/): `org:Role, org:Post` | ORG separates a generic role from a post that exists whether or not it is filled. | **high** |
| **`responsibilities`** | text | **proposed DA1-38** | What is this role responsible for? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Business Role` | What the role does; ArchiMate's role is defined by its responsibilities. | **medium** |

## 10. `A1.BusinessObject`

A business-level information concept.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `attributes` | list<string> | existing | — | SDEM | ArchiMate's business object has no attributes. SDEM records the bank's glossary attributes so the object can be aligned to a BIAN business object by attribute match (S12). Built on a standard concept; the field list is SDEM's. | medium |
| `field_aliases` | map<string,string> | existing | — | institution | The bank's decoded names, supplied as data so matching never guesses (the H2 finding). | medium |
| **`glossary_uri`** | text (URI) | **proposed DA1-39** | Where is the agreed definition of this term? | [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/): `skos:Concept` | Link to the business-glossary concept that defines the object. | **high** |
| **`personal_information`** | boolean | **proposed DA1-40** | Which objects hold personal information? What does a privacy change affect? | [EU GDPR Art. 4(1) and NZ Privacy Act 2020 s 7](https://eur-lex.europa.eu/eli/reg/2016/679/oj): `personal data / personal information` | Whether the object holds information about an identifiable person, as defined in public privacy law. | **high** |

## 11. `A1.BusinessRequirement`

An expressed architectural requirement.

| Field | Type | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|
| `applies_to` | list<string> | existing | — | ArchiMate relationship | ArchiMate links a requirement to the core element that realizes it; SDEM records the targets on the requirement for joining. | medium |
| **`requirement_kind`** | enum — one of: requirement, constraint, principle | **proposed DA1-41** | Is this something to achieve, a limit, or a guiding rule? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/): `Requirement, Constraint, Principle (motivation)` | ArchiMate has three separate concepts; SDEM holds them as one entity with a kind field. | **medium** |
| **`derived_from`** | list of text | **proposed DA1-42** | Which regulation, policy or decision does this come from? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): `dcterms:source` | The origin of the requirement (e.g. a regulation article or policy id). | **high** |
| **`priority`** | enum — one of: must, should, could, won't | **proposed DA1-43** | What must be met first? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework): `—` | MoSCoW priority, a common convention with no open standard definition. | **low** |

## Decisions for you

1. **The common set** — accept all eleven for every architecture? `owner` and `access_classification` are the two that are not purely Dublin Core.
2. **The 13 low-confidence fields** are the ones architects ask for most (`criticality`, `strategic_importance`, maturity, `customer_facing`) but no open standard defines them. Keep them as SDEM-defined, or drop some?
3. **Hierarchy stays a link, not a field.** Parent capability, parent process and parent unit are the existing composition links; `level` records depth only. ORG's `reportsTo` would be an association link between roles, not a field.
4. **Required fields** — everything is optional in this draft. Which, if any, should a valid export have to supply (e.g. `owner`, `criticality`)?

