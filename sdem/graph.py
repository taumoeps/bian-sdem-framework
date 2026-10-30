"""SDEM graphs: one LevelGraph per design model (A1-A4) and a FederatedGraph that joins them to the mappings.

Structural logic only. A level graph holds an institution's instances and within-level relationships;
the federated graph resolves mapping endpoints against them, traces chains with names, and classifies
impact by rule. Nothing here decides whether a mapping is right.
"""
from pathlib import Path
import argparse, json, re, sys
from sdem.metamodel import Metamodel, MM_DIR, PROJECTED_PREFIXES, is_projection_dataset
from sdem.conformance import check_level, estate_index
from sdem.validate import check_schema, load_registry, load_schema, normalize_type, validate, ROOT
from sdem.trace import load_edges, walk, paths as tree_paths

LEVEL_SCHEMA = ROOT / 'schema' / 'level-model.schema.json'
CLASSES = ('design_change_required', 'review_required', 'no_impact')
EXIT_OK, EXIT_ISSUES, EXIT_USAGE = 0, 1, 2

IMPACT_RULES_FILE = ROOT / 'schema' / 'impact-rules.json'


def load_impact_rules(path=IMPACT_RULES_FILE):
    """Impact classification is governed data (schema/impact-rules.json), not code."""
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    for kind, spec in doc['kinds'].items():
        bad = set(spec['rules'].values()) - set(doc['classes'])
        if bad:
            raise ValueError(f'impact-rules: kind {kind!r} uses unknown class(es) {sorted(bad)}')
    return doc


_IMPACT = load_impact_rules()
IMPACT_RULES = {k: v['rules'] for k, v in _IMPACT['kinds'].items()}
IMPACT_REASONS = {k: v['reason'] for k, v in _IMPACT['kinds'].items()}
SUPERSEDE_FOR = set(_IMPACT.get('supersede_mappings_touching_changed_instance_for', []))


class LevelGraph:
    def __init__(self, doc, metamodel):
        self.doc, self.mm = doc, metamodel
        self.level = doc['level']
        self.instances = {(i['id'], i['version']): i for i in doc.get('instances', [])}
        self.by_id = {}
        for i in doc.get('instances', []):
            self.by_id.setdefault(i['id'], []).append(i)
        self.relationships = doc.get('relationships', [])
        self.warnings, self.estate = [], None

    @classmethod
    def load(cls, path, metamodel=None):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')), metamodel or Metamodel.load())

    def validate(self):
        issues = check_schema(self.doc, json.loads(LEVEL_SCHEMA.read_text(encoding='utf-8')))
        if issues:
            return issues
        if self.doc.get('metamodel_version') and self.doc['metamodel_version'] != self.mm.version:
            issues.append(f"metamodel_version {self.doc['metamodel_version']!r} does not match loaded metamodel {self.mm.version!r} — move the workspace with `sdem migrate --workspace <dir> --person <you>`")
        seen = set()
        if not is_projection_dataset(self.doc):  # CTL-16: projected or design records never enter real architecture data
            for i in self.doc.get('instances', []):
                if str(i.get('id', '')).startswith(PROJECTED_PREFIXES):
                    issues.append(f"instance {i['id']}: a projected or design record cannot enter a real architecture dataset (CTL-16)")
        for i in self.doc.get('instances', []):
            key = (i['id'], i['version'])
            if key in seen:
                issues.append(f"instance {i['id']}@{i['version']}: duplicate")
            seen.add(key)
            t = i['type']
            if not self.mm.known(t):
                issues.append(f"instance {i['id']}: entity {t!r} is not in the metamodel")
            elif self.mm.level(t) != self.level:
                issues.append(f"instance {i['id']}: entity {t!r} is not an {self.level} entity")
            elif self.mm.is_abstract(t):
                issues.append(f"instance {i['id']}: entity {t!r} is abstract; level models must use concrete entities")
            elif self.mm.is_artefact(t):
                issues.append(f"instance {i['id']}: entity {t!r} is an artefact, not an instance type")
        for r in self.relationships:
            ends = [self.by_id.get(r['source']), self.by_id.get(r['target'])]
            if not all(ends):
                issues.append(f"relationship {r['source']} -{r['kind']}-> {r['target']}: endpoint not in this model")
                continue
            problem = self.mm.relationship_issue(self.level, ends[0][0]['type'], r['kind'], ends[1][0]['type'])
            if problem:
                issues.append(f"relationship {r['source']} -{r['kind']}-> {r['target']}: {problem}")
        errors, self.warnings, _ = check_level(self.doc, self.mm, self.estate)  # data-model conformance (LC-04 … LC-13)
        return issues + errors

    def neighbours(self, iid):
        out = []
        for r in self.relationships:
            if r['source'] == iid: out.append(('out', r['kind'], r['target']))
            if r['target'] == iid: out.append(('in', r['kind'], r['source']))
        return out


class FederatedGraph:
    """Four level graphs + mapping documents. Also an EntityResolver for the validator."""
    def __init__(self, levels, mapping_docs, metamodel=None, registry=None):
        self.mm = metamodel or Metamodel.load()
        self.registry = registry or load_registry()
        self.levels = {g.level: g for g in levels}
        self.mapping_docs = mapping_docs
        self.design_records = None   # <workspace>/designs/design-records.json, when loaded (beside the architectures, never in them)

    @classmethod
    def load(cls, paths, metamodel=None, registry=None):
        """Classify each file by content: architecture datasets have 'level' + 'instances'; mapping docs have 'mappings'."""
        from .designs import is_design_records
        mm = metamodel or Metamodel.load()
        levels, docs, design = [], [], None
        for p in paths:
            d = json.loads(Path(p).read_text(encoding='utf-8'))
            if 'mappings' in d: docs.append(d)
            elif 'instances' in d and 'level' in d: levels.append(LevelGraph(d, mm))
            elif is_design_records(d): design = d
            else: raise ValueError(f'{p}: neither an architecture dataset nor a mapping document')
        fg = cls(levels, docs, mm, registry); fg.design_records = design
        return fg

    # ---- EntityResolver protocol: an endpoint resolves if an instance with that id/version exists in the
    #      level its entity prefix names, and the instance's concrete entity is-a the referenced entity.
    def resolve_entity(self, id, type, version):
        t = normalize_type(type, self.registry)
        g = self.levels.get(self.mm.level(t) or '')
        inst = g.instances.get((id, version)) if g else None
        return inst if inst and self.mm.is_a(inst['type'], t) else None

    def instance(self, iid):
        for g in self.levels.values():
            if iid in g.by_id:
                return g.by_id[iid][-1]
        return None

    def check(self):
        """Validate every level graph, then every mapping document with this graph as the entity resolver."""
        report = {}; self.warnings = {}
        index = estate_index([g.doc for g in self.levels.values()])
        for lvl, g in sorted(self.levels.items()):
            g.estate = index
            report[f'level {lvl} ({g.doc["model_id"]})'] = g.validate()
            if g.warnings: self.warnings[f'level {lvl} ({g.doc["model_id"]})'] = g.warnings
        for n, d in enumerate(self.mapping_docs, 1):
            warnings = []
            issues = validate(d, self.registry, load_schema(), entity_resolver=self, warnings=warnings, metamodel=self.mm)
            report[f'mappings #{n}'] = issues
        if self.design_records is not None:  # GS-D-02: schema and references; an entity no longer in the workspace is a warning
            from .designs import check as _check_designs
            ids = {i for g in self.levels.values() for i in g.by_id}
            errs, warns = _check_designs(self.design_records, ids)
            report['design records'] = errs
            if warns: self.warnings['design records'] = warns
        return report

    def edges(self, statuses=('approved',)):
        return load_edges(self.mapping_docs, statuses)

    def enrich(self, node):
        inst = self.instance(node['id'])
        node['name'] = inst['name'] if inst else None
        node['level'] = self.mm.level(inst['type']) if inst else self.mm.level(node.get('type') or '')
        node['concrete_type'] = inst['type'] if inst else None
        node['resolved'] = inst is not None
        node['lifecycle_status'] = inst.get('lifecycle_status') if inst else None
        for c in node['children']:
            self.enrich(c['node'])
        return node

    def composition_hops(self, iid, direction):
        """Within-level part-whole links (composition and aggregation) as virtual hops: downstream climbs to the
        whole (a module's traceability continues through its application; a component's through its solution
        building block); upstream descends to the parts. Assignment and realization are not part-whole and are
        not followed (relationships test, finding 6)."""
        hops = []
        for g in self.levels.values():
            for r in g.relationships:
                if r['kind'] not in ('composition', 'aggregation'): continue
                if direction == 'down' and r['target'] == iid: hops.append(r['source'])
                if direction == 'up' and r['source'] == iid: hops.append(r['target'])
        return hops

    def trace(self, start, direction='down', statuses=('approved',), follow_composition=False):
        edges = self.edges(statuses)
        if follow_composition:
            # add virtual PART_OF / COMPOSES edges so a chain can pass from a part to its whole (and back)
            seen, frontier, virtual = set(), [start], []
            while frontier:
                n = frontier.pop()
                if n in seen: continue
                seen.add(n)
                for e in edges:
                    a, b = (e['source'], e['target']) if direction == 'down' else (e['target'], e['source'])
                    if a['id'] == n: frontier.append(b['id'])
                for whole in self.composition_hops(n, direction):
                    inst = self.instance(whole) or {}
                    src, tgt = ({'id': n, 'type': (self.instance(n) or {}).get('type'), 'version': (self.instance(n) or {}).get('version')}, {'id': whole, 'type': inst.get('type'), 'version': inst.get('version')})
                    if direction == 'up': src, tgt = tgt, src
                    virtual.append({'mapping_id': 'composition', 'relationship': 'PART_OF' if direction == 'down' else 'COMPOSES', 'status': 'structural', 'baseline_id': None, 'source': src, 'target': tgt})
                    frontier.append(whole)
            edges = edges + virtual
        return self.enrich(walk(edges, start, direction))

    def impact(self, changed, kind, statuses=('approved',)):
        if kind not in IMPACT_RULES:
            raise ValueError(f'unknown change kind {kind!r}; choose from {sorted(IMPACT_RULES)}')
        edges = self.edges(statuses)
        rules = IMPACT_RULES[kind]
        rows, touched = [], []
        def add(iid, relation, path):
            cls = rules.get(relation, 'no_impact')
            inst = self.instance(iid)
            rows.append({'id': iid, 'name': inst['name'] if inst else None, 'type': inst['type'] if inst else None,
                         'level': self.mm.level(inst['type']) if inst else None, 'relation': relation,
                         'classification': cls, 'via': [v for v in path if v]})
        add(changed, 'self', [])
        for direction, key in (('up', 'up'), ('down', 'down')):
            for p in tree_paths(walk(edges, changed, direction)):
                for depth, (iid, via) in enumerate(p[1:], 1):
                    relation = f'{key}1' if depth == 1 else f'{key}2+'
                    if not any(r['id'] == iid for r in rows):
                        add(iid, relation, [v['mapping_id'] for _, v in p[1:depth + 1]])
        for e in edges:
            if changed in (e['source']['id'], e['target']['id']) and kind in SUPERSEDE_FOR:
                touched.append(e['mapping_id'])
        return {'changed': changed, 'change': kind, 'reason': IMPACT_REASONS[kind], 'rules_version': _IMPACT['$schema_version'], 'instances': rows,
                'mappings_to_supersede': sorted(set(touched))}


def impact_report(result, generated=None):
    """DB-K02: a printable impact report (Markdown) from an impact result."""
    import datetime
    ch = next((r for r in result['instances'] if r['id'] == result['changed']), {})
    order = {'design_change_required': 0, 'review_required': 1, 'no_impact': 2}
    rows = sorted(result['instances'], key=lambda r: (order.get(r['classification'], 3), r['level'] or '', r['id']))
    label = {'design_change_required': 'design change required', 'review_required': 'review required', 'no_impact': 'no impact'}
    out = [f"# Impact report — {result['change']} of {result['changed']}", '',
           f"| | |", '|---|---|',
           f"| Record | {ch.get('name') or result['changed']} `{result['changed']}` ({ch.get('type') or '?'}) |",
           f"| Change | **{result['change']}** — {result['reason']} |",
           f"| Generated | {generated or datetime.date.today().isoformat()} by `sdem impact` (impact rules {result.get('rules_version', '?')}) from approved links |", '',
           '## Summary', '']
    for cls in ('design_change_required', 'review_required', 'no_impact'):
        n = [r for r in rows if r['classification'] == cls]
        if n: out.append(f"- **{label[cls]}**: {len(n)} — " + ', '.join(f"{r['name'] or r['id']} ({r['level'] or '?'})" for r in n))
    out += ['', '## Affected records', '', '| Layer | Record | Classification | Path (approved links) | Relation to the change |', '|---|---|---|---|---|']
    rel = {'self': 'the changed record', 'up1': 'depends on it directly', 'up2+': 'depends on it indirectly', 'down1': 'it depends on this directly', 'down2+': 'it depends on this indirectly'}
    out += [f"| {r['level'] or '?'} | {r['name'] or ''} `{r['id']}` | {label.get(r['classification'], r['classification'])} | {', '.join(r['via']) or '—'} | {rel.get(r['relation'], r['relation'])} |" for r in rows]
    out += ['', '## Links to supersede', '']
    out += [f"- `{m}` — replace with a new approved link (`sdem approve … --supersedes {m}`)" for m in result['mappings_to_supersede']] or ['None.']
    out += ['', '---', '', '*Classification is structural; an architect confirms before any design changes.*', '']
    return '\n'.join(out)


def level_trace(fg, level, direction, statuses=('approved',), follow_composition=False, to=None):
    """Every record of a layer traced one way (TR-L01…L04): per record its chains to the other layers; who is connected, who reaches
    which layer, and who is connected to nothing (the gaps)."""
    g = fg.levels.get(level)
    recs = sorted({i['id']: i for i in g.instances.values()}.values(), key=lambda i: i['id']) if g else []
    order = ['A1', 'A2', 'A3', 'A4'] if direction == 'down' else ['A4', 'A3', 'A2', 'A1']
    if to in order and order.index(to) <= order.index(level): to = None   # --to lies the other way: no limit this way
    stop = order.index(to) if to in order else len(order) - 1
    from .paths import DATA_ROOT
    types = json.loads((DATA_ROOT / 'schema' / 'relationship-types.json').read_text(encoding='utf-8'))['relationships']   # the official connection types
    ends = {r['source_type' if direction == 'down' else 'target_type'] for r in types}
    def can_connect(t):   # TR-L02: only kinds the metamodel lets connect this way can be a gap
        return any(t == e or fg.mm.is_a(t, e) for e in ends)
    chains, reach, orphans, not_applicable = [], {}, [], 0
    for r in recs:
        tree = fg.trace(r['id'], direction, statuses, follow_composition)
        mine = []
        def walk(n, path):
            kids = [c for c in n['children'] if (c['node'].get('level') or level) in order and order.index(c['node'].get('level') or level) <= stop]
            if not kids and path: mine.append(path)
            for c in kids: walk(c['node'], path + [{'id': c['node']['id'], 'name': c['node'].get('name'), 'level': c['node'].get('level'), 'via': c['via']['mapping_id']}])
        walk(tree, [])
        if not mine:
            if can_connect(r.get('type', '')): orphans.append({'id': r['id'], 'name': r.get('name'), 'type': r.get('type')})
            else: not_applicable += 1
            continue
        for path in mine:
            chains.append({'start': {'id': r['id'], 'name': r.get('name'), 'level': level}, 'steps': path})
            for st in path: reach.setdefault(st['level'], set()).add(r['id'])
    return {'level': level, 'direction': direction, 'records': len(recs), 'connected': len(recs) - len(orphans) - not_applicable, 'not_applicable': not_applicable,
            'reach': {l: len(v) for l, v in sorted(reach.items(), key=lambda x: order.index(x[0]) if x[0] in order else 9) if l != level},
            'orphans': orphans, 'chains': chains, 'to': to}


def render_level_trace(res, only_gaps=False):
    lvl, d = res['level'], res['direction']
    arrow = ' → ' if d == 'down' else ' ← '
    out = [f"{LAYER.get(lvl, lvl)} — {res['records']} record(s), traced {d}" + (f" to {LAYER.get(res['to'], res['to'])}" if res['to'] else '')]
    if not only_gaps:
        out.append(f"  connected {'onward' if d == 'down' else 'from above'}: {res['connected']} of {res['records']}"
                   + (f"  ({res['not_applicable']} not counted: kinds that never connect {'down' if d == 'down' else 'up'}, e.g. parts and attributes)" if res.get('not_applicable') else ''))
        for l, n in res['reach'].items(): out.append(f"  reaching {LAYER.get(l, l)}: {n} of {res['records']}")
    gaps = res['orphans']
    out.append(f"  connected to nothing {'below' if d == 'down' else 'above'} (gaps): {len(gaps)}" + (' — ' + ', '.join(f"{o['id']} {o['name']!r}" for o in gaps[:12]) + (' …' if len(gaps) > 12 else '') if gaps else ''))
    if only_gaps or not res['chains']: return '\n'.join(out)
    out += ['', f"  CHAINS ({len(res['chains'])}){'' if d == 'down' else ' — each record depends on the one to its left'}:"]
    for c in res['chains']:
        names = [c['start']['name'] or c['start']['id']] + [s['name'] or s['id'] for s in c['steps']]
        out.append('  ' + arrow.join(names) + '   (' + ', '.join(s['via'] for s in c['steps']) + ')')
    return '\n'.join(out)


def write_level_csv(results, path):
    import csv
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['direction', 'start_layer', 'start_id', 'start_name', 'chain_ids', 'chain_names', 'chain_layers', 'connections'])
        for res in results:
            for c in res['chains']:
                w.writerow([res['direction'], res['level'], c['start']['id'], c['start']['name'], ' > '.join(s['id'] for s in c['steps']),
                            ' > '.join(s['name'] or '' for s in c['steps']), ' > '.join(s['level'] or '' for s in c['steps']), ' '.join(s['via'] for s in c['steps'])])
            for o in res['orphans']: w.writerow([res['direction'], res['level'], o['id'], o['name'], '', '', '', 'gap: connected to nothing'])


LAYER = {'A1': 'A1 Business', 'A2': 'A2 BIAN', 'A3': 'A3 Application', 'A4': 'A4 Technology'}


def kind_label(t):
    """'A4.Node' → 'A4 Technology · Node'; 'A3.ApplicationComponent' → 'A3 Application · Application Component'."""
    lvl, _, kind = (t or '?').partition('.')
    return f"{LAYER.get(lvl, lvl)} · {re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', kind)}" if kind else t


def render_trace(tree, direction):
    arrow = '-' if direction == 'down' else '<-'
    def label(n):
        name = f" {n['name']!r}" if n.get('name') else ''
        t = n.get('concrete_type') or n.get('type') or '?'
        mark = '' if n.get('resolved') else '  (unresolved)'
        if n.get('lifecycle_status') == 'planned': mark += '  [DESIGN — planned, not observed]'
        return f"{n['id']}{name}  [{kind_label(t)}]" + mark
    lines = [label(tree)]
    def rec(n, prefix):
        for i, c in enumerate(n['children']):
            last = i == len(n['children']) - 1
            tag = f"{arrow}{c['via']['relationship']}{'->' if direction == 'down' else '-'}"
            ids = ', '.join([c['via']['mapping_id']] + c['via'].get('also', []))
            lines.append(f"{prefix}{'└─ ' if last else '├─ '}{tag} {label(c['node'])}  ({ids})")
            rec(c['node'], prefix + ('   ' if last else '│  '))
    rec(tree, '')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdem-graph', description='Federated graph over A1-A4 architecture datasets and mapping documents.')
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('check', 'trace', 'impact', 'stats'):
        sp = sub.add_parser(name)
        if name in ('trace', 'impact'):
            sp.add_argument('entity', help='instance id to start from' + (' — or a whole layer: A1, A2, A3 or A4' if name == 'trace' else ''))
        sp.add_argument('paths', nargs='*', help='architecture datasets and mapping documents, any order (or use --graph)')
        sp.add_argument('--graph', metavar='DIR', help='read a graph store (sdem build) instead of architecture datasets')
        sp.add_argument('--status', default='approved', help='mapping statuses to treat as arrows')
        sp.add_argument('--json', action='store_true')
        if name == 'trace':
            sp.add_argument('--direction', choices=['down', 'up', 'both', 'downstream', 'upstream', 'all'], default='both',
                            help='down: what it depends on; up: what depends on it; both (also: downstream, upstream, all)')
            sp.add_argument('--tree', action='store_true', help='a whole layer: one tree per record (default: summary, gaps and a table of chains)')
            sp.add_argument('--only-gaps', action='store_true', help='a whole layer: only the records with no connection in that direction')
            sp.add_argument('--to', metavar='LAYER', choices=['A1', 'A2', 'A3', 'A4', 'a1', 'a2', 'a3', 'a4'], help='a whole layer: stop the chains at this layer')
            sp.add_argument('--csv', metavar='FILE', help='a whole layer: also write the chains as CSV')
            sp.add_argument('--follow-composition', action='store_true', help='continue a chain through within-level part-whole links — composition and aggregation (part -> whole downstream, whole -> parts upstream)')
            sp.add_argument('--projection', metavar='DIR', help='also follow the links of an AID projection package, labelled PROJECTED (AID-O06)')
        if name == 'impact':
            sp.add_argument('--change', choices=sorted(IMPACT_RULES), required=True)
            sp.add_argument('--report', metavar='FILE.md', help='also write a printable impact report (Markdown)')
    sp = sub.add_parser('build', help='check architecture datasets and registry, then write the graph store')
    sp.add_argument('paths', nargs='+', help='architecture datasets and relationship registries')
    sp.add_argument('-o', '--out', required=True, metavar='DIR', help='graph store directory')
    sp.add_argument('--check', action='store_true', help='fail if the stored graph files differ from a fresh build (CI)')
    sp.add_argument('--json', action='store_true')
    sp = sub.add_parser('query', help='find records in a graph store')
    sp.add_argument('--graph', required=True, metavar='DIR')
    sp.add_argument('--level', choices=['A1', 'A2', 'A3', 'A4'])
    sp.add_argument('--type', help='entity type; subtypes included')
    sp.add_argument('--where', action='append', default=[], metavar='ATTR=VALUE', help='core field or attribute equals value (repeatable)')
    sp.add_argument('--neighbours', metavar='ID', help='within-level neighbours of a record')
    sp.add_argument('--kind', help='with --neighbours: only this relationship kind')
    sp.add_argument('--direction', choices=['in', 'out', 'both'], default='both')
    sp.add_argument('--unmapped', choices=['A1', 'A2', 'A3', 'A4'], help='records with no approved cross-level link where the catalogue expects one')
    sp.add_argument('--json', action='store_true')
    sp = sub.add_parser('view', help='write a self-contained HTML picture of a graph store')
    sp.add_argument('--graph', required=True, metavar='DIR'); sp.add_argument('-o', '--out', metavar='FILE', help='default <DIR>/view.html')
    sp.add_argument('--projection', metavar='DIR', help='overlay an AID projection package, drawn dashed and labelled PROJECTED (AID-O06)')
    sp.add_argument('--json', action='store_true')
    sp = sub.add_parser('baseline', help='freeze the current graph store under baselines/<name>')
    sp.add_argument('name'); sp.add_argument('--graph', required=True, metavar='DIR'); sp.add_argument('--json', action='store_true')
    # paths are optional (--graph replaces them), so argparse cannot place paths written after an option; collect them here
    args, extra = parser.parse_known_args(argv)
    if extra:
        if hasattr(args, 'paths') and args.cmd in ('check', 'trace', 'impact', 'stats') and not any(x.startswith('-') for x in extra): args.paths += extra
        else: parser.error(f"unrecognized arguments: {' '.join(extra)}")
    from sdem import store as _store
    if args.cmd == 'build':
        return _build(args, _store)
    if args.cmd == 'view':
        from sdem.view import write as _view
        try:
            build_no, stale = _store.stale_inputs(args.graph)
            if stale: print(f"WARN: the graph store is out of date — {len(stale)} input(s) changed since build {build_no}; the view shows the store. Rebuild with: sdem build … --out {args.graph}", file=sys.stderr)
            out = _view(args.graph, args.out, projection=args.projection)
            print(json.dumps({'wrote': str(out)}) if args.json else f'wrote {out}'); return EXIT_OK
        except (OSError, _store.StoreError) as exc: print(f'ERROR: {exc}', file=sys.stderr); return EXIT_USAGE
    if args.cmd == 'baseline':
        try:
            dest = _store.baseline(args.graph, args.name)
            print(json.dumps({'baseline': args.name, 'written': str(dest)}) if args.json else f'baseline written: {dest}'); return EXIT_OK
        except _store.StoreError as exc: print(f'ERROR: {exc}', file=sys.stderr); return EXIT_ISSUES
    try:
        if getattr(args, 'graph', None):
            if getattr(args, 'paths', None): print('ERROR: give architecture dataset paths or --graph, not both', file=sys.stderr); return EXIT_USAGE
            reader = _store.GraphReader.from_store(args.graph)
        else:
            if not args.paths: print('ERROR: give architecture dataset paths or --graph', file=sys.stderr); return EXIT_USAGE
            reader = _store.GraphReader.from_exports(args.paths)
        fg = reader.fg
    except (OSError, ValueError, _store.StoreError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return EXIT_USAGE
    if reader.origin == 'store':
        b = reader.baseline()
        print(f"baseline: graph store {args.graph}, build {b['build']} ({', '.join(f'{k} {v}' for k, v in b['levels'].items())})", file=sys.stderr)
        build_no, stale = _store.stale_inputs(args.graph)
        if stale:
            print(f"WARN: the graph store is out of date — {len(stale)} input(s) changed since build {build_no}: {', '.join(stale)}. "
                  f"Answers below reflect the store, not the current data; rebuild with: sdem build … --out {args.graph}", file=sys.stderr)
    if args.cmd == 'query':
        return _query(args, reader)
    statuses = tuple(s.strip() for s in args.status.split(',') if s.strip())
    if reader.origin == 'store' and set(statuses) - {'approved'}:
        print('ERROR: a graph store holds approved links only; use the registry files for other statuses', file=sys.stderr); return EXIT_USAGE
    if args.cmd == 'check':
        report = reader.check_store(args.graph) if reader.origin == 'store' else fg.check()
        if reader.origin != 'store':  # D2: the workspace's coordination records (agent platform), when there are any
            from sdem.agents import check_coordination
            for est in sorted({Path(p).resolve().parent for p in args.paths if (Path(p).resolve().parent / 'coordination').exists()}):
                issues, n = check_coordination(est)
                if n: report[f'coordination ({n} records)'] = issues
        failed = any(report.values())
        if args.json: print(json.dumps({'ok': not failed, 'report': report, 'warnings': fg.warnings}, indent=2))
        else:
            for k, issues in report.items():
                for i in issues: print(f'ERROR: {k}: {i}')
                for w in fg.warnings.get(k, []): print(f'WARN: {k}: {w}')
                if not issues: print(f'OK: {k}')
        return EXIT_ISSUES if failed else EXIT_OK
    if args.cmd == 'stats':
        out = {lvl: {'model_id': g.doc['model_id'], 'instances': len(g.instances), 'relationships': len(g.relationships)} for lvl, g in sorted(fg.levels.items())}
        out['mappings'] = {'documents': len(fg.mapping_docs), 'approved_edges': len(fg.edges())}
        print(json.dumps(out, indent=2)); return EXIT_OK
    if args.cmd == 'trace' and getattr(args, 'projection', None):
        from sdem import aid as _aid
        pkg = _aid.read(args.projection)
        for d in (['down', 'up'] if args.direction == 'both' else [args.direction]):
            print('DOWNSTREAM (depends on):' if d == 'down' else 'UPSTREAM (depended on by):')
            print('\n'.join(_aid.trace(reader, pkg, args.entity, d))); print()
        print('PROJECTED = made by AID for planning, not real data.')
        return EXIT_OK
    if args.cmd == 'trace':
        args.direction = {'downstream': 'down', 'upstream': 'up', 'all': 'both'}.get(args.direction, args.direction)
    if args.cmd == 'trace' and re.fullmatch(r'[Aa][1-4]', args.entity) and fg.instance(args.entity) is None:   # TR-L01: a whole layer
        lvl = args.entity.upper(); to = args.to.upper() if args.to else None
        results = [level_trace(fg, lvl, d, statuses, getattr(args, 'follow_composition', False), to) for d in (['down', 'up'] if args.direction == 'both' else [args.direction])]
        if args.csv: write_level_csv(results, args.csv)
        if args.json: print(json.dumps(results, indent=2)); return EXIT_OK
        for res in results:
            if args.tree:
                print('DOWNSTREAM (depends on):' if res['direction'] == 'down' else 'UPSTREAM (depended on by):')
                for rid in sorted({c['start']['id'] for c in res['chains']}):
                    print(render_trace(fg.trace(rid, res['direction'], statuses, getattr(args, 'follow_composition', False)), res['direction'])); print()
            print(render_level_trace(res, args.only_gaps)); print()
        if args.csv: print(f'chains written to {args.csv}')
        return EXIT_OK
    if fg.instance(args.entity) is None and not any(args.entity in (e['source']['id'], e['target']['id']) for e in fg.edges(statuses)):
        print(f'ERROR: {args.entity!r} is not an instance in any loaded level model or mapping', file=sys.stderr); return EXIT_ISSUES
    if args.cmd == 'trace':
        dirs = ['down', 'up'] if args.direction == 'both' else [args.direction]
        trees = {d: fg.trace(args.entity, d, statuses, getattr(args, 'follow_composition', False)) for d in dirs}
        if args.json: print(json.dumps(trees, indent=2))
        else:
            for d, t in trees.items():
                print('DOWNSTREAM (depends on):' if d == 'down' else 'UPSTREAM (depended on by):')
                print(render_trace(t, d) if t['children'] else f"{args.entity}  (no {d}stream mappings)"); print()
            used = []   # the approved connections the trace followed (MAP-…), as recorded in mappings.json
            def walk(n):
                for c in n['children']:
                    for mid in [c['via']['mapping_id']] + c['via'].get('also', []):
                        if mid not in used and mid != 'composition': used.append(mid)
                    walk(c['node'])
            for t in trees.values(): walk(t)
            if used:
                recs = {m.get('mapping_id'): m for doc in fg.mapping_docs for m in doc.get('mappings', [])}
                print('CONNECTIONS FOLLOWED (each approved connection, by its id in mappings.json — the code in brackets above):')
                for mid in used:
                    m = recs.get(mid, {})
                    ev = '; '.join(e for e in m.get('evidence', []) if not str(e).startswith('engine_rationale:')) or '—'
                    print(f"  {mid}  {m.get('source', {}).get('id', '?')} -{m.get('relationship', '?')}-> {m.get('target', {}).get('id', '?')}: "
                          f"approved by {m.get('reviewer_id', '?')} on {m.get('approved_at', '?')}; evidence {ev}")
                print()
            if fg.design_records:  # LD-R04: where the entity is documented, and what did not fit there
                from .designs import for_entity
                docs, gaps = for_entity(fg.design_records, args.entity)
                if docs:
                    print('DOCUMENTED IN (design records):')
                    for dd in docs:
                        n = sum(1 for g in gaps if g['status'] == 'open' and (g['document'] == dd['id'] or args.entity in g['about']))
                        print(f"  {dd['id']}  {dd['title']}  ({dd.get('modified') or 'no date'})" + (f" — {n} open gap(s)" if n else ''))
                    print(f"  details: sdem designs --entity {args.entity} …"); print()
        # consistent with sdem-trace: an empty result (no arrows in the chosen statuses) is exit 1
        return EXIT_OK if any(t['children'] for t in trees.values()) else EXIT_ISSUES
    if args.cmd == 'impact':
        result = fg.impact(args.entity, args.change, statuses)
        if getattr(args, 'report', None):
            Path(args.report).write_text(impact_report(result), encoding='utf-8'); print(f'wrote {args.report}', file=sys.stderr)
        if args.json: print(json.dumps(result, indent=2))
        else:
            print(f"IMPACT of '{args.change}' on {result['changed']}: {result['reason']}\n")
            width = max(len(r['id']) for r in result['instances'])
            for r in result['instances']:
                print(f"  {r['classification']:<24} {r['level'] or '?'}  {r['id']:<{width}}  {r['name'] or ''}  via {', '.join(r['via']) or '-'}")
            if result['mappings_to_supersede']:
                print(f"\n  mappings to supersede: {', '.join(result['mappings_to_supersede'])}")
            print("\n  Classification is structural; an architect confirms before any design changes.")
        return EXIT_OK


def _build(args, _store):
    if args.check:
        ok, detail = _store.check_current(args.paths, args.out)
        if args.json: print(json.dumps({'graph': args.out, 'current': ok, 'detail': detail}, indent=2)); return EXIT_OK if ok else EXIT_ISSUES
        print(f"graph store {args.out}: {'up to date' if ok else 'STALE or failing: ' + ', '.join(detail[:5])}")
        return EXIT_OK if ok else EXIT_ISSUES
    e = _store.build(args.paths, args.out)
    if args.json:   # errors in the result, not as lines (AG-01)
        print(json.dumps({'graph': args.out, **e, 'next': f'sdem trace <id> --graph {args.out}' if e['result'] == 'accepted' else 'fix the errors and build again'}, indent=2, ensure_ascii=False))
        return EXIT_OK if e['result'] == 'accepted' else EXIT_ISSUES
    for err in e['errors']: print(f'ERROR: {err}')
    for w in e['warnings']: print(f'WARN: {w}')
    if e['result'] == 'accepted':
        print(f"build {e['build']} accepted: " + ', '.join(f"{o['file']} ({o['nodes']} nodes, {o['edges']} edges)" for o in e['outputs']))
        return EXIT_OK
    print(f"build {e['build']} rejected: {len(e['errors'])} error(s); the previous graph store is unchanged")
    return EXIT_ISSUES


def _query(args, reader):
    if args.unmapped:
        rows = reader.unmapped(args.unmapped); cols = ('id', 'type', 'name', 'expected')
    elif args.neighbours:
        rows = reader.neighbours(args.neighbours, args.kind, args.direction); cols = ('direction', 'relation', 'id')
    else:
        where = {}
        for w in args.where:
            if '=' not in w: print(f'ERROR: --where needs ATTR=VALUE, got {w!r}', file=sys.stderr); return EXIT_USAGE
            k, v = w.split('=', 1); where[k] = v
        rows = reader.nodes(level=args.level, type=args.type, where=where or None); cols = ('id', 'type', 'name', 'version')
    if args.json: print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows: print('  '.join(', '.join(r[c]) if isinstance(r.get(c), list) else str(r.get(c, '')) for c in cols))
        print(f'{len(rows)} record(s)')
    return EXIT_OK if rows else EXIT_ISSUES


if __name__ == '__main__':
    raise SystemExit(main())
