# `sdem types` and `sdem bian search` — specification

> **Status: built (v0.16.0, 2026-11-02).** Owner's decision ("build types and search", 2026-11-02), after the agent baseline: three independent agents built a ledger design from a prompt; every one of their 19 distinct mistakes was a field name, an allowed value or a link that no command listed, and each looked up BIAN operation ids by importing BIAN into scratch files. Built only if it improves both people's and agents' ability to create designs — measured again against the same baseline before release. Code: `sdem/typeinfo.py`, `search` in `sdem/bian.py`; tests `tests/test_types_search.py`.

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| TS-01 | `sdem types` lists the layers and their kinds of record; `sdem types <layer>` each kind with its fields and links; a mistyped type gets "did you mean". | `test_a_layer_and_the_overview` |
| TS-02 | `sdem types <type>` gives a kind in full: definition and source, what it extends, its fields (type, required, allowed values, what a reference points to), the links it may have inside its layer (with the rule id) and from others, the link types to other layers with the evidence each needs, and the organisation's rules that apply. | `test_a_type_lists_its_fields_values_and_links` |
| TS-03 | `sdem types requirement` gives the requirements registry's format — fields, required or not, allowed categories and scopes, the workspace's layers for `owner_layer`, the condition's operators, and what SDEM sets itself; `sdem types change-set` the change-set format. | `test_the_requirement_and_change_set_formats` |
| TS-04 | `sdem bian search <words>` finds BIAN service domains and operations for plain words (base BIAN, your pack, or a downloaded release), with the ids exactly as `sdem bian import` and `sdem aid` write them. Each word counts by its rarity across BIAN and where it is found (name, control record, operation); a domain whose whole name is asked for comes first; words BIAN does not use are named. No synonyms. | `test_plain_words_find_domains_…`, `test_the_ids_are_the_ones_import_writes`, `test_words_bian_does_not_use_are_named` |
| TS-05 | With `--workspace`, the organisation's profile is included — its types, fields, rules, layers and requirement categories. | `test_a_workspace_profile_is_included` |
| TS-06 | The agent instructions (AGENTS.md, the records and change-set skills) say to ask `sdem types` and `sdem bian search` before writing, never to guess. | — |

## Fixed with it (found by the baseline)

- `sdem requirements` accepted an `owner_layer` that is not a layer of the workspace, and unknown fields; both are now refused.
- `sdem aid --dry-run --json` did not report `would_write`, which AGENTS.md promises; it does now.
- `sdem aid` crashed with an internal error when an approved connection pointed to a record the workspace no longer held; it now refuses with code `refused` and a hint.
