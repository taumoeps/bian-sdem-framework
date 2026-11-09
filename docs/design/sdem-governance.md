# SDEM governance — who decided, and how far that can be trusted

> **Status: built (v0.11.2; guidance revised v0.11.3).** Code: `sdem/governance.py`; tests: `tests/test_governance_hardening.py` (Test D, E). Owner's hardening brief, 2026-11-01.

## The trust boundary, plainly

`--person steven` is **attribution, not authentication.** SDEM runs as a local command line; an AI agent running in the same terminal can type the same name, omit `--agent`, or set any environment variable or flag. Nothing SDEM checks *inside* that environment can tell a person from an agent typing for them — a prompt, a marker file, a confirmation flag or a token the same agent can read or reproduce is **not** a security boundary, and SDEM does not present one as such.

What can be verified independently is a **signature the agent cannot make**: a Git commit signed with the person's own SSH key, where the key is passphrase- or hardware-protected and not available to the agent, checked against an approvers list that code owners protect, and merged through branch protection with an authenticated reviewer.

> SDEM records architectural decisions with attribution and provenance. Verified human authority requires independently protected signing credentials, authorised signers and repository governance controls. AI-agent instructions prohibit approval actions, but instructions alone are not a security boundary.

## Two operating modes

| | Local evaluation mode | Governed enterprise mode |
|---|---|---|
| For | learning, synthetic tests, trying agents | real architecture decisions |
| Where | any folder | a private workspace repository |
| Decisions | recorded in `decisions/` with the name given and the machine's OS and git user — **attributed** | the same, plus **verified**: the person's own SSH-signed commit, checked against `.github/allowed_signers` |
| Integrity | the ledger notices edits made outside `sdem` (`sdem check`) | the same, enforced in CI (`SDEM_REQUIRE_RECORDED`, `SDEM_REQUIRE_SIGNED`) |
| Fail closed | no — a typed name is enough to record a decision | `require_verified_decisions: true` — `sdem work plan` refuses until the acceptance and the authorisation are verified |
| Set-up | none | `governance.json`, allowed signers, approvers' signing keys kept from agents, code owners, branch protection with signed commits, required CI |
| Claim | **no** claim of verified human approval | verified where `sdem governance verify` says `verified` — and only as strong as the protection of the signing keys |

Verification is checked by `sdem governance verify` and by the gate in `sdem work plan`; it is **not** enforced when a decision is recorded — any command that takes `--person` records an attributed decision. Without the governed mode's controls, the command line alone cannot stop an agent with terminal access from recording a decision in a person's name.

## The decision points in a change

1. **Impact calculated** — deterministic, when the change set lands (`sdem change propose`).
2. **Requirements and risk evaluated** — `sdem events validate CE-001` (and `sdem events analyse CE-001` after new evidence).
3. **A1–A4 specialist assessments** — each layer's agent or architect: `sdem events assess CE-001 --layer … `.
4. **Human review** of the evidence, assumptions and risks — `sdem events show CE-001`.
5. **Acceptance of the impact** — a person, deciding any disputed layer and each confirmed requirement breach:
   ```bash
   sdem events accept CE-001 --workspace workspaces/payments --person steven --reason "Reviewed architecture impact and evidence" \
        [--accept-risk RF-BREACH-REQ-AV-02="…"]
   ```
6. **Authorisation of implementation** — a separate decision, possibly by someone else or later:
   ```bash
   sdem events authorise CE-001 --workspace workspaces/payments --person steven
   ```
   (`sdem events accept … --authorise` records both at once — convenient for evaluation; in the governed mode keep them separate.)
7. **Verification** — in the governed mode, commit each decision signed (`git commit -S`); `sdem governance verify --workspace workspaces/payments`.
8. **Work planning** — `sdem work plan --event CE-001 …`; refused until 5 and 6 exist — and, in the governed mode, are verified.

**Requirements dispositions** read at step 4: `compliant` · `current_breach_remediated` (breached today, the proposed architecture meets it — **not** a residual breach, no risk decision) · `proposed_breach` (introduced by the change) · `unresolved_breach` (breached today and after) · `missing_evidence` · `not_confirmed`. Only the two breach kinds need a decision at step 5. A compliant end state is not the same as a safe cutover: potential risks (e.g. downtime during migration) are reported separately.

## Requirements

| Id | Requirement | Verified by |
|---|---|---|
| GV-01 | **Every governed decision is one record**, `<workspace>/decisions/GD-….json`, append-only: kind, subject, the named person, when, and what the machine reports (OS user, git user and email). Written as **attributed** — never as verified. Kinds: `approve_link` (`sdem approve`), `state_link` (`sdem connect`), `confirm_requirement` / `retire_requirement` (`sdem requirements confirm|retire`), `accept_impact`, `accept_residual_risk`, `authorise_implementation` (`sdem events accept|authorise`), `adopt_edit` (`sdem change adopt`), `establish_baseline` (`sdem new --from`), `adopt_profile` (`sdem profile adopt`), `grant_exception` (`sdem exception grant` — a time-limited exception to one of the organisation's rules, PR-18). | Test D, E |
| GV-02 | A person's name is still checked: an agent's name is refused (CTL-21) — a guard against mistakes, not authentication. | existing tests |
| GV-03 | **`sdem governance verify`** reports, per decision: `verified` only when the commit that added its record has a valid SSH signature by the signer `governance.json` maps that person to (`git verify-commit` against the allowed-signers file); otherwise why not — `no_policy`, `not_in_git`, `no_allowed_signers`, `not_an_approver`, `not_committed`, `unsigned_or_invalid`, `signer_mismatch`. `--require-verified` exits 1 unless all are verified (CI on the protected branch). | Test D |
| GV-04 | **Fail closed where required**: with `require_verified_decisions: true` in `governance.json`, `sdem work plan` refuses until the event's `accept_impact` and `authorise_implementation` decisions are verified. An agent typing the person's name — with or without `--agent`, unsigned or signed with its own key — cannot open the gate. | Test D |
| GV-05 | **A governed baseline**: `sdem new --workspace … --person … --from DIR` starts a workspace with existing layers, links and requirements — checked first, recorded in the ledger as the baseline and as an `establish_baseline` decision. Only at creation: a workspace is never re-baselined. | Test E |
| GV-06 | **Explicit reconciliation, never silent repair**: a workspace whose files were copied in after `sdem new` shows them as unrecorded edits; a person accepts each with `sdem change adopt --layer A1|A2|A3|A4|registry|requirements --person … --reason …` — recorded as an `adopt_edit` decision, history untouched. SDEM never rewrites a stale ledger by itself. | Test E |
| GV-07 | Every acceptance says `attestation: attributed` and lists its decision ids; nothing in SDEM reports a decision as verified unless GV-03 found the signature. | Test D |

## Setting it up in a workspace repository

1. **Each approver signs commits with an SSH key** they alone control — passphrase-protected or on a hardware key, **not** loaded into an agent or a session the agent can use: `git config user.signingkey ~/.ssh/id_ed25519_sk.pub`, `git config gpg.format ssh`.
2. **List approvers** in `.github/allowed_signers` (`steven@example.org namespaces="git" ssh-ed25519 AAAA…`), and in `workspaces/<area>/governance.json`:
   ```json
   {"require_verified_decisions": true, "allowed_signers": "../../.github/allowed_signers",
    "approvers": [{"person": "steven", "signer": "steven@example.org"}]}
   ```
3. **Protect them**: code owners on `.github/allowed_signers`, `governance.json`, `decisions/` and `coordination/`; branch protection on `main` requiring signed commits and code-owner review.
4. **CI**: `SDEM_REQUIRE_SIGNED: '1'` in the workspace CI runs `sdem governance verify --require-verified` for every workspace.
5. **Working**: the person runs the decision command, then commits it **signed** (`git commit -S`); only then does `sdem work plan` proceed.

## What this does not guarantee

- If an agent can use the approver's signing key (an unlocked key in a shared agent, a key without a passphrase in the agent's environment), it can sign — protect the key; that is outside SDEM.
- Without `governance.json`, nothing is verified: decisions are attribution only, and SDEM says so (`no_policy`).
- Verification covers decisions committed to Git; a decision not yet committed is `not_committed`.
- SSH signing only (Git ≥ 2.34); GPG-signed commits are not checked by `sdem governance verify`.

## Upgrading a workspace to v0.11.2

- **Validations not yet accepted**: `sdem events analyse <CE-id> --workspace <dir> --agent sdem-orchestrator --person <name>`, then each layer re-assesses (`sdem events assess …`). Acceptance refuses an analysis made by an earlier SDEM, and assessments made against it are stale.
- **Accepted validations** stay exactly as they were; nothing is re-interpreted.
- **A workspace filled by copying files after `sdem new`** (unrecorded edits on files SDEM never wrote): `sdem check --workspace <dir>` lists them; a person reconciles each, explicitly and on record — `sdem change adopt --workspace <dir> --layer A1|A2|A3|A4|registry|requirements --person <name> --reason "<why>"`. Layers with change sets are adopted as change sets (their history continues); the others are accepted in the ledger. SDEM never does this by itself.
- **Rollback**: pin the previous release again. v0.11.1 ignores `decisions/` and the analysis `contract` field; re-analyse any validation you re-analysed under v0.11.2.
