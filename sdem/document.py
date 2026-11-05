"""`sdem document` — a layer's design as a readable document, generated from the workspace (UX-D01…UX-D08,
docs/design/sdem-workbench-ux-spec.md).

Deterministic: the same workspace gives the same document, word for word — no AI, no timestamps; the input files'
fingerprint says what it was made from. Nothing is invented: what the workspace does not hold is listed as a gap, and
every record says where it came from (a document section, a past design, AID's inference — confirmed or not — or a
person's change set). Markdown for people and agents (an agent can pour it into a Word template); HTML for the
workbench; JSON for anything else.
"""
import argparse, hashlib, html, json, re, sys
from pathlib import Path

LAYER_TITLES = {'A1': 'A1 Business Architecture', 'A2': 'A2 BIAN Service Domain Architecture',
                'A3': 'A3 Application Architecture', 'A4': 'A4 Technology Architecture'}
PLACEHOLDER = re.compile(r'\b(TBD|PLACEHOLDER|TODO)\b', re.I)
SKIP_ATTRS = {'inferred', 'source_id'}   # shown as provenance instead


def _j(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def _label(t):
    """A1.BusinessCapability → Business capabilities."""
    words = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', re.sub(r'([a-z])([A-Z])', r'\1 \2', t.split('.', 1)[-1])).split()
    last = words[-1]
    last = last + 's' if last.isupper() else last[:-1] + 'ies' if last.endswith('y') and last[-2:-1] not in 'aeiou' else last + 'es' if last.endswith(('s', 'x')) else last + 's'
    words = words[:-1] + [last]
    out = ' '.join(words)
    acronym = lambda w: len(w) > 1 and (w.isupper() or (w[:-1].isupper() and w.endswith('s')))   # API, APIs
    return ' '.join([words[0]] + [w if acronym(w) else w.lower() for w in words[1:]])


def _value(v):
    if isinstance(v, list): return ', '.join(map(str, v)) if v else '—'
    if isinstance(v, dict): return '; '.join(f'{k}: {x}' for k, x in v.items())
    return str(v)


def _placeholders(rec):
    out = []
    for k, v in (rec.get('attributes') or {}).items():
        if k in SKIP_ATTRS: continue
        vals = v if isinstance(v, list) else [v]
        if any(isinstance(x, str) and PLACEHOLDER.search(x) for x in vals) or v == []: out.append(k)
    return out


def provenance(rec):
    """Where a record came from, in words (UX-D04)."""
    a = rec.get('attributes') or {}
    inf = a.get('inferred') if isinstance(a.get('inferred'), dict) else None
    parts = []
    src = a.get('source_id')
    if src:
        kind, _, ref = str(src).partition(':')
        bian = re.match(r'(\d[\d.]*):(.+)', ref) if kind == 'bian-semantic-api' else None
        parts.append({'document': f'from the design document {ref}', 'confluence': f'from past design page(s) {ref}'}.get(kind)
                     or (f'from the BIAN catalogue, release {bian.group(1)} ({bian.group(2)})' if bian else f'from {src}'))
    if inf:
        state = f"confirmed by {inf.get('confirmed_by')}" if inf.get('status') == 'confirmed' else 'inferred — not yet confirmed by a person'
        parts.append(f"{state} (sdem aid {inf.get('run', '')}, rule {inf.get('rule', '—')}, confidence {inf.get('confidence', '—')}: {inf.get('reasoning', '')})".replace(' , ', ' '))
    return '; '.join(parts) or 'no source recorded (written by a person or an agent)'


def document(ws, layer):
    """The structured document for one layer: {'layer', 'title', 'workspace', 'fingerprint', 'summary', 'sections', 'requirements', 'gaps'}."""
    from .layers import FILES
    from .metamodel import Metamodel
    ws = Path(ws)
    if layer not in FILES: raise ValueError(f'{layer}: not a layer of this workspace (one of {", ".join(FILES)})')
    files = {l: ws / f for l, f in FILES.items()}
    if not files[layer].exists(): raise ValueError(f'{files[layer]}: no such dataset — is {ws} a workspace?')
    data = {l: _j(p) for l, p in files.items() if p.exists()}
    reg_path, req_path = ws / 'mappings.json', ws / 'requirements.json'
    reg = _j(reg_path).get('mappings', []) if reg_path.exists() else []
    reqs = _j(req_path).get('requirements', []) if req_path.exists() else []
    h = hashlib.sha256()
    for p in [files[l] for l in sorted(data)] + [x for x in (reg_path, req_path) if x.exists()]: h.update(p.read_bytes())
    names = {r['id']: r.get('name') or r['id'] for d in data.values() for r in d.get('instances', [])}
    recs = data[layer].get('instances', []); rels = data[layer].get('relationships', [])
    mm = Metamodel.load()
    order = [t for t, e in mm.entities.items() if e.get('level') == layer]
    by_type = {}
    for r in recs: by_type.setdefault(r['type'], []).append(r)
    types = [t for t in order if t in by_type] + sorted(t for t in by_type if t not in order)
    ids = {r['id'] for r in recs}

    def links(rid):
        out_, in_ = [], []
        for x in rels:
            if x['source'] == rid: out_.append({'kind': x['kind'], 'id': x['target'], 'name': names.get(x['target'], x['target'])})
            if x['target'] == rid: in_.append({'kind': x['kind'], 'id': x['source'], 'name': names.get(x['source'], x['source'])})
        return out_, in_

    def connections(rid):
        out = []
        for m in reg:
            s, t = m['source']['id'], m['target']['id']
            if rid not in (s, t): continue
            other = t if s == rid else s
            out.append({'relationship': m['relationship'], 'direction': 'out' if s == rid else 'in', 'id': other, 'name': names.get(other, other),
                        'mapping_id': m.get('mapping_id'), 'status': m.get('status'), 'evidence': m.get('evidence', [])})
        return out

    sections, gaps = [], {'unconfirmed': [], 'no_connection': [], 'placeholders': [], 'requirements_not_confirmed': []}
    for t in types:
        items = []
        for r in by_type[t]:
            o, i = links(r['id']); c = connections(r['id'])
            named = lambda v: f'{names[v]} ({v})' if isinstance(v, str) and v in names and names[v] != v else v
            attrs = {k: ([named(x) for x in v] if isinstance(v, list) else named(v)) for k, v in (r.get('attributes') or {}).items()
                     if k not in SKIP_ATTRS and v not in (None, '', [], {})}
            inf = (r.get('attributes') or {}).get('inferred')
            if isinstance(inf, dict) and inf.get('status') != 'confirmed': gaps['unconfirmed'].append(r['id'])
            if not [x for x in c if x['status'] == 'approved']: gaps['no_connection'].append(r['id'])
            ph = _placeholders(r)
            if ph: gaps['placeholders'].append({'id': r['id'], 'fields': ph})
            items.append({'id': r['id'], 'name': r.get('name') or r['id'], 'type': t, 'version': r.get('version'),
                          'lifecycle_status': r.get('lifecycle_status'), 'description': r.get('description', ''), 'attributes': attrs,
                          'links_out': o, 'links_in': i, 'connections': c, 'provenance': provenance(r)})
        sections.append({'type': t, 'title': _label(t), 'definition': (mm.entities.get(t) or {}).get('definition', ''), 'records': items})
    layer_reqs = []
    for q in reqs:
        subj = q.get('subject'); alloc = q.get('allocated_to') or []
        if q.get('owner_layer') == layer or subj in ids or any(a in ids for a in (alloc if isinstance(alloc, list) else [alloc])):
            layer_reqs.append({'id': q['id'], 'name': q.get('name', ''), 'status': q.get('status'), 'category': q.get('category'),
                               'statement': q.get('statement', ''), 'subject': subj, 'subject_name': names.get(subj, subj),
                               'condition': q.get('condition'), 'evidence': q.get('evidence', [])})
            if q.get('status') != 'confirmed': gaps['requirements_not_confirmed'].append(q['id'])
    counts = {s['title']: len(s['records']) for s in sections}
    return {'layer': layer, 'title': LAYER_TITLES.get(layer, layer), 'workspace': ws.name, 'fingerprint': h.hexdigest()[:12],
            'summary': {'records': len(recs), 'by_type': counts, 'unconfirmed': len(gaps['unconfirmed']),
                        'with_approved_connection': len(recs) - len(gaps['no_connection'])},
            'sections': sections, 'requirements': layer_reqs, 'gaps': gaps}


def _cond(c):
    if not isinstance(c, dict): return _value(c) if c else '—'
    v = c.get('value'); v = json.dumps(v) if isinstance(v, list) else v
    return f"{c.get('metric', '?')} {c.get('operator', '')} {v}{(' ' + c['unit']) if c.get('unit') else ''}{(' per ' + c['period']) if c.get('period') else ''}"


def markdown(doc):
    L = [f"# {doc['title']} — {doc['workspace']}", '',
         f"> Generated by `sdem document` from the workspace (inputs {doc['fingerprint']}). Read-only: it shows what the workspace holds — "
         'nothing added, nothing decided. Gaps are listed at the end.', '']
    s = doc['summary']
    L += ['## Summary', '', f"{s['records']} records; {s['with_approved_connection']} with an approved connection to another layer; "
          f"{s['unconfirmed']} inferred and not yet confirmed.", '']
    L += [f"- {t}: {n}" for t, n in s['by_type'].items()] + ['']
    for n, sec in enumerate(doc['sections'], 1):
        L += [f"## {n}. {sec['title']}", '']
        if sec['definition']: L += [f"*{sec['definition']}*", '']
        for r in sec['records']:
            L += [f"### {r['name']} ({r['id']})", '']
            if r['description']: L += [r['description'], '']
            meta = [f"version {r['version']}" if r['version'] else None, r['lifecycle_status']]
            L += [f"- **Status:** {', '.join(x for x in meta if x) or '—'}", f"- **Source:** {r['provenance']}"]
            for k, v in r['attributes'].items(): L.append(f"- **{k.replace('_', ' ')}:** {_value(v)}")
            if r['links_out'] or r['links_in']:
                L.append('- **Within the layer:** ' + '; '.join([f"{x['kind']} → {x['name']} ({x['id']})" for x in r['links_out']] +
                                                         [f"{x['name']} ({x['id']}) {x['kind']} → this" for x in r['links_in']]))
            for c in r['connections']:
                arrow = f"{c['relationship']} → {c['name']} ({c['id']})" if c['direction'] == 'out' else f"{c['name']} ({c['id']}) {c['relationship']} → this"
                L.append(f"- **Connection ({c['status']}):** {arrow} — {c['mapping_id']}" + (f"; evidence {', '.join(c['evidence'][:2])}" if c['evidence'] else ''))
            if not r['connections']: L.append('- **Connections to other layers:** none in the registry')
            L.append('')
    L += [f"## {len(doc['sections']) + 1}. Requirements", '']
    if doc['requirements']:
        L += ['| Id | Requirement | Condition | Subject | Status |', '|---|---|---|---|---|']
        L += [f"| {q['id']} | {q['name'] or q['statement']} | {_cond(q['condition'])} | {q['subject_name']} | {q['status']} |" for q in doc['requirements']]
    else: L.append('No requirement in the registry names a record of this layer.')
    g = doc['gaps']
    L += ['', f"## {len(doc['sections']) + 2}. Gaps and open items", '']
    rows = [('Inferred, not yet confirmed by a person', ', '.join(g['unconfirmed'])),
            ('No approved connection to another layer', ', '.join(g['no_connection'])),
            ('Placeholder or empty values', '; '.join(f"{x['id']} ({', '.join(x['fields'])})" for x in g['placeholders'])),
            ('Requirements not confirmed', ', '.join(g['requirements_not_confirmed']))]
    L += [f"- **{k}:** {v}" for k, v in rows if v] or ['- none']
    return '\n'.join(L) + '\n'


def to_html(doc):
    """The same document as one self-contained HTML page (no scripts, no external files)."""
    e = html.escape
    md = markdown(doc).splitlines()
    out, in_list, in_table = [], False, False
    inline = lambda s: re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', re.sub(r'`([^`]+)`', r'<code>\1</code>', e(s))))
    for line in md:
        if in_list and not line.startswith('- '): out.append('</ul>'); in_list = False
        if in_table and not line.startswith('|'): out.append('</tbody></table>'); in_table = False
        if line.startswith('# '): out.append(f'<h1>{inline(line[2:])}</h1>')
        elif line.startswith('## '): out.append(f'<h2>{inline(line[3:])}</h2>')
        elif line.startswith('### '): out.append(f'<h3>{inline(line[4:])}</h3>')
        elif line.startswith('> '): out.append(f'<p class="note">{inline(line[2:])}</p>')
        elif line.startswith('- '):
            if not in_list: out.append('<ul>'); in_list = True
            out.append(f'<li>{inline(line[2:])}</li>')
        elif line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if set(''.join(cells)) <= {'-'}: continue
            if not in_table: out.append('<table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in cells) + '</tr></thead><tbody>'); in_table = True
            else: out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
        elif line.strip(): out.append(f'<p>{inline(line)}</p>')
    if in_list: out.append('</ul>')
    if in_table: out.append('</tbody></table>')
    css = ('body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#1f2933;background:#fff}'
           'h2{border-bottom:1px solid #dde3e9;padding-bottom:.3rem;margin-top:2rem}h3{margin-bottom:.2rem}.note{color:#52606d;background:#f1f5f8;padding:.6rem .8rem;border-radius:6px}'
           'table{border-collapse:collapse;width:100%}th,td{border:1px solid #dde3e9;padding:.4rem;text-align:left;vertical-align:top}code{background:#f1f5f8;padding:0 .2rem}'
           '@media(prefers-color-scheme:dark){body{background:#111820;color:#e4e9ee}.note,code{background:#1d2731;color:#c9d3dc}th,td,h2{border-color:#2c3a47}}')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(doc["title"])} — {e(doc["workspace"])}</title><style>{css}</style></head><body>' + '\n'.join(out) + '</body></html>\n')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem document', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="A layer's design as a readable document, generated from the workspace — deterministic, nothing invented; "
                                             'every record says where it came from, and gaps are listed.',
                                 epilog='Examples:\n  sdem document --workspace examples/payment-initiation --layer A3\n'
                                        '  sdem document --workspace examples/payment-initiation --layer all --format html -o work/designs/')
    ap.add_argument('--workspace', required=True, metavar='DIR')
    ap.add_argument('--layer', default='all', help='A1, A2, A3, A4 (or a layer the profile adds), or all (default)')
    ap.add_argument('--format', choices=['md', 'html'], default='md')
    ap.add_argument('-o', '--out', metavar='PATH', help='a file (one layer) or a folder (all layers); without it, Markdown goes to the screen')
    ap.add_argument('--json', action='store_true', help='the structured document instead')
    a = ap.parse_args(argv)
    from .layers import FILES
    ws = Path(a.workspace)
    layers = [l for l in FILES if (ws / FILES[l]).exists()] if a.layer == 'all' else [a.layer]
    try: docs = [document(ws, l) for l in layers]
    except ValueError as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(docs[0] if len(docs) == 1 else {'documents': docs}, indent=2, ensure_ascii=False)); return 0
    render = to_html if a.format == 'html' else markdown
    if not a.out:
        sys.stdout.write('\n'.join(render(d) for d in docs)); return 0
    out = Path(a.out)
    if len(docs) > 1 or out.suffix == '':
        out.mkdir(parents=True, exist_ok=True)
        for d in docs:
            p = out / f"{d['layer'].lower()}-design.{a.format}"; p.write_text(render(d), encoding='utf-8'); print(f'wrote {p}')
    else:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(render(docs[0]), encoding='utf-8'); print(f'wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
