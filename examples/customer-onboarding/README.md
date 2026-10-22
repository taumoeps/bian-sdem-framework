# Synthetic Customer Onboarding mapping

All identifiers (`SD-001`, `APP-001`, `INF-001`, `DEMO-BIAN-*`, `DEMO-RELEASE`, …) are **synthetic**. They are not official BIAN IDs and do not represent verified BIAN release content.

The document exercises the full SDMM model:

| Records | What they show |
|---|---|
| MAP-001 → MAP-002 → MAP-003 | Architecture chain A1 capability → A2 domain → A3 component → A4 hosting |
| MAP-004, MAP-005 | Process perspective: value stream → scenario, process → domain (`USES_DOMAIN`) |
| MAP-006 → MAP-007 | Information perspective: A1 business object → A2 BIAN object → A3 data entity |
| MAP-008 → MAP-003 | Lifecycle: a `superseded` deployment and its successor via `previous_mapping_id` |
| MAP-009, MAP-010 | Engine output: `proposed` and `needs_review` candidates with `confidence`, no reviewer yet |

BIAN-grounded records (`bian_alignment_guidance` authority) carry a `bian_release` and a `canonical_id` on the A2 endpoint, ready for a licensed reference adapter (see `sdmm/reference.py`).

Level exports `a1–a4-*.json` (24 synthetic instances, written to `metamodel/export-conventions.json`) back every id in the mappings, so the graph tools run on this example — use case **E2** in `docs/use-case-testing.md`.

```bash
python -m sdmm.graph check examples/customer-onboarding/a*.json examples/customer-onboarding/mappings.json
python -m sdmm.graph trace CAP-001 --direction down examples/customer-onboarding/a*.json examples/customer-onboarding/mappings.json
python -m sdmm.graph impact APP-001 --change replace examples/customer-onboarding/a*.json examples/customer-onboarding/mappings.json
python -m sdmm.validate examples/customer-onboarding/mappings.json
python -m sdmm.validate --json examples/customer-onboarding/mappings.json
```

See `examples/card-fraud-alerts/` for a second example that walks through a change event (supersession).
