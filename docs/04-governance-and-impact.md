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

### Permitted transitions

| From | May move to |
|---|---|
| `proposed` | `validated`, `needs_review`, `rejected`, `approved` |
| `validated` | `approved`, `needs_review`, `rejected` |
| `needs_review` | `validated`, `approved`, `rejected`, `proposed` |
| `approved` | `superseded` only |
| `rejected`, `superseded` | nothing — terminal |

`sdmm-diff` enforces these between two versions of a document (a previous file, or a git revision such as `HEAD~1`). Run it in CI so an illegal transition cannot merge.

### Immutability

Once a record is `approved`, `rejected` or `superseded` its fields are frozen. The only permitted edit is `approved → superseded`, which may also set `valid_to`. Records are never deleted. `sdmm-diff` reports any other change. One exception: evidence references may be *re-typed* (`kind:ref` added to an existing reference) because that annotates the evidence without changing which artefact is cited.

### Evidence

Each registry entry lists `required_evidence` kinds. Cite evidence as `kind:reference`, e.g. `process_model:PM-2026-014`. When a mapping uses typed references, every required kind must be present or validation fails. Untyped references are accepted with a warning (`--strict` turns warnings into errors) so existing documents can be migrated gradually.

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

## Authoritative and derived relationships

Only adjacent-level edges (L0→L1, L1→L2, L2→L3) are ever **stored**; the registry self-check rejects anything else. A relationship that skips levels — a requirement traced straight to a security control at L3, say — is a **derived** relationship: computed by walking the stored edges, and reported with provenance to every approved edge on the path. Derived relationships are query results, never records. This keeps one authoritative chain while leaving traceability questions unrestricted.

## Handling legacy designs
Keep previous L1 conceptual architecture documents as immutable artefacts. Create derived map claims to current L1 BIAN-aligned design objects where justified; do not imply an old document was authored to BIAN standards.

## Design approvals
Enforce authorization and audit logs in any production deployment; this starter package intentionally does not implement identity management or a graph backend.
