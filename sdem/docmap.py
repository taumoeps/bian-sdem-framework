"""Where each document lives — so generated documents link correctly wherever they and their targets sit.

Generators write links as if from `docs/` (e.g. `[spec](relationship-rules-spec.md)`, `evidence/use-case-example-1/…`).
`relink(text, out)` rewrites each relative link that does not resolve from the output's own folder: first as a path from
`docs/`, then by the target's file name if exactly one document has it. `docs/<name>` mentions in the text are updated the
same way. The documentation layout (docs/README.md) can then change without editing every generator."""
import os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
_LINK = re.compile(r'(\[[^\]]*\])\(([^)\s]+)\)')
_MENTION = re.compile(r'(?<![\w/.-])docs/([\w./-]+\.(?:md|puml))\b')


def _index():
    idx = {}
    for p in DOCS.rglob('*'):
        if p.suffix in ('.md', '.puml') and p.is_file(): idx.setdefault(p.name, []).append(p)
    return idx


def relink(text, out):
    here = Path(out).resolve().parent
    idx = _index()

    def find(path):
        cand = DOCS / path
        if cand.exists(): return cand
        hits = idx.get(Path(path).name, [])
        return hits[0] if len(hits) == 1 else None

    def link(m):
        label, target = m.group(1), m.group(2)
        if re.match(r'^(https?:|mailto:|#)', target): return m.group(0)
        path, sep, frag = target.partition('#')
        if not path or (here / path).exists(): return m.group(0)
        cand = find(path)
        if cand is None: return m.group(0)
        rel = os.path.relpath(cand, here) + ('/' if path.endswith('/') else '')
        return f'{label}({rel}{sep}{frag})'

    def mention(m):
        if (DOCS / m.group(1)).exists(): return m.group(0)
        cand = find(m.group(1))
        return 'docs/' + cand.relative_to(DOCS).as_posix() if cand else m.group(0)

    return _MENTION.sub(mention, _LINK.sub(link, text))
