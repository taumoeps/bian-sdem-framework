# SDEM organisation profiles — specification

> **Status: built (v0.12.0, 2026-11-02).** Owner's decision ("approve the profile", 2026-11-02): an organisation's own design specifications sit **on top of** SDEM's metamodel — never instead of it. Code: `sdem/profile.py`; schema `schema/profile.schema.json`; tests `tests/test_profile.py`; synthetic examples `examples/profiles/`.

## Why

An organisation's A1–A4 design specifications differ from SDEM's defaults (BIAN, TOGAF, ArchiMate): its own kinds of thing, its own mandatory fields, its own words. Until now that meant editing SDEM's bundled files — lost on every upgrade, with no record of what was the organisation's. Different design teams also need different specifications. A profile keeps the organisation's additions as governed data in its private repository, layered on a core every team shares, so cross-team traces and dashboards still join on the common four layers.

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| PR-01 | **A profile is a file in the workspace**, `sdem-profile.json` (format `sdem-profile/1`), with a name and version. It may **extend one base profile** (`"extends"`, a path relative to the file — the organisation's standard profile every team inherits); bases may extend bases; a circle is refused. The merged result is base first, then the team's additions. | `test_the_example_profiles_check_and_extend` |
| PR-02 | **A profile adds, never changes.** It cannot redefine an SDEM type, remove one, or change the nine cross-layer link types, the impact rules or the requirements dispositions; `sdem profile check` refuses it. Profile types are named `<ORG>.<layer>.<Name>`. | `test_a_profile_never_changes_sdem_itself` |
| PR-03 | **Types**: each profile type `extends` an SDEM type (or another profile type) of the same layer and inherits its attributes, its link rules, its cross-layer link types, its impact rules and its place in requirements analysis. Records of that type are checked, linked, traced and assessed as records of the SDEM type they extend. | `test_a_bank_type_is_an_application_to_the_engine_and_the_names_show` |
| PR-04 | **Attributes and rules**: a profile declares attributes on a type (and so on its subtypes) — `string`, `integer`, `number`, `boolean`, `date`, `enum` (with values), `list<string>`, `map<string,string>`; required or optional — and rules that name attributes a type must carry, with the organisation's own message. `sdem check` enforces them like SDEM's own (LC-04 … LC-06); a planned record is advised, not refused. | `test_the_bank_rules_apply_to_the_data` |
| PR-05 | **Within-layer link kinds**: a profile may add its own kinds between two types of one layer, each mapped onto an ArchiMate kind SDEM already knows (`maps_to`); `sdem check` accepts them, an unknown kind is still refused. | `test_a_bank_link_kind_inside_a_layer` |
| PR-06 | **One merged metamodel**: every command sees SDEM's metamodel with the active profile applied (`Metamodel.load()`); SDEM's own metamodel is never modified (`Metamodel.base()`), and a workspace without a profile is unaffected. | `test_a_profile_never_changes_sdem_itself` |
| PR-07 | **Activation and provenance**: the profile is activated from the workspace a command works on (`--workspace`, the datasets' folder), is checked first, and a failing profile refuses the command. A graph store keeps the merged profile it was built with (`profile.json`) and reads under it; a baseline (`sdem new --from`) carries the source's profile and `workspace.json` records it. | `test_a_bank_type_is_…`, `test_a_baseline_carries_its_profile_…` |
| PR-08 | **Names**: a profile's words for layers and types appear in traces, impact and dashboards (`[L3 Applications · Application]`); a profile type shows its layer, its name and its organisation. | `test_a_bank_type_is_…` |
| PR-10 | **Conditional rules**: a rule's `when` names attribute values (or `lifecycle_status`) a record must have for the rule to apply — one value or a list. `{"when": {"environment": "production"}, "require": ["dr_tier", "dr_region"]}` applies to production platforms only. | `test_disaster_recovery_rules_are_conditional_and_cross_record` |
| PR-11 | **Cross-record rules**, along within-layer links: `link` — the record has at least `min` links of a kind (`direction` out or in, optionally `to` a type), e.g. every tier 1 production platform has a `dr_pair_of`; `compare` — every record linked by a kind has a different (`differ`) or the same (`equal`) value of an attribute, e.g. a platform and its DR pair run in different regions. Rules follow links inside one layer; cross-layer obligations are requirements (`requirements.json`). | `test_disaster_recovery_rules_are_conditional_and_cross_record` |
| PR-12 | **Requirement categories**: a profile adds categories to SDEM's nine (`requirement_categories`), accepted in `requirements.json` while the profile is active; one of SDEM's own cannot be redeclared. Risk rules for a new category fall back to SDEM's general (`*`) rules. | `test_the_organisation_adds_requirement_categories` |
| PR-09 | **Evidence**: a profile type carries `evidence_status: organisation_defined` and cites the profile and the organisation's source (`source`), so a reviewer can tell an organisation's extension from SDEM's own, source-cited vocabulary. | `test_a_profile_never_changes_sdem_itself` |

## Also built with it

**Requirements trace through what realises them.** The metamodel already allowed a capability, process, activity or service to *realise* an `A1.BusinessRequirement` (ArchiMate 3.2 ch. 6; constraints RA1-13, RA1-21, RA1-33, RA1-34), but `sdem trace` did not follow that link. It now does (with `--follow-composition`): a functional requirement traces downstream through the process that realises it to the BIAN domain, the application and the platform, and a trace up from the platform reaches the requirement. Non-functional requirements keep their mechanism — the measurable registry (`requirements.json`), whose entries can derive from an A1 requirement. No metamodel change was needed. (`test_a_requirement_traces_through_what_realises_it`)

## Not in a profile

- New **layers** above A1 or below A4 are declared in a profile too (`layers`, `link_types`) — see the layer registry ([`sdem-layers-spec.md`](sdem-layers-spec.md), v0.13.0).
- Anything a team wants **removed** from the core: that is a request to SDEM's owner, not a profile.

## Synthetic example

`examples/profiles/bank-base.json` (a made-up bank's standard: a payments microservice type, a control-function capability, `risk_tier` and `cost_centre` on applications, a `requirement_class` of functional / non-functional on requirements, rule BANK-R01; **disaster recovery on A4** — `environment`, `dr_tier`, `dr_region`, `replication_mode`, `failover_tested_on`, link kind `dr_pair_of`, rules BANK-DR01 (production platforms state DR tier, region and replication), BANK-DR02 (tier 1–2 production platforms have a DR pair) and BANK-DR03 (the pair runs in another region); requirement category `operational_resilience`; link kind `operated_by`; the bank's layer names L1–L4) and `payments-team.json`, which extends it. `sdem profile example --out <dir>` writes them.
