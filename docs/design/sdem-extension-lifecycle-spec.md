# Extension lifecycle — install, switch on, publish, switch off, remove, restore, purge (spec)

> **Status: proposed (2026-11-19) — for the owner's decisions EL-D1…EL-D7 (§9).** Written after the security extension's audit
> ([`audit-2026-11-19.md`](https://github.com/taumoeps/sdem-extensions/blob/main/security/docs/audit-2026-11-19.md)) and the owner's
> question: *removing the security extension seemed implicit — install and removal should be explicit, across SDEM and DESNRE, and say
> what happens to the data.* Builds on [metamodel extensions](sdem-metamodel-extensions-spec.md) (MX-01…MX-17), the
> [extensions contract](sdem-extensions-spec.md) (EXT-01…EXT-15), and DESNRE's publish and workbench designs (DP-…, DW-40…DW-42, DG-90…DG-93).
> The first extension it governs is `sdem-security`; it is written for any metamodel extension (e.g. a later resilience extension).

## 1. Why

Today an extension's life is explicit in SDEM and implicit everywhere else:

| Step | Today | The gap |
|---|---|---|
| Install | `pip install sdem-security` | nothing says the DESNRE features come with it, or which publisher version carries them |
| Switch on | `sdem profile include ext:security` — a recorded decision (MX-10) | the site learns of it only because `security.json` happens to be in the next publish |
| Switch off | `sdem security remove` — archived, a recorded decision (MX-16) | the site keeps showing security until the next publish, and then the views just **vanish**: no one is told, and the site cannot tell *switched off* from *never had it* |
| Data | archived in the workspace | nothing says what happens to it, to the site's previous version, or to the design document's history |

The site decides what to show by looking for a file in **seven separate places** (the Security tab, the 3D viewpoint, Health, Metamodel,
Connections, Document Output, the agent). A second extension would add seven more checks. This spec makes the lifecycle one documented
sequence, makes every step say what it does on both sides, and gives DESNRE one switchboard.

## 2. The lifecycle

```
 machine            workspace (SDEM)                         DESNRE site (per design)
 ───────            ────────────────                         ────────────────────────
 install ──────▶    switch on  (profile include, decision) ─▶ publish ─▶  state ON: its features shown
                    … design …                                 publish ─▶  (results refreshed)
                    switch off (profile exclude, decision,
                                layer + links archived) ───▶ publish ─▶  state OFF: features hidden, the notice shown
                    restore    (from the archive, decision) ─▶ publish ─▶  state ON again
                    purge      (archive deleted, decision) ──▶ publish ─▶  security removed from the previous version
                                                                           and the document history too
 uninstall          (a workspace still including it is refused — MX-11a)
```

**Nothing on the site changes without a publish**, and **a publish is always a person's step** (DP-14) — the commands say what will change,
and the publish shows it before anything leaves.

## 3. Install — one package, a stated set of features

| Id | Rule |
|---|---|
| **EL-01** | **An extension states everything it brings, in its manifest.** Beside `kind`, `sdem`, `metamodel` and `pack` (EXT-04, MX-01), a metamodel extension declares `viewer` — what it offers to a viewer: its layer code and sub-layers (security: `S`, `S1…S5`), the results its commands produce for publishing (`review`, `coverage`, `threats`, `document`), and the publisher version that carries them (`sdem-desnre >= 0.7.11`). `sdem extensions` lists it; the extension's README has the same table. |
| **EL-02** | **DESNRE keeps one registry of the extensions it supports** — `assets/extensions.json` on the site, read by the page and by the agent service — one entry per extension: its layer, the extension versions it accepts, and the features it switches on, each by a fixed name: `viewpoint` (the 3D stack), `tab` (the extension's tab), `health`, `metamodel`, `connections`, `document-output`, `agent-tool`, `agent-about`, `narrative-section`. The feature code stays in the site; the registry is the switchboard and the record of what exists. A second extension is one new entry plus its views. |
| **EL-03** | **What the site shows is the intersection** of the registry (what DESNRE can do), the extension's `viewer` (what it offers) and the design's published state (EL-07). A version the registry does not accept is shown as *"published with sdem-security 0.3.0, which this site does not support yet — its records are in Metamodel and Connections"*, never half-drawn. |

## 4. Switch on and switch off — in the workspace

| Id | Rule |
|---|---|
| **EL-04** | **Switching on** stays `sdem profile include ext:<name>` then `sdem profile adopt` (MX-10), a person's recorded decision. It now ends by saying what the site will do: *"The DESNRE site shows Security for this design after you publish it: sdem desnre publish <name>."* |
| **EL-05** | **Switching off** stays `sdem <name> remove` → `sdem profile exclude` (MX-16): tried on a copy and checked, the layer, its connections and the exceptions naming them archived **whole** in `archive/<name>-<date>[-n].json`, link ids retired, the decision recorded. **It never deletes data.** It ends by saying: *"The DESNRE site still shows Security for <design> until you publish again; then it shows that Security was switched off on <date> by <person>."* |
| **EL-06** | **Restore** — `sdem <name> restore --workspace … --person … --reason … --archive <file>` (`--dry-run` first): switches the extension on again and brings back the archived layer, connections and exceptions, re-checked; the retired ids come back with their links (they were never given to others); a recorded decision (`restore_from_archive`). Refused if the design has since changed so that an archived link no longer fits (a record it joined is gone) — the message lists those links, and the rest can be restored with `--skip-unfit`. |

## 5. Publish — the state travels with the design

| Id | Rule |
|---|---|
| **EL-07** | **The published design carries each extension's state**, not only its files: `extensions.<name> = {state: "on" \| "off", version, since, by, reason, decision, archive, results: {review, coverage, threats, document}}` — `results` only when on. `off` is read from SDEM's own records (the `exclude_from_profile` decision and the archive), never inferred from a missing file. An extension that was never on is absent. *(Today's `extensions.<name>.<result>` moves under `results`; the site reads both forms during the change.)* |
| **EL-08** | **A publish lists what changes about extensions before it goes**, against what is live: `+ Security (sdem-security 0.1.3) — switched on 2026-11-19 by steven` · `− Security — switched off 2026-11-19 by steven: "<reason>"` · `~ Security results refreshed`. The person confirms, as with every publish (`--yes` for scripts). |
| **EL-09** | **Results are stamped** with the extension version and when they were computed; the site shows that date beside them, so a reader can see they are as of the last publish (the audit's AUD-13). |

## 6. On the site — on, off, and the notice

| Id | Rule |
|---|---|
| **EL-10** | **One gate.** Every view asks one function — *is feature F of extension E on for this design?* (registry ∩ viewer ∩ state) — instead of looking for a file. The seven checks of §1 become seven calls to it. |
| **EL-11** | **Off is said, not hidden.** When a design's state for an extension is `off`, its features are hidden and **Health** and **Metamodel** show one line: *"Security architecture (sdem-security 0.1.3) — switched off 2026-11-19 by steven: '<reason>'. Archived in the workspace; not shown here."* A remembered viewpoint for it falls back to Architecture (fixes AUD-36). |
| **EL-12** | **An Extensions panel** (under Health): each extension the design has used, its state, version, since when and by whom, and the features it gives on this site (from the registry) — so a reader sees what security adds, and when it was on. |
| **EL-13** | **The agent knows the state.** On: its tools and template as now. Off: it says *"security was switched off on 19 November by steven"* — not *"the design holds no security architecture"* — and the narrative written after a switch-off says in its gap analysis that the security section was removed and why. The agent never reads the archive. |

## 7. Uninstall, and purge — what happens to the data

| Id | Rule |
|---|---|
| **EL-14** | **Uninstalling the package** (`pip uninstall`) touches no data. A workspace that still includes the extension is refused with a message naming it (MX-11a) until it is reinstalled or switched off; the site keeps what was last published. |
| **EL-15** | **Data is kept by default, everywhere.** Switching off archives in the workspace (EL-05); the site keeps its **previous published version** (rollback, DP-…) and the **design document's history** (DG-…), which may hold security content; neither is shown as the design. Reason: the links were approved by named people with evidence — a governed record — and keeping them makes switching off reversible (EL-06). |
| **EL-16** | **Purge is separate, explicit and never the default** — for a real need (a data request, a client's instruction). `sdem <name> purge --workspace … --person … --reason …` (`--dry-run` lists every file and every site copy it would remove): deletes the extension's archive files and their retired-id entries' links (the ids stay retired), records the decision (`purge_extension_data`) — the decision itself keeps no security content. If the design is published, the next publish asks the site (owner only, a person's step) to remove the extension's data from the **previous version** and the extension's sections from **every document in the history**, and the site confirms what it removed. |
| **EL-17** | **What purge cannot reach is said.** A workspace kept in git still holds the data in its history; copies people downloaded are theirs. The purge's message names these and leaves them to the person — SDEM never rewrites git history. |

## 8. Tests

- Switch on → publish: the site shows each registry feature; the Extensions panel lists Security *on*.
- Switch off → publish: every feature hidden; Health and Metamodel show the notice with date, person and reason; the agent says it was switched off; a remembered Security viewpoint opens Architecture.
- A publish's change list shows `+`, `−` and `~` correctly against the live design.
- Restore brings back the layer, links (with their old ids) and exceptions; refused with a list when a link no longer fits.
- Purge `--dry-run` lists local files and site copies; purge removes them, keeps the ids retired, records a decision with no security content; the site's previous version and document history hold no security text afterwards.
- A design published before EL-07 (no state) is read as `on` when its files hold the layer — no published design breaks.
- An extension version the registry does not accept shows the "not supported yet" line and no half-drawn view.

## 9. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| EL-D1 | When an extension is switched off, the site **says so** (EL-11) rather than only hiding it | **yes** — a reader can tell *switched off* from *never had it* |
| EL-D2 | Switching off does **not** republish by itself; the command says what the site will do and the publish shows it (EL-05, EL-08) | **yes** — publishing stays a person's step (DP-14) |
| EL-D3 | **Restore** from the archive (EL-06) | **yes**, in this build |
| EL-D4 | **Purge** as a separate command, never the default, reaching the site's previous version and document history (EL-16, EL-17) | **yes** |
| EL-D5 | DESNRE's **extension registry** as one file on the site, read by the page and the agent (EL-02) | **yes** |
| EL-D6 | The published record moves to `extensions.<name> = {state, …, results}` (EL-07), with both forms read during the change | **yes** |
| EL-D7 | Where the parts are built: SDEM (restore and purge decision kinds, the commands' messages), sdem-security 0.2.0 (`viewer`, `restore`, `purge`), sdem-desnre 0.8.0 (state, change list, results stamp), the site (registry, gate, notice, panel, agent, purge endpoint) | **yes** — in that order, each tested before the next |
