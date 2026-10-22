"""SDMM graphs: one LevelGraph per design model (A1-A4) and a FederatedGraph that joins them to the mappings.

Structural logic only. A level graph holds an institution's instances and within-level relationships;
the federated graph resolves mapping endpoints against them, traces chains with names, and classifies
impact by rule. Nothing here decides whether a mapping is right.
"""
from pathlib import Path
import argparse, json, sys
from sdmm.metamodel import Metamodel
from sdmm.validate import check_schema, load_registry, load_schema, normalize_type, validate, ROOT
from sdmm.trace import load_edges, walk, paths as tree_paths

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

    @classmethod
    def load(cls, path, metamodel=None):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')), metamodel or Metamodel.load())

    def validate(self):
        issues = check_schema(self.doc, json.loads(LEVEL_SCHEMA.read_text(encoding='utf-8')))
        if issues:
            return issues
        if self.doc.get('metamodel_version') and self.doc['metamodel_version'] != self.mm.version:
            issues.append(f"metamodel_version {self.doc['metamodel_version']!r} does not match loaded metamodel {self.mm.version!r}")
        seen = set()
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
        return issues

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

    @classmethod
    def load(cls, paths, metamodel=None, registry=None):
        """Classify each file by content: level exports have 'level' + 'instances'; mapping docs have 'mappings'."""
        mm = metamodel or Metamodel.load()
        levels, docs = [], []
        for p in paths:
            d = json.loads(Path(p).read_text(encoding='utf-8'))
            if 'mappings' in d: docs.append(d)
            elif 'instances' in d and 'level' in d: levels.append(LevelGraph(d, mm))
            else: raise ValueError(f'{p}: neither a level export nor a mapping document')
        return cls(levels, docs, mm, registry)

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
        report = {}
        for lvl, g in sorted(self.levels.items()):
            report[f'level {lvl} ({g.doc["model_id"]})'] = g.validate()
        for n, d in enumerate(self.mapping_docs, 1):
            warnings = []
            issues = validate(d, self.registry, load_schema(), entity_resolver=self, warnings=warnings, metamodel=self.mm)
            report[f'mappings #{n}'] = issues
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
        """Within-level composition as virtual hops: downstream climbs to the whole that composes the instance
        (a module's traceability continues through its application); upstream descends to the parts."""
        hops = []
        for g in self.levels.values():
            for r in g.relationships:
                if r['kind'] != 'composition': continue
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


def render_trace(tree, direction):
    arrow = '-' if direction == 'down' else '<-'
    def label(n):
        name = f" {n['name']!r}" if n.get('name') else ''
        t = n.get('concrete_type') or n.get('type') or '?'
        mark = '' if n.get('resolved') else '  (unresolved)'
        if n.get('lifecycle_status') == 'planned': mark += '  [DESIGN — planned, not observed]'
        return f"{n['id']}{name}  [{t}]" + mark
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
    parser = argparse.ArgumentParser(prog='sdmm-graph', description='Federated graph over A1-A4 level exports and mapping documents.')
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('check', 'trace', 'impact', 'stats'):
        sp = sub.add_parser(name)
        if name in ('trace', 'impact'):
            sp.add_argument('entity', help='instance id to start from')
        sp.add_argument('paths', nargs='+', help='level exports and mapping documents, any order')
        sp.add_argument('--status', default='approved', help='mapping statuses to treat as arrows')
        sp.add_argument('--json', action='store_true')
        if name == 'trace':
            sp.add_argument('--direction', choices=['down', 'up', 'both'], default='both')
            sp.add_argument('--follow-composition', action='store_true', help='continue a chain through within-level composition (part -> whole downstream, whole -> parts upstream)')
        if name == 'impact':
            sp.add_argument('--change', choices=sorted(IMPACT_RULES), required=True)
    args = parser.parse_args(argv)
    try:
        fg = FederatedGraph.load(args.paths)
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return EXIT_USAGE
    statuses = tuple(s.strip() for s in args.status.split(',') if s.strip())
    if args.cmd == 'check':
        report = fg.check()
        failed = any(report.values())
        if args.json: print(json.dumps({'ok': not failed, 'report': report}, indent=2))
        else:
            for k, issues in report.items():
                for i in issues: print(f'ERROR: {k}: {i}')
                if not issues: print(f'OK: {k}')
        return EXIT_ISSUES if failed else EXIT_OK
    if args.cmd == 'stats':
        out = {lvl: {'model_id': g.doc['model_id'], 'instances': len(g.instances), 'relationships': len(g.relationships)} for lvl, g in sorted(fg.levels.items())}
        out['mappings'] = {'documents': len(fg.mapping_docs), 'approved_edges': len(fg.edges())}
        print(json.dumps(out, indent=2)); return EXIT_OK
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
        # consistent with sdmm-trace: an empty result (no arrows in the chosen statuses) is exit 1
        return EXIT_OK if any(t['children'] for t in trees.values()) else EXIT_ISSUES
    if args.cmd == 'impact':
        result = fg.impact(args.entity, args.change, statuses)
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


if __name__ == '__main__':
    raise SystemExit(main())
