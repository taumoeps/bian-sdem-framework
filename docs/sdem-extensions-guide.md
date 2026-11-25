# Extending SDEM — the Extensions guide

> **Status:** current for SDEM 0.22. The rules behind it are in the [extension contract](design/sdem-extensions-spec.md) (EXT-…) and [metamodel extensions](design/sdem-metamodel-extensions-spec.md) (MX-…).

SDEM's core describes any organisation's solution designs in four layers — **Business, Data, Application, Technology** — checked against one metamodel aligned to ArchiMate 3.2 and TOGAF. Everything else is an **extension**: an industry's reference model (BIAN for banking), a cross-cutting architecture (security), a place to publish to (DESNRE's 3D view). You install the extensions you need; a design says which ones it uses.

## What an extension is

An extension is a program called `sdem-<name>`, installed beside SDEM (usually `pip install` into the same environment). It answers `sdem-<name> --manifest` with what it is: its kinds, the SDEM versions it supports, what it reads and where it sends data.

- **SDEM finds it** in the folder its own Python runs from, then on the `PATH` — or exactly where `SDEM_EXTENSIONS_PATH` says (EXT-15).
- **SDEM never imports its code** (R-D5). An extension works through SDEM's commands, its documented files, and `sdem.api` — the one Python interface SDEM keeps stable for extensions (ST-20, ST-21).
- **`sdem <name> …` runs it** with the rest of the line untouched, so its own `--help`, `--json` and `--dry-run` work as SDEM's do.

```bash
sdem extensions                 # what is installed, its version, what it reads and where it sends data
sdem extensions --workspace ws  # and whether each is on in this workspace, and why
```

## Kinds of extension

| Kind | What it adds | Example |
|---|---|---|
| **Vertical** metamodel extension | a layer **beside** the design's layers, whose links reach every one | [security](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/security) — threats, controls, zones |
| **Horizontal** metamodel extension | more types **inside** a core layer, or **a layer of its own between** core layers | [BIAN](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/bian) — the Service Domain layer between Business and Data |
| **Bridge** metamodel extension | only the links and rules that join two extensions | network-security (planned) |
| **Publisher** | sends something built from a workspace somewhere else | [DESNRE](https://github.com/taumoeps/sdem-extensions/tree/main/publishers/desnre) — a 3D view on the web |
| **Exporter**, **importer**, **checker** | another tool's format out, another tool's data in, an organisation's own checks | — |

A metamodel extension says its kind and scope in its manifest (`"scope": {"across": ["S"]}` vertical, `{"within": ["A2"]}` horizontal) and SDEM refuses a pack that does more than its scope (MX-18). **No extension changes the core or another extension** — it adds, never redefines (MX-19).

## Using one in a design

```bash
pip install <its package>                                                     # beside SDEM
sdem profile include ext:security --workspace ws --person you --reason "…"    # this design uses it — a recorded decision
sdem profile adopt --workspace ws --person you --reason "…"
```

Its types, link types and rules are then part of the design's metamodel: `sdem check` checks them, `sdem types` lists them, the knowledge graph and every view carry them. A workspace that does not include an extension never sees it (MX-10).

**BIAN** is started with the design instead:

```bash
pip install "sdem-bian @ git+https://github.com/taumoeps/sdem-extensions@main#subdirectory=metamodel/bian"
sdem new --workspace ws --person you --with bian   # a design with BIAN's Service Domain layer, empty — sdem aid brings in the domains it needs
```

A design that has a BIAN layer is refused, with what to install, where `sdem-bian` is not installed (R-D2) — and a design without one is a core design, installed or not (BX-15).

## What an extension can do

| It can | How | Rules |
|---|---|---|
| add types, link types, within-layer rules and attributes | its **pack** — the same format as an organisation's profile | MX-01…MX-44 |
| add commands | `sdem <name> …` runs its program | EXT-15, ST-22 |
| infer — records and links SDEM checks as its own, marked with who inferred them | `sdem-<name> infer --workspace DIR --step aid\|link --json` | MX-45…MX-53 |
| give its part of `sdem aid` where SDEM's own steps build on it | phases, with the state so far | MX-54 (BIAN) |
| keep its rows in their place among SDEM's | `order.json` and the files beside it | MX-55 (BIAN) |
| publish or export | reads the workspace through SDEM's commands | EXT-06…EXT-14 |

What SDEM keeps stable for extensions — the manifest, the files, `sdem.api`, the inference answer `sdem-inference/1` — is listed in the [extension contract](design/sdem-extensions-spec.md) §7.

## The three worked cases

- **Security** (vertical, a checker too): a pack with the S layer, its types and the links that reach A1–A4, and its own commands (`sdem security …`). [Its folder](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/security).
- **BIAN** (horizontal): the Service Domain layer, BIAN's types, link types and rules, the 258-domain catalogue, its own commands (`sdem bian …`), and its inference — `sdem link`'s BIAN rules and its part of `sdem aid`, answered at each phase. Since SDEM 0.22 it is BIAN's only source; its documentation lives [with it](https://github.com/taumoeps/sdem-extensions/tree/main/metamodel/bian/docs).
- **DESNRE** (publisher): publishes a made-up workspace to a 3D view on the web — a draft first, then live. [Its folder](https://github.com/taumoeps/sdem-extensions/tree/main/publishers/desnre); a [template](https://github.com/taumoeps/sdem-extensions/tree/main/templates/publisher) to start your own publisher.

## Writing one

1. Start from the publisher template or a metamodel extension's folder in [sdem-extensions](https://github.com/taumoeps/sdem-extensions).
2. Write the manifest (`sdem-extension.json`): `name`, `command`, `version`, `kind`, `sdem` (the versions you support), `scope`, `reads`, `sends_to`, `data` — and `api` if you use `sdem.api`, `infers` if you infer.
3. For a metamodel extension, write the pack; namespace your types (`SEC.`, `NET.`).
4. Test it against SDEM's examples for every SDEM version you claim (EXT-14) — `SDEM_EXTENSIONS_PATH` points SDEM at a made-up one in a test.
5. Publish it as a package; people install it beside SDEM and include it in the designs that use it.
