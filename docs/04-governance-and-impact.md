# Mapping governance, history and impact

## Lifecycle
`proposed` → `validated` → `approved` → `superseded`, with `needs_review` and `rejected` as side states.

| Status | Meaning | Validator requires |
|---|---|---|
| `proposed` | Candidate from analysis or an engine; may carry `confidence` | evidence, rationale, baseline |
| `validated` | Passed deterministic checks; awaiting architect decision | as above |
| `needs_review` | Flagged uncertain or contradictory; architect must decide | as above |
| `approved` | Published architecture fact | `reviewer_id` |
| `rejected` | Decision recorded, not published | `reviewer_id` |
| `superseded` | Replaced by a newer record | `reviewer_id`, and a successor whose `previous_mapping_id` points here |

- Only `approved` mappings are included in default traceability queries.
- Source and target references point to immutable entity versions.
- Store reviewer, evidence, rationale and applicability baseline.
- Publish new mapping versions (via `previous_mapping_id`) instead of overwriting historical relationships.
- Change detection traverses both outgoing and incoming edges without storing duplicate inverse edges.

## Impact classification
Impact analysis classifies each reachable entity as one of:

- `no_impact` — reachable, but the change type does not affect this relationship's semantics.
- `review_required` — potentially affected; an architect must assess.
- `design_change_required` — directly affected; a design revision is needed.

An architect confirms the outcome. Graph reachability alone never implies a required change.

## Handling legacy designs
Keep previous L1 conceptual architecture documents as immutable artefacts. Create derived map claims to current L1 BIAN-aligned design objects where justified; do not imply an old document was authored to BIAN standards.

## Design approvals
Enforce authorization and audit logs in any production deployment; this starter package intentionally does not implement identity management or a graph backend.
