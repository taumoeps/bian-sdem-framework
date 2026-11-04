"""Updating SDEM without harming your work (docs/design/sdem-update-framework.md, UF-01…UF-08).

  sdem releases [--since VERSION]          what each release changed: migrations, breaking changes, deprecations, actions to take
  sdem upgrade check [--root DIR | --workspace DIR …] [--repo DIR] [--from VERSION]
                                           run by the NEW version, installed side by side, against your workspaces —
                                           read-only: what upgrading means for you, before you switch

SDEM is a product you install; your work lives in your own repository. An update replaces the product and never changes your data
unless you run a recorded migration (`sdem migrate`). `upgrade check` writes nothing.
"""
import argparse, json, re, sys
from pathlib import Path

from .paths import version

NOTES = Path(__file__).parent / 'releases.json'


def _v(s):
    """'0.16.1' → (0, 16, 1); anything unreadable sorts first."""
    m = re.match(r'v?(\d+)\.(\d+)(?:\.(\d+))?', str(s or ''))
    return tuple(int(x or 0) for x in m.groups()) if m else (0, 0, 0)


def satisfies(ver, spec):
    """UF-04: whether `ver` meets a requirement such as '>=0.13', '>=0.13.0,<0.20' or '==0.16.1' (comma = and)."""
    for part in [p.strip() for p in str(spec).split(',') if p.strip()]:
        m = re.match(r'(>=|<=|==|!=|>|<)?\s*(\S+)', part)
        op, want = (m.group(1) or '=='), _v(m.group(2))
        have = _v(ver)
        ok = {'>=': have >= want, '<=': have <= want, '==': have == want, '!=': have != want, '>': have > want, '<': have < want}[op]
        if not ok: return False
    return True


def releases(since=None, until=None):
    """UF-03: the release notes after `since` up to and including `until` (default: this version), oldest first."""
    doc = json.loads(NOTES.read_text(encoding='utf-8'))
    until = until or version()
    return [r for r in doc['releases'] if (since is None or _v(r['version']) > _v(since)) and _v(r['version']) <= _v(until)]


def _from_version(repo):
    """The SDEM version the repository last used: its requirements.txt pin, else the agent files' record."""
    req = Path(repo) / 'requirements.txt'
    if req.exists():
        m = re.search(r'sdem\b[^\n]*?@v?(\d+\.\d+(?:\.\d+)?)', req.read_text(encoding='utf-8'))
        if m: return m.group(1), 'requirements.txt'
    rec = Path(repo) / 'sdem-agents.json'
    if rec.exists():
        try: return json.loads(rec.read_text(encoding='utf-8')).get('sdem_version'), 'sdem-agents.json'
        except ValueError: pass
    return None, None


def check_workspace(ws):
    """UF-01, UF-02: one workspace under this (new) version — read-only."""
    from . import profile as _p
    from .metamodel import Metamodel
    from .migrate import migrate, MigrateError
    ws = Path(ws); out = {'workspace': ws.as_posix(), 'steps': [], 'blocking': [], 'warnings': []}
    try: merged = _p.activate_from(ws)
    except _p.ProfileError as e:
        out['profile'] = {'ok': False, 'issues': str(e).split('\n')[1:] or [str(e)]}
        out['blocking'].append('the organisation profile does not pass under this version — fix sdem-profile.json (sdem profile check) before switching')
        merged = None
    else:
        out['profile'] = {'ok': True, 'name': merged['name'], 'requires_sdem': merged.get('requires_sdem')} if merged else None
    current = Metamodel.base().version
    files = {}
    for f in sorted(ws.glob('*.json')):
        try: d = json.loads(f.read_text(encoding='utf-8'))
        except ValueError: continue
        if isinstance(d, dict) and d.get('metamodel_version'): files[f.name] = d['metamodel_version']
    out['metamodel'] = {'this_version': current, 'workspace_files': files}
    if merged is not None or out['profile'] is None:
        try:
            res = migrate(ws, 'sdem upgrade check', dry_run=True)
            if res.get('files'):
                out['migration'] = {'needed': True, 'files': res['files'], 'changes': res.get('changes', {})}
                out['steps'].append(f'sdem migrate --workspace {ws.as_posix()} --person <you> --dry-run, then without --dry-run')
            else: out['migration'] = {'needed': False}
        except MigrateError as e:
            out['migration'] = {'needed': True, 'refused': str(e)}
            out['blocking'].append(f'the migration would be refused: {str(e).splitlines()[0]} — see the details, fix them under your current version, then check again')
        except ValueError as e:
            out['blocking'].append(str(e))
    if not out['blocking'] and not (out.get('migration') or {}).get('needed'):   # nothing to migrate: the workspace as this version sees it
        from .connect import estate_docs, estate_errors
        from .validate import validate
        try:
            docs, reg = estate_docs(ws)
            errs = estate_errors(docs, reg)
            if errs: out['blocking'].append(f'{len(errs)} check error(s) under this version, e.g. {errs[0][:160]}')
            warns = []; validate(reg, warnings=warns)
            dep = [w for w in warns if 'deprecated link type' in w]
            if dep: out['warnings'].append(f'{len(dep)} connection(s) use a deprecated link type — re-point or supersede them before it is removed, e.g. {dep[0][:160]}')
        except ValueError as e:
            out['blocking'].append(str(e))
    _p.deactivate()
    out['verdict'] = 'blocked' if out['blocking'] else 'migrate' if (out.get('migration') or {}).get('needed') else 'ready'
    return out


def check_agents(repo):
    """UF-02: the agent and Copilot files SDEM would update in the repository, and those your team changed (kept)."""
    from .copilot import install_agents
    repo = Path(repo)
    if not (repo / 'AGENTS.md').exists() and not (repo / '.github').exists(): return None
    res = install_agents(repo, dry_run=True)
    cp = res.get('copilot') or {}
    return {'would_update': sorted(res['written'] + [f'.github/{x}' for x in cp.get('written', [])]),
            'kept_your_changes': sorted(res['kept'] + [f'.github/{x}' for x in cp.get('kept', [])])}


def upgrade_check(workspaces, repo='.', from_version=None):
    """UF-01: what upgrading to this version means for a repository and its workspaces — read-only."""
    detected, source = _from_version(repo)
    frm = from_version or detected
    notes = releases(since=frm) if frm else releases()
    res = {'to': version(), 'from': frm, 'from_source': 'given' if from_version else source,
           'releases': [{k: r[k] for k in ('version', 'kind', 'metamodel', 'migration', 'breaking', 'deprecations', 'actions', 'summary')} for r in notes],
           'workspaces': [check_workspace(w) for w in workspaces], 'agent_files': check_agents(repo)}
    if frm and _v(frm) > _v(res['to']): res['note'] = f'this version ({res["to"]}) is older than the one you use ({frm}) — a downgrade'
    res['verdict'] = 'blocked' if any(w['verdict'] == 'blocked' for w in res['workspaces']) else 'migrate' if any(w['verdict'] == 'migrate' for w in res['workspaces']) else 'ready'
    steps = ['on a branch: change the pin in requirements.txt to @v' + res['to'] + ', then pip install -r requirements.txt']
    steps += sorted({s for w in res['workspaces'] for s in w['steps']})
    always = [a['do'] for r in notes for a in r['actions'] if a['when'] == 'always' and not a['do'].startswith('sdem migrate')]
    if any(x.startswith('sdem agents install') for x in always): steps.append('sdem agents install — your agents get this version\'s instructions (files your team changed are kept)')
    steps += sorted({x for x in always if not x.startswith('sdem agents install')})
    steps += sorted({f"if {a['when']}: {a['do']}" for r in notes for a in r['actions'] if a['when'] != 'always'})
    steps += ['sdem check --workspace <dir> for every workspace, then a pull request — CI — merge']
    res['steps'] = steps
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem upgrade', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Before you switch SDEM versions: run the NEW version, installed side by side, against your workspaces. Read-only.',
                                 epilog='Example:\n  python -m venv .sdem-next && .sdem-next/bin/pip install "sdem @ git+https://github.com/taumoeps/bian-sdem-framework@v0.18.0"\n'
                                        '  .sdem-next/bin/sdem upgrade check --root workspaces')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check', help='what upgrading to this version means for your workspaces: migrations, profile, deprecations, agent files, actions — writes nothing')
    c.add_argument('--workspace', dest='estates', action='append', metavar='DIR'); c.add_argument('--root', metavar='DIR', help='every workspace in a folder')
    c.add_argument('--repo', default='.', metavar='DIR', help='your workspace repository (requirements.txt, AGENTS.md); default the current folder')
    c.add_argument('--from', dest='frm', metavar='VERSION', help='the version you use now (default: read from requirements.txt)'); c.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    ws = list(a.estates or [])
    if a.root: ws += sorted(str(p.parent) for p in Path(a.root).glob('*/mappings.json'))
    if not ws and not a.root: ws = sorted(str(p.parent) for p in (Path(a.repo) / 'workspaces').glob('*/mappings.json'))
    res = upgrade_check(ws, a.repo, a.frm)
    if a.json: print(json.dumps(res, indent=2, ensure_ascii=False)); return 1 if res['verdict'] == 'blocked' else 0
    print(f"upgrade to SDEM {res['to']} from {res['from'] or 'an unknown version'}" + (f" ({res['from_source']})" if res['from_source'] else '') + f" — {res['verdict'].upper()}")
    if res.get('note'): print(f"NOTE: {res['note']}")
    for r in res['releases']:
        flag = ' — MIGRATION' if r['migration'] else ''
        print(f"\n  {r['version']} ({r['kind']}, metamodel {r['metamodel']}){flag}: {r['summary']}")
        for b in r['breaking']: print(f'    breaking: {b}')
        for d in r['deprecations']: print(f"    deprecated: {d['item']} (removed in metamodel {d['removed_in_metamodel']}) — {d['do']}")
        for x in r['actions']: print(f"    if {x['when']}: {x['do']}" if x['when'] != 'always' else f"    do: {x['do']}")
    for w in res['workspaces']:
        print(f"\n  workspace {w['workspace']}: {w['verdict'].upper()}" + (f" — profile {w['profile']['name']}" if w.get('profile') and w['profile'].get('ok') else ''))
        for b in w['blocking']: print(f'    BLOCKING: {b}')
        if (w.get('migration') or {}).get('files'):
            ch = w['migration'].get('changes') or {}
            print(f"    migration: {len(w['migration']['files'])} file(s) {w['migration']['files'][0]['from']} → {w['migration']['files'][0]['to']}"
                  + (f"; data changes: {', '.join(f'{k} ×{n}' for k, n in ch.items())}" if ch else '; no data changes — only the version is recorded') + ' — checked, would pass')
        for x in w['warnings']: print(f'    warning: {x}')
    if res['agent_files']:
        af = res['agent_files']
        print(f"\n  agent files: {len(af['would_update'])} would be updated by sdem agents install" + (f"; {len(af['kept_your_changes'])} your team changed are kept: {', '.join(af['kept_your_changes'][:6])}" if af['kept_your_changes'] else ''))
    print('\nsteps:'); [print(f'  {n}. {s}') for n, s in enumerate(res['steps'], 1)]
    print('\nnothing was written')
    return 1 if res['verdict'] == 'blocked' else 0


def releases_main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem releases', description='What each SDEM release changed: migrations, breaking changes, deprecations and the actions to take.')
    ap.add_argument('--since', metavar='VERSION', help='only releases after this one, e.g. the version you use'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rs = releases(since=a.since)
    if a.json: print(json.dumps({'this_version': version(), 'releases': rs}, indent=2, ensure_ascii=False)); return 0
    for r in rs:
        print(f"{r['version']}  {r['date']}  {r['kind']:<5}  metamodel {r['metamodel']}{'  MIGRATION' if r['migration'] else ''}  — {r['summary']}")
        for b in r['breaking']: print(f'    breaking: {b}')
        for x in r['actions']: print(f"    {'do' if x['when'] == 'always' else 'if ' + x['when']}: {x['do']}")
    return 0
