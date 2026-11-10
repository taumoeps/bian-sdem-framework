# Structural reference-architecture patterns — roles and connectors

> **Status: approved and built — the owner approved S1–S6 as recommended (2026-11-10); SDEM 0.18.0. Nothing in the metamodel changed.** Built: `structure` in `sdem-pattern/1` (S1), binding from the anchor with a role named in `conforms_to` winning (S2), the pattern's or part's `severity` (S3), `sdem pattern draw` (S4), no generation (S5), and `sdem pattern extract` for draw.io, Visio, PlantUML and Mermaid (S6). The rules are PR-21…PR-31 in [sdem-profile-spec.md](sdem-profile-spec.md); the synthetic example is `examples/profiles/patterns/example-secure-api-edge.json`, extracted from `examples/profiles/patterns/diagrams/secure-api-edge.{drawio,vsdx,puml,mmd}`; tests `tests/test_structural_patterns.py`.
>
> Originally: DRAFT, 2026-11-10, following the full-bank simulation (`tests/test_bank_simulation.py`), which showed that a pattern was a list of rules about one record.

## 1. The problem

A made-up bank's *Secure API* reference pattern, as its architects draw it:

```
 [external channel] ──▶ [API gateway] ──▶ [application] ──▶ [database platform]
                          (dmz)             │  deployed on       (restricted)
                                            ▼
                                     [container platform]
                                        (restricted, monitored, TLS 1.3)
```

Today (`sdem-pattern/1`) this can only be written as rules about the application: it is behind a gateway, and its platform is monitored.
The pattern cannot say:

- what the **parts** are;
- that the database is **reached from** the application;
- that every part sits in a **zone**.

So SDEM cannot say **which part is missing** or draw the pattern beside the design. Two other things are also missing:

- **Binding:** today a pattern applies to any record its `applies_when` matches. Since PR-10 (2026-11-10) that can be a record whose `conforms_to` names the pattern, but no record can say which **part** of the pattern it plays.
- **Depth:** a rule's `across` goes one cross-layer step. A pattern often spans two steps (application → platform → network).

## 2. Proposal: a `structure` in a pattern file

A pattern keeps `requires` (rules, as now) and may add a `structure`:

```json
{
  "format": "sdem-pattern/1",
  "pattern": {"id": "PAT-SECURE-API", "title": "Secure API integration", "version": "3.0", "owner": "security architecture",
              "applies_when": {"entity": "A3.ApplicationComponent", "when": {"exposure": "external"}}},
  "structure": {
    "anchor": "app",
    "roles": [
      {"id": "app",      "type": "A3.ApplicationComponent", "require": ["authentication"]},
      {"id": "gateway",  "type": "BANK.A3.APIGateway"},
      {"id": "platform", "type": "A4.InfrastructureComponent", "check": {"attribute": "network_zone", "op": "in", "value": ["restricted"]}},
      {"id": "database", "type": "A4.SystemSoftware", "min": 0}
    ],
    "connectors": [
      {"id": "C1", "from": "gateway", "to": "app",      "kind": "composition"},
      {"id": "C2", "from": "app",     "to": "platform", "relationship": "DEPLOYED_ON"},
      {"id": "C3", "from": "app",     "to": "database", "relationship": "DEPLOYED_ON", "min": 0}
    ]
  },
  "requires": [{"id": "PAT-SECURE-API-1", "rule": "SEC-API-01"}]
}
```

| Id | Proposed requirement |
|---|---|
| PR-21 | **Roles.** A role names a type: SDEM's own, or a profile type that extends one. It may also give `require`, `check` (the rule grammar of PR-15) and `min`/`max` (default 1/1; `min: 0` makes the part optional). `anchor` names the role the pattern applies to. The anchor's type must be the `applies_when` entity, or a subtype of it. |
| PR-22 | **Connectors.** A connector joins two roles by a link **inside a layer** (`kind`, e.g. composition, serving, flow) or **across layers** (`relationship`, e.g. DEPLOYED_ON). The pattern check refuses a connector that SDEM's metamodel does not allow between those two types: the inside check is `relationship_issue`, the across check the level relationships. **A pattern can never invent a link the metamodel forbids.** Across connectors follow only APPROVED links (PR-16). Inside links are links in the layer. |
| PR-23 | **Binding.** SDEM fills the roles **deterministically**. It starts from each record the pattern applies to (the anchor) and follows the connectors to the records of each role's type. A record can name its role itself in SDEM's own `conforms_to`, as `"PAT-SECURE-API#gateway"`. A named role wins, and **no new attribute is added**. If two records could fill a role with `max: 1` and neither names it, the outcome is `unresolved` ("ambiguous: GW-A or GW-B — name the role in conforms_to"). SDEM never guesses. |
| PR-24 | **Outcomes**, per anchor record, per role and per connector, as in `sdem comply` (PR-19): a role filled and meeting its checks is `compliant`; a role not filled, or a connector missing, is `non_compliant` ("no gateway composes APP-PAY-HUB"); a value unknown or a binding ambiguous is `unresolved`; an exception (PR-18) may name a role or connector id (`PAT-SECURE-API/C1`). Exit codes and `sdem check` enforcement as PR-19. |
| PR-25 | **Drawing** (DG-16): the pattern is drawn from its structure, with roles as ArchiMate shapes of their types and connectors as lines. With `--workspace` and `--focus <anchor>`, it is drawn **over the design**: filled roles show their record, a missing part is drawn dashed and marked. The same JSON drives the workbench and `sdem diagram`. |
| PR-26 | **Upgrades** (UF-09): a pattern's types and links are checked against each new SDEM version by `sdem upgrade check`, like the rest of the profile. A link the new metamodel deprecates warns (MS-06). A removed one blocks, with the reason. |

## 3. Why the metamodel stays as it is

- A role is a **type the metamodel already has** (or a profile type extending one, PR-02).
- A connector is a **link the metamodel already allows** (PR-22 refuses any other).
- A record's role is written in **SDEM's own `conforms_to`** (CA-08, Dublin Core `dcterms:conformsTo`). No attribute is added.
- A structure is checked at load like every profile rule. It adds no type, attribute, link kind or layer.

The structural part is **checking existing data against an organisation's template**: what PR-13…PR-20 already do, at the level of a whole structure.

## 4. How it is built (once approved)

1. **Compile, then evaluate.** Each role and connector becomes rules on the anchor, reusing `comply.evaluate`. A connector of two steps (app → platform → zone) needs a **path** evaluation (`across` followed by `within`). This is the one new evaluation step, and it stays read-only and deterministic.
2. **Binding** (PR-23) produces a table of roles to records per anchor. `sdem comply --json` reports it, so an agent or the workbench can show which record plays which part.
3. **Diagram** (PR-25) reuses the template engine (`sdem diagram`, DG-02 checks), with a pattern as a template.
4. **Tests:**
   - the bank simulation gains the structure;
   - a missing gateway, an optional database, and an ambiguous binding (two gateways);
   - a connector the metamodel forbids is refused at `sdem profile check`;
   - a named role wins over a found one;
   - deterministic order;
   - the drawing marks the missing part.

## 4a. From the organisation's diagrams to a pattern file (extraction)

Reference patterns are drawn, not written as JSON. A person never has to type the JSON: `sdem pattern extract` reads the diagram and
writes a **draft** pattern file plus an **extraction report**. The pattern owner reviews both, and `sdem profile check` validates the
result before the profile includes it. The organisation's diagrams in this case are **draw.io, PlantUML, Mermaid and Visio**. All four
are text or XML, so extraction is **deterministic** and needs the standard library only (`xml.etree`, `zipfile`, `zlib`, `re`). No image
recognition is used.

| Format | What is read | How |
|---|---|---|
| **draw.io** (`.drawio`, `.xml`) | each `mxCell`: vertices (shapes, with label and style, e.g. `mxgraph.archimate3…`), edges (`source`/`target`), containers (`parent` = zone or group) | XML; a compressed diagram is base64 + deflate + URL encoding, all in the standard library |
| **PlantUML** (`.puml`) | elements (`component`, `node`, `database`, `rectangle`, ArchiMate macros such as `Application_Component(id, "label")`), arrows (`-->`, `..>`, `Rel_…`), nesting `{ … }` for zones, `<<stereotypes>>` | a documented subset of the grammar; a line outside it is reported, never skipped silently |
| **Mermaid** (`.mmd`, a fenced block in Markdown) | `flowchart`/`graph` nodes (`A[label]`, `B[(database)]`), edges (`-->`, `-.->`, with labels), `subgraph` for zones, `classDef`/`:::class` as type hints | a documented subset (flowchart; C4 diagrams later) |
| **Visio** (`.vsdx`) | each page's shapes (`Shape`, text, master/stencil name), connectors via `Connects` (`FromSheet` and `ToSheet`), containers | zip + XML (Open Packaging Conventions) |

| Id | Proposed requirement |
|---|---|
| PR-27 | **One extraction step, for every format:** shape → role, connector → connector, container → zone. The output is a pattern file in the PR-21…PR-24 form. Each role and connector cites its source (`diagram.drawio#cell-17`, `pattern.vsdx#page1/shape-4`, `pattern.puml:12`). |
| PR-28 | **A mapping table, in the profile**, turns the organisation's shape names, stencils, stereotypes and styles into types (`"API Gateway" → BANK.A3.APIGateway`; `mxgraph.archimate3.application` + `appType=comp` → `A3.ApplicationComponent`), and connector styles or labels into links (`"deployed on" → DEPLOYED_ON`). A shape with no entry is **listed as unmapped**, never guessed. Shapes from ArchiMate stencils map by their ArchiMate type with no table needed. |
| PR-29 | **Every connector is checked against the metamodel** (PR-22) at extraction. One it does not allow is reported with the reason, never dropped. A zone becomes a role check (`network_zone in [restricted]`) only through the mapping table (`"Restricted zone" → network_zone = restricted`). |
| PR-30 | **A draft until a person approves it.** `sdem pattern extract … --out draft.json` writes nothing into the profile. The pattern owner reviews, edits if needed, and includes it (a profile change, recorded like any other). An agent may run the extraction and explain the report, never approve. |
| PR-31 | **Re-extraction shows the difference.** When the diagram changes, extracting again compares with the included pattern: roles and connectors added, removed or changed, so the owner approves a change, not a whole new file. |

## 5. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| S1 | Structural patterns as an optional `structure` block in `sdem-pattern/1`, or a new format `sdem-pattern/2`? | **Optional block in `/1`**: existing pattern files keep working unchanged. |
| S2 | Binding: automatic from the anchor, with a role named in `conforms_to` winning (PR-23)? | **Yes**: no new attribute, and ambiguity is reported, never guessed. |
| S3 | A required role or connector not met: an error (blocks `sdem check`) or a warning? | **The pattern's `severity`**, default error, as for rules. |
| S4 | Drawing a pattern over a design (PR-25, DG-16): in the same release, or after? | **Same release**: the drawing is how architects read a pattern. |
| S5 | Generating a design from a pattern? | **Still deferred (B5).** |
| S6 | Extract patterns from the organisation's diagrams (draw.io, PlantUML, Mermaid, Visio) into draft pattern files (PR-27…PR-31)? | **Yes, all four, deterministic, standard library only**: draw.io and Visio first (their files hold real shapes and connectors), then PlantUML and Mermaid (a documented subset of each grammar). Every unmapped shape or disallowed connector is reported, and a person approves the result. |
