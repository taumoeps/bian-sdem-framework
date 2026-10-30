"""`sdem` — SDEM's command line, its only interface (docs/design/sdem-workbench-design.md, SDEM-D07; spec WB-K01…K06).

One command with a subcommand per journey. Most subcommands hand over to the existing command code unchanged (the
`sdem-*` commands keep working as aliases); `review` and `explain` are new. Conventions everywhere: inputs as `--graph DIR`
or file paths, `--json` for machine-readable output, exit codes 0 = OK, 1 = issues found, 2 = usage error, no prompts.
"""
import argparse, contextlib, glob, importlib, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UsageError(Exception):
    """The command was given something it cannot use — reported as one line, exit 2."""

# name: (journey, what it does, module, fixed leading arguments, worked example)
JOURNEYS = {
    'check':    ('J1', 'check architecture datasets and registry against the metamodel', 'sdem.graph', ['check'],
                 'sdem check --workspace examples/payment-initiation'),
    'validate': ('J1', 'validate a relationship document (registry or proposals)', 'sdem.validate', [],
                 'sdem validate --strict --workspace examples/payment-initiation'),
    'link':     ('J2', 'run the inference engine: propose links between the architectures, and show them weakest first for review (--no-review: just write them)', 'sdem.inference', None,
                 'sdem link --workspace examples/payment-initiation --out work/links'),
    'review':   ('J3', 'list proposed links for review, weakest first', None, None,
                 'sdem review work/links/proposals.json'),
    'approve':  ('J3', 'a person approves proposed links into the registry — reviewer, date, required evidence, validated first', None, None,
                 'sdem approve P-RUN-001 --proposals work/links/proposals.json --workspace work/est --reviewer jane.architect --evidence deployment_design:PAY-REHOST#cutover'),
    'build':    ('J4', 'check the inputs and write the graph store (knowledge graph)', 'sdem.graph', ['build'],
                 'sdem build --workspace examples/card-fraud-alerts --out work/graph'),
    'query':    ('J4', 'find records in a graph store', 'sdem.graph', ['query'],
                 'sdem query --graph examples/card-fraud-alerts/graph --level A3'),
    'baseline': ('J4', 'freeze the current graph store under a name', 'sdem.graph', ['baseline'],
                 'sdem baseline release-1 --graph work/graph'),
    'trace':    ('J5', 'trace what a record depends on (down) or what depends on it (up)', 'sdem.graph', ['trace'],
                 'sdem trace CAP-310 --graph examples/card-fraud-alerts/graph'),
    'impact':   ('J5', 'classify what a change to a record affects', 'sdem.graph', ['impact'],
                 'sdem impact INF-CLOUD-K8S-PROD --change rehost --graph examples/card-fraud-alerts/graph'),
    'aid':      ('J6', 'Architecture Inference Design: fill a workspace\'s gaps — inferred records marked with source, reasoning and confidence; confirm, reject (also project, check, gaps for file-based planning)', 'sdem.aid', [],
                 'sdem aid --workspace workspaces/payments --person jane.architect'),
    'new':      ('J9', 'start a workspace: the four layers (A2 your BIAN layer) and an empty registry of connections — checked, recorded', 'sdem.new', [],
                 'sdem new --workspace workspaces/payments --person jane.architect'),
    'load':     ('J9', 'load reviewed candidate entities from sdem transform into a workspace — selected, checked first, recorded (the L of the ETL)', 'sdem.load', [],
                 'sdem load work/history --workspace workspaces/history --person jane.architect --exclude HIS-A3-X'),
    'designs':  ('J9', 'design records and gap records: the pages onboarded designs came from, and what did not fit an entity', 'sdem.designs', [],
                 'sdem designs --workspace workspaces/history --entity HIS-A3-PAYMENTS-HUB'),
    'bian':     ('J9', "the BIAN (A2) layer: from the base BIAN that ships with SDEM, your own BIAN pack, or BIAN's files — list, import the service domains you choose (checked), pack", 'sdem.bian', [],
                 'sdem bian import ~/bian/release14.0.0 --only "Payment Order Initiation" -o work/bian/a2-service-domain.json'),
    'transform': ('J9', 'transform an export of past designs (Confluence) into candidate architecture entities: inspect it, extract (rules; on-device OCR for pictures)', 'sdem.transform', [],
                 'sdem transform run tests/fixtures/confluence-export-sample -o work/history --known examples/payment-initiation/a3-application.json'),
    'view':     ('J7', 'write the HTML picture of a graph store, optionally with a projection', 'sdem.graph', ['view'],
                 'sdem view --graph examples/card-fraud-alerts/graph -o work/view.html'),
    'home':     ('J7', 'the main dashboard: the metamodel (entities, links inside and between architectures, engine rules), its picture, health, configuration — and every project', 'sdem.home', [],
                 'sdem home -o work/sdem'),
    'matrix':   ('J5', 'business → BIAN → application → technology matrices from approved links', 'sdem.matrix', [],
                 'sdem matrix --workspace examples/payment-initiation --md work/matrix.md'),
    'dashboard': ('J7', 'one read-only HTML dashboard for a workspace: health, attention, review, trace & impact, matrices, changes, AID, controls', 'sdem.dashboard', [],
                 'sdem dashboard --workspace examples/payment-initiation -o work/dashboard.html'),
    'explain':  ('J8', 'explain one element or link: why it exists, from what, how sure', None, None,
                 'sdem explain SD-PI --projection work/prj'),
    'change':   ('AG', 'agent platform: propose a change set to one layer — checked, then its impact recorded', None, None,
                 'sdem change propose cs.json --workspace work/est --agent sdem-a4-technology --person jane.architect'),
    'events':   ('AG', 'agent platform: change events, their impact and open work', None, None,
                 'sdem events --workspace work/est --open'),
    'work':     ('AG', 'agent platform: plan, list and claim work items', None, None,
                 'sdem work plan --event CE-001 --workspace work/est --agent sdem-orchestrator --person jane.architect'),
    'copilot':  ('AG', "put SDEM's Copilot instructions, agents, prompts and skills into your workspace repository, matching this SDEM version", 'sdem.copilot', [],
                 'sdem copilot install --dry-run'),
    'connect':  ('J3', 'a person states a connection the engine did not propose — the same checks as approve, both ends in the workspace', 'sdem.connect', [],
                 'sdem connect SD-PAYMENT-ORDER-INITIATION REALIZED_BY HIS-A3-PAYMENTS-HUB --workspace workspaces/payments --reviewer jane.architect --evidence application_architecture_document:PAYHUB-HLD#s2 --rationale "…"'),
    'migrate':  ('—', 'move a workspace to the current metamodel version — recorded migrations applied, checked, written all-or-nothing, recorded', 'sdem.migrate', [],
                 'sdem migrate --workspace workspaces/history --person jane.architect --dry-run'),
    'diff':     ('—', 'compare two versions of a relationship document', 'sdem.diff', [],
                 'sdem diff --git HEAD~1 examples/payment-initiation/mappings.json'),
    'model':    ('—', 'maintainers: regenerate and check generated files, acceptance, evaluation, examples', None, None,
                 'sdem model check'),
}

# generated documents and schemas, in the order CI checks them
GENERATORS = ['diagram', 'relationships', 'structure', 'spec', 'kgspec', 'catalogue', 'attributes', 'confidence',
              'logical', 'physical', 'metamodel_spec', 'controls', 'inferences']


ESTATE_FILES = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')
ESTATE_COMMANDS = ('check', 'validate', 'link', 'build', 'trace', 'impact', 'matrix')


def _estate_files(d, registry_only=False, designs=False):
    """A workspace folder's files: the architecture datasets it has (one to four — a partial workspace is normal), its registry,
    and — for check, build, trace and impact — its design records (designs/design-records.json) when it has them."""
    d = Path(d); reg = d / 'mappings.json'
    datasets = [] if registry_only else [d / f for f in ESTATE_FILES if (d / f).exists()]
    if not reg.exists() or (not registry_only and not datasets):
        raise UsageError(f"--workspace {d}: not a workspace folder (it needs mappings.json and at least one of {', '.join(ESTATE_FILES)})")
    extra = [d / 'designs' / 'design-records.json'] if designs and (d / 'designs' / 'design-records.json').exists() else []
    return [str(f) for f in datasets + [reg] + extra]


def _expand(name, rest):
    """T4: `--workspace DIR` in place of the file list, and `*` patterns expanded by sdem itself (Windows PowerShell does not)."""
    out = []
    for a in rest:
        hits = sorted(glob.glob(a)) if not a.startswith('-') and any(c in a for c in '*?[') else []
        out += hits or [a]
    if '--workspace' in out and name in ESTATE_COMMANDS:   # --workspace DIR in place of the workspace's file list
        i = out.index('--workspace')
        if i + 1 >= len(out): raise UsageError('--workspace needs a folder')
        d = out[i + 1]; del out[i:i + 2]
        files = _estate_files(d, registry_only=(name == 'validate'), designs=name in ('check', 'build', 'trace', 'impact'))
        out = files + out if name == 'link' else out + files   # link's parser wants paths before its options; trace/impact want the id first
    return out


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
        if name in ESTATE_COMMANDS:
            text = text.rstrip() + "\n\n--workspace DIR    a workspace folder instead of the file list" + (" (its mappings.json)" if name == 'validate' else " (a1…a4 datasets and mappings.json)")
        print(text.rstrip() + f'\n\nExample ({journey}):\n  {example}')
        return 0
    if name == 'link':
        return _link(lead + rest)
    return _main_of(module)(lead + rest)


def _link(argv):
    """The engine (sdem-infer) — and, with --out, also keep the proposals as proposals.json for `sdem review`."""
    show = '--no-review' not in argv and '--json' not in argv   # the review follows straight away (an architect wants it); --no-review for scripts
    argv = [x for x in argv if x != '--no-review']
    flag = next((f for f in ('--out', '-o') if f in argv), None)
    out = argv[argv.index(flag) + 1] if flag and argv.index(flag) + 1 < len(argv) else None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _main_of('sdem.inference')(argv)
    text = buf.getvalue()
    if code == 0 and out:
        (Path(out) / 'proposals.json').write_text(text, encoding='utf-8')
        n = len(json.loads(text).get('mappings', []))
        print(f"{n} proposed link(s) written to {Path(out) / 'proposals.json'}; candidates, inference log and any design datasets in {out}/")
        if show and n:
            names = [x for x in argv if x.endswith('.json') and Path(x).name[:3] in ('a1-', 'a2-', 'a3-', 'a4-') and Path(x).exists()]
            print(); review([str(Path(out) / 'proposals.json')] + (['--names', *names] if names else []))
            print(f"\nReview again any time: sdem review {Path(out) / 'proposals.json'}")
        elif n: print(f"next: sdem review {Path(out) / 'proposals.json'}")
    else:
        sys.stdout.write(text)
    return code


def _rule_of(m):
    ev = (m.get('evidence') or [''])[0].replace('engine_rationale:', '')
    r = re.match(r'(S\d\d|B\d\d)', ev)
    return r.group(1) if r else (m.get('projection') or {}).get('rule', '—')


def _metamodel_sources():
    """The rule records (id → record) and the published-source key (code → address) from the metamodel."""
    from .paths import DATA_ROOT
    mm = DATA_ROOT / 'metamodel'
    rules = {r['id']: r for r in json.loads((mm / 'relationship-rules.json').read_text(encoding='utf-8'))['mappings']}
    return rules, json.loads((mm / 'official-mappings.json').read_text(encoding='utf-8')).get('sources', {})


def _with_sources(x, rules, sources):
    """Add the rule in words and the published sources behind it (J8: rule, published source, evidence, reasoning)."""
    r = rules.get(x.get('rule'))
    if r:
        x.setdefault('rule_says', f"{r['source']} {r['relation']} {r['target']} — {r['reasoning']}")
        x.setdefault('source_reference', r.get('source_reference', ''))
    ref = x.get('source_reference') or ''
    if ref.count('(') > ref.count(')'): x['source_reference'] = ref + ')'
    codes = list(dict.fromkeys(re.findall(r'\[([A-Z][A-Z0-9]+)\]', ref)))
    if codes: x['sources'] = [f"[{c}] {sources[c]}" if c in sources else f"[{c}]" for c in codes]
    return x


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
                                 'Approving is done by a person: sdem approve <id> --proposals <file> --workspace <dir> --reviewer <your name> --evidence <kind:ref>, then a pull request.',
                                 epilog=f"Example (J3):\n  {JOURNEYS['review'][4]}", formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('proposals', nargs='+', help='proposals file(s), e.g. from `sdem link --out`')
    ap.add_argument('--graph', metavar='DIR', help='graph store to show record names')
    ap.add_argument('--names', nargs='*', default=[], metavar='DATASET', help='architecture datasets to show record names')
    ap.add_argument('--workspace', dest='estate', metavar='DIR', help='workspace folder — show record names from its datasets')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.estate: a.names = a.names + _estate_files(a.estate)[:-1]
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
    print('\nTo approve (a person — never the engine or Copilot): sdem approve <id> --proposals <file> --workspace <dir> --reviewer <your name> --evidence <kind:ref>, '
          'then open a pull request; the reviewed merge makes it final.')
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
    ap.add_argument('--workspace', dest='estate', metavar='DIR', help='workspace folder — show record names from its datasets')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.estate: a.names = a.names + _estate_files(a.estate)[:-1]
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
    rules, sources = _metamodel_sources()
    found = [_with_sources(x, rules, sources) for x in found]
    if a.json: print(json.dumps(found, indent=2, ensure_ascii=False)); return 0 if found else 1
    if not found: print(f'{a.id}: not found in the given projection or proposals'); return 1
    for x in found:
        print(f"{x['kind'].upper()}  {x['id']}  {x.get('name') or ''}" + (f"  ({x['level']} {x['type']})" if 'level' in x else ''))
        for k in ('step', 'rule', 'rule_says', 'source_reference', 'sources', 'inferred_from', 'reasoning', 'confidence', 'evidence'):
            if k in x and x[k] not in (None, '', []):
                v = ', '.join(f"{e} '{names[e]}'" if e in names and names[e] != e else e for e in x[k]) if k == 'inferred_from' else '; '.join(x[k]) if k in ('evidence', 'sources') else x[k]
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
    from .paths import CHECKOUT
    if not CHECKOUT:
        print('sdem model: maintainer commands need a checkout of the SDEM repository (they read and write docs/, examples/ and scripts/)', file=sys.stderr); return 2
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
    argv = ['--workspace' if x == '--estate' else x for x in (sys.argv[1:] if argv is None else argv)]   # --estate: the old name, still accepted
    lines = [f"  {n:<9} {j:<3} {w}" for n, (j, w, *_rest) in JOURNEYS.items()]
    epilog = ('Journeys (J1–J9; every command with examples: docs/sdem-workbench-user-guide.md §7):\n' + '\n'.join(lines) +
              '\n\nEvery subcommand takes --help with a worked example. Exit codes: 0 OK, 1 issues found, 2 usage or input error, 3 internal error.'
              '\nAG = agent platform (docs/sdem-copilot-setup.md). The sdem-* commands (sdem-graph, sdem-infer, sdem-aid, …) remain as aliases.')
    ap = argparse.ArgumentParser(prog='sdem', usage='sdem <command> [options]', epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="SDEM — Service Domain Enterprise Metamodel. SDEM's command line: run it in VS Code's terminal pane; "
                                             'ask Copilot Chat to explain any output.')
    ap.add_argument('command', nargs='?', choices=list(JOURNEYS), metavar='command', help='one of the commands below')
    if not argv or argv[0] in ('-h', '--help'):
        ap.print_help(); return 0 if argv else 2
    if argv[0] in ('--version', '-V'):
        from .paths import version
        print(f'sdem {version()}'); return 0
    try:
        return _run(argv)
    except KeyboardInterrupt:
        print('sdem: stopped', file=sys.stderr); return 130
    except UsageError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    except json.JSONDecodeError as e:   # a data file that is not valid JSON — the user's input, not SDEM
        print(f'ERROR: a file is not valid JSON — {e.msg} at line {e.lineno}, column {e.colno}', file=sys.stderr); return 2
    except OSError as e:
        print(f"ERROR: {e.strerror or e}" + (f': {e.filename}' if getattr(e, 'filename', None) else ''), file=sys.stderr); return 2
    except (ValueError, KeyError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    except Exception as e:   # a fault in SDEM itself: one line, and the traceback only when asked for
        import os, traceback
        if os.environ.get('SDEM_DEBUG'): traceback.print_exc()
        print(f'ERROR: internal error ({e.__class__.__name__}: {e}) — please report it; set SDEM_DEBUG=1 for the details', file=sys.stderr); return 3


def _run(argv):
    name, rest = argv[0], argv[1:]
    if name not in JOURNEYS:
        print(f"sdem: unknown command '{name}' — run 'sdem --help' for the list", file=sys.stderr); return 2
    rest = _expand(name, rest)
    if name == 'review': return review(rest)
    if name == 'explain': return explain(rest)
    if name == 'model': return model(rest)
    if name == 'approve':
        from . import approve as _ap
        return _ap.main(rest)
    if name in ('change', 'events', 'work'):
        from . import agents
        return {'change': agents.change_main, 'events': agents.events_main, 'work': agents.work_main}[name](rest)
    return _delegate(name, rest)


if __name__ == '__main__':
    raise SystemExit(main())
