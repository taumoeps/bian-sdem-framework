# Base BIAN

**What this is.** The base BIAN that ships with SDEM: BIAN's public **Semantic APIs, release 14.0.0**, packed into one file (`base-14.0.0.json`) for `sdem bian import --base`. It holds, for each of the 258 service domains, its name, its operations (method, path, operation name, input and output field names), its control record and its fields, and its behaviour qualifiers.

**Where it comes from.** Published by the Banking Industry Architecture Network (BIAN e.V.) at [github.com/bian-official/public](https://github.com/bian-official/public), folder `release14.0.0/semantic-apis/oas3/yamls`, under the **Apache License 2.0** — a copy is in [`LICENSE`](LICENSE) beside this file.

**What was changed.** The files were read and packed by `sdem bian pack` (rebuild: `python scripts/build_bian_base.py <release folder>`). BIAN's descriptions and object schemas were **left out**; nothing was added or reworded. The pack is a derived work of BIAN's files, distributed under the same Apache License 2.0.

**Not endorsed by BIAN.** BIAN® is a trademark of BIAN e.V. SDEM is independent and is not affiliated with, endorsed by or sponsored by BIAN.

**Using your own BIAN instead.** The base is a starting point. Pack your organisation's own BIAN (in BIAN's format) with `sdem bian pack <folder> -o <file>` and use `--base <file>`; or import straight from a folder. See [the base BIAN design](../docs/design/sdem-bian-base-design.md) and the [onboarding workflow — your BIAN (A2) layer](../docs/sdem-onboarding-workflow.md#your-bian-a2-layer).
