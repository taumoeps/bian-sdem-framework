"""`sdem copilot install` — put SDEM's Copilot instructions, agents, prompts and skills into a workspace repository
(docs/design/sdem-copilot-install-design.md).

Copilot reads them only from the folder open in VS Code — for real work, the private workspace repository. They ship with
SDEM; references to files of the SDEM project become links to those files at the installed SDEM version on GitHub.

  cd <your workspace repository>
  sdem copilot install [--dry-run] [--force]
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

from .paths import CHECKOUT, DATA_ROOT, REPO_URL, version as sdem_version

EXAMPLE_ONLY = {'prompts/example3-rehost.prompt.md'}              # CI-D3: works only on the made-up example
RECORD = 'sdem-copilot.json'
_PROJECT = r'(?:docs|metamodel|schema|examples|templates)/(?:[A-Za-z0-9_./-]*[A-Za-z0-9_/-])?'


def source():
    """SDEM's own Copilot files: `.github/` in a checkout, `sdem/data/copilot/` when installed (CI-01)."""
    root = DATA_ROOT / '.github' if CHECKOUT else DATA_ROOT / 'copilot'
    if not (root / 'copilot-instructions.md').exists():
        raise ValueError('the Copilot files are not installed with this SDEM — reinstall it (pip install -r requirements.txt)')
    return root


def files():
    """Relative path → path, for every Copilot file installed into a workspace (not CI workflows or code owners)."""
    root = source()
    out = {'copilot-instructions.md': root / 'copilot-instructions.md'}
    for sub in ('agents', 'prompts', 'skills'):
        for p in sorted((root / sub).rglob('*')):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and rel not in EXAMPLE_ONLY: out[rel] = p
    return out


def _url(path, ver):
    kind = 'tree' if path.endswith('/') or '.' not in path.rsplit('/', 1)[-1] else 'blob'
    return f"{REPO_URL}/{kind}/v{ver}/{path.rstrip('/')}"


def rewrite(text, rel, ver):
    """CI-03: references to SDEM-project files become links to them at version `ver`."""
    here = Path(rel).parent

    def link(m):                                           # [label](relative/path) that leaves .github → a web link
        label, target = m.group(1), m.group(2)
        if re.match(r'^(https?:|mailto:|#)', target): return m.group(0)
        path, sep, frag = target.partition('#')
        resolved = Path('.github', here, path)
        parts = []
        for part in resolved.parts:
            if part == '..':
                if parts: parts.pop()
            elif part != '.': parts.append(part)
        repo_path = '/'.join(parts)
        if repo_path.startswith('.github/'): return m.group(0)   # another Copilot file — installed alongside
        return f'{label}({_url(repo_path, ver)}{sep}{frag})'

    text = re.sub(r'(\[[^\]]*\])\(([^)\s]+)\)', link, text)
    text = re.sub(r'(?<![\[(/\w])`(' + _PROJECT + r')`(?!\])', lambda m: f'[`{m.group(1)}`]({_url(m.group(1), ver)})', text)
    return text


def _sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()


def plan(target, ver=None, force=False):
    """What an install into `target` would do: (writes {rel: text}, kept [rel], record)."""
    ver = ver or sdem_version()
    gh = Path(target) / '.github'
    old = {}
    if (gh / RECORD).exists():
        try: old = json.loads((gh / RECORD).read_text(encoding='utf-8')).get('files', {})
        except ValueError: old = {}
    writes, kept, record = {}, [], {}
    for rel, src in files().items():
        text = src.read_text(encoding='utf-8')
        if src.suffix == '.md': text = rewrite(text, rel, ver)
        dest = gh / rel
        if dest.exists():
            current = dest.read_text(encoding='utf-8')
            changed_by_team = rel not in old or _sha(current) != old[rel]
            if current != text and changed_by_team and not force:
                kept.append(rel); record[rel] = old.get(rel) or _sha(current); continue
        writes[rel] = text; record[rel] = _sha(text)
    return writes, kept, {'sdem_version': ver, 'files': dict(sorted(record.items()))}


def install(target='.', dry_run=False, force=False):
    target = Path(target)
    if not target.is_dir():
        from .errors import SdemError
        raise SdemError('not_found', f'{target}: no such folder', 'give --to an existing folder: your workspace repository')
    writes, kept, record = plan(target, force=force)
    gh = target / '.github'
    changed = [r for r, t in writes.items() if not (gh / r).exists() or (gh / r).read_text(encoding='utf-8') != t]
    if not dry_run:
        from .files import Batch
        b = Batch()
        for rel, text in writes.items(): b.text(gh / rel, text)
        b.json(gh / RECORD, record); b.commit()
    return {'target': str(gh), 'version': record['sdem_version'], 'written': sorted(changed), 'unchanged': sorted(set(writes) - set(changed)),
            'kept': sorted(kept), 'dry_run': dry_run}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem copilot', description="Put SDEM's Copilot instructions, agents, prompts and skills into your workspace repository — "
                                 'the folder you open in VS Code — matching this SDEM version.',
                                 epilog='Example:\n  cd <your workspace repository>\n  sdem copilot install --dry-run\n  sdem copilot install',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('install', help='write .github/copilot-instructions.md, agents/, prompts/, skills/ into a repository')
    i.add_argument('--to', default='.', metavar='DIR', help='the repository (default: the current folder)')
    i.add_argument('--dry-run', action='store_true', help='show what would change; write nothing')
    i.add_argument('--force', action='store_true', help='also replace files your team has changed since the last install')
    i.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    res = install(a.to, a.dry_run, a.force)
    if a.json: print(json.dumps(res, indent=2)); return 0
    verb = 'would write' if a.dry_run else 'wrote'
    print(f"{verb} {len(res['written'])} Copilot file(s) for SDEM {res['version']} into {res['target']}" + (f"; {len(res['unchanged'])} already current" if res['unchanged'] else ''))
    for r in res['written']: print(f'  {r}')
    if res['kept']:
        print(f"kept {len(res['kept'])} file(s) your team changed (replace them with --force):")
        for r in res['kept']: print(f'  {r}')
    if not a.dry_run: print('next: commit .github/ on a branch; in VS Code, reload the window so Copilot sees the agents and prompts')
    return 0


PLATFORMS = ('copilot', 'claude', 'codex', 'gemini')
AGENTS_RECORD = 'sdem-agents.json'


def agents_source():
    """The platform-neutral agent files: `templates/agents/` in a checkout, `sdem/data/agents/` when installed (AF-09)."""
    root = DATA_ROOT / 'templates' / 'agents' if CHECKOUT else DATA_ROOT / 'agents'
    if not (root / 'AGENTS.md').exists():
        raise ValueError('the agent files are not installed with this SDEM — reinstall it (pip install -r requirements.txt)')
    return root


def agent_files(platforms):
    """Installed path → (source, the path it is rewritten as) for each platform's files. One AGENTS.md for all; the skills are
    SDEM's one set (.github/skills), copied into each platform's skills folder; Claude Code and Gemini CLI get a pointer to AGENTS.md."""
    a = agents_source()
    skills = {rel: p for rel, p in files().items() if rel.startswith('skills/')}
    out = {'AGENTS.md': (a / 'AGENTS.md', 'AGENTS.md')}
    if 'claude' in platforms:
        out['CLAUDE.md'] = (a / 'CLAUDE.md', 'CLAUDE.md')
        out.update({f'.claude/{rel}': (p, rel) for rel, p in skills.items()})
    if 'codex' in platforms or 'gemini' in platforms:
        out.update({f'.agents/{rel}': (p, rel) for rel, p in skills.items()})
    if 'gemini' in platforms:
        out['.gemini/settings.json'] = (a / 'gemini-settings.json', None)
    return out


def install_agents(target='.', platforms=PLATFORMS, dry_run=False, force=False):
    """AF-09: the instructions and skills every agent platform reads, from one source, matching this SDEM version. A file your
    team changed since the last install is kept (replace it with force); Copilot's own files come from `install`."""
    target = Path(target)
    if not target.is_dir():
        from .errors import SdemError
        raise SdemError('not_found', f'{target}: no such folder', 'give --to an existing folder: your workspace repository')
    ver = sdem_version()
    old = {}
    if (target / AGENTS_RECORD).exists():
        try: old = json.loads((target / AGENTS_RECORD).read_text(encoding='utf-8')).get('files', {})
        except ValueError: old = {}
    writes, kept, record = {}, [], {}
    for rel, (src, as_rel) in agent_files(platforms).items():
        text = src.read_text(encoding='utf-8')
        if as_rel: text = rewrite(text, as_rel, ver)
        dest = target / rel
        if dest.exists():
            current = dest.read_text(encoding='utf-8')
            if current != text and (rel not in old or _sha(current) != old[rel]) and not force:
                kept.append(rel); record[rel] = old.get(rel) or _sha(current); continue
        writes[rel] = text; record[rel] = _sha(text)
    changed = [r for r, t in writes.items() if not (target / r).exists() or (target / r).read_text(encoding='utf-8') != t]
    if not dry_run:
        from .files import Batch
        b = Batch()
        for rel, text in writes.items(): b.text(target / rel, text)
        b.json(target / AGENTS_RECORD, {'sdem_version': ver, 'platforms': sorted(platforms), 'files': dict(sorted(record.items()))}); b.commit()
    res = {'target': str(target), 'version': ver, 'platforms': sorted(platforms), 'written': sorted(changed),
           'unchanged': sorted(set(writes) - set(changed)), 'kept': sorted(kept), 'dry_run': dry_run}
    if '.gemini/settings.json' in kept:
        res['notes'] = ['.gemini/settings.json is your own — add "AGENTS.md" to its context.fileName list so Gemini CLI reads the SDEM instructions']
    if 'copilot' in platforms: res['copilot'] = install(target, dry_run, force)
    return res


def agents_main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem agents', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="Put SDEM's instructions and skills for AI agents into your workspace repository — one AGENTS.md for every "
                                             'agent, the same skills in each platform\'s folder, and Copilot\'s own files — matching this SDEM version.',
                                 epilog='Example:\n  cd <your workspace repository>\n  sdem agents install --dry-run\n  sdem agents install --platform claude codex')
    sub = ap.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('install', help='write AGENTS.md, CLAUDE.md, .claude/skills, .agents/skills, .gemini/settings.json and .github/ (Copilot)')
    i.add_argument('--to', default='.', metavar='DIR', help='the repository (default: the current folder)')
    i.add_argument('--platform', nargs='+', choices=PLATFORMS, default=list(PLATFORMS), help='which agents (default: all four)')
    i.add_argument('--dry-run', action='store_true', help='show what would change; write nothing')
    i.add_argument('--force', action='store_true', help='also replace files your team has changed since the last install')
    i.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    res = install_agents(a.to, a.platform, a.dry_run, a.force)
    if a.json: print(json.dumps(res, indent=2)); return 0
    verb = 'would write' if a.dry_run else 'wrote'
    cp = res.get('copilot') or {'written': [], 'kept': []}
    print(f"{verb} {len(res['written']) + len(cp['written'])} agent file(s) for SDEM {res['version']} into {res['target']} ({', '.join(res['platforms'])})")
    for r in res['written'] + [f".github/{x}" for x in cp['written']]: print(f'  {r}')
    for r in res['kept'] + [f".github/{x}" for x in cp['kept']]: print(f'kept (your team changed it; replace with --force): {r}')
    for n in res.get('notes', []): print(f'NOTE: {n}')
    if not a.dry_run: print('next: commit them on a branch; each agent reads its files when it next starts in this folder')
    return 0


if __name__ == '__main__':
    sys.exit(main())
