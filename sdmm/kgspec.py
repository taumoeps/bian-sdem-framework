"""Render docs/knowledge-graph-spec.md — the SDMM Knowledge Graph Specification (local and federated graphs).

Generated from schema/level-model.schema.json, schema/mapping.schema.json, schema/relationship-types.json,
schema/impact-rules.json, metamodel/level-relationships.json and the entity catalogue, plus the identity,
versioning, query and load requirements written here. Regenerate with `python -m sdmm.kgspec`; CI checks it.
"""
from pathlib import Path
from collections import Counter
import argparse, json
from sdmm.metamodel import Metamodel, MM_DIR

ROOT = MM_DIR.parent
DOC = ROOT / 'docs' / 'knowledge-graph-spec.md'
LEVEL_NAMES = {'A1': 'A1 Business Architecture', 'A2': 'A2 Service Domain Architecture', 'A3': 'A3 Application Architecture', 'A4': 'A4 Technology Architecture'}
OWNER = {'A1': 'business architecture', 'A2': 'BIAN alignment (enterprise architecture)', 'A3': 'application architecture', 'A4': 'infrastructure / platform engineering'}
SOURCE = {'A1': 'EA tool — capability, value-stream and process models', 'A2': 'BIAN workbench / the bank\'s BIAN alignment', 'A3': 'application portfolio, API catalogue, data models', 'A4': 'CMDB, deployment manifests'}


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def _schema_rows(defn):
    req = set(defn.get('required', []))
    rows = []
    for name, p in defn['properties'].items():
        t = ', '.join(p['enum']) if p.get('enum') else p.get('type') or p.get('$ref', '').split('/')[-1]
        rows.append((name, t, 'yes' if name in req else 'no', p.get('description', '')))
    return rows


def render():
    mm = Metamodel.load()
    lm = _j(ROOT / 'schema' / 'level-model.schema.json'); ms = _j(ROOT / 'schema' / 'mapping.schema.json')
    reg = _j(ROOT / 'schema' / 'relationship-types.json'); imp = _j(ROOT / 'schema' / 'impact-rules.json')
    lr = _j(MM_DIR / 'level-relationships.json'); conv = _j(MM_DIR / 'export-conventions.json')
    REQ = []
    def req(g, text, basis, status):
        rid = f"KG-{g}-{sum(1 for r in REQ if r[1] == g) + 1:02d}"; REQ.append((rid, g, text, basis, status)); return rid
    def inline(g):
        rows = [r for r in REQ if r[1] == g]
        return ['', '| ID | Requirement | Status |', '|---|---|---|'] + [f"| {r[0]} | {r[2]} | {r[4]} |" for r in rows] + ['']
    out = ['# SDMM Knowledge Graph Specification — local and federated graphs', '',
           'Generated from the schemas and records by `python -m sdmm.kgspec`; the test suite checks it is current. Companion to `docs/mapping-model-design-spec.md`, which specifies the engine. This document specifies the graphs: what each holds, how its nodes and edges are shaped, how identity and versions work, what queries it must answer, and how it is loaded. Requirements carry `KG-*` IDs; each says whether it is **built** (in `sdmm/graph.py` and the validators) or **not built**.', '']

    # ---- 1 architecture
    out += ['## 1. Architecture', '',
            'Four **local graphs**, one per architecture level, each owned by the team that governs that level, and one **federated graph** that holds only the approved links between levels and resolves each link\'s ends into the local graphs. The federated graph never copies a local graph\'s content and never holds a proposal. The engine reads both kinds of graph and writes only proposals to the mapping set; an architect\'s approval is the only way a proposal becomes a federated edge.', '',
            '```mermaid', 'flowchart TB',
            '    subgraph SOURCES[Source tools]', '      T1[EA tool]', '      T2[BIAN workbench]', '      T3[Application portfolio]', '      T4[CMDB]', '    end',
            '    subgraph LOCAL[Local graphs — one per level]', '      L1[(A1 Business)]', '      L2[(A2 Service Domain)]', '      L3[(A3 Application)]', '      L4[(A4 Technology)]', '    end',
            '    MD[[Mapping set — approved cross-level links]]', '    FED[(Federated graph)]', '    Q[Trace · Impact · Unmapped]',
            '    T1 -->|adapter → export| L1', '    T2 -->|adapter → export| L2', '    T3 -->|adapter → export| L3', '    T4 -->|adapter → export| L4',
            '    ENG[Engine] -->|proposed| MD', '    ARCH[Architect] -->|approves| MD',
            '    L1 -.->|reads entities + changes| ENG', '    L2 -.-> ENG', '    L3 -.-> ENG', '    L4 -.-> ENG', '    FED -.->|reads approved edges| ENG',
            '    L1 -.->|entity references| FED', '    L2 -.-> FED', '    L3 -.-> FED', '    L4 -.-> FED', '    MD -->|approved edges| FED', '    FED --> Q', '```', '',
            '| Graph | Holds | Owner | Source | Built from |', '|---|---|---|---|---|']
    for l in ('A1', 'A2', 'A3', 'A4'):
        out.append(f"| {LEVEL_NAMES[l]} local graph | the level's entity instances and the links inside the level | {OWNER[l]} | {SOURCE[l]} | one level export (`schema/level-model.schema.json`) |")
    out += ['| Federated graph | approved cross-level edges, and references to their ends in the local graphs | enterprise architecture | the mapping set | the mapping set (`schema/mapping.schema.json`) joined to the four local graphs |', '']
    req('A', 'Hold each level in its own local graph, loaded only from that level\'s export; a change in one level never requires reloading another.', 'level-model.schema.json; `LevelGraph`', 'built (in memory)')
    req('A', 'Hold in the federated graph only approved cross-level edges and references to their ends; never copy local content; never hold a proposed, rejected or superseded record as an edge used for answers.', 'mapping.schema.json; `FederatedGraph` status filter', 'built (in memory)')
    req('A', 'The engine reads the four local graphs (entities, within-level links, and what changed since the last baseline) and the federated graph (approved edges), read-only; it never writes to either. Approved edges stop it re-proposing what exists and are the inputs to its step-3 derivations.', 'mapping-model-design-spec §6; §8 governance', 'partly built (reads exports and approved mappings directly; change-since-baseline not built)')
    out += inline('A')

    # ---- 2 local graphs
    out += ['## 2. Local graphs', '', '### 2.1 Node schema (every level)', '', 'One node per instance in the export. Fields from `schema/level-model.schema.json` › `instance`:', '',
            '| Field | Type | Required | Note |', '|---|---|---|---|']
    for n, t, r, d in _schema_rows(lm['$defs']['instance']):
        note = {'id': 'node key; see §4 identity', 'type': 'an entity from the catalogue; concrete, never abstract or artefact', 'version': 'the instance\'s version, matched by mapping ends',
                'attributes': 'level-specific properties, including the join keys of §2.3', 'canonical_id': 'the external reference identity (e.g. a BIAN id) on A2 nodes'}.get(n, d)
        out.append(f"| `{n}` | {t} | {r} | {note} |")
    out += ['', 'Graph header fields (one per local graph): ' + ', '.join(f"`{k}`" for k in lm['properties'] if k not in ('instances', 'relationships')) + ' — `model_version` is the local graph\'s version (§5).', '',
            '### 2.2 Edge schema (every level)', '', 'One edge per relationship in the export, from `relationship`:', '', '| Field | Type | Required |', '|---|---|---|']
    for n, t, r, d in _schema_rows(lm['$defs']['relationship']):
        out.append(f"| `{n}` | {t} | {r} |")
    out += ['', '### 2.3 Node and edge types per level', '']
    byl = Counter(c['level'] for c in lr['constraints'])
    out += ['| Level | Node types (concrete) | Edge rows | Join-key properties |', '|---|---|---|---|']
    for l in ('A1', 'A2', 'A3', 'A4'):
        nodes = [t.split('.')[1] for t, e in mm.entities.items() if e['level'] == l and not e.get('abstract') and not e.get('artefact')]
        keys = sorted({f"{ent.split('.')[1]}.{k}" for ent, ks in conv['conventions'].items() if ent.startswith(l) for k in ks})
        out.append(f"| {LEVEL_NAMES[l]} | {len(nodes)}: {', '.join(nodes)} | {byl[l]} (`R{l}-01` …) | {', '.join(keys)} |")
    out += ['', 'Every allowed edge is a row in `metamodel/level-relationships.json`, listed with ID, source, reasoning and verification in `docs/relationships-planning.md`. `association` is allowed between any two nodes of one level.', '']
    req('L', 'Accept a node only if its `type` resolves to a concrete, non-artefact catalogue entity of the graph\'s level.', 'entity catalogue', 'built')
    req('L', 'Accept an edge only if both ends are nodes of this graph and (source type, kind, target type) matches a constraint row of the level through inheritance, or the kind is `association`.', 'level-relationships.json', 'built')
    req('L', 'Reject the whole export, and keep the previously loaded local graph, if any node or edge fails; report every failure.', '`sdmm-graph check`', 'built (check); keep-previous not built')
    req('L', 'Answer within-level queries on its own: neighbours by kind, part-whole closure (composition, aggregation), and nodes by type and lifecycle status.', '`LevelGraph`', 'partly built (closure in trace); per-level query API not built')
    out += ['### 2.4 Local graph requirements'] + inline('L')

    # ---- 3 federated
    out += ['## 3. Federated graph', '', '### 3.1 Edge types — the nine registry relationships', '', '| Relationship | Source node type → target node type | Cardinality | Perspective | Authority |', '|---|---|---|---|---|']
    for r in reg['relationships']:
        out.append(f"| `{r['relationship']}` ({r['mapping_type_id']}) | {r['source_type']} → {r['target_type']} | {r['cardinality'].replace('_', ' ')} | {r['perspective']} | {r['authority']} |")
    out += ['', 'Adjacent levels only (A1→A2, A2→A3, A3→A4). A level-skipping answer is a path, never a stored edge. The 41 candidate and derived rows of the plan are never federated edges.', '',
            '### 3.2 Edge schema', '', 'One edge per approved mapping record; its fields become the edge\'s properties (`schema/mapping.schema.json` › `mapping`):', '', '| Field | Type | Required |', '|---|---|---|']
    for n, t, r, d in _schema_rows(ms['$defs']['mapping']):
        out.append(f"| `{n}` | {t} | {r} |")
    out += ['', 'Each end (`source`, `target`) is a reference, not a copy: ' + ', '.join(f"`{n}`" for n, *_ in _schema_rows(ms['$defs']['entity'])) + '.', '',
            '### 3.3 Resolving an edge\'s ends', '', '1. The end\'s `type` prefix names the level, and therefore the local graph.', '2. The local graph must contain a node with that `id` and `version`.', '3. The node\'s concrete type must be the end\'s `type` or a descendant of it (is-a) — so a `DEPLOYED_ON` edge to `A4.InfrastructureComponent` resolves to a node, system software or device.', '4. An end that does not resolve makes the edge unresolved: reported, not used.', '']
    req('F', 'Load an edge only from a record with `status: approved`; keep the other statuses in the mapping set for history but never in answers unless a query asks for them explicitly.', 'mapping.schema.json status', 'built (`--status`)')
    req('F', 'Resolve every edge end into its local graph by level prefix, id, version and is-a; report unresolved ends and exclude those edges.', '§3.3', 'built (`sdmm-graph check`)')
    req('F', 'Store only adjacent-level edges of the nine registry relationships; derive level-skipping answers as paths with the mapping id of every hop.', 'relationship-types.json', 'built')
    req('F', 'Collapse duplicate edges between the same two nodes with the same relationship into one answer hop listing every mapping id.', '`walk` via[\'also\']', 'built')
    out += ['### 3.4 Federated graph requirements'] + inline('F')

    # ---- 4 identity
    out += ['## 4. Identity', '', 'The federated graph points into the local graphs by id. These rules keep those pointers valid.', '']
    req('I', 'A node id is unique within its level and stable for the life of the thing it names; it is never reused for a different thing, even after retirement.', 'new requirement', 'not enforced (uniqueness within an export is checked; stability across versions is not)')
    req('I', 'A rename changes `name`, never `id`. A genuine re-keying in a source tool is handled as retire-and-add: the old node is retired, the new one added, and the mappings to the old one are superseded by mappings to the new one.', 'new requirement; supersession', 'not built (needs export diff)')
    req('I', 'A2 nodes that correspond to a BIAN concept carry `canonical_id`; the federated edge\'s A2 end repeats it, and BIAN-authority edges require it before approval.', 'mapping.schema.json; validator', 'built')
    req('I', 'Institution aliases (asset-type, qualifier, field and glossary aliases) are node attributes, never alternative ids.', 'export-conventions.json', 'built (convention)')
    out += inline('I')

    # ---- 5 versioning
    out += ['## 5. Versions and baselines', '', '| Thing | Versioned by | Meaning |', '|---|---|---|',
            '| A node | `version` | the instance\'s own version, which an edge end pins |', '| A local graph | `model_version`, `metamodel_version` | which export and which catalogue it was built from |',
            '| An edge | `baseline_id`, `valid_from` / `valid_to`, `previous_mapping_id` | which release it belongs to, its validity, and what it replaced |', '| The federated graph | the set of (local graph `model_version` ×4, mapping-set commit) it was loaded from | one reproducible state |', '']
    req('V', 'Record, for every federated load, the four local `model_version`s and the mapping-set version used — the load\'s baseline — and return it with every answer.', 'new requirement', 'not built')
    req('V', 'Keep earlier baselines queryable, so an impact analysis can be rerun against the state it was originally run on.', 'new requirement', 'not built (git history of the files is the substitute today)')
    req('V', 'Never edit an approved edge; change is a new edge with `previous_mapping_id` and the old one `superseded`.', '`sdmm-diff`', 'built')
    req('V', 'Reject a federated load where the four local graphs disagree on `metamodel_version`.', 'Metamodel load', 'built')
    out += inline('V')

    # ---- 6 queries
    out += ['## 6. Queries the graphs must answer', '']
    Q = [('Trace', 'from any node, follow approved edges down (towards A4) or up (towards A1), optionally through within-level part-whole links; every hop shows the mapping id', '`sdmm-graph trace`, `--follow-composition`', 'built'),
         ('Impact', f"given a node and a change kind ({', '.join(imp['kinds'])}), classify every dependent node design_change_required / review_required / no_impact and list the edges to supersede", '`sdmm-graph impact`, impact-rules.json', 'built'),
         ('Check', 'validate the four local graphs and the federated edges; report every unresolved or disallowed item', '`sdmm-graph check`', 'built'),
         ('Unmapped', 'list nodes of a level with no approved cross-level edge where the plan expects one — the engine\'s work list', 'new', 'not built'),
         ('History', 'for an edge or a node, list its superseded predecessors and the baselines it appeared in', 'mapping-set history', 'not built'),
         ('Stats', 'counts of nodes, edges and statuses per level', '`sdmm-graph stats`', 'built')]
    out += ['| Query | Must answer | Implemented by | Status |', '|---|---|---|---|']
    for name, text, impl, st in Q:
        rid = req('Q', f"{name}: {text}.", impl, st); out.append(f"| {rid} {name} | {text} | {impl} | {st} |")
    out.append('')

    # ---- 7 load
    out += ['## 7. Load and refresh', '', '```', 'source tool → adapter → level export → validate (local) → load local graph', '                                                  ↓', 'mapping set (approved records) → validate → resolve ends → load federated graph → record baseline', '```', '',
            '| Step | Requirement | Status |', '|---|---|---|']
    for text, st in (('An adapter per source tool translates its records to a level export; adapters are institution-specific and live in the institution\'s private repository.', 'not built (examples are hand-written exports)'),
                     ('A local graph is rebuilt in full from its export; incremental update is an optimisation, not a requirement.', 'built (full rebuild)'),
                     ('A failed export validation leaves the previous local graph in place and raises an alert.', 'not built'),
                     ('The federated graph is rebuilt whenever a local graph or the mapping set changes.', 'built (rebuilt on every run)'),
                     ('The refresh trigger is configurable per source: on demand, scheduled, event-driven, or refresh-on-read (§11 DEC-02).', 'not built')):
        rid = req('R', text, '§7', st); out.append(f"| {rid} | {text} | {st} |")
    out.append('')

    # ---- 8 components and dependencies
    out += ['## 8. Components and dependencies', '', 'Every component the local and federated graphs depend on to be built, updated and changed: what it reads, what it writes, what it needs first, where it lives, and whether it exists.', '',
            '```mermaid', 'flowchart LR',
            '    MODEL[Model records<br/>catalogue · relationship rows<br/>registry · conventions]', '    TOOL[Source tool]', '    ADP[Adapter]', '    EXP[Level export]', '    CHK[Export validator<br/>sdmm-graph check]', '    LDR[Graph loader]', '    LG[(Local graph)]',
            '    DIFF[Export diff]', '    ENG[Engine]', '    PROP[Proposals]', '    VAL[Mapping validator<br/>sdmm-validate]', '    ARCH[Architect]', '    MS[[Mapping set]]', '    HIST[History guard<br/>sdmm-diff]', '    FED[(Federated graph)]', '    QRY[Query tools<br/>trace · impact · unmapped]', '    AG[Assistant]', '    TRG[Refresh trigger]',
            '    MODEL --> ADP', '    MODEL --> CHK', '    MODEL --> ENG', '    TOOL --> ADP --> EXP --> CHK --> LDR --> LG', '    TRG --> ADP', '    EXP --> DIFF --> ENG', '    LG --> ENG', '    FED --> ENG', '    ENG --> PROP --> VAL --> ARCH --> MS', '    MS --> HIST', '    MS --> LDR', '    LDR --> FED', '    LG --> FED', '    FED --> QRY --> AG', '    AG -.->|runs| ENG', '```', '']
    C = [
     ('C-01', 'Model records', 'the entity catalogue, `level-relationships.json`, `relationship-types.json`, `export-conventions.json`, `impact-rules.json`', 'SDMM model owner\'s edits', 'the rules every other component applies', '—', '`metamodel/`, `schema/`', 'built'),
     ('C-02', 'Source tool', 'the institution\'s system of record for one level', 'its users', 'its own records', '—', 'institution', 'external'),
     ('C-03', 'Adapter', 'extract, translate to SDMM entities and keys, write the export', 'C-02; C-01 (catalogue and conventions)', 'one level export', 'C-01, C-02', 'institution\'s private repository', 'not built (examples hand-written; `sdmm/structure.py` is the one generator)'),
     ('C-04', 'Level export', 'the file a local graph is built from', 'C-03', '—', 'C-03', '`examples/*/a[1-4]-*.json` (stand-ins)', 'built (format); schema `level-model.schema.json`'),
     ('C-05', 'Export validator', 'checks an export against C-01', 'C-04, C-01', 'pass, or every failure', 'C-01, C-04', '`sdmm-graph check` (`LevelGraph`)', 'built'),
     ('C-06', 'Graph loader', 'rebuilds local graphs from exports and the federated graph from the mapping set; records the baseline', 'C-04 (validated), C-09', 'local graphs, federated graph', 'C-05, C-09', '`sdmm/graph.py` (`LevelGraph`, `FederatedGraph`)', 'built in memory; persistence and baselines not built'),
     ('C-07', 'Export diff', 'compares a new export with the last loaded one: added, removed, changed instances and links', 'two versions of C-04', 'a change list', 'C-04', '—', 'not built'),
     ('C-08', 'Engine', 'proposes cross-level links for what changed, with evidence and confidence', 'local graphs, federated graph, C-07, C-01', 'proposals, candidate reports, inference log', 'C-06, C-07, C-01', '`sdmm/engine.py` protocol; logic proven by executor runs', 'partly built (protocol, baseline, eval); step logic not built'),
     ('C-09', 'Mapping set', 'the register of cross-level links with status and evidence', 'C-08 proposals; architect decisions', '—', 'C-08, C-11', '`examples/*/mappings.json`; schema `mapping.schema.json`', 'built'),
     ('C-10', 'Mapping validator', 'checks proposals and the mapping set: registry, evidence, anchoring', 'C-09, C-01', 'pass, or every failure', 'C-01', '`sdmm-validate`', 'built'),
     ('C-11', 'Architect approval', 'approves, rejects or supersedes mapping records', 'validated proposals; impact reports', 'status changes in C-09', 'C-10, C-14', 'a person; recorded as fields', 'built (as fields); review queue not built'),
     ('C-12', 'History guard', 'rejects edits to approved records and invalid status transitions', 'two versions of C-09', 'pass, or every violation', 'C-09', '`sdmm-diff`', 'built'),
     ('C-13', 'Local graphs, federated graph', 'the graphs themselves', 'C-06', '—', 'C-06', 'in memory', 'built in memory; store is DEC-01'),
     ('C-14', 'Query tools', 'trace, impact, check, stats; unmapped and history to come', 'C-13', 'answers with mapping ids', 'C-13', '`sdmm-graph`, `sdmm-trace`', 'built (unmapped, history not built)'),
     ('C-15', 'Refresh trigger', 'decides when C-03 and C-06 run: on demand, scheduled, event, refresh-on-read', 'source events or queries', 'runs', 'C-03, C-06', '—', 'not built (on demand only)'),
     ('C-16', 'Assistant', 'answers design questions from C-14; runs C-08 and C-10 on request', 'C-14 answers', 'proposals via C-08 only', 'C-14, C-08', 'per DEC-04', 'not built (Opus executor runs stood in)'),
     ('C-17', 'Generators and CI', 'regenerate documents, diagrams and the reference-structure estate from C-01; fail the build if any is stale; rerun acceptance cases', 'C-01', 'generated files; pass / fail', 'C-01', '`sdmm/diagram.py`, `relationships.py`, `structure.py`, `spec.py`, `kgspec.py`; `.github/workflows/validate.yml`', 'built'),
    ]
    out += ['| ID | Component | Does | Reads | Writes | Depends on | Lives in | Status |', '|---|---|---|---|---|---|---|---|']
    for row in C: out.append('| ' + ' | '.join(row) + ' |')
    out.append('')
    req('C', 'Build an adapter (C-03) per source tool that writes a valid level export and fails loudly rather than writing a partial one.', 'C-03', 'not built')
    req('C', 'Build the export diff (C-07) so the engine re-checks only changed instances and removals are routed to impact and supersession.', 'C-07', 'not built')
    req('C', 'Build the engine step logic (C-08) to the mapping-model design specification, accepted by reproducing the eleven executor runs.', 'C-08; mapping-model-design-spec §8', 'not built')
    req('C', 'Provide a review queue for C-11 that lists proposals and pending supersessions with their evidence and impact.', 'C-11', 'not built')
    out += ['### 8.1 Component requirements'] + inline('C')

    # ---- 9 change workflows
    out += ['## 9. Change workflows — which components run for each change', '', '| Change | Example | Components, in order | Human step |', '|---|---|---|---|']
    W = [
     ('Model structure', 'a new entity kind, relationship row or join key', 'C-01 edit → C-17 regenerate and test → C-03 updated to emit it → C-04 → C-05 → C-06', 'model owner decides; adapter maintainer updates the translation'),
     ('Instance added', 'a new API operation appears', 'C-15 → C-03 → C-04 → C-05 → C-06 (local) → C-07 → C-08 → C-10 → C-11 → C-12 → C-06 (federated)', 'approve the proposals'),
     ('Instance removed or retired', 'a platform is decommissioned', 'C-15 → C-03 → C-04 → C-05 → C-06 (local) → C-07 → C-14 impact → C-11 supersede → C-12 → C-06 (federated)', 'confirm the supersessions'),
     ('Instance attributes changed', 'an API path or a table\'s columns change', 'C-03 → C-04 → C-05 → C-06 → C-07 → C-08 re-checks dependent mappings', 'only if an approved mapping no longer holds'),
     ('Within-level link changed', 'a process gains an activity', 'C-03 → C-04 → C-05 → C-06', 'none; derived paths recompute'),
     ('Instance re-keyed in its tool', 'an application gets a new id', 'as removed + added, then C-11 supersedes the old mappings with new ones (KG-I-02)', 'approve the replacements'),
     ('Mapping approved, rejected or superseded', 'an architect reviews the queue', 'C-11 → C-09 → C-10 → C-12 → C-06 (federated)', 'the decision itself'),
     ('Mapping rule changed', 'a threshold or alias convention', 'C-01 → C-17 (acceptance cases rerun and scored) → C-08 on affected estates → C-11', 'model owner adopts the rule only if the scores hold'),
     ('BIAN release', 'a new Service Landscape version', 'C-01 (A2 rows and catalogue) → C-03 for A2 → C-04 → C-05 → C-06 → C-07 → C-08 → C-11', 'review changed A2 mappings'),
    ]
    for row in W: out.append('| ' + ' | '.join(row) + ' |')
    out += ['', 'Every workflow ends with C-06 rebuilding the graphs; no component edits a graph in place.', '']

    # ---- 10 governance
    out += ['## 10. Governance boundary', '', '| Actor | May | May not |', '|---|---|---|',
            '| Level owner | change its source tool; publish a new export | write federated edges |', '| Engine | read local graphs and approved edges; write proposals | approve; write to any graph |',
            '| Architect | approve, reject or supersede mapping records | edit an approved record |', '| Agent (assistant) | query the graphs; run the engine and validators | approve; write to any graph or mapping set |',
            '| Graph loader | rebuild graphs from exports and the mapping set | change any input |', '']
    req('G', 'Only an architect action sets `approved`; no automated component, engine or agent may.', 'mapping-execution.md §2; registry enterprise_rule', 'built (convention; validator requires reviewer_id and approved_at)')
    out += inline('G')

    # ---- 11 decisions
    out += ['## 11. Open design decisions', '', '| ID | Decision | Options | SDMM default |', '|---|---|---|---|',
            '| DEC-01 | Graph store | in memory from files (today); property graph (e.g. Neo4j: nodes and edges map one-to-one to §2 and §3); RDF store (named graph per local graph, edges as reified statements with PROV) | in memory until a team needs persistent queries; then property graph |',
            '| DEC-02 | Refresh trigger per source | on demand; scheduled; event-driven (webhook); refresh-on-read | on demand now; event-driven where the tool supports it |',
            '| DEC-03 | One store or five | one store with a partition per local graph plus the federated edges; or separate stores per team federated by id | one store, partitioned, until teams need independent operation |',
            '| DEC-04 | Agent access | CLI run by the assistant; VS Code extension; context snapshot; MCP where policy allows | per the organisation\'s Copilot policy |',
            '| DEC-05 | Standard export of the mapping set | none; SSSOM; RDF + PROV-O | SSSOM export when interoperability is needed |', '']

    # ---- 10 index
    status = Counter(r[4].split(' ')[0] for r in REQ)
    out += ['## 12. Requirements index', '', f"{len(REQ)} requirements — " + ', '.join(f"{k} {v}" for k, v in status.most_common()) + '. Groups: A architecture, L local graph, F federated graph, I identity, V versions, Q queries, R load and refresh, C components, G governance.', '',
            '| ID | Requirement | Basis | Status |', '|---|---|---|---|']
    for rid, g, text, basis, st in REQ:
        out.append(f"| {rid} | {text} | {basis} | {st} |")
    out.append('')
    return '\n'.join(out) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-kgspec', description='Render docs/knowledge-graph-spec.md from the schemas and records.')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        ok = DOC.exists() and DOC.read_text(encoding='utf-8') == text
        print('up to date' if ok else 'STALE: regenerate with python -m sdmm.kgspec'); return 0 if ok else 1
    DOC.write_text(text, encoding='utf-8'); print(f'wrote {DOC}'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
