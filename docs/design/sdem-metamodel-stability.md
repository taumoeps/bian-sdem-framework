# SDEM metamodel health and stability — specification

> **Status: built (v0.14.0, 2026-11-02).** Owner's decision ("approve A", 2026-11-02), following the sustainability review: make what is not yet settled measurable, show what workspaces use, keep the core stable by policy, and see what a BIAN release would affect before updating. Code: `sdem/model_health.py`, `release_impact` in `sdem/bian.py`; tests `tests/test_model_health.py`; freeze record `metamodel/stability.json`.

## Why

SDEM's metamodel rests mostly on published standards (BIAN, ArchiMate 3.2, TOGAF) — that is what makes it sustainable. What needs watching: the links *between* the frameworks (most are SDEM's own reasoning, not a standard's), items still pending validation, and a core that changed four times in its first weeks. Organisations now change things through profiles (v0.12.0) and added layers (v0.13.0), so SDEM's core can settle down.

## The stability policy

1. **The core** is SDEM's entity types, the nine cross-layer link types, the within-layer rules and the attributes. Organisation-specific needs go into a profile, never into the core.
2. **A core change** needs a reason: a new release of a standard, a proven error, or the owner's decision on evidence (`sdem model usage`).
3. **Every core change** raises `metamodel_version`, records a migration in `metamodel/migrations.json` (with the owner's approval and any data steps), and is then frozen with `sdem model freeze`.
4. **Nothing is removed without notice**: an item is first marked `deprecated` and frozen; it may be removed in a later version.
5. **CI enforces it**: the test suite fails when the core differs from its freeze without all of the above.

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| MS-01 | `sdem model status` lists every part of SDEM's metamodel that is not fully settled — entity types, cross-layer link types, within-layer rules, attributes, open specification gaps — with totals per area and counts per reason. Works installed. | `test_every_unsettled_item_has_a_source_and_a_way_to_settle_it` |
| MS-02 | Each item shows **its source** and **what would settle it**, in plain words, by reason: pending release validation, proposed extension, SDEM's own definition, intent-only, login-gated and unread, TOGAF unverified, SDEM's reading, medium or low confidence, open gap. | same |
| MS-03 | `sdem model usage --workspace DIR … | --root DIR` shows what workspaces use — entity types (counting subtypes), cross-layer link types (approved and proposed), within-layer kinds, attributes — and which of SDEM's types and link types no workspace uses, unsettled ones first. Each workspace is read under its own profile; a profile's type counts for the SDEM type it extends. | `test_usage_shows_what_is_used_and_what_no_workspace_uses` |
| MS-04 | `metamodel/stability.json` records the core at its last freeze: every entity type, link type, within-layer rule and attribute with its status. `sdem model stability` compares the core with it; the test suite fails on any difference the policy does not allow, and asks for a freeze when a change is allowed. | `test_the_core_is_as_frozen` |
| MS-05 | A changed core needs a higher `metamodel_version` and a migration to it. | `test_a_change_needs_a_new_version_…` |
| MS-06 | An item is removed only if it was already `deprecated` at the freeze. | same |
| MS-07 | `sdem model freeze --person …` records the core, only when stability finds no issue (a checkout; maintainers). The first freeze: metamodel 0.7.0, 2026-11-02. | — |
| MS-08 | `sdem bian impact --workspace DIR | --root DIR --a2 FILE` — read-only, before `sdem bian update`: per workspace, the BIAN records the new layer would drop, rename or change, and the service domains held that the release no longer has; for each, the connections, records, requirements and BIAN links that point at it. | `test_a_release_impact_lists_what_points_at_changed_records` |

## Changes since the first freeze

| Metamodel | Date | Change | Approved |
|---|---|---|---|
| 0.8.0 | 2026-11-02 | B1 cross-layer link review ([b1-cross-layer-link-review.md](b1-cross-layer-link-review.md)): DEPLOYED_ON narrowed to Node, Device, System Software and verified against ArchiMate 3.2 (old row deprecated, removed in 0.9.0); DEPLOYED_AS grounded; one authority corrected; two link types re-cited | the SDEM owner |

## Found while building

`sdem bian impact` showed that `sdem bian update` replaces a workspace's BIAN layer with the held service domains and their parts **as reached from the domains**: a record the new layer still has but that is not reached from a held domain (a business domain grouping, a business scenario) is dropped. An approved connection to such a record makes the update refuse, so nothing is lost silently — but the behaviour is noted for the owner's decision.
