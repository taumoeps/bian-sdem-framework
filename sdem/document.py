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
SKIP_ATTRS = {'inferred', 'source_id', 'sources'}   # shown as provenance instead


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
        from .conformance import unknown_value   # the same reading as `sdem check` (LC-04), plus a placeholder word inside a longer value
        if unknown_value(v) or any(isinstance(x, str) and PLACEHOLDER.search(x) for x in vals) or v == []: out.append(k)
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
            if x['source'] == rid: out_.append({'kind': x['kind'], 'id': x['target'], 'name': names.get(x['target'], x['target']), 'source_id': x.get('source_id')})
            if x['target'] == rid: in_.append({'kind': x['kind'], 'id': x['source'], 'name': names.get(x['source'], x['source']), 'source_id': x.get('source_id')})
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
                          'links_out': o, 'links_in': i, 'connections': c, 'provenance': provenance(r),
                          'attribute_sources': {k: v for k, v in ((r.get('attributes') or {}).get('sources') or {}).items() if isinstance(v, str)}})   # CA-13
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
            for k, v in r['attributes'].items(): L.append(f"- **{k.replace('_', ' ')}:** {_value(v)}" + (f" — from {r['attribute_sources'][k]}" if k in r.get('attribute_sources', {}) else ''))
            if r['links_out'] or r['links_in']:
                cite = lambda x: f" — from {x['source_id']}" if x.get('source_id') else ''   # where the link came from (D4)
                L.append('- **Within the layer:** ' + '; '.join([f"{x['kind']} → {x['name']} ({x['id']}){cite(x)}" for x in r['links_out']] +
                                                         [f"{x['name']} ({x['id']}) {x['kind']} → this{cite(x)}" for x in r['links_in']]))
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


# ------------------------------------------------------------------ verify an agent's narrative (UX-D09…UX-D11)

CITE = re.compile(r'\[([A-Za-z][\w.-]*(?:\s+[\w.-]+\s+[A-Za-z][\w.-]*)?)\]')
CAVEAT = re.compile(r'\b(inferred|not yet confirmed|unconfirmed|proposed|suggested|to be confirmed)\b', re.I)


def _paragraphs(text):
    """(first line number, text) of each paragraph — blank lines and headings split them; fenced code is left out."""
    out, cur, start, fence = [], [], 0, False
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith(('```', '~~~')): fence = not fence; continue
        if fence: continue
        if not s or s.startswith('#') or re.match(r'([-*+]|\d+[.)])\s', s):
            if cur: out.append((start, ' '.join(cur))); cur = []
            if s and not s.startswith('#'): start, cur = n, [s]
            elif s.startswith('#'): out.append((n, s))
            continue
        if not cur: start = n
        cur.append(s)
    if cur: out.append((start, ' '.join(cur)))
    return out


def verify(text, ws):
    """UX-D09: check a narrative an agent wrote from `sdem document --json` against the workspace. Every citation `[ID]` must name a
    record or an approved connection (its link id); a stated link `[SOURCE KIND TARGET]` must be a link inside a layer or an approved
    connection between layers; a record named in the text must be cited in the same paragraph; an inferred, unconfirmed record must
    be said to be so; the gaps must be mentioned. Returns {'findings': [...], 'cited': n, 'errors': n, 'warnings': n}."""
    from .layers import FILES
    ws = Path(ws)
    data = {l: _j(ws / f) for l, f in FILES.items() if (ws / f).exists()}
    if not data: raise ValueError(f'{ws}: no layer datasets — is it a workspace?')
    recs = {r['id']: r for d in data.values() for r in d.get('instances', [])}
    rels = {(x['source'], x['kind'].lower(), x['target']) for d in data.values() for x in d.get('relationships', [])}
    reg = _j(ws / 'mappings.json').get('mappings', []) if (ws / 'mappings.json').exists() else []
    maps = {m.get('mapping_id'): m for m in reg if m.get('mapping_id')}
    cross = {}
    for m in reg: cross.setdefault((m['source']['id'], m['relationship'].upper(), m['target']['id']), []).append(m)
    unconfirmed = {i for i, r in recs.items() if isinstance((r.get('attributes') or {}).get('inferred'), dict) and r['attributes']['inferred'].get('status') != 'confirmed'}
    names = {}
    for i, r in recs.items():
        n = (r.get('name') or '').strip()
        if len(n) >= 4 and n.lower() != i.lower(): names.setdefault(n.lower(), set()).add(i)
    findings, cited_total = [], 0
    add = lambda line, level, code, msg: findings.append({'line': line, 'level': level, 'code': code, 'message': msg})
    paras = _paragraphs(text)
    for line, para in paras:
        cited = set()
        for m in CITE.finditer(para):
            parts = m.group(1).split()
            if len(parts) == 1:
                x = parts[0]
                if x in recs: cited.add(x); cited_total += 1
                elif x in maps:
                    cited_total += 1; mp = maps[x]; cited |= {mp['source']['id'], mp['target']['id']}
                    if mp.get('status') != 'approved' and not CAVEAT.search(para):
                        add(line, 'error', 'not_approved', f"[{x}] is a {mp.get('status')} connection, not an approved one — say it is proposed, or leave it out")
                elif re.fullmatch(r'[A-Z][A-Z0-9]*(-[A-Z0-9]+)+', x):
                    add(line, 'error', 'unknown_id', f'[{x}] is not a record or a connection in {ws.name}')
                continue
            a, kind, b = parts; cited_total += 1
            for x in (a, b):
                if x not in recs: add(line, 'error', 'unknown_id', f'[{x}] (in [{m.group(1)}]) is not a record in {ws.name}')
            cited |= {a, b}
            if a not in recs or b not in recs: continue
            if (a, kind.lower(), b) in rels: continue
            ms = cross.get((a, kind.upper(), b)) or cross.get((b, kind.upper(), a)) or []
            if any(x.get('status') == 'approved' for x in ms): continue
            if ms and CAVEAT.search(para): continue
            add(line, 'error', 'not_approved' if ms else 'unknown_link',
                f"[{m.group(1)}] — " + (f"a {ms[0].get('status')} connection, not an approved one" if ms else f'no such link: neither a link inside a layer nor a connection between layers in {ws.name}'))
        if not para.startswith('#'):   # a record named but not cited: longest names first, so 'Payments' inside 'Payments Hub' is that one name
            taken = []
            for n in sorted(names, key=len, reverse=True):
                ids = names[n]; one_word = ' ' not in n
                pat = re.compile(r'(?<![\w-])' + re.escape(recs[sorted(ids)[0]]['name'].strip() if one_word else n) + r'(?![\w-])', 0 if one_word else re.I)
                for mm in pat.finditer(para):
                    if any(a <= mm.start() < b for a, b in taken): continue
                    taken.append((mm.start(), mm.end()))
                    if not (ids & cited): add(line, 'warning', 'uncited_name', f"names {recs[sorted(ids)[0]]['name']!r} without citing it — add [{'] or ['.join(sorted(ids))}]"); break
        for x in sorted(cited & unconfirmed):
            if not CAVEAT.search(para): add(line, 'warning', 'unconfirmed_as_fact', f'[{x}] is inferred and not yet confirmed by a person — say so')
    if not cited_total: add(1, 'error', 'no_citations', 'no citations — every fact cites its record as [ID]; write it from `sdem document --json`')
    open_items = any(document(ws, l)['gaps'][k] for l in data if l in FILES for k in ('unconfirmed', 'no_connection', 'placeholders', 'requirements_not_confirmed'))
    if open_items and not re.search(r'\b(gaps?|open items?|not yet known|still open)\b', text, re.I):
        add(1, 'warning', 'gaps_not_mentioned', 'the workspace has gaps and open items (sdem document lists them) — the narrative does not mention them')
    findings.sort(key=lambda f: (f['line'], f['level'] != 'error', f['code']))
    return {'workspace': ws.name, 'cited': cited_total, 'errors': sum(f['level'] == 'error' for f in findings),
            'warnings': sum(f['level'] == 'warning' for f in findings), 'findings': findings}


def verify_main(argv):
    ap = argparse.ArgumentParser(prog='sdem document verify', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Check a narrative an agent wrote from `sdem document --json` against the workspace (UX-D09…D11): every [ID] it cites '
                                             'is a record or an approved connection, every link it states ([SOURCE KIND TARGET]) exists and is approved, every record it '
                                             'names is cited, inferred records are said to be inferred, gaps are mentioned. Read-only. Exit 1 when it finds an error.',
                                 epilog='Example:\n  sdem document verify work/a3-narrative.md --workspace examples/payment-initiation')
    ap.add_argument('file', help='the narrative (Markdown) an agent wrote'); ap.add_argument('--workspace', required=True, metavar='DIR', help='the workspace the narrative describes'); ap.add_argument('--json', action='store_true', help='the findings as JSON')
    a = ap.parse_args(argv)
    try: r = verify(Path(a.file).read_text(encoding='utf-8'), a.workspace)
    except (OSError, ValueError) as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps({'file': a.file, **r}, indent=2, ensure_ascii=False)); return 1 if r['errors'] else 0
    for f in r['findings']: print(f"{f['level'].upper():7} line {f['line']}: {f['message']} ({f['code']})")
    print(f"{a.file}: {r['cited']} citation(s); {r['errors']} error(s), {r['warnings']} warning(s) — "
          + ('fix the errors: the text states something the workspace does not hold' if r['errors'] else 'every citation checks out; a person still reads it before it is shared'))
    return 1 if r['errors'] else 0


def main(argv=None):
    if argv is None: argv = sys.argv[1:]
    if argv and argv[0] == 'verify': return verify_main(argv[1:])
    ap = argparse.ArgumentParser(prog='sdem document', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="A layer's design as a readable document, generated from the workspace — deterministic, nothing invented; "
                                             'every record says where it came from, and gaps are listed.',
                                 epilog='Examples:\n  sdem document --workspace examples/payment-initiation --layer A3\n'
                                        '  sdem document --workspace examples/payment-initiation --layer all --format html -o work/designs/\n'
                                        '  sdem document verify work/a3-narrative.md --workspace examples/payment-initiation   # check an agent\'s narrative (UX-D09)')
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
