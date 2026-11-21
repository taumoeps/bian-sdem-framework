# Payment Initiation v3 — a full design, traced from its plan to its data

> **Made-up data only.** An invented New Zealand retail bank; the standards it cites are public. Nothing here comes from any real organisation.

A complete solution design — business, BIAN, application and technology — built without any organisation's own designs, and traceable end to end.

| Step | What | Where |
|---|---|---|
| 1 | The plan: why, and the scope (scenario S1 — a third party initiates a single domestic payment) | [`plan.md`](plan.md) |
| 2 | The brief given to the design's author | [`brief.md`](brief.md) |
| 3 | The narrative design, written to that brief outside SDEM | [`narrative/design.md`](narrative/design.md) |
| 4 | The design as SDEM data — the package `sdem intake` takes | [`data/`](data/) |
| 5 | The design in an SDEM workspace | [`sdem/`](sdem/) |

**[`TRACEABILITY.md`](TRACEABILITY.md)** follows the chain: each line of the brief's scope to the design's sections to the records; every record to its section; every link to what it rests on — stated in the document, implied by it ([`added-by-reading.json`](added-by-reading.json)), or decided where the document is silent ([`decided-by-ai.json`](decided-by-ai.json)); every requirement to what meets it.

```
sdem status --workspace examples/payment-initiation-v3/sdem        # 100% connected, both patterns in place, clear
sdem intake examples/payment-initiation-v3/data --check            # the package: OK, COMPLETE
python examples/payment-initiation-v3/scripts/trace.py               # regenerate TRACEABILITY.md from the workspace
```

**How the data was made — [`scripts/`](scripts/).** No `sdem transform` and no `sdem aid`: an AI read the narrative design.

| Script | What it adds |
|---|---|
| `1_stated_in_the_document.py` | the records, and the links the document states outright — each citing its section |
| `2_as_a_package.py` | the same, as the package `sdem intake` takes |
| `3_implied_by_the_document.py` | the 91 links that follow from the document's own sentences → `added-by-reading.json` |
| `4_decided_by_the_ai.py` | the 18 things the document does not say, decided, each with its reason → `decided-by-ai.json` |
| `build.sh` | runs them in order and checks the result: `sh examples/payment-initiation-v3/scripts/build.sh <folder>` reproduces `data/` exactly |
| `trace.py` | writes `TRACEABILITY.md` from the workspace |

`plan.md` and `brief.md` are copies of `docs/design/sdem-public-twin-benchmark-plan.md` and `docs/design/sdem-public-twin-reference-brief.md`, kept here so the chain reads in one place. The approvals in `sdem/` are recorded under `jane.architect`, the made-up architect of SDEM's examples.
