# Updating SDEM without harming your work — specification

> **Status: built (v0.17.0, 2026-11-03).** Owner's decision ("build the update framework", 2026-11-03): architects download SDEM, use it in their own environment with their own, sensitive data, customise it, and never upload anything; SDEM keeps evolving, and they must be able to take each new version without destroying their work. Code: `sdem/upgrade.py`, `sdem/releases.json`; tests `tests/test_upgrade.py`.

## The model

```
SDEM (the product)                               your workspace repository (private — never shared)
github.com/…/bian-sdem-framework                 ├── requirements.txt    pins "sdem @ …@v0.17.0"
  tagged releases                ── pip ──▶       ├── sdem-profile.json   your types, rules, layers, names, requires_sdem
                                                 ├── standards/, patterns/  your standards and reference architectures (PR-13, PR-17)
  (downloaded; nothing uploaded)                 ├── governance.json, .github/, AGENTS.md (your agents, CI)
                                                 └── workspaces/…        your designs
```

**Never edit SDEM itself.** Every customisation lives in the workspace repository — profiles (with a shared base profile), added layers, governance, your agents' instructions, your CI. Editing SDEM's code is a fork: every update becomes a merge.

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| UF-01 | **Know before you switch.** `sdem upgrade check` is run by the *new* version, installed side by side, against the repository's workspaces; it writes nothing. It reads the version in use from `requirements.txt` (or `--from`). | `test_it_tells_what_upgrading_means_and_writes_nothing` |
| UF-02 | It reports, per workspace: the migration needed and what it changes in the data (already checked as a dry run), whether the organisation profile passes, check errors, connections using a deprecated link type; for the repository: the agent and Copilot files `sdem agents install` would update and those your team changed (kept); and a verdict — **ready**, **migrate**, **blocked** — with the steps in order. Exit 1 only when blocked. | `test_it_tells_…`, `test_a_profile_this_version_does_not_meet_blocks`, `test_a_deprecated_link_in_use_is_named` |
| UF-03 | **Release notes as data** (`sdem/releases.json`, shipped in the package): per release, its kind, metamodel version, migration, breaking changes, deprecations (with the version that removes them) and the actions to take. `sdem releases --since <version>` lists them; `upgrade check` shows those since your version. Every CHANGELOG release since 0.10.0 has its notes. | `test_every_release_since_0_10_has_its_notes`, `test_releases_since` |
| UF-04 | **Profiles state the SDEM they need**: `requires_sdem` (e.g. `">=0.13,<1.0"`) in a profile and in its base; a version outside it refuses the profile with a message saying so. | `test_version_requirements`, `test_a_profile_this_version_does_not_meet_blocks` |
| UF-05 | **The version promise**: a **patch** (0.16.x) never changes the metamodel or your data and has no migration; a **minor** (0.x) may add features and change the metamodel — always with a recorded, checked migration and deprecation before removal (MS-05, MS-06); the **metamodel version** is the data format. Enforced: a release whose metamodel changes is a minor, announces the migration, and the migration is recorded. | `test_the_notes_agree_with_the_metamodel_and_its_migrations` |
| UF-06 | **Stable surfaces**: command names and options (removed only after a deprecation), `--json` output (fields added, never renamed), file formats (versioned by `metamodel_version` and `format`), exit codes and error codes. | the agent CLI contract tests |
| UF-07 | **Nothing leaves**: SDEM never contacts a server; updates are pulled by the architect; feedback to SDEM is by issue with a synthetic reproduction, never data. | SECURITY.md, PRIVACY.md |
| UF-08 | **Rollback**: pin the previous version and revert the upgrade commit. A migration is one recorded commit (`migrations/MIG-nnn.json`), so reverting it restores the files exactly. | `docs/sdem-administration.md` |
| UF-09 | **Your standards, patterns and exceptions come with you.** They are files in your repository that a profile includes (PR-13, PR-17) and `exceptions.json` per workspace (PR-18); an upgrade never touches them. `sdem upgrade check` checks the profile with everything it includes under the new version; a rule or attribute the new version no longer accepts — including an attribute SDEM now defines that your profile also declares (PR-14) — blocks the switch with the reason, before anything changes. Run `sdem comply` on your test workspaces in the upgrade branch to see any change in findings. | `test_sdem_s_own_attributes_are_never_redefined`, `test_a_profile_this_version_does_not_meet_blocks` |

## Still to do (recommended next)

Release downloads with SHA-256 checksums and offline-install steps (internal mirror, `pip install --require-hashes`); CI that migrates examples written at every past metamodel version; `sdem agents install --diff` for files your team kept.
