"""Acceptance harness for the inference engine (relationship-rules-spec.md §8; DEC-E-01, DEC-E-05).

For each case in examples/acceptance-cases.json: build a graph store from the workspace's architecture datasets and the case's GIVEN
registry only (never the workspace's full registry, which would leak the answers), run the engine on it through the graph
access layer, validate its proposals, and score them against the sealed gold. The floor is the hand-executed run,
scored the same way from its committed files. A case passes when the engine's precision and recall are each at least
the floor's, for registry proposals and, where the case has a candidate gold, for candidate reports in its scope.

Usage: python -m sdem.acceptance [--engine rules] [--case C1 ...] [--json] [--out DIR]
"""
import argparse, glob, json, shutil, sys, tempfile
from pathlib import Path

from .evaluate import evaluate
from .metamodel import Metamodel, ROOT
from .store import GraphReader, build
from .validate import load_registry, load_schema, validate

CASES = ROOT / 'examples' / 'acceptance-cases.json'
EPS = 1e-9


def load_cases(ids=None):
    cases = json.loads(CASES.read_text(encoding='utf-8'))['cases']
    return [c for c in cases if not ids or c['id'] in ids]


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def case_inputs(case):
    e = ROOT / 'examples' / case['estate']
    return sorted(str(p) for p in e.glob('a[1-4]-*.json')) + [str(e / case['given'])]


def open_case(case, workdir):
    """Build the case's graph store (architecture datasets + given registry) and return a reader on it."""
    out = Path(workdir) / case['id']
    entry = build(case_inputs(case), out)
    if entry['result'] != 'accepted':
        raise RuntimeError(f"{case['id']}: store build rejected: {entry['errors'][:3]}")
    return GraphReader.from_store(out)


def _doc(mappings, engine, case):
    return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': Metamodel.load().version,
            'engine': engine, 'use_case': case['id'].lower(), 'mappings': mappings}


def check_proposals(doc, reader, design=()):
    """sdem validate --strict on the proposal document, ends resolved against the case's graph (plus any design architecture datasets)."""
    from .graph import FederatedGraph, LevelGraph
    fg = reader.fg
    if design:
        fg = FederatedGraph(list(reader.fg.levels.values()) + [LevelGraph(d, reader.mm) for d in design], reader.fg.mapping_docs, reader.mm)
    warnings = []
    issues = validate(doc, load_registry(), load_schema(), entity_resolver=fg, warnings=warnings, metamodel=reader.mm)
    return list(issues) + [w for w in warnings if 'must be supplied before approval' not in w]  # --strict, as sdem validate


def _scoped(docs, scope):
    return [{**d, 'mappings': [m for m in d.get('mappings', []) if m['relationship'] in scope]} for d in docs]


def floor(case):
    """The hand-executed run, scored like an engine."""
    e = ROOT / 'examples' / case['estate']
    out = {'registry': evaluate([_j(e / case['gold'])], [_j(e / case['executor']['proposals'])])['overall']}
    if case.get('gold_candidates'):
        sc = set(case['candidate_scope'])
        out['candidates'] = evaluate(_scoped([_j(e / case['gold_candidates'])], sc), _scoped([_j(e / case['executor']['candidates'])], sc))['overall']
    return out


def run_case(case, engine, workdir):
    e = ROOT / 'examples' / case['estate']
    reader = open_case(case, workdir)
    result = engine.infer(reader, case)
    name = getattr(engine, 'name', type(engine).__name__)
    pdoc = _doc(result.get('proposals', []), name, case)
    issues = check_proposals(pdoc, reader, result.get('design', ()))
    got = {'registry': evaluate([_j(e / case['gold'])], [pdoc])}
    if case.get('gold_candidates'):
        sc = set(case['candidate_scope'])
        got['candidates'] = evaluate(_scoped([_j(e / case['gold_candidates'])], sc), _scoped([_doc(result.get('candidates', []), name, case)], sc))
    fl = floor(case)
    ok = not issues and all(got[k]['overall']['precision'] + EPS >= fl[k]['precision'] and got[k]['overall']['recall'] + EPS >= fl[k]['recall'] for k in fl)
    return {'case': case['id'], 'estate': case['estate'], 'mode': case['mode'], 'engine_status': case.get('engine_status'), 'passed': ok, 'issues': issues,
            'floor': fl, 'score': {k: v['overall'] for k, v in got.items()}, 'detail': got, 'result': result}


def run(engine, ids=None, out=None):
    tmp = Path(tempfile.mkdtemp(prefix='sdem-accept-'))
    try:
        rows = [run_case(c, engine, tmp) for c in load_cases(ids)]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if out:
        out = Path(out); out.mkdir(parents=True, exist_ok=True)
        for r in rows:
            uc = r['case'].lower(); res = r['result']
            case = next(c for c in load_cases([r['case']]))
            (out / f'{uc}-proposals.json').write_text(json.dumps(_doc(res.get('proposals', []), getattr(engine, 'name', ''), case), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            if res.get('candidates') is not None:
                (out / f'{uc}-candidates.json').write_text(json.dumps(_doc(res['candidates'], getattr(engine, 'name', ''), case), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            for d in res.get('design', []):
                (out / f"{uc}-design-{d['level'].lower()}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            (out / f'{uc}-inference-log.json').write_text(json.dumps({'use_case': r['case'], 'engine': getattr(engine, 'name', ''), 'attempts': res.get('log', [])}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return rows


def render(rows):
    f = lambda s: f"P {s['precision']:.2f} R {s['recall']:.2f}"
    lines = [f"{'case':<5} {'estate':<20} {'kind':<11} {'hand-run (floor)':<18} {'engine':<18} result"]
    for r in rows:
        for k in r['floor']:
            lines.append(f"{r['case'] if k == 'registry' else '':<5} {r['estate'] if k == 'registry' else '':<20} {k:<11} {f(r['floor'][k]):<18} {f(r['score'][k]):<18} "
                         + (('PASS' if r['passed'] else 'FAIL') if k == 'registry' else ''))
        for i in r['issues'][:3]: lines.append(f'      invalid proposal: {i}')
    n = sum(r['passed'] for r in rows)
    lines.append(f"\n{n} of {len(rows)} cases pass")
    return '\n'.join(lines)


class ReplayEngine:
    """Returns the hand-executed run's committed outputs. Used to prove the harness: replay must pass every case."""
    name = 'replay-executor'

    def infer(self, reader, case):
        e = ROOT / 'examples' / case['estate']; x = case['executor']
        out = {'proposals': _j(e / x['proposals'])['mappings']}
        if x.get('candidates'): out['candidates'] = _j(e / x['candidates'])['mappings']
        if x.get('design'): out['design'] = [_j(e / d) for d in x['design']]
        return out


def calibrate(engine=None, ids=None):
    """AID-E03 (OPEN-06): how often each confidence band and each evidence class is right — every acceptance case run by the engine, each
    proposal and candidate looked up in the case's sealed gold. A report, not a setting: the bands stay as the rules give them (D3)."""
    from .evaluate import key
    from .rules_engine import BAND, EVIDENCE_CLASSES
    engine = engine or engines()['rules']()
    tally = {'band': {}, 'evidence_class': {}}
    tmp = Path(tempfile.mkdtemp(prefix='sdem-calibrate-'))
    try:
        for case in load_cases(ids):
            e = ROOT / 'examples' / case['estate']
            res = engine.infer(open_case(case, tmp), case)
            for part, gold_file, scope in (('proposals', case['gold'], None), ('candidates', case.get('gold_candidates'), set(case.get('candidate_scope') or []))):
                if not gold_file: continue
                gold = {key(m) for m in _j(e / gold_file).get('mappings', []) if m.get('status') in (None, 'approved', 'proposed', 'validated')}
                for m in res.get(part) or []:
                    if scope is not None and m['relationship'] not in scope: continue
                    right = key(m) in gold
                    band = next((b for b, v in BAND.items() if v == m.get('confidence')), str(m.get('confidence')))
                    for dim, k in (('band', band), ('evidence_class', m.get('evidence_class') or 'unclassified')):
                        t = tally[dim].setdefault(k, {'proposed': 0, 'right': 0}); t['proposed'] += 1; t['right'] += right
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    order = {'band': ['high', 'medium', 'low'], 'evidence_class': list(EVIDENCE_CLASSES) + ['unclassified']}
    out = {}
    for dim, rows in tally.items():
        out[dim] = [{dim: k, **rows[k], 'precision': round(rows[k]['right'] / rows[k]['proposed'], 3), 'stated': BAND.get(k) if dim == 'band' else None}
                    for k in order[dim] + sorted(set(rows) - set(order[dim])) if k in rows]
    out['note'] = ('Observed precision against the sealed golds of the acceptance cases, written by SDEM (OPEN-05): a check that the bands are '
                   'conservative — a band whose observed precision falls below its stated value is a finding for the owner, not a setting.')
    return out


def render_calibration(r):
    L = ['Confidence calibration (AID-E03) — the acceptance cases against their sealed golds', '']
    for dim, title in (('band', 'By confidence band (stated value)'), ('evidence_class', 'By evidence class')):
        L += [title, f"  {'':<16}{'proposed':>9}{'right':>7}{'precision':>11}"]
        for row in r[dim]:
            flag = '  below its stated value' if row.get('stated') is not None and row['precision'] < row['stated'] else ''
            L.append(f"  {row[dim]:<16}{row['proposed']:>9}{row['right']:>7}{row['precision']:>11.0%}" + (f"  (stated {row['stated']:.0%}){flag}" if row.get('stated') is not None else ''))
        L.append('')
    return '\n'.join(L + [r['note']])


def engines():
    from .inference import ENGINES
    return {**ENGINES, 'replay': ReplayEngine}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem model accept', description='Run an inference engine over the acceptance cases and score it against the hand-executed runs.')
    ap.add_argument('--engine', default='rules', choices=sorted(engines()))
    ap.add_argument('--case', nargs='*', help='case ids (default: all)')
    ap.add_argument('--out', help='write each case\'s proposals, candidates and inference log here')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    eng = engines()[args.engine]()
    rows = run(eng, args.case, args.out)
    if args.json: print(json.dumps([{k: v for k, v in r.items() if k not in ('result', 'detail')} for r in rows], indent=2))
    else: print(render(rows))
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
