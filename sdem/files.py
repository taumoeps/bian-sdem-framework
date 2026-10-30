"""Safe file writes: a file is written to a temporary copy beside it and moved into place in one step (os.replace), so a
crash or a full disk never leaves a half-written file. `Batch` writes several files all-or-nothing as far as the file
system allows: every file is written to its temporary copy first, and only then are they moved into place."""
import datetime, hashlib, json, os, sys, tempfile
from pathlib import Path

LEDGER = 'sdem-ledger.json'   # in a workspace: each layer file and the registry as SDEM last wrote it (AF-07)
TRACKED = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json')


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + '\n'


def _mode(path):
    """The permissions the file should have: an existing file's own, else what a normal write would give (0666 less the
    umask). mkstemp creates its temporary copy as 0600 — moved into place as is, every file SDEM wrote was owner-only."""
    try: return os.stat(path).st_mode & 0o7777
    except FileNotFoundError:
        umask = os.umask(0); os.umask(umask)
        return 0o666 & ~umask


def _stage(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f: f.write(text)   # LF on every platform (AF-10)
        os.chmod(tmp, _mode(path))
    except BaseException:
        if os.path.exists(tmp): os.unlink(tmp)
        raise
    return tmp


def write_text(path, text):
    path = Path(path)
    tmp = _stage(path, text)
    try:
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp): os.unlink(tmp)
        raise
    if path.name in TRACKED: record([path])


def write_json(path, obj):
    write_text(path, dumps(obj))


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _command():
    args = [a for a in sys.argv[1:3] if not a.startswith('-')]
    return 'sdem ' + ' '.join(args) if args else 'sdem'


def record(paths, by=None, note=None):
    """AF-07: note in each workspace's ledger the files just written — by SDEM, or a person's edit accepted with `sdem change adopt`."""
    groups = {}
    for p in map(Path, paths):
        if p.name in TRACKED and p.exists(): groups.setdefault(p.parent, []).append(p)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    for d, ps in groups.items():
        if not ((d / 'mappings.json').exists() and ((d / 'workspace.json').exists() or (d / LEDGER).exists())): continue   # workspaces only
        f = d / LEDGER
        try: led = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
        except ValueError: led = {}
        led['format'] = 'sdem-ledger/1'
        files = led.setdefault('files', {})
        for p in ps:
            files[p.name] = {'sha256': _sha(p), 'by': by or _command(), 'at': now, **({'note': note} if note else {})}
        led['files'] = dict(sorted(files.items()))
        write_text(f, dumps(led))


def unrecorded(workspace):
    """AF-07: the tracked files changed since SDEM last wrote them (by hand, or by an agent editing files directly) — or None
    when the workspace has no ledger yet (started before v0.9.13)."""
    f = Path(workspace) / LEDGER
    if not f.exists(): return None
    try: files = json.loads(f.read_text(encoding='utf-8')).get('files', {})
    except ValueError: return None
    out = []
    for name in TRACKED:
        p = Path(workspace) / name
        if not p.exists(): continue
        last = files.get(name)
        if not last or last.get('sha256') != _sha(p):
            out.append({'file': name, 'last_written_by': (last or {}).get('by'), 'at': (last or {}).get('at')})
    return out


class Batch:
    """Collect writes; `commit()` writes every temporary copy, then moves them all into place."""
    def __init__(self): self.items = []
    def json(self, path, obj): self.items.append((Path(path), dumps(obj)))
    def text(self, path, text): self.items.append((Path(path), text))

    def commit(self):
        staged = []
        try:
            for path, text in self.items:
                staged.append((_stage(path, text), path))
        except BaseException:
            for tmp, _ in staged:
                if os.path.exists(tmp): os.unlink(tmp)
            raise
        for tmp, path in staged: os.replace(tmp, path)
        record([p for p, _ in self.items])
