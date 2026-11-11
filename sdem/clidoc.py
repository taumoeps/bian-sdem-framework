"""Generate docs/reference/cli-reference.md — every sdem command and subcommand, its options, its example, and what it needs from a
person — from the same catalogue as `sdem commands --json` (CR-01…CR-03). Never edited by hand: `sdem model regenerate` writes it and
`sdem model check` (CI) fails when it is stale, so the reference cannot fall behind the code.

  python -m sdem.clidoc            # write it
  python -m sdem.clidoc --check    # is it current?
"""
import argparse, contextlib, io, re

from .paths import DATA_ROOT as ROOT

OUT = ROOT / 'docs' / 'reference' / 'cli-reference.md'
JOURNEYS = [('J9', 'Start and onboard', 'start a workspace or an organisation, bring in designs, upgrade'),
            ('J1', 'Check and specify', "check the data; the organisation's profile, standards and patterns"),
            ('J2', 'Link the architectures', 'propose links between the layers'),
            ('J3', 'Review and approve', 'a person decides on proposed links'),
            ('J4', 'Build the knowledge graph', 'the graph store, queries and baselines'),
            ('J5', 'Trace, impact and requirements', 'what depends on what, what a change affects'),
            ('J6', 'Infer with AID', 'fill the gaps, confirm or reject'),
            ('J7', 'See it', 'pages, diagrams, documents'),
            ('J8', 'Explain', 'why a record or link exists'),
            ('AG', 'Agents and change', 'change sets, events, work items, agent setup'),
            ('—', 'SDEM maintenance', "the owner's commands in SDEM's own repository")]
PERSON = re.compile(r'--(person|reviewer)\b')


def _catalogue():
    from . import agent
    from .cli import JOURNEYS as J, _run
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return agent.catalogue({k: v for k, v in J.items() if k != 'commands'}, _run)


def _md(s):
    return (s or '').replace('|', '\\|').replace('\n', ' ').strip()


def _anchor(name):
    return 'sdem-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _usage(name, c):
    parts = [f'sdem {name}']
    for p in c.get('positionals', []):
        parts.append(f"<{p['name']}>" if p.get('required', True) else f"[<{p['name']}>]")
    for o in c.get('options', []):
        if o['name'] in ('--json', '-h', '--help'): continue
        v = f" {o['name'].lstrip('-').upper().replace('-', '_')}" if o.get('takes_value') else ''
        if o.get('choices'): v = ' {' + ','.join(map(str, o['choices'])) + '}'
        t = o['name'] + v + (' …' if o.get('many') else '')
        parts.append(t if o.get('required') else f'[{t}]')
    return ' '.join(parts)


def render():
    from .cli import ESTATE_COMMANDS
    cat = _catalogue(); cmds = cat['commands']
    L = ['# SDEM CLI reference', '',
         '> **Generated** from the code by `sdem model regenerate` (`sdem/clidoc.py`), from the same catalogue as `sdem commands --json`; '
         '`sdem model check` fails in CI when it is stale — **do not edit by hand**. Each command\'s `--help` has the same options and a worked example. '
         'For *when* to use which command, in order, see the [scenarios](../sdem-scenarios.md); for what each does to your data, the '
         '[user guide](../sdem-workbench-user-guide.md#7-command-reference).', '',
         f'{len(cmds)} commands and subcommands.', '',
         '## Every command takes', '',
         '| Option | What it does |', '|---|---|']
    L += [f'| `{k}` | {_md(v)} |' for k, v in cat['agent_flags'].items()]
    L += ['', '**Exit codes:** ' + ' · '.join(f'`{k}` {v}' for k, v in cat['exit_codes'].items()) + '. '
          '**Error codes** (with `--json`, in `{"error": {"code", …}}`): ' + ', '.join(f'`{c}`' for c in cat['error_codes']) + '.', '',
          f"**A person's decision:** {_md(cat['decisions_need_a_person'])}. Commands below marked 👤 take such a name.", '',
          '## Index', '']
    groups = {j: [] for j, _, _ in JOURNEYS}
    for n, c in cmds.items(): groups.setdefault(c.get('journey') or '—', []).append(n)
    for j, title, what in JOURNEYS:
        names = sorted(groups.get(j, []))
        if not names: continue
        L += [f'### {j} · {title}', '', f'*{what}*', '', '| Command | What it does |', '|---|---|']
        for n in names:
            c = cmds[n]
            mark = ' 👤' if any(PERSON.match(o['name']) for o in c.get('options', [])) else ''
            L.append(f"| [`sdem {n}`](#{_anchor(n)}){mark} | {_md((c.get('description') or '').split(' — ')[0])[:160] or '—'} |")
        L.append('')
    L += ['## Commands', '']
    for n in sorted(cmds):
        c = cmds[n]
        L += [f'### sdem {n}', '', f'<a id="{_anchor(n)}"></a>', '']
        if c.get('description'): L += [_md(c['description']), '']
        if 'group' in c:
            L += ['Subcommands: ' + ' · '.join(f'[`sdem {g}`](#{_anchor(g)})' for g in c['group']), '']
            if not (c.get('options') or c.get('positionals')): continue
        L += ['```', _usage(n, c), '```', '']
        flags = [f"JSON: {c.get('json', '—')}", f"dry run: {c.get('dry_run', '—')}"]
        L += ['*' + ' · '.join(flags) + (' · 👤 a person\'s own name' if any(PERSON.match(o['name']) for o in c.get('options', [])) else '') + '*', '']
        rows = [(f"`<{p['name']}>`", 'yes' if p.get('required', True) else '', p.get('help')) for p in c.get('positionals', [])]
        common = {k.split()[0]: v for k, v in cat['agent_flags'].items()}
        rows += [(', '.join(f'`{x}`' for x in [o['name']] + o.get('aliases', [])) + (f" {{{', '.join(map(str, o['choices']))}}}" if o.get('choices') else ''),
                  'yes' if o.get('required') else '', o.get('help') or common.get(o['name']))
                 for o in c.get('options', []) if o['name'] not in ('-h', '--help')]
        if n in ESTATE_COMMANDS:
            rows.append(('`--workspace`', '', 'the workspace folder, in place of the list of files (its layer datasets and mappings.json)'))
        if rows:
            L += ['| Argument | Required | What it is |', '|---|---|---|'] + [f'| {a} | {r} | {_md(h) or "—"} |' for a, r, h in rows] + ['']
        if c.get('example'): L += ['Example:', '', '```bash', c['example'], '```', '']
    return '\n'.join(L).rstrip() + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-clidoc'); ap.add_argument('--check', action='store_true'); a = ap.parse_args(argv)
    t = render()
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding='utf-8') == t
        print(f"{OUT.name}: {'up to date' if ok else 'STALE: regenerate with sdem model regenerate'}"); return 0 if ok else 1
    OUT.write_text(t, encoding='utf-8'); print(f'wrote {OUT.relative_to(ROOT)}'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
