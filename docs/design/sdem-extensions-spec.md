# SDEM extensions — the contract

> **Status: approved by the SDEM owner (2026-11-15) — D1, D2 yes; EXT-15 approved the same day and built (`sdem/extensions.py`: `sdem <name>`, `sdem extensions`).** EXT-01…EXT-14 need **no change to SDEM's core** (code, metamodel, commands); EXT-15 is the one optional core change and is decided separately. The first extension is the DESNRE 3D publisher.

## 1. Why

SDEM is open source, and its core stays small and standard: the metamodel, the checks, inference, the knowledge graph and the commands. Organisations and tools will want more — publish a workspace to a site, feed a CMDB, export to a modelling tool, add their own checks or reports. Those belong **outside** the core, built on what SDEM already offers, so the core never grows for one adopter's need and an extension never breaks when SDEM changes inside.

## 2. Where extensions live

Not in SDEM's repository: an extension changes when its target changes, may need what SDEM does not allow itself (a dependency, a network call), and may be an organisation's own. Shareable extensions live in **[sdem-extensions](https://github.com/taumoeps/sdem-extensions)** (public, Apache 2.0) — one folder per extension, each its own package, with a `template/` to start from and every extension tested against SDEM's examples. The first is `desnre/`, the DESNRE 3D publisher. An organisation's own extensions live in its own, usually private, repository. Install one into SDEM's environment — `pip install "git+https://github.com/taumoeps/sdem-extensions#subdirectory=<name>"` — and `sdem extensions` lists it.

## 2a. What an extension is

| ID | Rule |
|---|---|
| **EXT-01** | An extension is **a separate program or package with its own command**, named `sdem-<name>` (for example `sdem-desnre`). It is not part of SDEM's repository and SDEM does not ship it. |
| **EXT-02** | An extension **uses SDEM only through its public interface**: the `sdem` commands with `--json` (the same interface agents use, `templates/agents/AGENTS.md`), the workspace files as documented, and the generated documents. It **never imports SDEM's code** (`import sdem…`) — SDEM's modules are internal and may change in any release — **except `sdem.api`** (amended 2026-11-20, [stable identity](sdem-stable-identity-spec.md) ST-21, approved ST-D5): SDEM's one published, versioned code interface, which an extension names in its manifest (`"api": ">=0.1,<0.2"`). A test fails if an extension imports any other module of SDEM's. |
| **EXT-03** | It **discovers what it needs** with `sdem commands --json` (the commands, their flags, exit codes and error codes) and reads SDEM's version from `sdem --version`. |
| **EXT-04** | It **declares the SDEM versions and metamodel versions it supports**, checks them when it starts, and stops with a clear message outside them — never runs on a version it does not know. |

## 3. The manifest

| ID | Rule |
|---|---|
| **EXT-05** | Every extension has a manifest, `sdem-extension.json`, shipped with it, and prints it when run as `sdem-<name> --manifest` (how SDEM recognises it, EXT-15): |

```json
{
  "name": "desnre",
  "command": "sdem-desnre",
  "version": "0.1.0",
  "description": "Publishes a synthetic workspace to the DESNRE site's 3D view",
  "kind": "publisher",
  "sdem": ">=0.18,<0.19",
  "metamodel": ">=0.14,<0.15",
  "uses": ["check", "layout", "zones --layout", "commands"],
  "reads": ["a1-business.json", "a2-service-domain.json", "a3-application.json", "a4-technology.json", "mappings.json"],
  "writes": "nothing in the workspace",
  "sends_to": ["https://<the DESNRE site>/api/models"],
  "data": "synthetic only",
  "owner": "the DESNRE maintainers",
  "licence": "…"
}
```

`uses` names the SDEM commands it depends on (so a change to one is easy to trace); `reads`, `writes` and `sends_to` say plainly what it touches; `data` says which workspaces it accepts. A metamodel extension that contributes to SDEM's inference also says `"infers": ["aid", "link"]` — SDEM then runs `sdem-<name> infer …` for a workspace that includes it ([MX-45…MX-52](sdem-metamodel-extensions-spec.md#16-extensions-that-infer)).

Two optional fields tell a viewer's AI agent about the extension ([extensions and the AI agent](sdem-extension-agent-context-spec.md)): its read-only **reports**, as `viewer.results` (or `results`) — command names a publisher runs with `--json`, and `document` for its readable Markdown report (XA-01) — and **`agent_guide`**, at most 2,000 characters on what its layer, types and reports mean, which an agent reads as reference, never as instructions (XA-02, XA-06).

## 4. Kinds of extension

| ID | Kind | Does | Example |
|---|---|---|---|
| **EXT-06** | **publisher** | sends something built from a workspace to somewhere else | the DESNRE 3D view; a portal; a wiki |
| | **exporter** | writes a file in another tool's format | an ArchiMate exchange file; a CMDB load file |
| | **importer** | turns another tool's data into SDEM records | a modelling tool's export; a CMDB |
| | **checker** | adds an organisation's own checks and reports | house rules beyond the profile |

One extension may be more than one kind; its manifest lists each.

## 5. Rules every extension follows

| ID | Rule |
|---|---|
| **EXT-07** | **Read-only by default.** An extension writes nothing in a workspace. An importer, or anything that changes records, does so **only through a change set** (`sdem change propose`) that a person accepts — never by editing the architecture files directly. |
| **EXT-08** | **A person decides.** Anything that leaves the workspace — a publish, an upload, a send — has a `--dry-run` that shows exactly what would go, and goes only on a person's explicit step. A publisher that reaches a live target lands as a **draft** a person approves. |
| **EXT-09** | **Checked before it leaves.** A publisher or exporter runs `sdem check` first and refuses a workspace with errors. |
| **EXT-10** | **Data stays where it belongs.** An extension declares where it sends data (`sends_to`). A publisher to a **public** target accepts only a workspace a person has **marked synthetic** (EXT-11), and the target checks it again. |
| **EXT-11** | **The synthetic mark.** A person marks a workspace synthetic in the extension's own file in the workspace, `extensions/<name>.json` (`{"data": "synthetic", "marked_by": "…", "on": "YYYY-MM-DD"}`). It is the extension's file: SDEM does not read it, so SDEM's core does not change. An extension never marks a workspace itself. |
| **EXT-12** | **No secrets in workspaces.** Tokens and keys come from the environment or the operating system's keychain, never from a workspace file or the manifest. |
| **EXT-13** | **Same input, same output.** What an extension builds from an unchanged workspace is identical each time (no timestamps inside), so a publish or export can be compared and reviewed. |
| **EXT-14** | **Tested against SDEM's examples.** Each extension runs its tests against SDEM's synthetic examples for every SDEM version it claims (EXT-04), and fails clearly — not silently — when a `--json` result has a shape it does not know. |

## 6. Optional — `sdem` finds its extensions (a core change)

| ID | Rule |
|---|---|
| **EXT-15** | *Approved and built.* `sdem <name> …` runs an installed extension `sdem-<name>` (the way `git` finds its add-ons) with the rest of the line **untouched** — its own `--help`, `--dry-run` and `--json` — and its exit code is SDEM's. An extension is found beside SDEM (the same environment, so `pip install <its folder>` installs it) or on the PATH, and is run only if it answers `--manifest` with its manifest, so a stray `sdem-<name>` program is never run; SDEM's own commands and its own `sdem-*` programs always win. `sdem extensions` lists the installed ones. SDEM knows no extension by name. Every extension also still runs as its own command (`sdem-desnre …`). |

## 7. What SDEM keeps stable for extensions

Nothing new is built for this; it is what SDEM already promises its agents, written down for extensions:

- the `--json` results of the commands listed by `sdem commands --json` — a list result is `{"count", "items"}` (AF-08);
- the exit and error codes listed there;
- the workspace file names and record shapes in the metamodel guide;
- a change to any of these is stated in the CHANGELOG, in plain words.

## 8. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| D1 | Approve EXT-01…EXT-14 as the contract for every SDEM extension | yes — no core change |
| D2 | The synthetic mark lives in the extension's own file (EXT-11), not in SDEM | yes — keeps the core unchanged; a core-level mark can follow if many extensions need it |
| D3 | EXT-15, `sdem <name>` finding installed extensions | later — only once a second extension exists |

**Decided (2026-11-15):** D1 yes, D2 yes, D3 later — then, the same day, EXT-15 approved by the owner ("install the extension so it expands onto sdem core") and built.
