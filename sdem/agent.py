"""Built for agents too (docs/design/sdem-agent-cli-spec.md, AF-01…AF-06) — what every command gets from `sdem` itself:

  --json      the result as JSON on stdout. An object carries "sdem": {"version", "command"}; a failure is JSON too —
              {"sdem": …, "error": {"code", "exit", "message", "hint", "details"}} — never only prose on stderr (AG-01, AG-05).
              A command with no JSON of its own gives {"sdem": …, "ok", "exit", "output": [its lines], "wrote": [files]} (AG-03).
  --limit N   with --json: every list in the result cut to N items; what was cut is listed under "truncated" (AG-02).
  --dry-run   what the command would write, nothing written: a command with its own --dry-run uses it; any other runs with
              every file write caught and listed under "would_write" — only the temporary files it makes itself are written (AG-04).
  sdem commands --json   every command, its options and what it supports (AG-06).

Notes (baseline:, WARN:, NOTE:) stay on stderr; stdout carries only the result.
"""
import argparse, builtins, contextlib, io, json, os, re, shutil, sys, tempfile
from pathlib import Path

from .paths import version

AGENT_FLAGS = ('--json', '--dry-run', '--limit')


class Sink(io.StringIO):
    """A file opened for writing in a dry run: written to nowhere."""
    def __exit__(self, *a): self.close()


@contextlib.contextmanager
def sandbox():
    """Catch every file write, folder made or file removed — except in the temporary files and folders the command itself makes
    while it runs; yield the list of what was caught."""
    caught, made = [], []
    def outside(p):
        try: r = os.path.realpath(os.fspath(p))
        except TypeError: return False
        return not any(r == m or r.startswith(m + os.sep) for m in made)
    def note(kind, p):
        s = os.path.relpath(os.fspath(p)) if not os.path.isabs(os.fspath(p)) or os.fspath(p).startswith(os.getcwd()) else os.fspath(p)
        if (kind, s) not in caught: caught.append((kind, s))
    from . import files as F
    saved = {'open': builtins.open, 'write_text': Path.write_text, 'mkdir': Path.mkdir, 'unlink': Path.unlink, 'replace': os.replace,
             'rmtree': shutil.rmtree, 'copy2': shutil.copy2, 'copy': shutil.copy, 'f_write': F.write_text, 'commit': F.Batch.commit,
             'mkdtemp': tempfile.mkdtemp, 'mkstemp': tempfile.mkstemp}
    def _mkdtemp(*a, **k):
        d = saved['mkdtemp'](*a, **k); made.append(os.path.realpath(d)); return d
    def _mkstemp(*a, **k):
        fd, f = saved['mkstemp'](*a, **k); made.append(os.path.realpath(f)); return fd, f
    def _open(file, mode='r', *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)) and any(c in mode for c in 'wax+') and outside(file):
            note('write', file); return Sink()
        return saved['open'](file, mode, *a, **k)
    def _write_text(self, data, *a, **k):
        if outside(self): note('write', self); return len(data)
        return saved['write_text'](self, data, *a, **k)
    def _mkdir(self, *a, **k):
        if outside(self):
            if not self.exists(): note('folder', self)
            return None
        return saved['mkdir'](self, *a, **k)
    def _unlink(self, *a, **k):
        if outside(self): note('remove', self); return None
        return saved['unlink'](self, *a, **k)
    def _replace(src, dst):
        if outside(dst): note('write', dst); return None
        return saved['replace'](src, dst)
    def _rmtree(p, *a, **k):
        if outside(p): note('remove', p); return None
        return saved['rmtree'](p, *a, **k)
    def _copy(src, dst, *a, **k):
        if outside(dst): note('write', dst); return dst
        return saved['copy2'](src, dst, *a, **k)
    def _f_write(path, text):
        if outside(path): note('write', path); return None
        return saved['f_write'](path, text)
    def _commit(self):
        for path, _ in self.items:
            if outside(path): note('write', path)
        inside = [(p, t) for p, t in self.items if not outside(p)]
        if inside:
            b = F.Batch(); b.items = inside; saved['commit'](b)
    builtins.open, Path.write_text, Path.mkdir, Path.unlink, os.replace = _open, _write_text, _mkdir, _unlink, _replace
    shutil.rmtree, shutil.copy2, shutil.copy, F.write_text, F.Batch.commit = _rmtree, _copy, _copy, _f_write, _commit
    tempfile.mkdtemp, tempfile.mkstemp = _mkdtemp, _mkstemp
    try:
        yield caught
    finally:
        builtins.open, Path.write_text, Path.mkdir, Path.unlink, os.replace = saved['open'], saved['write_text'], saved['mkdir'], saved['unlink'], saved['replace']
        shutil.rmtree, shutil.copy2, shutil.copy, F.write_text, F.Batch.commit = saved['rmtree'], saved['copy2'], saved['copy'], saved['f_write'], saved['commit']
        tempfile.mkdtemp, tempfile.mkstemp = saved['mkdtemp'], saved['mkstemp']


class Tee(io.StringIO):
    """stderr kept, and still shown."""
    def __init__(self, show): super().__init__(); self.show = show
    def write(self, s): self.show.write(s); return super().write(s)


def command_of(argv):
    """The command path an agent called, e.g. 'trace', 'aid confirm', 'bian import'."""
    words = [argv[0]]
    if len(argv) > 1 and re.fullmatch(r'[a-z][a-z-]+', argv[1]) and argv[0] in SUBCOMMANDED: words.append(argv[1])
    return ' '.join(words)


SUBCOMMANDED = {'aid', 'bian', 'change', 'copilot', 'model', 'transform', 'work'}


def supports(run, argv, flag):
    """Does the command itself take this flag? Read from its own --help (built once per call)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try: run([a for a in argv if a not in AGENT_FLAGS] + ['--help'])
        except SystemExit: pass
        except Exception: return False
    return re.search(rf'(^|[\s\[,]){re.escape(flag)}([\s\],=]|$)', buf.getvalue(), re.M) is not None


def _limit_arg(argv):
    if '--limit' not in argv: return argv, None
    i = argv.index('--limit')
    if i + 1 >= len(argv) or not argv[i + 1].isdigit(): raise ValueError('--limit needs a whole number, e.g. --limit 20')
    return argv[:i] + argv[i + 2:], int(argv[i + 1])


def limit(obj, n, path='', cut=None):
    """Every list cut to n items; cut records path → full length."""
    cut = {} if cut is None else cut
    if isinstance(obj, list):
        if len(obj) > n: cut[path or '$'] = len(obj)
        return [limit(x, n, f'{path}[{i}]', cut) for i, x in enumerate(obj[:n])], cut
    if isinstance(obj, dict):
        return {k: limit(v, n, f'{path}.{k}' if path else k, cut)[0] for k, v in obj.items()}, cut
    return obj, cut


CODES = [  # (pattern in the message, code) — first match wins
    (r'^usage:|unrecognized arguments|the following arguments are required|invalid choice|expected one argument|needs a whole number', 'usage'),
    (r'a person|\(CTL-21\)|person\'s decision', 'needs_person'),
    (r'not valid JSON|fails the dataset check|not an A\d dataset|is not valid', 'invalid_input'),
    (r'not found|No such file|does not exist|is not an instance|not a workspace|no workspace here|unknown', 'not_found'),
    (r'already exists', 'exists'),
    (r'internal error', 'internal'),
]


def fallback_hint(kind, command, msg):
    """The usual next step for an error the command gave no hint for."""
    if kind == 'usage': return f'sdem {command} --help'
    if kind == 'needs_person': return "give a person's own name with --person or --reviewer: decisions on record are a person's, not an agent's (CTL-21)"
    if kind == 'not_found' and 'workspace' in msg: return 'sdem new --workspace <dir> --person <name> starts one'
    if kind == 'not_found' and command in ('trace', 'impact', 'explain', 'query'): return 'sdem query --graph <dir> --json lists the record ids'
    if kind == 'invalid_input': return 'sdem check --workspace <dir> --json lists every problem'
    if kind == 'internal': return 'set SDEM_DEBUG=1 and run again for the details; please report it'
    return None


def error_json(code, err_text, command):
    lines = [l for l in err_text.splitlines() if l.strip() and not re.match(r'(baseline:|WARN:|NOTE:)', l)]
    errs = [l for l in lines if l.startswith('ERROR') or re.search(r'error:', l)] or lines
    msg = re.sub(r'^(ERROR:\s*|sdem[\w -]*: error:\s*)', '', errs[0]).strip() if errs else f'exit {code}, no message'
    kind = 'internal' if code == 3 else next((c for p, c in CODES if re.search(p, err_text, re.I | re.M)), 'refused' if code == 1 else 'input')
    hint = re.search(r'(sdem [a-z][^;)\n`]*)', ' '.join(errs[1:] + [msg]))
    hint = hint.group(1).strip() if hint else fallback_hint(kind, command, msg)
    return {'sdem': {'version': version(), 'command': command},
            'error': {'code': kind, 'exit': code, 'message': msg, 'hint': hint,
                      'details': [re.sub(r'^ERROR:\s*', '', l) for l in errs[1:6]]}}


def run(fn, argv):
    """Run one sdem command for an agent: --json, --limit and --dry-run handled here when the command does not itself (AF-01…AF-05)."""
    want_json, want_dry = '--json' in argv, '--dry-run' in argv
    command = command_of(argv)
    try: argv, n = _limit_arg(argv)
    except ValueError as e:
        if want_json: print(json.dumps(error_json(2, f'ERROR: {e}', command), indent=2)); return 2
        print(f'ERROR: {e}', file=sys.stderr); return 2
    if n is not None and not want_json:
        print('ERROR: --limit works with --json', file=sys.stderr); return 2
    native_json = want_json and supports(fn, argv, '--json')
    native_dry = want_dry and supports(fn, argv, '--dry-run')
    call = [a for a in argv if (a != '--json' or native_json) and (a != '--dry-run' or native_dry)]
    out, err = io.StringIO(), Tee(sys.stderr)
    caught = []
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            if want_dry and not native_dry:
                with sandbox() as caught: code = fn(call)
            else: code = fn(call)
        except SystemExit as e: code = e.code if isinstance(e.code, int) else (0 if e.code is None else 2)
    text = out.getvalue()
    dry = {'dry_run': True, 'would_write': [f'{k}: {p}' for k, p in caught]} if want_dry and not native_dry else None
    if not want_json:
        sys.stdout.write(text)
        if dry: print(f"DRY RUN — nothing written; it would have written {len(caught)} item(s)" + ''.join(f'\n  {x}' for x in dry['would_write']))
        return code
    if code != 0 and not text.strip():
        print(json.dumps(error_json(code, err.getvalue(), command), indent=2, ensure_ascii=False)); return code
    try: data = json.loads(text) if native_json else None
    except ValueError: data = None
    if data is None:   # AG-03: a command with no JSON of its own — its lines, and the files it says it wrote
        lines = [l for l in text.splitlines() if l.strip()]
        data = {'ok': code == 0, 'exit': code, 'output': lines,
                'wrote': [re.sub(r'^(wrote|written to)\s+', '', l).strip() for l in lines if re.match(r'(wrote|written to)\s', l)]}
        if code != 0: data['error'] = error_json(code, err.getvalue() + '\n' + text, command)['error']
    cut = {}
    if n is not None: data, cut = limit(data, n)
    if isinstance(data, dict):
        data = {'sdem': {'version': version(), 'command': command}, **{k: v for k, v in data.items() if k != 'sdem'}}
        if cut: data['truncated'] = cut
        if dry: data.update(dry)
        warns = [l for l in err.getvalue().splitlines() if l.startswith('WARN')]
        if warns: data.setdefault('warnings', warns)
    elif cut or dry:
        print(f"NOTE: {'; '.join(x for x in ([f'cut to {n}: ' + ', '.join(f'{k} ({v})' for k, v in cut.items())] if cut else []) + (['dry run: ' + ', '.join(dry['would_write']) or 'nothing'] if dry else []))}", file=sys.stderr)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def describe(parser):
    """One parser as data: options, positionals, subcommands."""
    opts, pos, subs = [], [], {}
    for a in parser._actions:
        if isinstance(a, argparse._HelpAction): continue
        if isinstance(a, argparse._SubParsersAction):
            helps = {c.dest: c.help for c in a._choices_actions}
            for name, p in a.choices.items():
                subs[name] = describe(p)
                subs[name]['description'] = subs[name]['description'] or helps.get(name)
            continue
        d = {'name': a.option_strings[0] if a.option_strings else a.dest, 'takes_value': a.nargs != 0,
             'required': bool(a.required), 'help': (a.help or '').replace('%(default)s', str(a.default)) or None}
        if a.option_strings and len(a.option_strings) > 1: d['aliases'] = a.option_strings[1:]
        if a.choices: d['choices'] = list(a.choices)
        if a.nargs in ('*', '+'): d['many'] = True
        (opts if a.option_strings else pos).append(d)
    out = {'description': parser.description, 'positionals': pos, 'options': opts}
    if subs: out['subcommands'] = subs
    return out


class _Got(Exception):
    def __init__(self, parser): self.parser = parser


def parser_of(fn, argv):
    """The argparse parser a command builds — caught as it parses, so nothing runs."""
    saved = argparse.ArgumentParser.parse_args, argparse.ArgumentParser.parse_known_args
    def grab(self, *a, **k): raise _Got(self)
    argparse.ArgumentParser.parse_args = argparse.ArgumentParser.parse_known_args = grab
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            fn(argv)
    except _Got as g: return g.parser
    except (Exception, SystemExit): return None
    finally: argparse.ArgumentParser.parse_args, argparse.ArgumentParser.parse_known_args = saved
    return None


PROBES = {'aid': [('aid', ['--workspace', 'W']), ('aid confirm', ['confirm']), ('aid reject', ['reject']), ('aid', ['project'])],
          'bian': [('bian', []), ('bian inference', ['inference'])]}
# how to reach each entry point of a command whose parsers one call does not show: (its name, the arguments that reach it)


def catalogue(journeys, run_one):
    """AG-06: every command — what it does, an example, its options, and what it supports."""
    cmds = {}
    for name, (journey, what, module, lead, *_rest) in journeys.items():
        example = _rest[-1] if _rest else None
        for path, probe in PROBES.get(name) or [(name, [])]:
            p = parser_of(lambda a, n=name: run_one([n] + a), probe)
            d = describe(p) if p else {'description': None, 'positionals': [], 'options': []}
            subs = d.pop('subcommands', None) or {}
            if lead and lead[0] in subs:            # one parser shared by several commands (sdem-graph): this command's part only
                d = subs[lead[0]]; subs = {}
            for s, sd in subs.items():
                if f'{path} {s}' not in cmds: cmds[f'{path} {s}'] = _entry(sd, journey, None)
            if subs and path in cmds and 'group' not in cmds[path]: del cmds[path]
            if path not in cmds:
                cmds[path] = _entry(d, journey, example if path == name else None, what if path == name else None)
                if subs: cmds[path] = {**{k: cmds[path][k] for k in ('journey', 'description', 'example')}, 'group': sorted(f'{path} {x}' for x in subs)}
    return {'sdem': {'version': version(), 'command': 'commands'},
            'agent_flags': {'--json': 'the result as JSON on stdout; failures as {"error": {code, exit, message, hint, details}}',
                            '--limit N': 'with --json: every list cut to N items, listed under "truncated"',
                            '--dry-run': 'nothing written; what would be written is listed under "would_write"'},
            'exit_codes': {'0': 'ok', '1': 'refused by a check', '2': 'usage or input error', '3': 'internal error'},
            'error_codes': sorted({c for _, c in CODES} | {'refused', 'input'}),
            'decisions_need_a_person': 'approve, load, new, aid confirm/reject and other recorded decisions take --person/--reviewer: a person\'s own name, never an agent\'s (CTL-21)',
            'commands': dict(sorted(cmds.items()))}


def _entry(d, journey, example, what=None):
    names = {o['name'] for o in d['options']}
    return {'journey': journey, 'description': what or d.get('description'), 'example': example,
            'json': 'native' if '--json' in names else 'wrapped', 'dry_run': 'native' if '--dry-run' in names else 'sandbox',
            'positionals': d['positionals'], 'options': d['options']}
