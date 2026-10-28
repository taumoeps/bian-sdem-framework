"""Safe file writes: a file is written to a temporary copy beside it and moved into place in one step (os.replace), so a
crash or a full disk never leaves a half-written file. `Batch` writes several files all-or-nothing as far as the file
system allows: every file is written to its temporary copy first, and only then are they moved into place."""
import json, os, tempfile
from pathlib import Path


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
        with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(text)
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


def write_json(path, obj):
    write_text(path, dumps(obj))


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
