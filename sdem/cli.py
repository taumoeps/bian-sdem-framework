"""`sdem` — SDEM's command line, its only interface (docs/sdem-workbench-design.md, SDEM-D07; spec WB-K01…K06).

One command with a subcommand per journey. Most subcommands hand over to the existing command code unchanged (the
`sdem-*` commands keep working as aliases); `review` and `explain` are new. Conventions everywhere: inputs as `--graph DIR`
or file paths, `--json` for machine-readable output, exit codes 0 = OK, 1 = issues found, 2 = usage error, no prompts.
"""
import argparse, contextlib, importlib, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name: (journey, what it does, module, fixed leading arguments, worked example)
JOURNEYS = {
    'check':    ('J1', 'check architecture datasets and registry against the rulebook', 'sdem.graph', ['check'],
                 'sdem check examples/payment-initiation/a*.json examples/payment-initiation/mappings.json'),
    'validate': ('J1', 'validate a relationship document (registry or proposals)', 'sdem.validate', [],
                 'sdem validate --strict examples/payment-initiation/mappings.json'),
    'link':     ('J2', 'run the inference engine: propose links between the architectures', 'sdem.inference', None,
                 'sdem link examples/payment-initiation/a*.json --out work/links'),
    'review':   ('J3', 'list proposed links for review, weakest first', None, None,
                 'sdem review work/links/proposals.json'),
    'build':    ('J4', 'check the inputs and write the graph store (knowledge graph)', 'sdem.graph', ['build'],
                 'sdem build examples/card-fraud-alerts/a*.json examples/card-fraud-alerts/mappings.json --out work/graph'),
    'query':    ('J4', 'find records in a graph store', 'sdem.graph', ['query'],
                 'sdem query --graph examples/card-fraud-alerts/graph --level A3'),
    'baseline': ('J4', 'freeze the current graph store under a name', 'sdem.graph', ['baseline'],
                 'sdem baseline release-1 --graph work/graph'),
    'trace':    ('J5', 'trace what a record depends on (down) or what depends on it (up)', 'sdem.graph', ['trace'],
                 'sdem trace CAP-310 --graph examples/card-fraud-alerts/graph'),
    'impact':   ('J5', 'classify what a change to a record affects', 'sdem.graph', ['impact'],
                 'sdem impact INF-CLOUD-K8S-PROD --change rehost --graph examples/card-fraud-alerts/graph'),
    'aid':      ('J6', 'Architecture Inference Design: project, check, gaps', 'sdem.aid', [],
                 'sdem aid project --have examples/payment-initiation/a1-business.json --catalogue bian.json --out work/prj'),
    'view':     ('J7', 'write the HTML picture of a graph store, optionally with a projection', 'sdem.graph', ['view'],
                 'sdem view --graph examples/card-fraud-alerts/graph -o work/view.html'),
    'explain':  ('J8', 'explain one element or link: why it exists, from what, how sure', None, None,
                 'sdem explain SD-PI --projection work/prj'),
    'change':   ('AG', 'agent platform: propose a change set to one layer — checked, then its impact recorded', None, None,
                 'sdem change propose cs.json --estate work/est --agent sdem-a4-technology --person jane.architect'),
    'events':   ('AG', 'agent platform: change events, their impact and open work', None, None,
                 'sdem events --estate work/est --open'),
    'work':     ('AG', 'agent platform: plan, list and claim work items', None, None,
                 'sdem work plan --event CE-001 --estate work/est --agent sdem-orchestrator --person jane.architect'),
    'diff':     ('—', 'compare two versions of a relationship document', 'sdem.diff', [],
                 'sdem diff --git HEAD~1 examples/payment-initiation/mappings.json'),
    'model':    ('—', 'maintainers: regenerate and check generated files, acceptance, evaluation, examples', None, None,
                 'sdem model check'),
}

# generated documents and schemas, in the order CI checks them
GENERATORS = ['diagram', 'relationships', 'structure', 'spec', 'kgspec', 'catalogue', 'attributes', 'confidence',
              'logical', 'physical', 'metamodel_spec', 'controls']


def _main_of(module):
    return importlib.import_module(module).main


def _delegate(name, rest):
    journey, _, module, lead, example = JOURNEYS[name]
    if name == 'link':
        lead, rest = (['baseline'], [a for a in rest if a != '--baseline']) if '--baseline' in rest else (['rules'], rest)
    if '-h' in rest or '--help' in rest:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try: _main_of(module)(lead + rest)
            except SystemExit: pass
        text = buf.getvalue()
        text = re.sub(r'\bsdem-(graph|aid|infer|validate|diff)\b( (check|build|query|baseline|trace|impact|view))?', f'sdem {name}', text, count=1)
        if name == 'link':  # the engine is chosen by sdem link itself: rules, or --baseline
            text = re.sub(r'\s*\{baseline,rules\}', '', text).replace('positional arguments:', 'positional arguments (the rules engine runs; add --baseline for the name-overlap baseline):', 1)
            text = re.sub(r'\n\s+\{baseline,rules\}\n', '\n', text)
        print(text.rstrip() + f'\n\nExample ({journey}):\n  {example}')
        return 0
    if name == 'link':
        return _link(lead + rest)
    return _main_of(module)(lead + rest)


def _link(argv):
    """The engine (sdem-infer) — and, with --out, also keep the proposals as proposals.json for `sdem review`."""
    out = argv[argv.index('--out') + 1] if '--out' in argv and argv.index('--out') + 1 < len(argv) else None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _main_of('sdem.inference')(argv)
    text = buf.getvalue()
    if code == 0 and out:
        (Path(out) / 'proposals.json').write_text(text, encoding='utf-8')
        n = len(json.loads(text).get('mappings', []))
        print(f"{n} proposed link(s) written to {Path(out) / 'proposals.json'}; candidates, inference log and any design datasets in {out}/")
        print(f"next: sdem review {Path(out) / 'proposals.json'}")
    else:
        sys.stdout.write(text)
    return code


def _rule_of(m):
    ev = (m.get('evidence') or [''])[0].replace('engine_rationale:', '')
    r = re.match(r'(S\d\d|B\d\d)', ev)
    return r.group(1) if r else (m.get('projection') or {}).get('rule', '—')


def _names(paths, graph):
    """id → name from a graph store or architecture datasets, if given (for readable output)."""
    out = {}
    try:
        from .store import GraphReader
        r = GraphReader.from_store(graph) if graph else GraphReader.from_exports(paths) if paths else None
        for n in (r.nodes() if r else []): out[n['id']] = n.get('name', n['id'])
    except Exception:  # names are a convenience; never fail a review over them
        pass
    return out


def review(argv):
    ap = argparse.ArgumentParser(prog='sdem review', description='List proposed links for review, weakest first — each with its rule, confidence and reasoning. '
                                 'Approving is done by a person: set status approved, reviewer_id and approved_at in the registry, and open a pull request.',
                                 epilog=f"Example (J3):\n  {JOURNEYS['review'][4]}", formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('proposals', nargs='+', help='proposals file(s), e.g. from `sdem link --out`')
    ap.add_argument('--graph', metavar='DIR', help='graph store to show record names')
    ap.add_argument('--names', nargs='*', default=[], metavar='DATASET', help='architecture datasets to show record names')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rows = []
    for f in a.proposals:
        try: doc = json.loads(Path(f).read_text(encoding='utf-8'))
        except (OSError, ValueError) as e: print(f'ERROR: {f}: {e}', file=sys.stderr); return 2
        rows += [dict(m, _file=f) for m in doc.get('mappings', []) if m.get('status', 'proposed') == 'proposed']
    rows.sort(key=lambda m: (m.get('confidence', 0), m['relationship'], m['source']['id']))
    names = _names(a.names, a.graph)
    if a.json:
        print(json.dumps([{'mapping_id': m['mapping_id'], 'source': m['source']['id'], 'relationship': m['relationship'], 'target': m['target']['id'],
                           'rule': _rule_of(m), 'confidence': m.get('confidence'), 'reasoning': m.get('rationale', '')} for m in rows], indent=2, ensure_ascii=False))
        return 0
    if not rows: print('no proposed links to review'); return 0
    print(f'{len(rows)} proposed link(s), weakest first:\n')
    for m in rows:
        s, t = m['source']['id'], m['target']['id']
        nm = lambda x: f"{x} '{names[x]}'" if x in names else x
        print(f"  [{m.get('confidence')}] {m['mapping_id']}  {nm(s)} -{m['relationship']}-> {nm(t)}   rule {_rule_of(m)}")
        why = re.sub(r'\s*\((?:P|C)-[A-Z0-9]+-\d+\)', '', m.get('rationale', ''))[:300]
        print(f'        why: {why}')
    print('\nTo approve: in the registry set status "approved", reviewer_id and approved_at for the links you accept, then open a pull request. '
          'A person approves — never the engine or Copilot.')
    return 0


def explain(argv):
    ap = argparse.ArgumentParser(prog='sdem explain', description='Explain one element or link: why it exists, from what, by which rule and published source, and how sure.',
                                 epilog=f"Example (J8):\n  {JOURNEYS['explain'][4]}\n  sdem explain P-RUN-003 --proposals work/links/proposals.json",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('id', help='a record id, projected id (PRJ-…), or link id')
    ap.add_argument('--projection', metavar='DIR', help='an AID projection package')
    ap.add_argument('--proposals', nargs='*', default=[], metavar='FILE', help='proposals file(s) from `sdem link`')
    ap.add_argument('--graph', metavar='DIR', help='graph store to show record names')
    ap.add_argument('--names', nargs='*', default=[], metavar='DATASET', help='architecture datasets to show record names')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if not a.projection and not a.proposals: ap.error('give --projection DIR and/or --proposals FILE')
    found, names = [], _names(a.names, a.graph)
    if a.projection:
        from .aid import read
        try: pkg = read(a.projection)
        except (OSError, ValueError) as e: print(f'ERROR: {a.projection}: {e}', file=sys.stderr); return 2
        names.update({i['id']: i.get('name', i['id']) for d in pkg['layers'].values() for i in d['instances']})
        for lvl, d in pkg['layers'].items():
            for i in d['instances']:
                if i['id'] == a.id: found.append({'kind': 'projected element', 'level': lvl, 'id': i['id'], 'name': i.get('name'), 'type': i['type'], **i['projection']})
        for l in pkg['links']['links']:
            if a.id in (l['mapping_id'], l['source']['id'], l['target']['id']):
                found.append({'kind': 'projected link', 'id': l['mapping_id'], 'name': f"{l['source']['id']} -{l['relationship']}-> {l['target']['id']}", **l['projection']})
    for f in a.proposals:
        try: doc = json.loads(Path(f).read_text(encoding='utf-8'))
        except (OSError, ValueError) as e: print(f'ERROR: {f}: {e}', file=sys.stderr); return 2
        for m in doc.get('mappings', []):
            if a.id in (m['mapping_id'], m['source']['id'], m['target']['id']):
                found.append({'kind': 'proposed link', 'id': m['mapping_id'], 'name': f"{m['source']['id']} -{m['relationship']}-> {m['target']['id']}",
                              'rule': _rule_of(m), 'confidence': m.get('confidence'), 'reasoning': m.get('rationale', ''), 'evidence': m.get('evidence', [])})
    if a.json: print(json.dumps(found, indent=2, ensure_ascii=False)); return 0 if found else 1
    if not found: print(f'{a.id}: not found in the given projection or proposals'); return 1
    for x in found:
        print(f"{x['kind'].upper()}  {x['id']}  {x.get('name') or ''}" + (f"  ({x['level']} {x['type']})" if 'level' in x else ''))
        for k in ('step', 'rule', 'source_reference', 'inferred_from', 'reasoning', 'confidence', 'evidence'):
            if k in x and x[k] not in (None, '', []):
                v = ', '.join(f"{e} '{names[e]}'" if e in names and names[e] != e else e for e in x[k]) if k == 'inferred_from' else '; '.join(x[k]) if k == 'evidence' else x[k]
                print(f"  {k.replace('_', ' '):<17} {v}")
        print()
    return 0


def model(argv):
    ap = argparse.ArgumentParser(prog='sdem model', description='Maintainer commands: generated documents and schemas, acceptance, evaluation, examples.',
                                 epilog='Examples:\n  sdem model check          # fail if any generated file is stale (as CI)\n  sdem model regenerate\n'
                                        '  sdem model accept --engine rules\n  sdem model examples       # re-run use-case examples 1 and 2',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('regenerate', help='regenerate every generated document, diagram and schema')
    sub.add_parser('check', help='fail if any generated file differs from a fresh generation')
    sub.add_parser('accept', help='engine acceptance cases (sdem-accept)', add_help=False)
    sub.add_parser('eval', help='score proposals against approved links (sdem-eval)', add_help=False)
    sub.add_parser('examples', help='re-run use-case examples 1 and 2 (evidence packs and results)')
    sub.add_parser('baseline-pack', help='write the metamodel baseline review pack')
    a, rest = ap.parse_known_args(argv)
    if a.cmd in ('accept', 'eval'):
        return _main_of('sdem.acceptance' if a.cmd == 'accept' else 'sdem.evaluate')(rest)
    if rest: ap.error(f"unrecognized arguments: {' '.join(rest)}")
    if a.cmd in ('regenerate', 'check'):
        stale = []
        for g in GENERATORS:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = _main_of(f'sdem.{g}')(['--check'] if a.cmd == 'check' else [])
            print(f"  {'OK   ' if code == 0 else 'STALE' if a.cmd == 'check' else 'FAIL '} {g}")
            if code: stale.append(g)
        if stale: print(f"{len(stale)} generator(s) {'stale — run: sdem model regenerate' if a.cmd == 'check' else 'failed'}: {', '.join(stale)}"); return 1
        print('all generated files current' if a.cmd == 'check' else 'all generated files regenerated'); return 0
    sys.path.insert(0, str(ROOT / 'scripts'))
    if a.cmd == 'examples':
        codes = [importlib.import_module(m).main() for m in ('use_case_example_1', 'use_case_example_2')]
        return 1 if any(codes) else 0
    if a.cmd == 'baseline-pack':
        return importlib.import_module('baseline_pack').main() or 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    lines = [f"  {n:<9} {j:<3} {w}" for n, (j, w, *_rest) in JOURNEYS.items()]
    epilog = ('Journeys (J1–J8, docs/sdem-workbench-design.md §3):\n' + '\n'.join(lines) +
              '\n\nEvery subcommand takes --help with a worked example. Exit codes: 0 OK, 1 issues found, 2 usage error.'
              '\nAG = agent platform (docs/sdem-agent-platform-design.md). The sdem-* commands (sdem-graph, sdem-infer, sdem-aid, …) remain as aliases.')
    ap = argparse.ArgumentParser(prog='sdem', usage='sdem <command> [options]', epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="SDEM — Service Domain Enterprise Metamodel. SDEM's command line: run it in VS Code's terminal pane; "
                                             'ask Copilot Chat to explain any output.')
    ap.add_argument('command', nargs='?', choices=list(JOURNEYS), metavar='command', help='one of the commands below')
    if not argv or argv[0] in ('-h', '--help'):
        ap.print_help(); return 0 if argv else 2
    name, rest = argv[0], argv[1:]
    if name not in JOURNEYS:
        print(f"sdem: unknown command '{name}' — run 'sdem --help' for the list", file=sys.stderr); return 2
    if name == 'review': return review(rest)
    if name == 'explain': return explain(rest)
    if name == 'model': return model(rest)
    if name in ('change', 'events', 'work'):
        from . import agents
        return {'change': agents.change_main, 'events': agents.events_main, 'work': agents.work_main}[name](rest)
    return _delegate(name, rest)


if __name__ == '__main__':
    raise SystemExit(main())
