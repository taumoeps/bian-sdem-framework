# Two changes from the public twin — rejecting a proposed link, and flat network zones (RJ-01…RJ-07, ZF-01…ZF-06)

> **Status: approved — the owner approved D1–D4 as recommended (2026-11-17); being built, tests first.** From the first run of the public twin ([report](../evidence/payment-initiation-v3/report.md), findings F14 and F1). **No metamodel file changes in either.**

## 1. Rejecting a proposed link (F14)

**The gap.** `sdem approve` approves a proposed link between layers. There is no way to say *no*. A proposal the architect leaves alone reads to SDEM as *not yet decided*: `sdem link` proposes it again, and `sdem aid`, finding the thing still unconnected, infers something in its place. In the twin the owner declined *BIAN Payment Transaction MAPPED_TO PaymentLedger*; on the next pass SDEM inferred a new 30-field table for the object. (`sdem aid reject` already does this for inferred *records* and for inferred links *inside* a layer — not for proposals *between* layers.)

| Id | Rule |
|---|---|
| RJ-01 | `sdem reject <proposal id …> --proposals <file> --workspace <dir> --reviewer <person> --reason <why>` — the mirror of `sdem approve`. **A person only** (CTL-21: an agent never rejects, as it never approves). `--reason` is required. `--dry-run`, `--json` as every command. |
| RJ-02 | The link is written to the registry (`mappings.json`) with status **`rejected`** — a status the registry's schema already has — with the reviewer, the date and the reason (in its rationale: the schema has no separate field, and is not changed). A rejected entry needs no proving evidence — a rejection is a person's reason, not a document; a governance decision `reject_link` is recorded beside the `approve_link` ones; the ledger notes the write. |
| RJ-03 | **Remembered.** `sdem link` and `sdem aid` do not propose a link whose source, relationship and target are rejected. They say how many they left out for that reason. |
| RJ-04 | **Nothing is put in its place.** `sdem aid` does not infer a table for a BIAN object one of whose MAPPED_TO proposals was rejected (AID-I01): where the object is stored is now the architect's to say. A rejected REALIZED_BY does not count as the domain being realised (AID-I08 — already so). |
| RJ-05 | **Undone by approving.** `sdem approve` of the same link later overrides the rejection: the approved link names the rejected entry (`previous_mapping_id`), which stays in the registry as it was. *(Built so: a rejected entry is not re-labelled "superseded", so the registry still shows a person once said no.)* |
| RJ-06 | A rejected link is never an arrow: trace, impact, documents and the views ignore it — already so, they follow approved links only. |
| RJ-07 | `sdem handback`, `sdem review` and the dashboard list rejected links apart from those still to decide. |

**Touches:** a new `sdem/reject.py` and its command; `sdem link` (`rules_engine.py`), `sdem aid` (`aid_fill.py`, `aid_info.py`); the handback and dashboard; the approve-links skill and the CLI reference (generated). Tests first, one per rule.

## 2. Flat network zones (F1)

**The gap.** SDEM's zone structure (LC-17, the owner's decisions of 2026-11-14) is: a level-0 zone that is on premises or cloud; inside it exactly one internal zone and at most one DMZ (level 1); private zones inside the internal one (level 2). A design that simply names its zones — *edge, application, data, security, integration* — and says nothing of cloud or on premises is refused outright. To hold the twin at all, the operator added two zones the document does not contain and changed the kind of four.

**The change: the full structure stays available and unchanged; it stops being compulsory.**

| Id | Rule |
|---|---|
| ZF-01 | A level-1 or level-2 zone **may stand with no parent**. If it has a parent, the parent is one level up, as now. (LC-17 today: "a level-1 zone is part of a level-0 zone" — an error.) |
| ZF-02 | Kinds by level are unchanged: level 0 on premises or cloud; level 1 internal or DMZ; level 2 private. A flat design records its DMZ and internal zones at level 1 and its restricted zones at level 2. |
| ZF-03 | "Exactly one internal zone, at most one DMZ" still holds **inside each level-0 zone**. Zones with no level-0 parent are not counted: a flat design may have several internal zones. |
| ZF-04 | **What SDEM then does not work out.** Zone connections (ZC-01…ZC-03) come from the structure; between parentless zones there is none to read, so none is worked out — `sdem zones` says so, and the connections are what the design's paths state. |
| ZF-05 | **Zone placement in a flat workspace.** `sdem aid` does not create a level-0 template zone (AID-Z01) when the workspace's zones are flat; a shape in no zone, with no host to follow, is left for a person — "which of your zones?" — and named. |
| ZF-06 | A workspace started with its zones from a template (`sdem new --hosting`) is unchanged: it has its level-0 zone, and everything above applies to it as now. |

**Not changed:** LC-16 (every shape in a zone), LC-18 (internet-facing shapes in a DMZ), the zone attributes (`zone_level`, `zone_kind` stay required), the metamodel's RA4-39 (already "a zone is part of *at most* one zone").

**Touches:** `sdem/conformance.py` (LC-17), `sdem/hosting.py` (ZF-05), `sdem/zones.py` and `sdem/hosting.py` (ZF-04's message), [`sdem-network-zones-design.md`](sdem-network-zones-design.md) and [`sdem-hosting-inference-design.md`](sdem-hosting-inference-design.md), the logical-data-model reference (generated). Tests first; every existing example must check exactly as before.

**What it would have changed in the twin:** five zones recorded as the document has them — no invented zones, no changed kinds (three records and five links fewer; F1 closed).

## 3. Decisions for the owner

| # | Decision | Decided (the owner, 2026-11-17 — as recommended) |
|---|---|---|
| D1 | Build `sdem reject` as RJ-01…RJ-07 | Yes |
| D2 | RJ-04 — a rejected MAPPED_TO stops AID inferring a table for that object | Yes. The alternative — still infer one — repeats the invention the rejection was meant to stop |
| D3 | Allow flat zones as ZF-01…ZF-06 | Yes |
| D4 | ZF-05 — in a flat workspace AID leaves an unplaced shape to a person, and does not guess a zone | Yes: with no level-0 zone there is no cloud/on-premises evidence to place it by |
