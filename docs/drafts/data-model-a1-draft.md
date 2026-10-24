# A1 Business Architecture — Data Model (DRAFT for review)

> **Status: draft, 2026-10-24.** Proposed fields are marked **proposed**; nothing here is in the model until you approve it. Record: `metamodel/drafts/a1-descriptive-attributes.json`.

**How to read each entity.** The **Data Model** table is the complete record for the entity: every field, its type, whether it is required, its allowed values and what it holds. Fields come in three groups — **Core** (identity, on every entity), **Common** (descriptive, on every entity) and **Specific** (this entity only). The **Sources** table under it gives, for each specific field, the question it answers, where it comes from, why, and how confident that basis is. The common fields' sources are in section 1. In an export file the common and specific fields sit inside the instance's `attributes` object.

**How the draft was built.** One field per design question, each from the highest available source — BIAN → open public standards readable without login (Dublin Core, W3C ORG, W3C SKOS, public privacy law) → ArchiMate concepts (meaning only) → SDEM-defined. Not used: TOGAF and the ArchiMate text (login), paid standards, vendor schemas, your employer's model. Confidence: **high** = a public standard defines it and it was checked; **medium** = built on a standard concept as SDEM chose; **low** = SDEM-defined.

## 1. Fields every entity has

### Core fields (existing)

| Field | Type | Required | Holds |
|---|---|---|---|
| `id` | text | yes | the instance's permanent key — the source tool's own persistent id |
| `type` | text | yes | an entity type from the catalogue |
| `version` | text | yes | the instance's version |
| `name` | text | yes | human-readable name |
| `lifecycle_status` | enum | no | lifecycle state |
| `canonical_id` | text | no | external reference id, e.g. a BIAN concept id on A2 instances |
| `description` | text | no | scope statement |
| `definition_uri` | text | no | link to the source definition |

### Common fields (proposed for all four architectures)

| ID | Field | Type | Allowed values | Holds | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|---|---|---|
| DA1-01 | `source_id` | text | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | Which record in the source tool is this? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:identifier` | The record's own key in the tool it came from, so any node can be traced back to its system of record. Distinct from SDEM `id`, which may be the same value. | **high** |
| DA1-02 | `created` | date | — | Date the thing was created in the source. | How old is this? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:created` | Date the thing was created in the source. | **high** |
| DA1-03 | `modified` | date | — | Date of the last change in the source. | What changed recently? Is this stale? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:modified` | Date of the last change in the source; lets reviews spot stale entries. | **high** |
| DA1-04 | `valid_from` | date | — | Start of the validity period. | Is this in force on a given date? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:valid` | Start of the validity period. Dublin Core defines `valid` as a date or range; SDEM stores the range as two dates. | **high** |
| DA1-05 | `valid_to` | date | — | End of the validity period (empty = open). | Is this in force on a given date? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:valid` | End of the validity period (empty = open). | **high** |
| DA1-06 | `replaces` | reference (same entity type) | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | What did this replace? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:replaces` | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | **high** |
| DA1-07 | `replaced_by` | reference (same entity type) | — | The later instance that supersedes this one. | What replaced this? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:isReplacedBy` | The later instance that supersedes this one. | **high** |
| DA1-08 | `conforms_to` | list of text | — | E.g. | Which standard, framework or policy does this follow? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:conformsTo` | E.g. "BIAN BCM 14.0", an internal policy id. Makes alignment claims explicit and queryable. | **high** |
| DA1-09 | `subject` | list of text | — | Free topic tags. | Find everything about a topic (e.g. "payments", "fraud"). | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:subject` | Free topic tags; lets architects slice the graph by theme. | **high** |
| DA1-10 | `owner` | reference → A1.BusinessActor or A1.BusinessRole | — | Accountability is the most-asked design question. | Who is accountable for this? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `assignment (active structure assigned to behaviour or object)` | Accountability is the most-asked design question. No public standard defines an "owner" field: Dublin Core's rightsHolder is about rights, not accountability. Built on ArchiMate's assignment of an actor or role. | **medium** |
| DA1-11 | `access_classification` | enum | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | Who may see this? How sensitive is it? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:accessRights` | Dublin Core defines the field (access or security status); the four values are SDEM's common banking scale, not a standard. | **medium** |

## 2. A1.BusinessCapability — Data Model

**A business ability independent of how it is implemented.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessCapability` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | **`level`** | Specific | integer ≥ 1 | no | — | Depth in the capability hierarchy. | **proposed** |
| 21 | **`strategic_importance`** | Specific | enum | no | core, differentiating, supporting, commodity | Common capability heat-map dimension. | **proposed** |
| 22 | **`maturity_current`** | Specific | integer 1–5 | no | — | Current maturity on a 1–5 scale. | **proposed** |
| 23 | **`maturity_target`** | Specific | integer 1–5 | no | — | Target maturity, same scale. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `level` | proposed DA1-12 | Show the capability map at level 1, 2 or 3. | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Capability composition (hierarchy)` | Depth in the capability hierarchy. The hierarchy itself is the composition link between capabilities; `level` makes the depth queryable without walking it. | **medium** |
| `strategic_importance` | proposed DA1-13 | Which capabilities matter most to strategy? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Common capability heat-map dimension; no open standard defines it or its values. | **low** |
| `maturity_current` | proposed DA1-14 | Where do we need to invest? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Current maturity on a 1–5 scale. Maturity scales (e.g. CMMI) are proprietary; SDEM defines only the range. | **low** |
| `maturity_target` | proposed DA1-15 | Where do we need to invest? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Target maturity, same scale; the gap to current drives investment questions. | **low** |
| ~~`owner`~~ (existing text field) | **replaced** by the common `owner` | — | SDEM | Informational field used by one example; no rule reads it. Kept so exports that carry it validate. The common field supersedes it: it refers to an actor or role instead of holding free text. | low |

## 3. A1.ValueStream — Data Model

**The stages by which stakeholders receive value.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.ValueStream` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `stages` | Specific | list of text | no | refers to `A1.ValueStreamStage` | ordered ids of the stream's stages | existing |
| 21 | **`stakeholder`** | Specific | text | no | — | The stakeholder the stream delivers value to. | **proposed** |
| 22 | **`value_proposition`** | Specific | text | no | — | The value the stream produces. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `stages` | existing | — | ArchiMate relationship (ArchiMate 3.2 (relationship)) | ArchiMate composes a value stream of stages; SDEM keeps them as an ordered list because stage order is what is matched to a BIAN scenario's operation sequence. | medium |
| `stakeholder` | proposed DA1-16 | Who is this value stream for? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Stakeholder (motivation)` | The stakeholder the stream delivers value to; ArchiMate has a Stakeholder concept. | **medium** |
| `value_proposition` | proposed DA1-17 | What value does it deliver? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Value (motivation)` | The value the stream produces; ArchiMate has a Value concept associated with value streams. | **medium** |

## 4. A1.ValueStreamStage — Data Model

**One named segment of a value stream.** A kind of `A1.ValueStream`: it has all of its parent's fields as well.

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.ValueStreamStage` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `stages` | Inherited from `ValueStream` | list of text | no | refers to `A1.ValueStreamStage` | ordered ids of the stream's stages | existing |
| 21 | `stakeholder` | Inherited from `ValueStream` | text | no | — | The stakeholder the stream delivers value to. | proposed |
| 22 | `value_proposition` | Inherited from `ValueStream` | text | no | — | The value the stream produces. | proposed |
| 23 | **`entrance_criteria`** | Specific | text | no | — | Condition for entering the stage. | **proposed** |
| 24 | **`exit_criteria`** | Specific | text | no | — | Condition for leaving the stage. | **proposed** |
| 25 | **`value_item`** | Specific | text | no | — | The value a stage contributes. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `entrance_criteria` | proposed DA1-18 | When does a stage start? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Condition for entering the stage. Widely used in value-stream mapping, but the source that defines it (BIZBOK) is membership-only. | **low** |
| `exit_criteria` | proposed DA1-19 | When is a stage done? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Condition for leaving the stage; as above. | **low** |
| `value_item` | proposed DA1-20 | What value does each stage add? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Value (motivation)` | The value a stage contributes; ArchiMate Value concept. | **medium** |

## 5. A1.BusinessProcess — Data Model

**Coordinated business behaviour.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessProcess` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `invokes` | Specific | list of text | no | refers to `A2.ServiceOperation` | A2 operations the process steps call | existing |
| 21 | **`level`** | Specific | integer ≥ 1 | no | — | Depth in the process hierarchy. | **proposed** |
| 22 | **`triggered_by`** | Specific | text | no | — | The business event that starts it (e.g. | **proposed** |
| 23 | **`outcome`** | Specific | text | no | — | The end result the process achieves. | **proposed** |
| 24 | **`criticality`** | Specific | enum | no | high, medium, low | The single most useful field for impact analysis. | **proposed** |
| 25 | **`frequency`** | Specific | enum | no | continuous, daily, weekly, monthly, ad hoc | How often the process runs. | **proposed** |
| 26 | **`automation_level`** | Specific | enum | no | manual, partly automated, automated | Degree of automation. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `invokes` | existing | — | ArchiMate relationship (ArchiMate 3.2 (relationship)) | Records on the process which BIAN operations it uses, so the A1→A2 USES_DOMAIN relationship can be derived by join instead of guessed. ArchiMate expresses this as behaviour served by a service; listing the operation ids on the process is SDEM's encoding. | medium |
| `level` | proposed DA1-21 | Show processes at level 1, 2, 3 … | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Business Process composition` | Depth in the process hierarchy; the hierarchy itself is the composition link. | **medium** |
| `triggered_by` | proposed DA1-22 | What starts this process? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Business Event triggering a process` | The business event that starts it (e.g. "customer submits payment"). | **medium** |
| `outcome` | proposed DA1-23 | What result does it produce? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Outcome (motivation)` | The end result the process achieves. | **medium** |
| `criticality` | proposed DA1-24 | Which critical processes depend on this platform or application? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | The single most useful field for impact analysis. No open standard defines it; business-continuity standards (ISO 22301) are paid. | **low** |
| `frequency` | proposed DA1-25 | How often does it run? What is the blast radius of an outage? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | How often the process runs; informs outage impact. | **low** |
| `automation_level` | proposed DA1-26 | Where is manual effort? What is a candidate for automation? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Degree of automation; no standard scale. | **low** |

## 6. A1.BusinessActivity — Data Model

**A fine-grained activity within a process.** A kind of `A1.BusinessProcess`: it has all of its parent's fields as well.

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessActivity` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `invokes` | Inherited from `BusinessProcess` | list of text | no | refers to `A2.ServiceOperation` | A2 operations the process steps call | existing |
| 21 | `level` | Inherited from `BusinessProcess` | integer ≥ 1 | no | — | Depth in the process hierarchy. | proposed |
| 22 | `triggered_by` | Inherited from `BusinessProcess` | text | no | — | The business event that starts it (e.g. | proposed |
| 23 | `outcome` | Inherited from `BusinessProcess` | text | no | — | The end result the process achieves. | proposed |
| 24 | `criticality` | Inherited from `BusinessProcess` | enum | no | high, medium, low | The single most useful field for impact analysis. | proposed |
| 25 | `frequency` | Inherited from `BusinessProcess` | enum | no | continuous, daily, weekly, monthly, ad hoc | How often the process runs. | proposed |
| 26 | `automation_level` | Inherited from `BusinessProcess` | enum | no | manual, partly automated, automated | Degree of automation. | proposed |
| 27 | `invokes` | Specific | list of text | no | refers to `A2.ServiceOperation` | A2 operations the activity calls | existing |
| 28 | **`sequence`** | Specific | integer ≥ 1 | no | — | Position of the step in its process. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `invokes` | existing | — | ArchiMate relationship (ArchiMate 3.2 (relationship)) | As for the process, at the level where one step calls one operation; makes S06 a step-1 join. | medium |
| `sequence` | proposed DA1-27 | In what order do the steps run? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `triggering / flow between process steps` | Position of the step in its process; ArchiMate orders steps with triggering and flow. | **medium** |

## 7. A1.BusinessService — Data Model

**Business behaviour exposed to consumers.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessService` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `inputs` | Specific | list of text | no | — | attribute names the service takes | existing |
| 21 | `outputs` | Specific | list of text | no | — | attribute names the service returns | existing |
| 22 | **`consumers`** | Specific | list of references → A1.BusinessActor or A1.BusinessRole | no | — | The actors or roles the service serves. | **proposed** |
| 23 | **`customer_facing`** | Specific | boolean | no | — | Whether customers use the service directly. | **proposed** |
| 24 | **`channels`** | Specific | list of enum | no | branch, online, mobile, contact centre, partner, API | Delivery channels. | **proposed** |
| 25 | **`service_level`** | Specific | text | no | — | The service-level target (e.g. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `inputs` | existing | — | SDEM (SDEM) | ArchiMate defines no attributes for a business service. SDEM adds inputs and outputs so a business service can be matched to BIAN operation inputs and outputs (S09). No standard defines them. | medium |
| `outputs` | existing | — | SDEM (SDEM) | As for inputs. | medium |
| `consumers` | proposed DA1-28 | Who uses this service? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `serving (service serves actor or role)` | The actors or roles the service serves. | **medium** |
| `customer_facing` | proposed DA1-29 | Which customer-facing services depend on this? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Whether customers use the service directly; key for customer-impact questions. | **low** |
| `channels` | proposed DA1-30 | Through which channels is it offered? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Delivery channels. ArchiMate models channels as business interfaces; the value list is SDEM's. | **low** |
| `service_level` | proposed DA1-31 | What has the bank committed to? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | The service-level target (e.g. "same-day"). Service-management standards that define this (ITIL) are paid. | **low** |

## 8. A1.BusinessActor — Data Model

**An individual or organisation capable of business behaviour.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessActor` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | **`actor_kind`** | Specific | enum | no | formal organisation, organisational unit, person | The three kinds of agent ORG distinguishes. | **proposed** |
| 21 | **`external`** | Specific | boolean | no | — | Whether the actor is outside the bank. | **proposed** |
| 22 | **`classification`** | Specific | text | no | — | A category from a scheme (e.g. | **proposed** |
| 23 | **`purpose`** | Specific | text | no | — | The organisation's or unit's purpose. | **proposed** |
| 24 | **`location`** | Specific | text | no | — | The site where the actor is based. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `actor_kind` | proposed DA1-32 | Is this a company, a department or a person? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/) `org:FormalOrganization, org:OrganizationalUnit (persons via foaf:Person, which ORG uses)` | The three kinds of agent ORG distinguishes. | **high** |
| `external` | proposed DA1-33 | Which external parties (customers, partners, regulators) are involved? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | Whether the actor is outside the bank. ORG does not distinguish internal from external. | **low** |
| `classification` | proposed DA1-34 | What category of organisation is this? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/) `org:classification` | A category from a scheme (e.g. regulator, partner, business line). | **high** |
| `purpose` | proposed DA1-35 | Why does this unit exist? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/) `org:purpose` | The organisation's or unit's purpose. | **high** |
| `location` | proposed DA1-36 | Where is it based? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/) `org:basedAt / org:Site` | The site where the actor is based. | **high** |

## 9. A1.BusinessRole — Data Model

**Responsibility for a class of business behaviour.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessRole` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | **`role_kind`** | Specific | enum | no | role, post | ORG separates a generic role from a post that exists whether or not it is filled. | **proposed** |
| 21 | **`responsibilities`** | Specific | text | no | — | What the role does. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `role_kind` | proposed DA1-37 | Is this a generic role or a specific position? | [W3C Organization Ontology](https://www.w3.org/TR/vocab-org/) `org:Role, org:Post` | ORG separates a generic role from a post that exists whether or not it is filled. | **high** |
| `responsibilities` | proposed DA1-38 | What is this role responsible for? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Business Role` | What the role does; ArchiMate's role is defined by its responsibilities. | **medium** |

## 10. A1.BusinessObject — Data Model

**A business-level information concept.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessObject` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `attributes` | Specific | list of text | no | — | glossary attribute names | existing |
| 21 | `field_aliases` | Specific | name map | no | — | glossary name → canonical attribute name | existing |
| 22 | **`glossary_uri`** | Specific | text (URI) | no | — | Link to the business-glossary concept that defines the object. | **proposed** |
| 23 | **`personal_information`** | Specific | boolean | no | — | Whether the object holds information about an identifiable person, as defined in public privacy law. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `attributes` | existing | — | SDEM (SDEM) | ArchiMate's business object has no attributes. SDEM records the bank's glossary attributes so the object can be aligned to a BIAN business object by attribute match (S12). Built on a standard concept; the field list is SDEM's. | medium |
| `field_aliases` | existing | — | institution (institution data (SDEM convention)) | The bank's decoded names, supplied as data so matching never guesses (the H2 finding). | medium |
| `glossary_uri` | proposed DA1-39 | Where is the agreed definition of this term? | [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/) `skos:Concept` | Link to the business-glossary concept that defines the object. | **high** |
| `personal_information` | proposed DA1-40 | Which objects hold personal information? What does a privacy change affect? | [EU GDPR Art. 4(1) and NZ Privacy Act 2020 s 7](https://eur-lex.europa.eu/eli/reg/2016/679/oj) `personal data / personal information` | Whether the object holds information about an identifiable person, as defined in public privacy law. | **high** |

## 11. A1.BusinessRequirement — Data Model

**An expressed architectural requirement.**

| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |
|---|---|---|---|---|---|---|---|
| 1 | `id` | Core | text | yes | — | the instance's permanent key — the source tool's own persistent id | existing |
| 2 | `type` | Core | text | yes | — | always `A1.BusinessRequirement` | existing |
| 3 | `version` | Core | text | yes | — | the instance's version | existing |
| 4 | `name` | Core | text | yes | — | human-readable name | existing |
| 5 | `lifecycle_status` | Core | enum | no | planned, active, deprecated, retired | lifecycle state | existing |
| 6 | `canonical_id` | Core | text | no | — | external reference id, e.g. a BIAN concept id on A2 instances | existing |
| 7 | `description` | Core | text | no | — | scope statement | existing |
| 8 | `definition_uri` | Core | text | no | — | link to the source definition | existing |
| 9 | `source_id` | Common | text | no | — | The record's own key in the tool it came from, so any node can be traced back to its system of record. | proposed |
| 10 | `created` | Common | date | no | — | Date the thing was created in the source. | proposed |
| 11 | `modified` | Common | date | no | — | Date of the last change in the source. | proposed |
| 12 | `valid_from` | Common | date | no | — | Start of the validity period. | proposed |
| 13 | `valid_to` | Common | date | no | — | End of the validity period (empty = open). | proposed |
| 14 | `replaces` | Common | reference (same entity type) | no | — | The earlier instance this one supersedes, so history can be followed through renames and re-designs. | proposed |
| 15 | `replaced_by` | Common | reference (same entity type) | no | — | The later instance that supersedes this one. | proposed |
| 16 | `conforms_to` | Common | list of text | no | — | E.g. | proposed |
| 17 | `subject` | Common | list of text | no | — | Free topic tags. | proposed |
| 18 | `owner` | Common | reference → A1.BusinessActor or A1.BusinessRole | no | — | Accountability is the most-asked design question. | proposed |
| 19 | `access_classification` | Common | enum | no | public, internal, confidential, restricted | Dublin Core defines the field (access or security status). | proposed |
| 20 | `applies_to` | Specific | list of text | no | refers to `A1.BusinessProcess`, `A1.BusinessActivity` | ids of the processes or activities the requirement constrains | existing |
| 21 | **`requirement_kind`** | Specific | enum | no | requirement, constraint, principle | ArchiMate has three separate concepts. | **proposed** |
| 22 | **`derived_from`** | Specific | list of text | no | — | The origin of the requirement (e.g. | **proposed** |
| 23 | **`priority`** | Specific | enum | no | must, should, could, won't | MoSCoW priority, a common convention with no open standard definition. | **proposed** |

**Sources of the specific fields**

| Field | Status | Answers | Source | Reasoning | Confidence |
|---|---|---|---|---|---|
| `applies_to` | existing | — | ArchiMate relationship (ArchiMate 3.2 (relationship)) | ArchiMate links a requirement to the core element that realizes it; SDEM records the targets on the requirement for joining. | medium |
| `requirement_kind` | proposed DA1-41 | Is this something to achieve, a limit, or a guiding rule? | [ArchiMate 3.2 concept](https://pubs.opengroup.org/architecture/archimate3-doc/) `Requirement, Constraint, Principle (motivation)` | ArchiMate has three separate concepts; SDEM holds them as one entity with a kind field. | **medium** |
| `derived_from` | proposed DA1-42 | Which regulation, policy or decision does this come from? | [Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) `dcterms:source` | The origin of the requirement (e.g. a regulation article or policy id). | **high** |
| `priority` | proposed DA1-43 | What must be met first? | [SDEM-defined](https://github.com/taumoeps/bian-sdem-framework) `—` | MoSCoW priority, a common convention with no open standard definition. | **low** |

## Summary of proposed fields

| Group | Fields | High | Medium | Low |
|---|---|---|---|---|
| Common (every entity) | 11 | 9 | 2 | 0 |
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

## Decisions for you

1. **Common fields** — accept all eleven for every architecture? `owner` and `access_classification` are the two not purely Dublin Core. Accepting `owner` replaces the existing free-text `owner` on capabilities.
2. **The 13 SDEM-defined (low) fields** — keep all, or drop some?
3. **Hierarchy stays a link, not a field** — parent capability, process and unit remain composition links; `level` records depth only.
4. **Required fields** — all proposed fields are optional. Should any be required (e.g. `owner`, `criticality`)?

