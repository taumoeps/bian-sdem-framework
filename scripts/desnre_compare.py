"""Compare a design as DESNRE serves it with the 0.19 reference (tests/reference/desnre-0.19/payment): the same records, links,
layers, security, SDEM's check, documents and narrative structure? The narrative's wording is the site's agent's and differs from
run to run; its sections and citations should not.

    python scripts/desnre_compare.py tests/reference/desnre-0.19/payment <snapshot folder>
    python scripts/desnre_compare.py tests/reference/desnre-0.19/payment --live taumoeps/payment-v3-020
    python scripts/desnre_compare.py --fetch example/payment <folder>        # a fresh snapshot (is the live reference unchanged?)

A snapshot folder holds model.json, workspace.json and narrative.json — what https://desnre.vercel.app/api/u/<user>/<name>[/workspace|/narrative]
returns. Standard library only; made-up data only."""
import json, re, sys, tempfile, urllib.request
from collections import Counter
from pathlib import Path

SITE = 'https://desnre.vercel.app'


def fetch(design, folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    for part, name in (('', 'model'), ('/workspace', 'workspace'), ('/narrative', 'narrative')):
        with urllib.request.urlopen(f'{SITE}/api/u/{design}{part}', timeout=60) as r: (folder / f'{name}.json').write_bytes(r.read())
    return folder


def facts(folder):
    j = lambda n: json.loads((Path(folder) / f'{n}.json').read_text(encoding='utf-8'))
    m, w, n = j('model'), j('workspace'), j('narrative').get('narrative') or {}
    ids = [x[0] for x in m['nodes']]
    files = w.get('files') or {}
    recs = {k: len((v or {}).get('instances', [])) for k, v in files.items() if isinstance(v, dict) and 'instances' in v}
    links_inside = sum(len((v or {}).get('relationships', [])) for v in files.values() if isinstance(v, dict) and 'instances' in v)
    maps = (files.get('mappings.json') or {}).get('mappings', [])
    sec = (w.get('extensions') or {}).get('security') or {}
    chk = w.get('check') or {}
    text = n.get('text') or ''
    return {
        'drawn records': sorted(ids),
        'drawn links': sorted(f'{ids[e[0]]} -{e[3] if len(e) > 3 else e[2]}-> {ids[e[1]]}' for e in m['edges']),
        'records per layer file': recs,
        'records in all': sum(recs.values()),
        'links inside layers': links_inside,
        'links between layers': Counter(x.get('relationship') for x in maps),
        'approved links between layers': sum(1 for x in maps if x.get('status') == 'approved'),
        'security': {'state': sec.get('state'), 'results': sorted(sec.get('results') or []), 'records': recs.get('security.json', 0)},
        'SDEM check ok': chk.get('ok'),
        'SDEM warnings': len(chk.get('warnings') or []),
        'documents': sorted((w.get('documents') or {}).keys()),
        'narrative sections': [h.strip() for h in re.findall(r'^#{2,3} (.+)$', text, re.M)],
        'narrative citations': len(re.findall(r'\[\[|\{\{|`[A-Z][A-Z0-9-]+`|\b[A-Z]{2,}-[A-Z0-9-]+\b', text)),
        'SDEM (as labelled)': f"{m['source'].get('sdem')} · metamodel {m['source'].get('metamodel')}",
    }


def compare(ref, new):
    a, b = facts(ref), facts(new)
    same, diff = [], []
    for k in a:
        if a[k] == b[k]: same.append(k)
        else: diff.append(k)
    print(f'{"":<32} {"0.19 reference":<28} {"compared":<28}')
    for k in a:
        va, vb = a[k], b[k]
        show = lambda v: (f'{len(v)} items' if isinstance(v, list) and len(v) > 6 else str(dict(v)) if isinstance(v, Counter) else str(v))[:26]
        print(f"{('  ' if k in same else '≠ ') + k:<32} {show(va):<28} {show(vb):<28}")
    for k in diff:
        va, vb = a[k], b[k]
        if isinstance(va, list) and isinstance(vb, list):
            only_a, only_b = sorted(set(map(str, va)) - set(map(str, vb))), sorted(set(map(str, vb)) - set(map(str, va)))
            if only_a or only_b: print(f'\n{k}: only in the reference {only_a[:8]}{" …" if len(only_a) > 8 else ""}; only compared {only_b[:8]}{" …" if len(only_b) > 8 else ""}')
    print(f'\n{len(same)} of {len(a)} the same' + (f'; differ: {", ".join(diff)}' if diff else ''))
    return 0 if not diff else 1


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['--fetch'] and len(args) == 3: print(fetch(args[1], args[2])); sys.exit(0)
    if len(args) == 3 and args[1] == '--live': sys.exit(compare(args[0], fetch(args[2], tempfile.mkdtemp())))
    if len(args) == 2: sys.exit(compare(*args))
    sys.exit(__doc__)
