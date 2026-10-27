# Evidence each link type needs before approval

From `schema/relationship-types.json` (the `required_evidence` of each relationship type). Write evidence as `kind:document-reference`.

| Link | Required evidence kind(s) |
|---|---|
| A1.BusinessCapability **SUPPORTED_BY** A2.ServiceDomain | `business_architecture_document`, `domain_scope_assessment` |
| A1.ValueStream **ALIGNED_TO** A2.BusinessScenario | `process_model`, `scenario_suitability_review` |
| A1.BusinessProcess **USES_DOMAIN** A2.ServiceDomain | `process_model` |
| A1.BusinessObject **ALIGNED_TO** A2.BusinessObject | `business_glossary`, `object_alignment_review` |
| A2.ServiceDomain **REALIZED_BY** A3.ApplicationComponent | `application_architecture_document` |
| A2.ServiceOperation **IMPLEMENTED_BY** A3.APIOperation | `api_contract` |
| A2.BusinessObject **MAPPED_TO** A3.DataEntity | `data_model` |
| A3.ApplicationComponent **DEPLOYED_ON** A4.InfrastructureComponent | `deployment_design` |
| A3.ApplicationComponent **DEPLOYED_AS** A4.Deployment | `deployment_design` |
