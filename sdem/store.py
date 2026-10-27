"""Local JSON graph store (docs/graph-store-spec.md): the four local knowledge graphs and the federated graph of
approved links, persisted as JSON Graph Format v2 files, plus a load record; and the graph access layer every
reader uses.

A store is built only from inputs that pass every `sdem-graph check` rule; a failed build leaves the last good
store untouched (GS-B-02). Output is deterministic (GS-F-04): same inputs, byte-identical graph files; records and links keep the order of
the architecture dataset and registry, so every reader sees them in the same order as the source.
"""
import datetime, hashlib, json, os, shutil, tempfile
from pathlib import Path

from .graph import FederatedGraph, LevelGraph
from .metamodel import Metamodel
from .paths import DATA_ROOT

STORE_VERSION = '1.0'
LEVEL_FILES = {'A1': 'a1-business.graph.json', 'A2': 'a2-service-domain.graph.json', 'A3': 'a3-application.graph.json', 'A4': 'a4-technology.graph.json'}
FEDERATED = 'federated.graph.json'
LOAD_RECORD = 'load-record.json'
CORE = ('lifecycle_status', 'canonical_id', 'description', 'definition_uri')
EXPORT_HEADER = ('level', 'model_id', 'model_version', 'metamodel_version', 'source_system')


class StoreError(Exception):
    pass


def _dump(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + '\n'  # input order kept: deterministic, and readers see the architecture dataset's order


def _sha(text):
    return hashlib.sha256(text.encode('utf-8') if isinstance(text, str) else text).hexdigest()


def key(level, iid, version):
    """Store-wide node key (GD-02): `<level>:<id>@<version>`."""
    return f'{level}:{iid}@{version}'


def _row(mm, level, stype, kind, ttype):
    for c in mm.relationships['constraints']:
        if c['level'] == level and c['kind'] == kind and mm.is_a(stype, c['source_type']) and mm.is_a(ttype, c['target_type']):
            return c['id']
    return 'association' if kind == 'association' else None


# ---------------------------------------------------------------- architecture dataset / registry  ->  JGF

def local_graph(doc, mm, export_sha):
    lvl = doc['level']; nodes = {}; latest = {}
    for i in doc['instances']:
        meta = {'level': lvl, 'type': i['type'], 'id': i['id'], 'version': i['version']}
        meta.update({k: i[k] for k in CORE if k in i})
        if 'attributes' in i: meta['attributes'] = i['attributes']
        nodes[key(lvl, i['id'], i['version'])] = {'label': i['name'], 'metadata': meta}
        latest[i['id']] = i  # relationships name instances by id; the architecture dataset's last version of an id is the one linked
    edges, seen = [], {}
    for r in doc.get('relationships', []):
        s, t = latest[r['source']], latest[r['target']]
        base = f"{lvl}:{r['source']}-{r['kind']}-{r['target']}"; seen[base] = seen.get(base, 0) + 1
        e = {'id': base if seen[base] == 1 else f'{base}#{seen[base]}', 'source': key(lvl, s['id'], s['version']), 'target': key(lvl, t['id'], t['version']),
             'relation': r['kind'], 'metadata': {'scope': 'within-level', 'row': _row(mm, lvl, s['type'], r['kind'], t['type'])}}
        if r.get('name'): e['label'] = r['name']
        edges.append(e)
    meta = {'sdem_store_version': STORE_VERSION, 'export_sha256': export_sha}
    meta.update({k: doc[k] for k in EXPORT_HEADER if k in doc})
    return {'graph': {'id': f"sdem:{doc['model_id']}", 'type': 'sdem.local', 'label': f"{lvl} local knowledge graph ({doc['model_id']})",
                      'directed': True, 'metadata': meta, 'nodes': nodes, 'edges': edges}}


def federated_graph(fg, registries, statuses=('approved',)):
    """registries: [(file name, document, sha256)]."""
    nodes, edges, heads = {}, [], []
    for name, doc, sha in registries:
        heads.append({'file': name, 'sha256': sha, **{k: v for k, v in doc.items() if k != 'mappings'}})
        for m in doc.get('mappings', []):
            if m.get('status') not in statuses: continue
            ends = []
            for side in ('source', 'target'):
                ref = m[side]; inst = fg.resolve_entity(ref['id'], ref['type'], ref['version'])
                if inst is None: raise StoreError(f"{name}: {m['mapping_id']} {side} {ref['id']}@{ref['version']} does not resolve")
                lvl = fg.mm.level(inst['type']); k = key(lvl, inst['id'], inst['version']); ends.append(k)
                nodes[k] = {'label': inst['name'], 'metadata': {'level': lvl, 'type': inst['type'], 'id': inst['id'], 'version': inst['version'], 'stub': True, 'graph': LEVEL_FILES[lvl]}}
            meta = {'scope': 'cross-level', 'registry': name, 'source_ref': m['source'], 'target_ref': m['target']}
            meta.update({k: v for k, v in m.items() if k not in ('mapping_id', 'relationship', 'source', 'target')})
            edges.append({'id': m['mapping_id'], 'source': ends[0], 'target': ends[1], 'relation': m['relationship'], 'metadata': meta})
    levels = {lvl: g.doc['model_version'] for lvl, g in sorted(fg.levels.items())}
    return {'graph': {'id': 'sdem:federated', 'type': 'sdem.federated', 'label': 'Federated knowledge graph (approved cross-level links)', 'directed': True,
                      'metadata': {'sdem_store_version': STORE_VERSION, 'metamodel_version': fg.mm.version, 'levels': levels, 'registries': heads, 'statuses': list(statuses)},
                      'nodes': nodes, 'edges': edges}}


# ---------------------------------------------------------------- JGF  ->  architecture dataset / registry documents

def _export_doc(g):
    meta = g['metadata']; doc = {k: meta[k] for k in EXPORT_HEADER if k in meta}
    by_key, inst = {}, []
    for k, n in g['nodes'].items():
        m = n['metadata']; i = {'id': m['id'], 'type': m['type'], 'version': m['version'], 'name': n['label']}
        i.update({c: m[c] for c in CORE if c in m})
        if 'attributes' in m: i['attributes'] = m['attributes']
        inst.append(i); by_key[k] = m['id']
    rels = []
    for e in g['edges']:
        r = {'source': by_key[e['source']], 'kind': e['relation'], 'target': by_key[e['target']]}
        if 'label' in e: r['name'] = e['label']
        rels.append(r)
    doc['instances'] = inst; doc['relationships'] = rels
    return doc


def _registry_docs(g):
    docs = {}
    for h in g['metadata']['registries']:
        docs[h['file']] = {k: v for k, v in h.items() if k not in ('file', 'sha256')}; docs[h['file']]['mappings'] = []
    for e in g['edges']:
        m = dict(e['metadata']); reg = m.pop('registry'); m.pop('scope')
        rec = {'mapping_id': e['id'], 'source': m.pop('source_ref'), 'relationship': e['relation'], 'target': m.pop('target_ref')}
        rec.update(m); docs[reg]['mappings'].append(rec)
    return list(docs.values())


# ---------------------------------------------------------------- build

def _load_record(out):
    p = Path(out) / LOAD_RECORD
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'store': Path(out).name, 'entries': []}


def stale_inputs(store):
    """T3: the inputs of the store's last accepted build that have changed since (checksum differs) — the stored graph is then
    out of date. Inputs that cannot be found from here (moved, or a relative path from another folder) are not judged."""
    rec = _load_record(store)
    last = next((e for e in reversed(rec['entries']) if e.get('result') == 'accepted'), None)
    out = []
    for i in (last or {}).get('inputs', []):
        p = Path(i['path']) if isinstance(i, dict) else None
        if p and p.exists() and _sha(p.read_text(encoding='utf-8')) != i.get('sha256'): out.append(str(p))
    return (last or {}).get('build'), out


def _write_record(out, rec):
    Path(out).mkdir(parents=True, exist_ok=True); (Path(out) / LOAD_RECORD).write_text(_dump(rec), encoding='utf-8')


def render(paths, mm=None):
    """Check the inputs and return (files {name: text}, report). files is None when any check fails."""
    mm = mm or Metamodel.load()
    texts = {str(p): Path(p).read_text(encoding='utf-8') for p in paths}
    inputs, levels, registries = [], [], []
    for p, t in texts.items():
        d = json.loads(t); sha = _sha(t)
        if 'mappings' in d:
            registries.append((Path(p).name, d, sha)); inputs.append({'path': p, 'kind': 'registry', 'registry_version': d.get('registry_version'), 'sha256': sha})
        elif 'instances' in d and 'level' in d:
            levels.append((d, sha)); inputs.append({'path': p, 'kind': 'export', 'level': d['level'], 'model_id': d.get('model_id'), 'model_version': d.get('model_version'), 'sha256': sha})
        else:
            raise StoreError(f'{p}: neither an architecture dataset nor a relationship registry')
    if len({d['level'] for d, _ in levels}) != len(levels): raise StoreError('more than one architecture dataset for a level')
    from .metamodel import is_projection_dataset
    proj = [d['model_id'] for d, _ in levels if is_projection_dataset(d)]
    if proj: raise StoreError(f"{', '.join(proj)}: a projected or target design cannot be loaded into a graph store of real data (CTL-16)")
    cand = [d['model_id'] for d, _ in levels if d.get('source_system') == 'CONFLUENCE-EXTRACT']
    if cand: raise StoreError(f"{', '.join(cand)}: unreviewed candidates from sdem transform cannot be built into a graph store — review them, then `sdem load` (CTL-23)")
    names = [n for n, _, _ in registries]
    if len(set(names)) != len(names): raise StoreError('two registries share a file name')
    fg = FederatedGraph([LevelGraph(d, mm) for d, _ in levels], [d for _, d, _ in registries], mm)
    report = fg.check()
    errors = [f'{k}: {i}' for k, v in report.items() for i in v]
    warnings = [f'{k}: {w}' for k, v in getattr(fg, 'warnings', {}).items() for w in v]
    result = {'inputs': inputs, 'metamodel_version': mm.version, 'errors': errors, 'warnings': warnings}
    if errors: return None, result
    files = {LEVEL_FILES[d['level']]: _dump(local_graph(d, mm, sha)) for d, sha in levels}
    try:
        files[FEDERATED] = _dump(federated_graph(fg, registries))
    except StoreError as exc:
        result['errors'].append(str(exc)); return None, result
    return files, result


def build(paths, out, mm=None, now=None):
    """Build the store at `out`. Returns the load-record entry; raises nothing on a failed check (GS-B-02)."""
    out = Path(out); rec = _load_record(out)
    entry = {'build': (rec['entries'][-1]['build'] + 1) if rec['entries'] else 1, 'at': now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()}
    try:
        files, result = render(paths, mm)
    except (StoreError, OSError, ValueError, KeyError) as exc:
        files, result = None, {'inputs': [str(p) for p in paths], 'errors': [str(exc)], 'warnings': []}
    entry.update(result)
    if files is None:
        entry['result'] = 'rejected'
    else:
        tmp = Path(tempfile.mkdtemp(prefix='.sdem-store-', dir=out.parent if out.parent.exists() else None))
        try:
            for name, text in files.items(): (tmp / name).write_text(text, encoding='utf-8')
            out.mkdir(parents=True, exist_ok=True)
            for name in list(LEVEL_FILES.values()) + [FEDERATED]:
                if name not in files and (out / name).exists(): (out / name).unlink()
            for name in files: os.replace(tmp / name, out / name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        entry['result'] = 'accepted'
        entry['outputs'] = [{'file': n, 'sha256': _sha(t), 'nodes': len(json.loads(t)['graph']['nodes']), 'edges': len(json.loads(t)['graph']['edges'])} for n, t in sorted(files.items())]
    rec['entries'].append(entry); _write_record(out, rec)
    return entry


def check_current(paths, out, mm=None):
    """GS-B-05: True when the stored graph files equal a fresh in-memory build."""
    files, result = render(paths, mm)
    if files is None: return False, result['errors']
    stale = [n for n, t in files.items() if not (Path(out) / n).exists() or (Path(out) / n).read_text(encoding='utf-8') != t]
    stale += [n for n in list(LEVEL_FILES.values()) + [FEDERATED] if n not in files and (Path(out) / n).exists()]
    return not stale, stale


def baseline(store, name):
    """GS-R-03: freeze the current graph files and the latest accepted load-record entry under baselines/<name>/."""
    store = Path(store); dest = store / 'baselines' / name
    if dest.exists(): raise StoreError(f'baseline {name!r} already exists')
    rec = _load_record(store); acc = [e for e in rec['entries'] if e['result'] == 'accepted']
    if not acc: raise StoreError('no accepted build to baseline')
    dest.mkdir(parents=True)
    for n in list(LEVEL_FILES.values()) + [FEDERATED]:
        if (store / n).exists(): shutil.copy2(store / n, dest / n)
    _write_record(dest, {'store': f'{store.name}/baselines/{name}', 'baseline_of': store.name, 'entries': [acc[-1]]})
    return dest


# ---------------------------------------------------------------- graph access layer (GS-A-01 … 03)

class GraphReader:
    """One read interface over a federated graph, whether it came from the store or from architecture datasets."""

    def __init__(self, fg, origin, record=None):
        self.fg, self.mm, self.origin, self._record = fg, fg.mm, origin, record

    @classmethod
    def from_store(cls, store, mm=None):
        store = Path(store); mm = mm or Metamodel.load()
        if not (store / FEDERATED).exists(): raise StoreError(f'{store}: not a graph store (no {FEDERATED})')
        levels = []
        for lvl, name in LEVEL_FILES.items():
            if (store / name).exists():
                levels.append(LevelGraph(_export_doc(json.loads((store / name).read_text(encoding='utf-8'))['graph']), mm))
        fed = json.loads((store / FEDERATED).read_text(encoding='utf-8'))['graph']
        return cls(FederatedGraph(levels, _registry_docs(fed), mm), 'store', _load_record(store))

    @classmethod
    def from_exports(cls, paths, mm=None):
        return cls(FederatedGraph.load(paths, mm or Metamodel.load()), 'architecture datasets')

    def check_store(self, store):
        """GS-F-02/03 and resolution for a stored graph: file shapes, the local graphs, every stored link resolving.
        Registry history (supersession chains) was validated when the store was built and is not in the store."""
        from .validate import check_schema
        schema = json.loads((DATA_ROOT / 'schema' / 'graph-store.schema.json').read_text(encoding='utf-8'))
        report = {}
        for name in list(LEVEL_FILES.values()) + [FEDERATED]:
            p = Path(store) / name
            if not p.exists(): continue
            g = json.loads(p.read_text(encoding='utf-8')); issues = check_schema(g, schema)
            issues += [f'node {k}: {i}' for k, n in g['graph']['nodes'].items() for i in check_schema(n, schema['$defs']['node'], schema)]
            keys = set(g['graph']['nodes'])
            issues += [f"edge {e['id']}: end not a node of this file" for e in g['graph']['edges'] if e['source'] not in keys or e['target'] not in keys]
            report[f'file {name}'] = issues
        for lvl, g in sorted(self.fg.levels.items()):
            report[f'level {lvl} ({g.doc["model_id"]})'] = g.validate()
        report['federated links'] = [f"{e['mapping_id']}: {side} {e[side]['id']}@{e[side]['version']} does not resolve"
                                     for e in self.fg.edges() for side in ('source', 'target') if self.fg.resolve_entity(e[side]['id'], e[side]['type'], e[side]['version']) is None]
        self.fg.warnings = {k: g.warnings for k, g in ((f'level {l} ({g.doc["model_id"]})', g) for l, g in sorted(self.fg.levels.items())) if g.warnings}
        return report

    # -- provenance
    def levels(self):
        return {lvl: g.doc['model_version'] for lvl, g in sorted(self.fg.levels.items())}

    def baseline(self):
        acc = [e for e in (self._record or {}).get('entries', []) if e.get('result') == 'accepted']
        return {'origin': self.origin, 'build': acc[-1]['build'] if acc else None, 'built_at': acc[-1]['at'] if acc else None, 'levels': self.levels()}

    # -- nodes
    def _node(self, lvl, i):
        return {'key': key(lvl, i['id'], i['version']), 'level': lvl, **i}

    def node(self, level, iid, version=None):
        g = self.fg.levels.get(level)
        vs = (g.by_id.get(iid) if g else None) or []
        if version is not None: vs = [i for i in vs if i['version'] == version]
        return self._node(level, vs[-1]) if vs else None

    def nodes(self, level=None, type=None, include_subtypes=True, where=None):
        out = []
        for lvl, g in sorted(self.fg.levels.items()):
            if level and lvl != level: continue
            for i in g.doc['instances']:
                if type and not (self.mm.is_a(i['type'], type) if include_subtypes else i['type'] == type): continue
                if where and not all(_matches(i, k, v) for k, v in where.items()): continue
                out.append(self._node(lvl, i))
        return out

    # -- edges
    def edges(self, scope='cross-level', source=None, target=None, relation=None, statuses=('approved',)):
        if scope == 'within-level':
            out = [{'level': lvl, **r} for lvl, g in sorted(self.fg.levels.items()) for r in g.relationships]
        else:
            out = self.fg.edges(statuses)
        sid = lambda e, s: e[s]['id'] if isinstance(e[s], dict) else e[s]
        return [e for e in out if (source is None or sid(e, 'source') == source) and (target is None or sid(e, 'target') == target)
                and (relation is None or e.get('kind', e.get('relationship')) == relation)]

    def neighbours(self, iid, relation=None, direction='both'):
        out = []
        for e in self.edges('within-level', relation=relation):
            if direction in ('out', 'both') and e['source'] == iid: out.append({'direction': 'out', 'relation': e['kind'], 'id': e['target']})
            if direction in ('in', 'both') and e['target'] == iid: out.append({'direction': 'in', 'relation': e['kind'], 'id': e['source']})
        return out

    def links(self, iid, direction='both'):
        return [e for e in self.fg.edges() if (direction in ('out', 'both') and e['source']['id'] == iid) or (direction in ('in', 'both') and e['target']['id'] == iid)]

    def is_a(self, t, ancestor):
        return self.mm.is_a(t, ancestor)

    def unmapped(self, level):
        """GS-Q-04: nodes of `level` with no approved cross-level link of a type the catalogue expects for them."""
        types = json.loads((DATA_ROOT / 'schema' / 'relationship-types.json').read_text(encoding='utf-8'))['relationships']
        edges = self.fg.edges(); out = []
        for n in self.nodes(level=level):
            expected = sorted({(x['relationship'], 'source' if self.mm.is_a(n['type'], x['source_type']) else 'target') for x in types
                               if self.mm.is_a(n['type'], x['source_type']) or self.mm.is_a(n['type'], x['target_type'])})
            missing = [rel for rel, side in expected if not any(e['relationship'] == rel and e[side]['id'] == n['id'] for e in edges)]
            if expected and len(missing) == len(expected):
                out.append({**n, 'expected': [rel for rel, _ in expected]})
        return out


def _matches(inst, k, v):
    val = inst.get(k, (inst.get('attributes') or {}).get(k))
    if isinstance(val, list): return v in [str(x) for x in val]
    if isinstance(val, bool): return v.lower() == str(val).lower()
    return val is not None and str(val) == v
