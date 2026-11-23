# Golden answers — SDEM 0.21 (the 0.22 plan's baseline)

> **Status: a record** — what SDEM 0.21.14 (with the 0.22 plan's steps 1 and 2) answers on its own examples, captured 2026-11-24 with `scripts/golden/capture.py` (normalised: no times, run ids or local paths). Step 3 of the [0.22 plan](../../docs/design/sdem-0.22-plan.md) is proved against them: with BIAN's inference in `sdem-bian`, every answer must be identical except the provenance that names the inferer (R-D11).

| Folder | Captured from |
|---|---|
| `0.21-form-0.19/` | the examples in SDEM 0.19's form (`SDEM_FORM=0.19`) |
| `0.21-form-0.20/` | the examples in SDEM 0.20's form (`SDEM_GOLDEN_P2=1`); the full trace kept compressed (`trace__pi-A1.json.gz`) |

`0.19/` beside them is 0.20's own baseline (BX-30) and is unchanged.
