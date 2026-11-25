"""Architecture Relationship Inference Engine: the interface and a baseline, for the rule-based engine (sdem/rules_engine.py, v0.10).

An engine reads a FederatedGraph and returns *proposed* mapping records. It never writes approved
records; everything it returns goes through sdem validate and an architect. The baseline here exists
to exercise the evaluation harness; it is not the rule-based engine specified in docs/design/relationship-rules-spec.md.
"""
from .identity import for_file as _for_file  # DL-11: what a design's file stores (docs/design/sdem-data-layer-spec.md)
from pathlib import Path
import argparse, json, re, sys
from typing import Protocol
from sdem.graph import FederatedGraph
from sdem.validate import load_registry

STOP = {'the', 'and', 'of', 'for', 'a', 'an', 'to', 'in', 'on', 'synthetic', 'selection', 'stand', 'bian'}


class RelationshipInferenceEngine(Protocol):
    """An engine reads a graph through the access layer (sdem/store.py GraphReader) and returns
    {'proposals': [...], 'candidates': [...], 'log': [...], 'design': [...]} — proposals only ever `proposed`."""
    name: str
    def infer(self, reader, case=None) -> dict: ...


def proposal(mapping_id, src, rel, tgt, confidence, rationale, engine, baseline_id='ENGINE-RUN'):
    """Shape every engine output the same way: a valid record with status proposed."""
    def ref(i):
        r = {'id': i['id'], 'type': i['type'], 'version': i['version']}
        if i.get('canonical_id'): r['canonical_id'] = i['canonical_id']   # carried from the architecture dataset, never invented
        return r
    return {'mapping_id': mapping_id, 'source': ref(src), 'relationship': rel, 'target': ref(tgt),
            'status': 'proposed', 'confidence': round(confidence, 2),
            'evidence': [f'engine_rationale:{rationale}'],
            'rationale': rationale, 'baseline_id': baseline_id, 'created_by': engine}


def _words(*texts):
    return {w for t in texts if t for w in re.findall(r'[a-z]+', t.lower()) if len(w) > 2 and w not in STOP}



class NameOverlapBaseline:
    """Proposes an arrow for every registry rule where the two instances' names/descriptions share enough words
    (overlap coefficient = shared / smaller vocabulary).

    Deterministic, explainable, and deliberately naive: it is the floor an engine must beat.
    """
    name = 'baseline-name-overlap/0.5'

    def __init__(self, threshold=0.2):
        self.threshold = threshold

    def propose(self, graph):
        registry = load_registry()
        mm = graph.mm
        out, n = [], 0
        instances = [i for g in graph.levels.values() for i in g.doc.get('instances', [])]
        for rule in registry['relationships']:
            srcs = [i for i in instances if mm.is_a(i['type'], rule['source_type'])]
            tgts = [i for i in instances if mm.is_a(i['type'], rule['target_type'])]
            for s in srcs:
                ws = _words(s['name'], s.get('description'))
                for t in tgts:
                    wt = _words(t['name'], t.get('description'))
                    if not ws or not wt:
                        continue
                    shared = ws & wt
                    score = len(shared) / min(len(ws), len(wt))   # overlap coefficient
                    if score >= self.threshold:
                        n += 1
                        out.append(proposal(f'PROP-{n:04d}', s, rule['relationship'], t, min(0.95, 0.4 + score),
                                            f"shared terms {sorted(shared)} between '{s['name']}' and '{t['name']}'", self.name))
        return out

    def infer(self, reader, case=None):
        """Harness interface (sdem/acceptance.py): proposals only, links already approved left out."""
        approved = {(e['source']['id'], e['relationship'], e['target']['id']) for e in reader.fg.edges()}
        return {'proposals': [m for m in self.propose(reader.fg) if (m['source']['id'], m['relationship'], m['target']['id']) not in approved]}


def _rules_engine():
    from sdem.rules_engine import RulesEngine
    return RulesEngine()


ENGINES = {'baseline': NameOverlapBaseline, 'rules': _rules_engine}


def propose(reader, ext_workspace=None, engine='rules', threshold=0.2, options=None):
    """What `sdem link` proposes — (engine, result, extension report): the rules engine's proposals, with what the workspace's extensions
    propose (MX-51). Where an installed extension provides a built-in one's steps (BIAN, MX-53) the engine runs the core's, the extension
    the rest, and every proposal and candidate is numbered in the whole run's order, as the extension ran it with the core's — the same ids
    the engine alone gave (P-RUN-…). Every command that lists proposals goes through here (sdem link, the dashboard), so their ids agree."""
    core_only = False
    if ext_workspace and engine == 'rules':
        from sdem.ext_infer import provides_builtin
        core_only = provides_builtin('link')
    eng = ENGINES[engine](threshold) if engine == 'baseline' else (RE_CORE() if core_only else ENGINES[engine]())
    result = eng.infer(reader, {'id': 'RUN', **({'options': options} if options else {})})
    report = []
    if ext_workspace:
        import datetime
        from sdem.ext_infer import for_link
        props, report = for_link(ext_workspace, datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), options)
        have = {_key(p) for p in result['proposals']}
        theirs = [p for p in props if _key(p) not in have]
        ctheirs = [x for e in report for x in e.pop('_candidates', [])]
        for e in report:
            if e.get('_design'): result['design'] = list(result.get('design') or []) + e['_design']
            e.pop('_design', None)
        order = next((e['_order'] for e in report if e.get('_order')), None)
        corder = next((e['_corder'] for e in report if e.get('_corder')), None)
        log = next((e['_log'] for e in report if e.get('_order') and e.get('_log')), None)
        for e in report: e.pop('_order', None); e.pop('_corder', None); e.pop('_log', None)
        if order and log is not None: result['log'] = log   # MX-53: the whole run's log, as its order — the engine alone's, every attempt
        result['proposals'] = _numbered(result['proposals'], theirs, order, 'RUN-X')
        result['candidates'] = _numbered(result.get('candidates', []), ctheirs, corder, 'C-RUN-X')
    return eng, result, report


def _files_workspace(paths, folder):
    """The datasets and registry given as files, as a workspace an extension can read (MX-51) — None when an installed extension gives no
    built-in one's rules (nothing to ask for). The registry (a document with "mappings") is its mappings.json; the rest keep their names."""
    from sdem.ext_infer import provides_builtin
    if not provides_builtin('link'): return None
    import shutil
    have_reg = False
    for p in map(Path, paths):
        try: d = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError): continue
        if isinstance(d, dict) and 'mappings' in d: shutil.copy(p, folder / 'mappings.json'); have_reg = True
        else: shutil.copy(p, folder / p.name)
    if not have_reg: (folder / 'mappings.json').write_text(json.dumps({'registry_version': load_registry()['$schema_version'], 'mappings': []}), encoding='utf-8')
    return str(folder)


def _key(p): return (p['source']['id'], p['relationship'], p['target']['id'])


def _numbered(own, theirs, order, prefix):
    """MX-53: the engine's items (`own`) with the extensions' (`theirs`). With the whole run's order (an extension that ran the core's
    rules with its own): every item it holds in that order, with its id; the rest after. Without: the engine's as numbered, then theirs.
    What no order holds is numbered prefix### after the items before it."""
    if order:
        pos = {(s, r, t): (i, pid) for i, (s, r, t, pid) in enumerate(order)}
        items = own + theirs
        out = [{**p, 'mapping_id': pos[_key(p)][1]} if 'mapping_id' in p else p for p in sorted((p for p in items if _key(p) in pos), key=lambda p: pos[_key(p)][0])]
        rest = [p for p in items if _key(p) not in pos]
    else:
        out, rest = list(own), list(theirs)
    n = len(out)
    for p in rest:
        n += 1
        out.append({**p, 'mapping_id': f'{prefix}{n:03d}'} if 'mapping_id' in p or prefix == 'RUN-X' else p)
    return out


def RE_CORE():
    from sdem.rules_engine import RulesEngine
    return RulesEngine(core_only=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdem link', description='Run an inference engine over a graph store (or architecture datasets) and emit a document of proposed relationships.')
    parser.add_argument('engine', choices=sorted(ENGINES))
    parser.add_argument('paths', nargs='*', help='architecture datasets and the approved registry (or use --graph)')
    parser.add_argument('--graph', metavar='DIR', help='read a graph store (sdem build) — the normal path')
    parser.add_argument('-o', '--out', metavar='DIR', help='also write candidates, the inference log and any target-design architecture datasets here')
    parser.add_argument('--threshold', type=float, default=0.2, help='baseline only')
    parser.add_argument('--json', action='store_true', help='with --out (sdem link): the proposals, weakest first, as JSON — without --out the output is JSON already')
    parser.add_argument('--ext-workspace', metavar='DIR', help=argparse.SUPPRESS)   # MX-51: the workspace, for its extensions' proposals (set by sdem link --workspace)
    args = parser.parse_args(argv)
    from sdem.store import GraphReader, StoreError
    try:
        reader = GraphReader.from_store(args.graph) if args.graph else GraphReader.from_exports(args.paths)
    except (OSError, ValueError, StoreError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 2
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        ws = args.ext_workspace or (_files_workspace(args.paths, Path(t)) if args.paths and args.engine == 'rules' else None)   # files given: BIAN's rules (sdem-bian) read them as a workspace
        engine, result, report = propose(reader, ws, args.engine, args.threshold)
    if result.get('left_out_rejected'):   # RJ-03: said, not silently dropped
        print(f"{len(result['left_out_rejected'])} link(s) a person rejected were not proposed again (RJ-03): " + '; '.join(f'{a} {r} {b}' for a, r, b in result['left_out_rejected'][:5]), file=sys.stderr)
    from sdem import parts
    for e in report:
        if e['extension'] == parts.EXT_BIAN.split(':', 1)[1] and not e['refused']: continue   # BIAN's are part of the list, as SDEM's own were (MX-53)
        print(f"extension {e['extension']} {e.get('version') or ''}: {e['proposals']} proposal(s)" + (f"; refused {len(e['refused'])}: " + '; '.join(f"{x['item']} — {x['why']}" for x in e['refused'][:3]) if e['refused'] else ''), file=sys.stderr)
    head = {'registry_version': load_registry()['$schema_version'], 'metamodel_version': reader.mm.version, 'engine': engine.name}
    print(json.dumps({**head, 'mappings': result['proposals']}, indent=2, ensure_ascii=False))
    if args.out:
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        (out / 'candidates.json').write_text(json.dumps(_for_file(out / 'candidates.json', {**head, 'mappings': result.get('candidates', [])}), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (out / 'inference-log.json').write_text(json.dumps(_for_file(out / 'inference-log.json', {'engine': engine.name, 'attempts': result.get('log', [])}), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        for d in result.get('design', []):
            (out / f"design-{d['level'].lower()}.json").write_text(json.dumps(_for_file(out / f"design-{d['level'].lower()}.json", d), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
