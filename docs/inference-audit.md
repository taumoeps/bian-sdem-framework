# SDEM inference audit

A snapshot taken 2026-10-23 by `python scripts/inference_audit.py` from the records (`metamodel/`, `schema/`). It answers one question: **without access to the login-gated standards or a standards MCP server, how much of SDEM is inferred rather than taken from a verifiable public source?** Counts are computed by script from the records; attribute sources are read from `metamodel/entity-attributes.json` (see `architecture-attribute-design.md`).

**Definitions used.** *Grounded*: stated in a public source anyone can check (BIAN public portal and Semantic API guide; ArchiMate concept names; OpenAPI). *Oracle-confirmed*: inferred by SDEM, then confirmed against the open-source Archi implementation of the ArchiMate relationship tables. *Inferred*: SDEM's own reading or design, with reasoning recorded, tested by the use cases but not by a standard. *Gated*: cited to TOGAF or the ArchiMate text and not checkable without an Open Group login.

## 1. Summary by layer

| Layer | Total | Grounded | Oracle-confirmed | Inferred | Gated / unverified |
|---|---|---|---|---|---|
| Entity definitions | 44 | 32 | — | 12 (7 SDEM extensions, 5 interpreted alignments) | 0 |
| Attributes | 53 | 12 (BIAN 9, OpenAPI 3) | — | 35 (relationship held as attribute 19, SDEM-defined 16) | 1 TOGAF; plus 5 institution data (not a standards question) |
| Within-level rows | 132 | 16 | 113 | 1 | 2 |
| Cross-level rules (50 that can produce a link or report) | 50 | 10 official | — | 34 (28 with no official source, 6 SDEM definitions) | 6 |

**Across all four layers** (274 items, institution data excluded): 70 grounded (26%), 113 oracle-confirmed (41%), the rest inferred or gated (33%).

**Where inference concentrates.** (1) **Cross-level rules**: BIAN publishes almost nothing below A2 and no capability-to-domain mapping, so most rules are SDEM's; they are the part tested by the eleven use-case runs (50 rows validated against sealed answers), not by a standard. (2) **Attributes of ArchiMate-derived entities**: ArchiMate defines no attributes, so every A1, A3 and A4 field is either a relationship SDEM chose to record on the entity or a field SDEM defined. (3) **Within-level rows** were mostly inferred, but 113 of them are now confirmed by the Archi oracle.

**Where it does not.** A2 is grounded almost entirely in BIAN's public material; entity *concepts* are grounded for 32 of 44 entities; API attributes follow OpenAPI.

## 2. Attribute sources (from metamodel/entity-attributes.json)

| Attribute | Source |
|---|---|
| `A1.BusinessActivity.invokes` | ArchiMate relationship held as attribute |
| `A1.BusinessCapability.owner` | SDEM-defined |
| `A1.BusinessObject.attributes` | SDEM-defined |
| `A1.BusinessObject.field_aliases` | institution data |
| `A1.BusinessProcess.invokes` | ArchiMate relationship held as attribute |
| `A1.BusinessRequirement.applies_to` | ArchiMate relationship held as attribute |
| `A1.BusinessService.inputs` | SDEM-defined |
| `A1.BusinessService.outputs` | SDEM-defined |
| `A1.ValueStream.stages` | ArchiMate relationship held as attribute |
| `A2.AssetType.aliases` | institution data |
| `A2.BehaviorQualifier.aliases` | institution data |
| `A2.BusinessObject.attributes` | BIAN (public) |
| `A2.BusinessScenario.operation_sequence` | BIAN (public) |
| `A2.ControlRecord.attributes` | BIAN (public) |
| `A2.ControlRecord.lifecycle_states` | SDEM-defined |
| `A2.ServiceDomain.asset_type` | BIAN (public) |
| `A2.ServiceDomain.functional_pattern` | BIAN (public) |
| `A2.ServiceOperation.action_term` | BIAN (public) |
| `A2.ServiceOperation.behavior_qualifier` | BIAN (public) |
| `A2.ServiceOperation.input_attributes` | BIAN (public) |
| `A2.ServiceOperation.output_attributes` | BIAN (public) |
| `A3.APIOperation.method` | OpenAPI (public) |
| `A3.APIOperation.path` | OpenAPI (public) |
| `A3.APIOperation.payload_fields` | OpenAPI (public) |
| `A3.ApplicationComponent.built_as` | ArchiMate relationship held as attribute |
| `A3.ApplicationComponent.deployed_as` | SDEM-defined |
| `A3.ApplicationComponent.deployed_on` | ArchiMate relationship held as attribute |
| `A3.ApplicationComponent.network_zone` | SDEM-defined |
| `A3.ApplicationComponent.vendor` | SDEM-defined |
| `A3.ApplicationFunction.consumes` | ArchiMate relationship held as attribute |
| `A3.ApplicationFunction.exposed_through` | SDEM-defined |
| `A3.ApplicationInterface.exposed_through` | ArchiMate relationship held as attribute |
| `A3.ApplicationInterface.field_aliases` | institution data |
| `A3.ApplicationService.consumes` | ArchiMate relationship held as attribute |
| `A3.DataEntity.attributes` | SDEM-defined |
| `A3.DataEntity.field_aliases` | institution data |
| `A3.DataEntity.stored_in` | ArchiMate relationship held as attribute |
| `A3.Event.published_to` | SDEM-defined |
| `A3.SolutionBuildingBlock.components` | TOGAF (login-gated) |
| `A4.Artifact.of_component` | ArchiMate relationship held as attribute |
| `A4.CommunicationNetwork.connects` | ArchiMate relationship held as attribute |
| `A4.Deployment.component_id` | SDEM-defined |
| `A4.Deployment.environment_id` | SDEM-defined |
| `A4.Deployment.platform_id` | SDEM-defined |
| `A4.Device.hosts` | ArchiMate relationship held as attribute |
| `A4.Node.hosts` | ArchiMate relationship held as attribute |
| `A4.Path.carries` | SDEM-defined |
| `A4.Path.from` | ArchiMate relationship held as attribute |
| `A4.Path.network` | ArchiMate relationship held as attribute |
| `A4.Path.to` | ArchiMate relationship held as attribute |
| `A4.SystemSoftware.hosts` | ArchiMate relationship held as attribute |
| `A4.TechnologyInterface.exposes` | SDEM-defined |
| `A4.TechnologyInterface.of_service` | ArchiMate relationship held as attribute |

## 3. Entity by entity

| Entity | Standard: concept | Definition | Attributes (source) | Within-level rows | Cross-level rules | Review note |
|---|---|---|---|---|---|---|
| `A1.BusinessCapability` | BIAN BCM: Business Capability | aligned (interpreted) | `owner` SDEM | 7 inferred, oracle-confirmed | 1 official (S01) | definition interpreted from a standard; has SDEM-defined fields |
| `A1.ValueStream` | ArchiMate 3.2: Value Stream | grounded | `stages` rel. | 4 inferred, oracle-confirmed | 1 SDEM definition (S02) | grounded |
| `A1.ValueStreamStage` | SDEM: Value Stream Stage | SDEM extension (inferred) | — | 6 inferred, oracle-confirmed | 1 inferred (no official source) (S03) | definition is SDEM's; 1 cross-level rule(s) with no official source |
| `A1.BusinessProcess` | ArchiMate 3.2: Business Process | grounded | `invokes` rel. | 13 inferred, oracle-confirmed | 1 cited, unverified (S04) | grounded |
| `A1.BusinessActivity` | SDEM: Business Activity | SDEM extension (inferred) | `invokes` rel. | 13 inferred, oracle-confirmed | 2 inferred (no official source) (S06, S07) | definition is SDEM's; 2 cross-level rule(s) with no official source |
| `A1.BusinessService` | ArchiMate 3.2: Business Service | grounded | `inputs` SDEM; `outputs` SDEM | 9 inferred, oracle-confirmed | 2 inferred (no official source) (S08, S09) | has SDEM-defined fields; 2 cross-level rule(s) with no official source |
| `A1.BusinessActor` | ArchiMate 3.2: Business Actor | grounded | — | 6 inferred, oracle-confirmed | — | grounded |
| `A1.BusinessRole` | ArchiMate 3.2: Business Role | grounded | — | 6 inferred, oracle-confirmed | — | grounded |
| `A1.BusinessObject` | ArchiMate 3.2: Business Object | grounded | `attributes` SDEM; `field_aliases` inst. | 6 inferred, oracle-confirmed | 1 official (S12) | has SDEM-defined fields |
| `A1.BusinessRequirement` | ArchiMate 3.2: Requirement | grounded | `applies_to` rel. | 6 inferred, oracle-confirmed | 2 inferred (no official source) (S13, S14) | 2 cross-level rule(s) with no official source |
| `A2.BusinessArea` | BIAN Service Landscape: Business Area | grounded | — | 1 grounded | 1 inferred (no official source) (S15) | 1 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.BusinessDomain` | BIAN Service Landscape: Business Domain | grounded | — | 2 grounded | 1 inferred (no official source) (S16) | 1 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.ServiceDomain` | BIAN Service Landscape: Service Domain | grounded | `asset_type` BIAN; `functional_pattern` BIAN | 8 grounded | 3 inferred (no official source), 2 official, 1 cited, unverified (S01, S04, S07, S08, S13, S17) | 3 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.FunctionalPattern` | BIAN Service Landscape: Functional Pattern | grounded | — | 1 grounded | 1 inferred (no official source) (S18) | 1 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.AssetType` | BIAN Service Landscape: Asset Type | grounded | `aliases` inst. | 1 grounded | 1 inferred (no official source) (S19) | 1 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.ControlRecord` | BIAN Service Landscape: Control Record | grounded | `attributes` BIAN; `lifecycle_states` SDEM | 4 grounded | 2 official (S20, S21) | has SDEM-defined fields; BIAN release not yet verified |
| `A2.ServiceGroup` | BIAN Service Landscape: Service Group | grounded | — | 2 grounded | 2 inferred (no official source) (S22, S23) | 2 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.ServiceOperation` | BIAN Service Landscape: Service Operation | grounded | `action_term` BIAN; `behavior_qualifier` BIAN; `input_attributes` BIAN; `output_attributes` BIAN | 4 grounded | 3 inferred (no official source), 2 official (S06, S09, S14, S24, S25) | 3 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.BehaviorQualifier` | BIAN Service Landscape: Behavior Qualifier | grounded | `aliases` inst. | 2 grounded | 2 inferred (no official source) (S26, S27) | 2 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.BusinessScenario` | BIAN Service Landscape: Business Scenario | grounded | `operation_sequence` BIAN | 1 grounded | 2 official, 1 SDEM definition, 1 inferred (no official source) (S02, S03, S28, S29) | 1 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.BusinessObject` | BIAN Service Landscape: Business Object | grounded | `attributes` BIAN | 2 grounded, 1 inferred | 2 official (S12, S30) | BIAN release not yet verified |
| `A2.BusinessObjectAttribute` | BIAN Service Landscape: Business Object attribute | grounded | — | 1 grounded | 1 inferred (no official source) (S31) | 1 cross-level rule(s) with no official source; BIAN release not yet verified |
| `A2.BOMModel` | BIAN Service Landscape: Business Object Model | SDEM extension (inferred) | — | 1 inferred | — | definition is SDEM's |
| `A2.Wireframe` | BIAN Service Landscape: Wireframe | grounded | — | 1 grounded | — | BIAN release not yet verified |
| `A2.SemanticAPI` | BIAN Semantic API: Semantic API | aligned (interpreted) | — | 1 grounded | — | definition interpreted from a standard |
| `A3.ApplicationComponent` | ArchiMate 3.2: Application Component | grounded | `deployed_on` rel.; `deployed_as` SDEM; `built_as` rel.; `network_zone` SDEM; `vendor` SDEM | 13 inferred, oracle-confirmed, 1 inferred, unverified | 5 inferred (no official source), 3 SDEM definition, 2 official, 2 cited, unverified (S15, S16, S17, S29, S32, S33, S34, S35, S37, S38, S39, S40) | has SDEM-defined fields; 5 cross-level rule(s) with no official source |
| `A3.ApplicationService` | ArchiMate 3.2: Application Service | grounded | `consumes` rel. | 6 inferred, oracle-confirmed | 2 inferred (no official source), 2 official, 1 cited, unverified (S22, S25, S28, S41, S42) | 2 cross-level rule(s) with no official source |
| `A3.ApplicationInterface` | ArchiMate 3.2: Application Interface | grounded | `exposed_through` rel.; `field_aliases` inst. | 3 inferred, oracle-confirmed | 3 inferred (no official source) (S23, S43, S44) | 3 cross-level rule(s) with no official source |
| `A3.ApplicationFunction` | ArchiMate 3.2: Application Function | grounded | `exposed_through` SDEM; `consumes` rel. | 9 inferred, oracle-confirmed | 2 inferred (no official source), 1 official, 1 cited, unverified (S18, S21, S45, S46) | has SDEM-defined fields; 2 cross-level rule(s) with no official source |
| `A3.APIOperation` | BIAN Semantic API: Service Operation (API) | SDEM extension (inferred) | `method` OpenAPI; `path` OpenAPI; `payload_fields` OpenAPI | 3 inferred, oracle-confirmed | 2 SDEM definition, 1 official, 1 inferred (no official source) (S24, S26, S47, S48) | definition is SDEM's; 1 cross-level rule(s) with no official source |
| `A3.DataEntity` | ArchiMate 3.2: Data Object | aligned (interpreted) | `attributes` SDEM; `stored_in` rel.; `field_aliases` inst. | 8 inferred, oracle-confirmed | 4 inferred (no official source), 2 official, 1 cited, unverified (S19, S20, S27, S30, S31, S49, S50) | definition interpreted from a standard; has SDEM-defined fields; 4 cross-level rule(s) with no official source |
| `A3.Event` | ArchiMate 3.2: Application Event | aligned (interpreted) | `published_to` SDEM | 5 inferred, oracle-confirmed | 1 inferred (no official source) (S51) | definition interpreted from a standard; has SDEM-defined fields; 1 cross-level rule(s) with no official source |
| `A3.SolutionBuildingBlock` | TOGAF: Solution Building Block | aligned (interpreted) | `components` TOGAF | 2 inferred, unverified | 3 inferred (no official source) (S52, S53, S54) | definition interpreted from a standard; 3 cross-level rule(s) with no official source |
| `A4.InfrastructureComponent` | SDEM: Infrastructure Component | SDEM extension (inferred) | — | — | 1 SDEM definition, 1 inferred (no official source) (S33, S52) | definition is SDEM's; 1 cross-level rule(s) with no official source |
| `A4.Deployment` | SDEM: Deployment | SDEM extension (inferred) | `component_id` SDEM; `environment_id` SDEM; `platform_id` SDEM | 5 inferred, oracle-confirmed | 2 SDEM definition, 1 inferred (no official source) (S32, S47, S53) | definition is SDEM's; has SDEM-defined fields; 1 cross-level rule(s) with no official source |
| `A4.DeploymentEnvironment` | SDEM: Deployment Environment | SDEM extension (inferred) | — | 4 inferred, oracle-confirmed | 1 SDEM definition (S40) | definition is SDEM's |
| `A4.Node` | ArchiMate 3.2: Node | grounded | `hosts` rel. | 12 inferred, oracle-confirmed | 1 cited, unverified, 1 inferred (no official source) (S34, S54) | 1 cross-level rule(s) with no official source |
| `A4.Device` | ArchiMate 3.2: Device | grounded | `hosts` rel. | 10 inferred, oracle-confirmed | 1 inferred (no official source) (S35) | 1 cross-level rule(s) with no official source |
| `A4.SystemSoftware` | ArchiMate 3.2: System Software | grounded | `hosts` rel. | 9 inferred, oracle-confirmed | 2 inferred (no official source) (S46, S50) | 2 cross-level rule(s) with no official source |
| `A4.TechnologyService` | ArchiMate 3.2: Technology Service | grounded | — | 8 inferred, oracle-confirmed | 2 cited, unverified, 2 inferred (no official source) (S41, S44, S45, S51) | 2 cross-level rule(s) with no official source |
| `A4.TechnologyInterface` | ArchiMate 3.2: Technology Interface | grounded | `of_service` rel.; `exposes` SDEM | 4 inferred, oracle-confirmed | 2 inferred (no official source), 1 SDEM definition (S42, S43, S48) | has SDEM-defined fields; 2 cross-level rule(s) with no official source |
| `A4.CommunicationNetwork` | ArchiMate 3.2: Communication Network | grounded | `connects` rel. | 2 inferred, oracle-confirmed | 1 inferred (no official source) (S37) | 1 cross-level rule(s) with no official source |
| `A4.Path` | ArchiMate 3.2: Path | grounded | `from` rel.; `to` rel.; `network` rel.; `carries` SDEM | 1 inferred, oracle-confirmed | 1 inferred (no official source) (S38) | has SDEM-defined fields; 1 cross-level rule(s) with no official source |
| `A4.Artifact` | ArchiMate 3.2: Artifact | grounded | `of_component` rel. | 6 inferred, oracle-confirmed | 2 cited, unverified (S39, S49) | grounded |

## 4. What would reduce the inference

| Action | Reduces | Needs |
|---|---|---|
| Verify the 13 BIAN entities and 16 A2 rows against a licensed BIAN release | the `pending_release_validation` status on all of A2 | BIAN membership access |
| Read the ArchiMate 3.2 and TOGAF 10 specifications | the 2 TOGAF rows, the TOGAF attribute, the 7 gated cross-level citations; would upgrade 113 oracle-confirmed rows to specification-verified | a free Open Group account |
| Adopt AsyncAPI for events | adds a public source for `A3.Event` fields | nothing (public standard) |
| A blind test case | tests the inferred cross-level rules on data their author has not seen | a second author |
| Ask BIAN for the unpublished capability-to-domain mapping (B01) | the largest unsourced cross-level rule, S01 | engagement with BIAN |

