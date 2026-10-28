# Base BIAN — specification

> **Status: approved by the owner 2026-10-29**, with the design [`sdem-bian-base-design.md`](sdem-bian-base-design.md). Each requirement has an id (BB-*), what it requires, and how it is accepted (`tests/test_bian.py`, `tests/test_installed.py`).

| ID | Requirement | Accepted by |
|---|---|---|
| BB-S01 | SDEM includes `bian/base-14.0.0.json`: for each service domain of BIAN's Semantic APIs 14.0.0, its name, release, source file, operations (method, path, operation name, input and output field names), control record and its field names, and behaviour qualifiers. No descriptions, no object schemas. | test: 258 domains, release 14.0.0, no description text |
| BB-S02 | `bian/` holds BIAN's Apache-2.0 licence (`LICENSE`) and a `README.md` saying where the files come from, what was changed (extracted; descriptions and schemas left out), and that BIAN does not endorse SDEM. `THIRD_PARTY.md` lists it. | test: files present; review |
| BB-S03 | The base is installed with SDEM (package data) and found from any directory. | `tests/test_installed.py` runs `sdem bian list --base` |
| BB-C01 | `sdem bian list --base [FILE]` and `sdem bian import --base [FILE] …` use the base (bundled when no FILE is given, or a packed file of the organisation's own BIAN). A folder of BIAN-format files still works as before. Naming neither is an error. | tests |
| BB-C02 | `sdem bian list` marks each service domain whose asset type and functional pattern cannot be derived (*needs your pattern*). | test |
| BB-C03 | `sdem bian pack <folder> -o <file>` writes a packed file from a folder of BIAN-format files — the same form as the base — and refuses a folder with no readable files. | test: pack the made-up release, then import from it |
| BB-C04 | `--descriptions` and `--objects` with `--base` are refused with a message to import from BIAN's files instead (the base leaves them out). | test |
| BB-C05 | An import from the base gives exactly the same A2 dataset as an import from the raw files it was packed from (same ids, records and links). | test on the made-up release; maintainer check on 14.0.0 |
| BB-M01 | `scripts/build_bian_base.py <release folder>` rebuilds `bian/base-<release>.json` from a downloaded release. | run by the maintainer |
