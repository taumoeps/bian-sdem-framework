"""`sdem transform` — read a Confluence HTML export of past designs and turn it into candidate architecture records.

Rules only: no AI, no network, Python standard library only, so it runs on a locked-down machine. What it reads
(docs/sdem-transform-design.md; spec HI-*):
  tables          → records, by their column headings (rules HT-*), and links from source/target tables (HL-*)
  draw.io         → records from shapes (ArchiMate type, else colour, label and shape words) and links from lines;
                    read from .drawio/XML attachments, from PNGs and SVGs that carry the diagram inside them
  PlantUML        → records and links from the source: .puml files, code blocks in pages, PNGs and SVGs that carry
                    the source inside them (component, deployment, sequence, C4, ArchiMate notation)
  narrative       → only names already found (or given with --known), and simple phrases between two of them
  pictures        → their text, read on the machine (macOS Vision, built in; or Tesseract), or exactly from SVG text;
                    labels become low-confidence candidates, lines are not read; always listed for a person
Every record is a candidate with its sources (page, where, rule, confidence, reasoning) — never above medium, never
real until a person confirms it. The rules are in metamodel/transform-rules.json; copy it and pass --rules to tune.

  sdem transform inspect EXPORT_DIR                      what is in the export and which rules match (structure only)
  sdem transform run EXPORT_DIR -o OUT [--known …]       candidate datasets, extraction.json, design-index.json, report
  then: review the report, `sdem load` the entities you keep (docs/sdem-load-design.md)
"""
import argparse, base64, collections, csv, datetime, hashlib, io, json, os, re, sys, urllib.parse, zlib
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

from .metamodel import Metamodel
from .paths import DATA_ROOT

RULES = DATA_ROOT / 'metamodel' / 'transform-rules.json'
DATASETS = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
RANK = {'low': 1, 'medium': 2, 'high': 3}
SOURCE_SYSTEM = 'CONFLUENCE-EXTRACT'
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp')


# ---------------------------------------------------------------- HTML: a small tree from the standard library parser
VOID = {'br', 'img', 'hr', 'meta', 'link', 'input', 'col', 'area', 'base', 'wbr', 'source', 'param'}


class Node:
    __slots__ = ('tag', 'attrs', 'children', 'parent')

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs or {}), [], parent

    def text(self):
        out = []
        for c in self.children:
            if isinstance(c, str): out.append(c)
            elif c.tag == 'br': out.append('\n')
            else:
                t = c.text()
                out.append(f'\n{t}\n' if c.tag in ('p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6') else t)
        return ''.join(out)

    def iter(self):
        yield self
        for c in self.children:
            if isinstance(c, Node): yield from c.iter()

    def find(self, pred):
        return next((n for n in self.iter() if pred(n)), None)

    def cls(self):
        return (self.attrs.get('class') or '').split()


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.root = Node('#root'); self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur); self.cur.children.append(n)
        if tag not in VOID: self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag: n = n.parent
        if n is not None and n.parent is not None: self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_html(text):
    b = _Builder(); b.feed(text); b.close(); return b.root


def clean(s):
    return ' '.join(str(s or '').split())


def norm(s):
    """Matching form: lower case, punctuation to spaces, single spaces."""
    return ' '.join(re.sub(r'[^0-9a-z]+', ' ', str(s or '').lower()).split())


def first_line(s):
    lines = [clean(x) for x in str(s or '').split('\n')]
    lines = [x for x in lines if x]
    return (lines[0] if lines else ''), ' '.join(lines[1:])


MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def parse_date(text):
    """The page's last-modified date from Confluence's page metadata line, as YYYY-MM-DD (None if not found)."""
    t = clean(text)
    m = re.search(r'modified (?:on )?(.*)$', t, re.I)
    t = m.group(1) if m else t
    for pat, order in ((r'(\d{4})-(\d{2})-(\d{2})', 'ymd'), (r'([A-Za-z]{3})[a-z]*\.? (\d{1,2}), (\d{4})', 'mdy'), (r'(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})', 'dmy')):
        m = re.search(pat, t)
        if not m: continue
        try:
            if order == 'ymd': y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif order == 'mdy': mo, d, y = MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3))
            else: d, mo, y = int(m.group(1)), MONTHS[m.group(2).lower()], int(m.group(3))
            return datetime.date(y, mo, d).isoformat()
        except (KeyError, ValueError):
            continue
    return None


# ---------------------------------------------------------------- the export: any folder layout
CONTENT_EXT = ('.html', '.htm', '.md', '.markdown', '.txt', '.csv')
DIAGRAM_EXT = ('', '.drawio', '.dio', '.xml', '.png', '.svg') + ('.puml', '.plantuml', '.pu', '.iuml', '.wsd')


def scan(root, rules):
    """Sort every file of the export by what it is — by content and place, not by a fixed layout:
    provenance (files in the root that are not pages: readme, source, evidence), pages (HTML, Markdown, text, CSV),
    draw.io diagrams (any file holding one), pictures, other. Returns a dict of lists plus the folder layout."""
    root = Path(root); skip_files = set(rules.get('skip_files', [])); skip = [s.strip('/') for s in rules.get('skip_folders', [])]
    att = {a.strip('/').lower() for a in rules.get('attachment_folders', [])}; limit = rules.get('max_diagram_bytes', 50_000_000)
    out = {'provenance': [], 'pages': [], 'diagrams': {}, 'pictures': [], 'other': [], 'layout': collections.defaultdict(collections.Counter)}
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel = p.relative_to(root).as_posix(); parts = rel.split('/'); folder = '/'.join(parts[:-1]) or '.'
        if any(x.startswith('.') or x == '__MACOSX' for x in parts) or p.name in skip_files or any(('/' + rel).startswith('/' + s + '/') or f'/{s}/' in '/' + rel for s in skip):
            out['layout'][folder]['skipped'] += 1; continue
        ext = p.suffix.lower(); in_att = bool({x.lower() for x in parts[:-1]} & att)
        if len(parts) == 1 and ext not in ('.html', '.htm'):
            out['provenance'].append(p); kind = 'provenance'
        elif ext in CONTENT_EXT and not in_att:
            out['pages'].append(p); kind = 'page'
        else:
            data = p.read_bytes() if ext in DIAGRAM_EXT and p.stat().st_size <= limit else b''
            xml = find_mxfile(data) if data else None
            pu = None if xml or not data else find_plantuml(data, ext)
            if xml: out['diagrams'][rel] = ('drawio', xml); kind = 'diagram'
            elif pu: out['diagrams'][rel] = ('plantuml', pu); kind = 'diagram'
            elif ext in IMAGE_EXT: out['pictures'].append(rel); kind = 'picture'
            else: out['other'].append(rel); kind = 'other'
        out['layout'][folder][kind] += 1
    return out


def folder_sections(rel, rules):
    """The folders above a file, as section headings — container folders (archives, attachments …) left out."""
    skip = {norm(c) for c in rules.get('container_folders', [])}
    return [re.sub(r'^\d+(\.\d+)*[\s._-]+', '', x).strip() or x for x in rel.split('/')[:-1] if norm(x) not in skip]


def read_page(path, root, rules=None):
    """One content file → {page_id, title, space, file, modified, breadcrumb, blocks, links, attachment_names}."""
    rules = rules or {}
    rel = path.relative_to(root).as_posix(); ext = path.suffix.lower(); prefix = folder_sections(rel, rules)
    m = re.search(r'_(\d+)\.html?$', path.name) or re.match(r'(\d+)\.html?$', path.name)
    page = {'page_id': m.group(1) if m else rel, 'id_from': 'file name' if m else 'path', 'title': '', 'space': '', 'file': rel,
            'modified': None, 'breadcrumb': prefix, 'blocks': [], 'links': [], 'attachment_names': {}, 'url': None}
    text = path.read_text(encoding='utf-8', errors='replace')
    if ext in ('.html', '.htm'):
        tree = parse_html(text)
        title = clean((tree.find(lambda n: n.attrs.get('id') == 'title-text') or tree.find(lambda n: n.tag == 'title') or Node('x')).text())
        if ' : ' in title: page['space'], title = [x.strip() for x in title.split(' : ', 1)]
        h1 = tree.find(lambda n: n.tag == 'h1')
        page['title'] = title or (clean(h1.text()) if h1 else '')
        meta = tree.find(lambda n: 'page-metadata' in n.cls())
        page['modified'] = parse_date(meta.text()) if meta else None
        crumbs = tree.find(lambda n: n.attrs.get('id') == 'breadcrumbs')
        if crumbs: page['breadcrumb'] = [clean(li.text()) for li in crumbs.iter() if li.tag == 'li']
        content = tree.find(lambda n: n.attrs.get('id') == 'main-content') or tree.find(lambda n: n.tag == 'body') or tree
        page['blocks'] = html_blocks(content, prefix)
        for a in tree.iter():
            ref = a.attrs.get('href') if a.tag == 'a' else a.attrs.get('data') if a.tag == 'object' else a.attrs.get('src') if a.tag in ('embed', 'iframe') else None
            if ref: page['links'].append((ref, clean(a.text())))
            if a.tag == 'a' and 'attachments/' in (a.attrs.get('href') or ''):
                page['attachment_names'][urllib.parse.unquote(a.attrs['href'].split('?')[0])] = clean(a.text())
    elif ext in ('.md', '.markdown'):
        page['blocks'], page['links'] = md_blocks(text, prefix)
        h = next((x for x in text.splitlines() if re.match(r'#\s', x)), None)
        page['title'] = clean(h[1:]) if h else ''
    elif ext == '.csv':
        rows = [r for r in csv.reader(io.StringIO(text.lstrip('﻿'))) if any(c.strip() for c in r)]
        if rows: page['blocks'] = [('table', ' / '.join(prefix), ('grid', [clean(c) for c in rows[0]], rows[1:]))]
    else:  # plain text: PlantUML blocks, then paragraphs split by blank lines
        sec = ' / '.join(prefix)
        page['blocks'] = [('plantuml', sec, b) for b in plantuml_blocks(text)]
        rest = re.sub(r'@start(?:uml)?\b.*?@end(?:uml)?\b', '', text, flags=re.S)
        page['blocks'] += [('text', sec, clean(p)) for p in re.split(r'\n\s*\n', rest) if clean(p)]
    page['title'] = page['title'] or (prefix[-1] + ' — ' if prefix else '') + path.stem
    return page


def html_blocks(content, prefix=()):
    """The page in reading order: ('table', section, (kind, headers, rows)), ('text', section, str), ('img', section, ref)."""
    out, heads = [], []

    def section():
        return ' / '.join(list(prefix) + [h for _, h in heads])

    def img(n):
        return {'src': n.attrs.get('src') or '', 'alias': n.attrs.get('data-linked-resource-default-alias') or '', 'alt': n.attrs.get('alt') or ''}

    def walk(n):
        for c in n.children:
            if isinstance(c, str):
                if clean(c) and n.tag in ('div', 'td', 'body', '#root', 'section', 'article'): out.append(('text', section(), clean(c)))
                continue
            if re.fullmatch(r'h[1-6]', c.tag):
                lvl = int(c.tag[1]); heads[:] = [h for h in heads if h[0] < lvl] + [(lvl, clean(c.text()))]; continue
            if c.tag == 'table': out.append(('table', section(), table_rows(c))); continue
            if c.tag in ('p', 'li'):
                t = clean(c.text())
                if t: out.append(('text', section(), t))
                for i in c.iter():
                    if i.tag == 'img': out.append(('img', section(), img(i)))
                continue
            if c.tag == 'img': out.append(('img', section(), img(c))); continue
            if c.tag in ('script', 'style', 'head'): continue
            if c.tag in ('pre', 'code') or 'plantuml' in ' '.join(c.cls()).lower():
                t = c.text()
                if '@start' in t:
                    for b in plantuml_blocks(t): out.append(('plantuml', section(), b))
                    continue
            walk(c)
    walk(content)
    return out


def _md_plain(s):
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s); s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    return clean(re.sub(r'[*_`]+', '', s))


def md_blocks(text, prefix=()):
    """Markdown → the same blocks: # headings, pipe tables, paragraphs and list items, ![pictures](path); and [links](path)."""
    out, heads, para, links = [], [], [], []
    lines = text.splitlines(); i = 0

    def section():
        return ' / '.join(list(prefix) + [h for _, h in heads])

    def flush():
        t = clean(' '.join(para)); para.clear()
        if t: out.append(('text', section(), t))

    def cells(s):
        return [c.strip() for c in s.strip().strip('|').split('|')]
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith(('```', '~~~')):  # a fenced code block: PlantUML is read as a diagram, other code is skipped
            fence = s[:3]; j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(fence): j += 1
            code = '\n'.join(lines[i + 1:j]); flush()
            for b in plantuml_blocks(code) or ([code] if s[3:].strip().lower() == 'plantuml' and code.strip() else []):
                out.append(('plantuml', section(), b if '@start' in b else '@startuml\n' + b + '\n@enduml'))
            i = j + 1; continue
        m = re.match(r'(#{1,6})\s+(.*?)\s*#*$', s)
        if m:
            flush(); lvl = len(m.group(1)); heads[:] = [h for h in heads if h[0] < lvl] + [(lvl, _md_plain(m.group(2)))]; i += 1; continue
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|?\s*:?-{2,}', lines[i + 1]):
            flush(); head = [_md_plain(c) for c in cells(s)]; i += 2; rows = []
            while i < len(lines) and lines[i].strip().startswith('|'): rows.append([_md_plain(c) for c in cells(lines[i])]); i += 1
            out.append(('table', section(), ('grid', head, rows))); continue
        for m in re.finditer(r'!\[([^\]]*)\]\(([^)\s]+)', s): out.append(('img', section(), {'src': m.group(2), 'alias': m.group(1), 'alt': m.group(1)}))
        for m in re.finditer(r'(?<!!)\[([^\]]*)\]\(([^)\s]+)', s): links.append((m.group(2), m.group(1)))
        if not s: flush()
        elif re.match(r'([-*+]|\d+[.)])\s', s): flush(); para.append(_md_plain(re.sub(r'^([-*+]|\d+[.)])\s+', '', s))); flush()
        else: para.append(_md_plain(s))
        i += 1
    flush()
    return out, links


def table_rows(t):
    """Rows of cell texts; header = the first row (Confluence puts headings in <th>). Key-value tables (a heading
    down the first column) are returned with kind 'keyvalue'."""
    rows = []
    for tr in t.iter():
        if tr.tag != 'tr': continue
        cells = [c for c in tr.children if isinstance(c, Node) and c.tag in ('td', 'th')]
        if cells: rows.append([(c.tag, c.text()) for c in cells])
    if not rows: return 'empty', [], []
    if all(r[0][0] == 'th' for r in rows) and len(rows) > 1 and all(len(r) == 2 for r in rows) and not any(c[0] == 'th' for c in rows[0][1:]):
        return 'keyvalue', [clean(r[0][1]) for r in rows], [[r[1][1]] for r in rows]
    return 'grid', [clean(c[1]) for c in rows[0]], [[c[1] for c in r] for r in rows[1:]]


# ---------------------------------------------------------------- draw.io: find the diagram inside files of any kind
def _png_text(data):
    """Text chunks of a PNG: draw.io stores the diagram in a chunk named 'mxfile'."""
    out, i = {}, 8
    while i + 8 <= len(data):
        n = int.from_bytes(data[i:i + 4], 'big'); kind = data[i + 4:i + 8]; body = data[i + 8:i + 8 + n]; i += 12 + n
        try:
            if kind == b'tEXt':
                k, v = body.split(b'\0', 1); out[k.decode('latin-1')] = v.decode('latin-1')
            elif kind == b'zTXt':
                k, v = body.split(b'\0', 1); out[k.decode('latin-1')] = zlib.decompress(v[1:]).decode('latin-1')
            elif kind == b'iTXt':
                k, rest = body.split(b'\0', 1); comp = rest[0]; rest = rest[2:]
                _, rest = rest.split(b'\0', 1); _, text = rest.split(b'\0', 1)
                out[k.decode('latin-1')] = (zlib.decompress(text) if comp else text).decode('utf-8')
        except (ValueError, zlib.error, UnicodeDecodeError):
            continue
        if kind == b'IEND': break
    return out


def find_mxfile(data):
    """The draw.io XML in a file's bytes, or None: plain XML (.drawio), a PNG with the diagram inside, or an SVG
    with the diagram in its content attribute."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        t = _png_text(data).get('mxfile')
        if not t: return None
        return urllib.parse.unquote(t) if t.lstrip().startswith('%3C') else t
    try: s = data.decode('utf-8')
    except UnicodeDecodeError: return None
    head = s.lstrip()[:400]
    if head.startswith('<mxfile') or head.startswith('<mxGraphModel') or ('<mxfile' in head and head.startswith('<?xml')):
        return s
    if '<svg' in s[:2000]:
        m = re.search(r'<svg[^>]*\scontent="([^"]*)"', s)
        if m and 'mxfile' in m.group(1):
            import html as _h
            return _h.unescape(m.group(1))
    return None


def mx_pages(xml):
    """[(page name, mxGraphModel element)] — inline or compressed (base64 → raw deflate → URL-encoded)."""
    root = ET.fromstring(xml)
    if root.tag == 'mxGraphModel': return [('', root)]
    out = []
    for d in root.iter('diagram'):
        model = d.find('mxGraphModel')
        if model is None and (d.text or '').strip():
            raw = zlib.decompress(base64.b64decode(d.text.strip()), -15).decode('utf-8')
            model = ET.fromstring(urllib.parse.unquote(raw))
        if model is not None: out.append((d.get('name') or '', model))
    return out


def style_of(s):
    out = {}
    for part in (s or '').split(';'):
        if not part: continue
        if '=' in part: k, v = part.split('=', 1); out[k] = v
        else: out.setdefault('_bare', []).append(part)
    return out


def label_text(value):
    """A shape's label: draw.io labels may be HTML."""
    if not value: return '', ''
    if '<' in value:
        t = parse_html(value.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')).text()
    else:
        t = value
    return first_line(t)


def mx_cells(model):
    """Shapes and lines of one diagram page: draw.io wraps labelled cells in <object>/<UserObject>."""
    cells = []
    for el in model.iter():
        if el.tag in ('object', 'UserObject'):
            c = el.find('mxCell')
            if c is None: continue
            cells.append({'id': el.get('id'), 'value': el.get('label') or '', **{k: c.get(k) for k in ('style', 'parent', 'source', 'target', 'vertex', 'edge')}})
        elif el.tag == 'mxCell':
            if el.get('id') in {x['id'] for x in cells}: continue
            cells.append({'id': el.get('id'), 'value': el.get('value') or '', **{k: el.get(k) for k in ('style', 'parent', 'source', 'target', 'vertex', 'edge')}})
    return cells


# ---------------------------------------------------------------- PlantUML: read the diagram's source, not its picture
PUML_EXT = ('.puml', '.plantuml', '.pu', '.iuml', '.wsd')
_P64 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'


def plantuml_decode(code):
    """PlantUML's text encoding (as in its URLs and SVG `plantuml-src`): its own base64 alphabet over raw deflate; '~h' = hex."""
    code = code.strip()
    if code.startswith('~h'): return bytes.fromhex(code[2:]).decode('utf-8')
    if code.startswith('~1'): code = code[2:]
    bits = [_P64.index(c) for c in code if c in _P64]
    data = bytearray()
    for i in range(0, len(bits) - 1, 4):
        b = bits[i:i + 4] + [0] * (4 - len(bits[i:i + 4]))
        data += bytes([(b[0] << 2) | (b[1] >> 4), ((b[1] & 15) << 4) | (b[2] >> 2), ((b[2] & 3) << 6) | b[3]])
    return zlib.decompressobj(-15).decompress(bytes(data)).decode('utf-8')


def find_plantuml(data, ext=''):
    """PlantUML source in a file's bytes, or None: a .puml text file, a PNG with the source in its 'plantuml' text chunk,
    or an SVG with the source in a `plantuml-src` instruction or a comment."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        t = _png_text(data).get('plantuml')
        if not t: return None
        if '@start' not in t:
            try: t = plantuml_decode(t)
            except (ValueError, zlib.error, UnicodeDecodeError): return None
        return t if '@start' in t else None
    try: s = data.decode('utf-8')
    except UnicodeDecodeError: return None
    if '<svg' in s[:4000]:
        m = re.search(r'<\?plantuml-src\s+(\S+?)\s*\?>', s)
        if m:
            try: return plantuml_decode(m.group(1))
            except (ValueError, zlib.error, UnicodeDecodeError): return None
        m = re.search(r'(@startuml.*?@enduml)', s, re.S)
        return m.group(1) if m else None
    if ext in PUML_EXT or s.lstrip().startswith('@start'):
        return s if '@start' in s else None
    return None


def plantuml_blocks(text):
    """Every @startuml … @enduml block in a text (a page's code block, a .txt file)."""
    return re.findall(r'(@start(?:uml)?\b.*?@end(?:uml)?\b)', text, re.S)


_PU_KEYWORDS = ('component', 'node', 'database', 'cloud', 'actor', 'artifact', 'interface', 'rectangle', 'queue', 'frame', 'package',
                'folder', 'card', 'storage', 'file', 'collections', 'boundary', 'control', 'entity', 'participant', 'agent', 'stack',
                'hexagon', 'person', 'archimate', 'usecase', 'process', 'label')
_PU_EP = r'(\[[^\]]+\]|"[^"]+"|\(\)\s*"[^"]+"|\(\)\s*[\w.]+|:[^:]+:|[\w.]+)'
_PU_ARROW = r'(<\|?|<<|o|\*|\+|#|x|\})?([-.=~]+)(?:\[[^\]]*\]|(?:up|down|left|right|u|d|l|r)(?=[-.=~]))?([-.=~]*)(\|?>|>>|o|\*|\+|#|x|\{)?'
_PU_SKIP = re.compile(r'(skinparam|title|left to right|top to bottom|hide|show|legend|header|footer|caption|scale|autonumber|activate|deactivate|destroy|return|group|alt|else|opt|loop|par|break|critical|ref|box|end box|newpage|mainframe|allowmixing|together|set|end)\b', re.I)
_PU_REL = re.compile(r'^' + _PU_EP + r'\s*' + _PU_ARROW + r'\s*' + _PU_EP + r'\s*(?::\s*(.*))?$')
_PU_MACRO = re.compile(r'^(\w+)\s*\(\s*(\w+)\s*(?:,\s*("([^"]*)"|\w+))?\s*(?:,\s*"([^"]*)")?(?:\s*,\s*"([^"]*)")?[^)]*\)\s*(\{)?')


def plantuml_parse(src):
    """PlantUML source → (elements, relations, kind). elements: {key: {name, keyword, stereo, desc, parent}};
    relations: [(a, b, label, keyword)]. Reads component, deployment, sequence, C4 and ArchiMate notation; other
    diagram kinds (activity, mind map …) give no elements."""
    kind = (re.search(r'@start(\w+)', src) or [None, 'uml'])[1]
    els, rels, alias, stack = {}, [], {}, []
    if kind != 'uml': return els, rels, kind
    src = re.sub(r"/'.*?'/", '', src, flags=re.S)
    lines = iter(src.splitlines())

    def key_of(token):
        t = token.strip()
        if t.startswith('()'): t = t[2:].strip()
        t = t.strip('"').strip()
        if t.startswith('[') and t.endswith(']'): t = t[1:-1]
        if t.startswith(':') and t.endswith(':'): t = t[1:-1]
        return alias.get(t, t)

    def declare(name, keyword, al=None, stereo='', desc=''):
        name = clean(name.replace('\\n', ' '))
        k = al or name
        if not name: return None
        if k not in els: els[k] = {'name': name, 'keyword': keyword, 'stereo': stereo, 'desc': desc, 'parent': stack[-1] if stack else None}
        if al: alias[al] = k
        alias.setdefault(name, k)
        return k

    def ensure(token, implied):
        k = key_of(token)
        if k not in els:
            t = token.strip()
            kw = 'component' if t.startswith('[') else 'interface' if t.startswith('()') else 'actor' if t.startswith(':') else implied
            declare(k, kw)
        return k
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("'", '@', '!', '==', '...', '|||')) or _PU_SKIP.match(line):
            if re.match(r'legend\b', line) and not line.startswith('legend '):
                for l2 in lines:
                    if re.match(r'\s*(endlegend|end legend)', l2): break
            continue
        if re.match(r'(note|rnote|hnote)\b', line):
            if ':' not in line:
                for l2 in lines:
                    if re.match(r'\s*end\s*(note|rnote|hnote)', l2): break
            continue
        if line.startswith('}'):
            if stack: stack.pop()
            continue
        m = _PU_MACRO.match(line)
        if m and m.group(1)[0].isupper() or (m and m.group(1).lower().startswith(('rel', 'birel'))):
            macro = m.group(1); low = macro.lower()
            if low.startswith(('rel', 'birel')):
                b = m.group(4) if m.group(4) is not None else (m.group(3) or '')
                rels.append((alias.get(m.group(2), m.group(2)), alias.get(b, b), m.group(5) or '', macro)); continue
            name = m.group(4) if m.group(4) is not None else m.group(2)
            c4_tech = re.match(r'(container|component)', low) is not None   # C4: Container(alias, label, technology, description)
            k = declare(name, low, m.group(2), desc=(m.group(6) if c4_tech else m.group(5)) or '')
            if m.group(7) and k: stack.append(k)
            continue
        kw = line.split(None, 1)[0].lower() if line.split() else ''
        if kw in _PU_KEYWORDS and len(line.split(None, 1)) > 1:
            rest = line.split(None, 1)[1].strip()
            opens = rest.endswith('{'); rest = rest.rstrip('{').strip()
            stereo = ' '.join(re.findall(r'<<\s*([^>]+?)\s*>>', rest)); rest = re.sub(r'<<[^>]*>>', '', rest)
            rest = re.sub(r'#[\w]+(\s|$)', ' ', rest).strip()
            if kw == 'archimate': rest = re.sub(r'^#\w+\s*', '', rest)
            m2 = re.match(r'^"([^"]+)"\s+as\s+([\w.]+)', rest) or re.match(r'^([\w.]+)\s+as\s+"([^"]+)"', rest) or re.match(r'^\[([^\]]+)\]\s+as\s+([\w.]+)', rest)
            if m2:
                a, b = m2.group(1), m2.group(2)
                name, al = (b, a) if re.match(r'^[\w.]+\s+as\s+"', rest) else (a, b)
            else:
                m3 = re.match(r'^("([^"]+)"|\[([^\]]+)\]|([\w.]+))(?:\s+as\s+([\w.]+))?', rest)
                if not m3: continue
                name = m3.group(2) or m3.group(3) or m3.group(4); al = m3.group(5)
            k = declare(name, kw, al, stereo)
            if opens and k: stack.append(k)
            continue
        m = re.match(r'^(\[[^\]]+\])(?:\s+as\s+([\w.]+))?\s*(<<[^>]*>>)?\s*$', line) or re.match(r'^\(\)\s*("?[^"]+"?)(?:\s+as\s+([\w.]+))?\s*$', line)
        if m:
            tok = m.group(1); declare(key_of(tok) if not tok.startswith('[') else tok[1:-1], 'component' if tok.startswith('[') else 'interface', m.group(2)); continue
        m = _PU_REL.match(line)
        if m:
            a_tok, head, body1, body2, tail, b_tok, label = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6), m.group(7)
            a, b = ensure(a_tok, 'participant'), ensure(b_tok, 'participant')
            if head in ('<', '<|', '<<') and not tail: a, b = b, a
            rels.append((a, b, clean(label or ''), 'dotted' if '.' in body1 + body2 else 'line'))
    return els, rels, kind


# ---------------------------------------------------------------- pictures: text read by OCR (local, no network) or from SVG text
OCR_JS = r'''ObjC.import('Foundation'); ObjC.import('Vision');
function run(argv) {
  const out = [];
  for (const path of argv) {
    const req = $.VNRecognizeTextRequest.alloc.init; req.recognitionLevel = 0; req.usesLanguageCorrection = false;
    const h = $.VNImageRequestHandler.alloc.initWithURLOptions($.NSURL.fileURLWithPath(path), $({}));
    const lines = [];
    if (h.performRequestsError($([req]), $())) {
      const res = req.results;
      for (let i = 0; i < res.count; i++) {
        const o = res.objectAtIndex(i); const c = o.topCandidates(1).objectAtIndex(0); const b = o.boundingBox;
        lines.push({text: c.string.js, confidence: c.confidence, x: b.origin.x, y: 1 - b.origin.y - b.size.height, w: b.size.width, h: b.size.height});
      }
      out.push({path: path, lines: lines});
    } else out.push({path: path, error: 'not an image Vision can read'});
  }
  return JSON.stringify(out);
}'''


def ocr_engine(name='auto'):
    """A function path -> [{'text', 'confidence', 'x', 'y', 'w', 'h'}] (fractions of the picture, y from the top), or None.
    'vision': macOS's built-in text recognition (Apple Vision, on the device, nothing to install); 'tesseract': the
    Tesseract command if installed; 'auto': whichever is available; 'off': none. Both run locally — no network."""
    import shutil, subprocess, tempfile
    if name == 'off': return None
    if name in ('auto', 'vision') and sys.platform == 'darwin' and shutil.which('osascript'):
        js = Path(tempfile.mkdtemp(prefix='sdem-ocr-')) / 'ocr.js'; js.write_text(OCR_JS, encoding='utf-8')

        def vision(path):
            r = subprocess.run(['osascript', '-l', 'JavaScript', str(js), str(Path(path).resolve())], capture_output=True, text=True, timeout=120)
            if r.returncode != 0: raise OSError(clean(r.stderr)[:200] or 'osascript failed')
            res = json.loads(r.stdout)[0]
            if 'error' in res: raise OSError(res['error'])
            return res['lines']
        vision.engine = 'macOS Vision'
        return vision
    if name in ('auto', 'tesseract') and shutil.which('tesseract'):
        def tesseract(path):
            r = subprocess.run(['tesseract', str(path), 'stdout', 'tsv'], capture_output=True, text=True, timeout=300)
            if r.returncode != 0: raise OSError(clean(r.stderr)[:200] or 'tesseract failed')
            return tesseract_lines(r.stdout)
        tesseract.engine = 'Tesseract'
        return tesseract
    if name in ('vision', 'tesseract'): raise ValueError(f'OCR engine {name!r} is not available on this machine')
    return None


def tesseract_lines(tsv):
    """Tesseract's TSV (level 5 = words) → lines with their box as fractions of the picture."""
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE))
    page = next((r for r in rows if r.get('level') == '1'), None)
    W, H = (float(page['width']), float(page['height'])) if page else (1.0, 1.0)
    lines = collections.OrderedDict()
    for r in rows:
        if r.get('level') != '5' or not (r.get('text') or '').strip(): continue
        k = (r['block_num'], r['par_num'], r['line_num']); x, y, w, h = (float(r[c]) for c in ('left', 'top', 'width', 'height'))
        l = lines.setdefault(k, {'words': [], 'x1': x, 'y1': y, 'x2': x + w, 'y2': y + h, 'conf': []})
        l['words'].append(r['text'].strip()); l['conf'].append(float(r['conf']) / 100)
        l['x1'], l['y1'], l['x2'], l['y2'] = min(l['x1'], x), min(l['y1'], y), max(l['x2'], x + w), max(l['y2'], y + h)
    return [{'text': ' '.join(l['words']), 'confidence': sum(l['conf']) / len(l['conf']), 'x': l['x1'] / W, 'y': l['y1'] / H,
             'w': (l['x2'] - l['x1']) / W, 'h': (l['y2'] - l['y1']) / H} for l in lines.values()]


def svg_text_lines(data):
    """The text of a plain SVG picture (not draw.io, not PlantUML): exact, no OCR needed."""
    try: root = ET.fromstring(data)
    except ET.ParseError: return None
    vb = (root.get('viewBox') or '').replace(',', ' ').split()
    W = float(vb[2]) if len(vb) == 4 else float(re.sub(r'[^\d.]', '', root.get('width') or '') or 1)
    H = float(vb[3]) if len(vb) == 4 else float(re.sub(r'[^\d.]', '', root.get('height') or '') or 1)
    out = []
    for t in root.iter():
        if t.tag.split('}')[-1] != 'text': continue
        s = clean(''.join(t.itertext()))
        if not s: continue
        num = lambda v: float(re.sub(r'[^\d.\-]', '', (v or '0').split()[0]) or 0)
        size = num(t.get('font-size') or '12')
        out.append({'text': s, 'confidence': 1.0, 'x': num(t.get('x')) / W, 'y': (num(t.get('y')) - size) / H, 'w': len(s) * size * 0.55 / W, 'h': size / H})
    return out


def group_labels(lines, rules):
    """OCR lines → labels: lines stacked closely, centred on each other, are one box's label (name, then description)."""
    o = rules.get('ocr', {}); minc = o.get('min_confidence', 0.5)
    ls = sorted((l for l in lines if l.get('confidence', 1) >= minc and re.search(r'[A-Za-z]{2}', l['text'])), key=lambda l: (l['y'], l['x']))
    groups = []
    for l in ls:
        cx = l['x'] + l['w'] / 2
        g = next((g for g in groups if 0 <= l['y'] - (g[-1]['y'] + g[-1]['h']) <= 0.8 * l['h'] and abs(cx - (g[-1]['x'] + g[-1]['w'] / 2)) <= max(l['w'], g[-1]['w']) / 2), None)
        if g: g.append(l)
        else: groups.append([l])
    out = []
    for g in groups:
        name = clean(g[0]['text']); desc = clean(' '.join(x['text'] for x in g[1:]))
        if not (o.get('min_chars', 3) <= len(name) <= o.get('max_chars', 60)) or len(name.split()) > o.get('max_words', 6): continue
        if norm(name) in {norm(x) for x in o.get('ignore', [])}: continue
        if o.get('skip_lowercase', True) and name[:1].islower(): continue
        out.append({'name': name, 'desc': desc, 'confidence': min(x.get('confidence', 1) for x in g)})
    return out


# ---------------------------------------------------------------- the extraction
class Extraction:
    def __init__(self, rules=None, known=(), mm=None, ocr=None):
        self.rules = rules or json.loads(RULES.read_text(encoding='utf-8'))
        self.ocr = ocr                 # a function path -> text lines (ocr_engine), or None
        self.mm = mm or Metamodel.load()
        self.records = {}          # (type, norm name) -> record
        self.links, self.cross, self.review, self.pages, self.bian_mentions = [], [], [], [], []
        self.known = {}            # norm name -> (id, type, file) from --known datasets
        self.stats = collections.Counter()
        self.inspect = {'tables': collections.Counter(), 'shapes': collections.Counter(), 'headings': collections.Counter()}
        for f in known:
            d = json.loads(Path(f).read_text(encoding='utf-8'))
            for i in d.get('instances', []):
                self.known.setdefault(norm(i['name']), (i['id'], i['type'], Path(f).name))
        self.cap = self.rules['confidence']

    # ---- records
    def _id(self, etype, name):
        lvl = etype[:2]; slug = re.sub(r'[^A-Z0-9]+', '-', name.upper()).strip('-')[:40] or 'UNNAMED'
        base = f"{self.rules.get('id_prefix', 'HIS-')}{lvl}-{slug}"
        used = {r['id'] for r in self.records.values()}
        if base not in used: return base
        return f"{base}-{etype.split('.')[1].upper()}"

    def record(self, etype, name, page, where, rule, how, reasoning, description='', lifecycle=None, attributes=None):
        name = clean(name)
        if not name or not self.mm.known(etype) or self.mm.is_abstract(etype): return None
        if etype.startswith('A2.'):  # CTL-17: BIAN elements come from the BIAN catalogue only — a document's mention is a hint for a link, never an entity
            k = self.known.get(norm(name))
            m = {'name': name, 'type': etype, 'page_id': page['page_id'], 'page_title': page['title'], 'where': where,
                 'existing_id': k[0] if k else None, 'why': 'names a BIAN element; A2 entities come from the BIAN catalogue only (CTL-17) — link to it with sdem link after adoption'}
            if not any((x['name'], x['page_id'], x['where']) == (name, page['page_id'], where) for x in self.bian_mentions): self.bian_mentions.append(m)
            return None
        key = (etype, norm(name))
        r = self.records.get(key)
        if r is None:
            r = self.records[key] = {'id': self._id(etype, name), 'type': etype, 'name': name, 'description': '', 'lifecycle_status': None,
                                     'attributes': {}, 'sources': [], 'modified': None}
        rank = {'table': 3, 'table_endpoint': 2}.get(how, 1)   # a table's description column beats a diagram's second line
        if description and (not r['description'] or rank > r.get('_desc_rank', 0)): r['description'] = clean(description); r['_desc_rank'] = rank
        if lifecycle and not r['lifecycle_status']: r['lifecycle_status'] = lifecycle
        for k, v in (attributes or {}).items(): r['attributes'].setdefault(k, v)
        if page.get('modified') and (not r['modified'] or page['modified'] > r['modified']): r['modified'] = page['modified']
        src = {'page_id': page['page_id'], 'page_title': page['title'], 'file': page['file'], 'where': where, 'rule': rule,
               'confidence': self.cap[how], 'reasoning': reasoning}
        if src not in r['sources']: r['sources'].append(src)
        self.stats[f'{how} evidence'] += 1
        return r

    def link(self, a, kind, b, page, where, rule, how, reasoning, label=''):
        """A line between two records. Same architecture → a within-architecture relationship, the kind checked against
        the rulebook (falls back to association, which ArchiMate allows between any two). Different architectures →
        a candidate link between architectures, for the engine and a person."""
        if not a or not b or a is b: return
        if a['type'][:2] == b['type'][:2]:
            lvl = a['type'][:2]
            kinds = [kind] if kind and kind != 'deployed_on' else []
            kinds += [k for k in self.rules['line_kinds']['order'] if k not in kinds]
            chosen = next(k for k in kinds if self.mm.relationship_issue(lvl, a['type'], k, b['type']) is None)
            if kind and chosen != kind: reasoning += f'; the rulebook does not allow {kind} between these types, so {chosen}'
            key = (a['id'], chosen, b['id'])
            ex = next((l for l in self.links if (l['source'], l['kind'], l['target']) == key), None)
            src = {'page_id': page['page_id'], 'page_title': page['title'], 'where': where, 'rule': rule, 'confidence': self.cap[how], 'reasoning': reasoning}
            if ex: ex['sources'].append(src) if src not in ex['sources'] else None
            else: self.links.append({'source': a['id'], 'kind': chosen, 'target': b['id'], 'name': clean(label), 'sources': [src]})
            return
        types = [r for r in _cross_types() if self.mm.is_a(a['type'], r['source_type']) and self.mm.is_a(b['type'], r['target_type'])]
        if not types:
            types_rev = [r for r in _cross_types() if self.mm.is_a(b['type'], r['source_type']) and self.mm.is_a(a['type'], r['target_type'])]
            if types_rev: a, b, types = b, a, types_rev
        if kind != 'deployed_on':  # only containment or "runs on / hosted on" suggests a deployment; any other line is left for a person
            types = [t for t in types if 'DEPLOY' not in t['mapping_type_id']]
        src = {'page_id': page['page_id'], 'page_title': page['title'], 'where': where, 'rule': rule, 'confidence': self.cap[how],
               'reasoning': reasoning + ('' if types else '; a line between two architectures — which SDEM link type (if any) is for a person to decide')}
        mt = types[0]['mapping_type_id'] if types else None
        ex = next((c for c in self.cross if (c['source'], c['target'], c['mapping_type_id']) == (a['id'], b['id'], mt)), None)
        if ex:
            if src not in ex['sources']: ex['sources'].append(src)
            ex['confidence'] = best(ex['sources']); return
        self.cross.append({'source': a['id'], 'target': b['id'], 'mapping_type_id': mt, 'name': clean(label), 'confidence': src['confidence'], 'sources': [src]})

    def lifecycle(self, value):
        v = norm(value)
        if not v: return None
        for status, words in self.rules['lifecycle_values'].items():
            if any(v == norm(w) or v.startswith(norm(w) + ' ') for w in words): return status
        return None

    def layer_of(self, *texts):
        for t in texts:
            t = ' ' + (t or '').lower()
            for lvl, words in self.rules['section_layers'].items():
                if lvl == 'note': continue
                if any(w in t for w in words): return lvl
        return None

    # ---- tables
    def table(self, page, section, data, n):
        kind, headers, rows = data
        hn = [norm(h) for h in headers]
        where = f"table {n}" + (f" under '{section}'" if section else '')
        if kind != 'grid' or not rows:
            self.inspect['tables'][(kind, tuple(hn), 'not read — ' + ('key-value table' if kind == 'keyvalue' else 'no rows'))] += 1; return
        for lr in self.rules.get('link_tables', []):
            si = next((i for i, h in enumerate(hn) if h in map(norm, lr['source'])), None)
            ti = next((i for i, h in enumerate(hn) if h in map(norm, lr['target'])), None)
            if si is None or ti is None or si == ti: continue
            li = next((i for i, h in enumerate(hn) if h in map(norm, lr['label'])), None)
            self.inspect['tables'][('grid', tuple(hn), lr['id'])] += 1
            for k, row in enumerate(rows, 1):
                if len(row) <= max(si, ti): continue
                s, _ = first_line(row[si]); t, _ = first_line(row[ti])
                if not s or not t: continue
                w = f'{where}, row {k}'
                a = self.find(s) or self.record(lr['endpoint_type'], s, page, w, lr['id'], 'table_endpoint', f"named as the source in a '{headers[si]}' column — assumed {lr['endpoint_type'].split('.')[1]}")
                b = self.find(t) or self.record(lr['endpoint_type'], t, page, w, lr['id'], 'table_endpoint', f"named as the target in a '{headers[ti]}' column — assumed {lr['endpoint_type'].split('.')[1]}")
                lab = first_line(row[li])[0] if li is not None and len(row) > li else ''
                self.link(a, lr.get('kind'), b, page, w, lr['id'], 'table', f"row of a source/target table ('{headers[si]}' → '{headers[ti]}')", lab)
            return
        best, score = None, 0
        for tr in self.rules['tables']:
            ni = next((i for i, h in enumerate(hn) if h in map(norm, tr['name'])), None)
            if ni is None: continue
            s = 2 + sum(1 for h in hn if h in map(norm, tr.get('description', []) + tr.get('lifecycle', []) + sum(tr.get('attributes', {}).values(), [])))
            if ni == 0: s += 1
            if s > score: best, score = (tr, ni), s
        if not best:
            self.inspect['tables'][('grid', tuple(hn), 'no rule')] += 1; return
        tr, ni = best
        self.inspect['tables'][('grid', tuple(hn), tr['id'])] += 1
        col = lambda words: next((i for i, h in enumerate(hn) if h in map(norm, words) and i != ni), None)
        di, li = col(tr.get('description', [])), col(tr.get('lifecycle', []))
        ai = {k: col(v) for k, v in tr.get('attributes', {}).items()}
        for k, row in enumerate(rows, 1):
            if len(row) <= ni: continue
            name, rest = first_line(row[ni])
            if not name: continue
            cell = lambda i: clean(row[i]) if i is not None and i < len(row) else ''
            attrs = {a: cell(i) for a, i in ai.items() if cell(i)}
            self.record(tr['type'], name, page, f'{where}, row {k}', tr['id'], 'table',
                        f"listed in a table whose '{headers[ni]}' column names {tr['type'].split('.')[1]} records",
                        cell(di) or rest, self.lifecycle(cell(li)), attrs)

    def find(self, name):
        n = norm(name)
        hits = [r for (t, k), r in self.records.items() if k == n]
        return hits[0] if len(hits) == 1 else None

    # ---- diagrams
    def classify(self, cell, st, name, desc, context, container_type):
        bare = ' '.join(st.get('_bare', [])).lower(); shape = (st.get('shape') or '').lower()
        for r in self.rules['diagram_shapes']:
            if all((st.get(k) or '').lower() == str(v).lower() or (k == 'shape' and shape == str(v).lower()) for k, v in r['match'].items()):
                return r['type'], 'diagram_shape', r['id'], f"drawn with the ArchiMate {r['type'].split('.')[1]} shape"
        label = (name + ' ' + desc).lower()
        fill = (st.get('fillColor') or '').lower()
        lvl = next((l for l, cs in self.rules['diagram_colours'].items() if l != 'note' and fill in [c.lower() for c in cs]), None)
        k = self.known.get(norm(name))  # a name already known — from the --known datasets, or a table or diagram in the export
        if k and (not lvl or k[1][:2] == lvl): return k[1], 'diagram_label', 'HD-K', f"named like the existing {k[1].split('.')[1]} {k[0]} ({k[2]})"
        hit = self.find(name)
        if hit and (not lvl or hit['type'][:2] == lvl): return hit['type'], 'diagram_label', 'HD-N', f"named like {hit['id']}, found elsewhere in the export"
        how = 'diagram_colour' if lvl else 'diagram_label'
        for etype, words in self.rules['label_words'].items():
            if etype == 'note' or (lvl and etype[:2] != lvl): continue
            w = next((w.strip() for w in words if re.search(r'\b' + re.escape(w.strip().lower()) + r'\b', label)), None)
            if w: return etype, how, 'HD-L', f"the label contains the word '{w}'" + (f' and the fill colour {fill} is {lvl}' if lvl else '')
        for etype, words in self.rules['shape_words'].items():
            if etype == 'note' or (lvl and etype[:2] != lvl): continue
            w = next((w for w in words if w in shape or w in bare), None)
            if w: return etype, how, 'HD-S', f"drawn with the shape '{w}'"
        lvl = lvl or self.layer_of(context)
        if lvl and lvl in self.rules['layer_default_type']:
            return self.rules['layer_default_type'][lvl], 'diagram_label', 'HD-D', f"nothing else to go by: the {lvl} default for a diagram under '{context}'"
        return None, None, None, None

    def diagram(self, page, dname, xml, where, context):
        try: pages = mx_pages(xml)
        except (ET.ParseError, ValueError, zlib.error) as e:
            self.review.append({'page_id': page['page_id'], 'page_title': page['title'], 'what': 'diagram', 'where': where, 'why': f'draw.io file could not be read ({e.__class__.__name__})'}); return
        self.stats['diagrams read'] += 1
        for pname, model in pages:
            cells = mx_cells(model); by = {c['id']: c for c in cells}; recs = {}
            ctx = ' / '.join(x for x in (context, dname, pname) if x)
            for c in cells:
                if c.get('vertex') != '1': continue
                st = style_of(c.get('style'))
                if 'text' in st.get('_bare', []) or st.get('shape') == 'text' or (c.get('parent') in by and by[c['parent']].get('edge') == '1'): continue
                name, desc = label_text(c['value'])
                key = st.get('shape') or (st.get('_bare') or ['(plain box)'])[0]
                if not name:
                    self.inspect['shapes'][(key, 'no label — skipped')] += 1; continue
                if name.lower() in ('legend', 'key', 'title') or len(name) > 80: continue
                etype, how, rule, why = self.classify(c, st, name, desc, ctx, None)
                self.inspect['shapes'][(key, etype or 'unclassified')] += 1
                w = f"{where}{' page ' + repr(pname) if pname else ''}, shape {c['id']}"
                if not etype:
                    self.review.append({'page_id': page['page_id'], 'page_title': page['title'], 'what': 'shape', 'where': w, 'name': name,
                                        'why': 'no rule decides its type — add a label or shape word to the rules, or record it by hand'}); continue
                recs[c['id']] = self.record(etype, name, page, w, rule, how, why, desc)
            for cid, r in recs.items():  # a shape inside another: part of it (same architecture) or deployed on it
                p = by.get(cid, {}).get('parent')
                if p in recs and recs[p] is not r:
                    outer = recs[p]
                    w = f"{where}, shape {cid} inside {p}"
                    if outer['type'][:2] == r['type'][:2]:
                        self.link(outer, 'composition', r, page, w, 'HD-C', 'diagram_line', 'drawn inside the other shape')
                    else:
                        self.link(r, 'deployed_on', outer, page, w, 'HD-C', 'diagram_line', 'drawn inside the other shape')
            for c in cells:
                if c.get('edge') != '1': continue
                a, b = recs.get(c.get('source')), recs.get(c.get('target'))
                if not a or not b:
                    self.stats['lines not between two read shapes'] += 1; continue
                lab, _ = label_text(c['value'])
                lab = lab or next((label_text(x['value'])[0] for x in cells if x.get('parent') == c['id'] and x.get('value')), '')
                kind, rev, rule = self.phrase(lab)
                if rev: a, b = b, a
                self.link(a, kind, b, page, f"{where}, line {c['id']}", rule or 'HD-E', 'diagram_line', 'a line between the two shapes' + (f" labelled '{lab}'" if lab else ''), lab)

    def read_diagram(self, page, dname, diagram, where, context):
        kind, source = diagram
        if kind == 'plantuml': return self.plantuml(page, dname, source, where, context)
        return self.diagram(page, dname, source, where, context)

    def guess(self, name, desc, context, how, rule_prefix):
        """The type of a name with no notation to go by: a name already found, a label word, then the section's architecture."""
        k = self.known.get(norm(name))
        if k: return k[1], f'{rule_prefix}-K', f"named like the existing {k[1].split('.')[1]} {k[0]} ({k[2]})"
        hit = self.find(name)
        if hit: return hit['type'], f'{rule_prefix}-N', f"named like {hit['id']}, found elsewhere in the export"
        label = (name + ' ' + desc).lower()
        for etype, words in self.rules['label_words'].items():
            if etype == 'note': continue
            w = next((w.strip() for w in words if re.search(r'\b' + re.escape(w.strip().lower()) + r'\b', label)), None)
            if w: return etype, f'{rule_prefix}-L', f"the label contains the word '{w}'"
        lvl = self.layer_of(context)
        if lvl and lvl in self.rules['layer_default_type']:
            return self.rules['layer_default_type'][lvl], f'{rule_prefix}-D', f"nothing else to go by: the {lvl} default under '{context}'"
        return None, None, None

    def plantuml(self, page, dname, src, where, context):
        els, rels, kind = plantuml_parse(src)
        if not els:
            self.review.append({'page_id': page['page_id'], 'page_title': page['title'], 'what': 'PlantUML diagram not read', 'where': where,
                                'why': f'a @start{kind} diagram with no elements SDEM reads (activity, mind map, Gantt …) — a person records it'}); return
        self.stats['diagrams read'] += 1; self.stats['plantuml diagrams'] += 1
        types = {re.sub(r'[^a-z]', '', k.lower()): v for k, v in self.rules['plantuml_types'].items() if k != 'note'}
        groups = {re.sub(r'[^a-z]', '', g.lower()) for g in self.rules.get('plantuml_groups', [])}
        recs = {}
        for key, e in els.items():
            kw = re.sub(r'[^a-z]', '', e['keyword'].lower()); st = re.sub(r'[^a-z]', '', (e['stereo'] or '').lower())
            w = f"{where}, element {key}"
            etype = types.get(st) or (types.get(kw) if kw != 'archimate' else None)
            if etype:
                how = 'plantuml_untyped' if kw == 'participant' else 'plantuml_typed'
                why = f"declared as PlantUML {e['keyword']}" + (f" <<{e['stereo']}>>" if e['stereo'] else '')
                self.inspect['shapes'][('plantuml ' + (e['stereo'] or e['keyword']), etype)] += 1
                recs[key] = self.record(etype, e['name'], page, w, 'HU-T', how, why, e['desc'])
                continue
            if kw in groups or kw.endswith('boundary'):
                self.inspect['shapes'][('plantuml ' + e['keyword'], 'group — not a record')] += 1; continue
            etype, rule, why = self.guess(e['name'], e['desc'], ' / '.join(x for x in (context, dname) if x), 'plantuml_untyped', 'HU')
            self.inspect['shapes'][('plantuml ' + e['keyword'], etype or 'unclassified')] += 1
            if not etype:
                self.review.append({'page_id': page['page_id'], 'page_title': page['title'], 'what': 'shape', 'where': w, 'name': e['name'],
                                    'why': 'no rule decides its type — add a word to the rules, or record it by hand'}); continue
            recs[key] = self.record(etype, e['name'], page, w, rule, 'plantuml_untyped', why, e['desc'])
        for key, e in els.items():  # nesting: part of the group's record, or deployed on it
            par = e['parent']
            while par and par not in recs: par = els.get(par, {}).get('parent')
            if key in recs and par and recs[par] is not recs[key]:
                outer, r = recs[par], recs[key]
                if outer['type'][:2] == r['type'][:2]: self.link(outer, 'composition', r, page, f"{where}, {key} inside {par}", 'HU-C', 'diagram_line', 'declared inside the other element')
                else: self.link(r, 'deployed_on', outer, page, f"{where}, {key} inside {par}", 'HU-C', 'diagram_line', 'declared inside the other element')
        for a, b, label, how in rels:
            ra, rb = recs.get(a), recs.get(b)
            if not ra or not rb: self.stats['lines not between two read shapes'] += 1; continue
            m = re.match(r'(?i)(?:bi)?rel_(flow|serving|triggering|realization|realisation|assignment|composition|aggregation|access|association|specialization)', how)
            kind, rev, rule = (m.group(1).lower().replace('realisation', 'realization'), False, 'HU-R') if m else self.phrase(label)
            if rev: ra, rb = rb, ra
            self.link(ra, kind, rb, page, f"{where}, {a} → {b}", rule or 'HU-E', 'diagram_line', 'a PlantUML relation' + (f" labelled '{label}'" if label else ''), label)

    def picture(self, page, rel, shown_as, section, alt):
        """A picture: its text read (SVG text exactly; other pictures by OCR, on the machine) into low-confidence candidate
        records where a rule decides their type; lines are not read. Always listed for a person."""
        where = f"picture {rel or shown_as}" + (f" under '{section}'" if section else '')
        lines, how, note = None, None, ''
        if rel and rel.lower().endswith('.svg'):
            lines, how = svg_text_lines((self.root / rel).read_bytes()), 'svg_text'
        elif rel and self.ocr:
            try: lines, how = self.ocr(self.root / rel), 'ocr'; self.stats['pictures read by OCR'] += 1
            except (OSError, ValueError, json.JSONDecodeError) as e: note = f' (OCR could not read it: {e})'
        elif rel and not self.ocr: note = ' (OCR is off)'
        labels = group_labels(lines or [], self.rules)
        made, unknown = [], []
        for lab in labels:
            etype, rule, why = self.guess(lab['name'], lab['desc'], section, how, 'HO')
            if not etype: unknown.append(lab['name']); continue
            r = self.record(etype, lab['name'], page, where, rule, how, ('text read from the picture' if how == 'ocr' else 'text of the SVG picture') + f'; {why}', lab['desc'])
            if r: made.append(r['name']); self.stats['labels read from pictures'] += 1
        read = (f"; read {len(labels)} label(s){' by OCR' if how == 'ocr' else ''}: " + ', '.join(l['name'] for l in labels[:12]) + (' …' if len(labels) > 12 else '')
                + (f" — {len(made)} became candidates" if made else '') + (f"; type unknown: {', '.join(unknown[:8])}" if unknown else '')) if labels else ''
        self.review.append({'page_id': page['page_id'], 'page_title': page['title'], 'what': 'picture', 'where': where, 'name': alt or Path(rel or shown_as).name,
                            'why': ('lines and boxes cannot be read from a picture — a person checks the labels and adds the links' if labels else
                                    'a pasted picture — a person records what it shows, or redraws it in draw.io or PlantUML') + read + note
                                   + ('' if rel else ' (the file is not in the export)')})
        page['images_for_review'].append(rel or shown_as); self.stats['pictures for a person'] += 1
        return made

    def phrase(self, text):
        t = ' ' + norm(text) + ' '
        for p in self.rules['phrases']:
            if any(f' {norm(w)} ' in t for w in p['words']): return p['kind'], p.get('reverse', False), p['id']
        return None, False, None

    # ---- narrative
    def narrative(self, page, texts):
        nr = self.rules['narrative']; ignore = set(map(norm, nr['ignore_names']))
        names = {}
        for r in self.records.values():
            n = norm(r['name'])
            if len(n) >= nr['min_name_chars'] and n not in ignore: names.setdefault(n, r)
        if not names: return
        rx = re.compile(r'\b(' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r')\b')
        for section, text in texts:
            for sent in re.split(r'(?<=[.;!?])\s+', text):
                s = norm(sent); hits = [(m.start(), m.end(), names[m.group(1)]) for m in rx.finditer(s)]
                where = 'text' + (f" under '{section}'" if section else '')
                for _, _, r in hits:
                    src = {'page_id': page['page_id'], 'page_title': page['title'], 'file': page['file'], 'where': where, 'rule': 'HN-01',
                           'confidence': self.cap['narrative'], 'reasoning': 'mentioned by name in the text'}
                    if src not in r['sources']: r['sources'].append(src); self.stats['narrative mentions'] += 1
                for (s1, e1, a), (s2, e2, b) in zip(hits, hits[1:]):
                    between = s[e1:s2]
                    if len(between) > nr['max_gap_chars']: continue
                    kind, rev, rule = self.phrase(between)
                    if not kind: continue
                    x, y = (b, a) if rev else (a, b)
                    self.link(x, kind, y, page, where, rule, 'narrative', f"the text says '{clean(sent)[:160]}'")
            for n, k in self.known.items():
                if len(n) >= nr['min_name_chars'] and n not in ignore and re.search(r'\b' + re.escape(n) + r'\b', norm(text)):
                    page.setdefault('existing_mentions', set()).add(k[0])

    # ---- where a page points: a file of the export, resolved from the page's own folder
    def resolve(self, page, ref):
        ref = urllib.parse.unquote((ref or '').split('?')[0].split('#')[0]).strip()
        if not ref or re.match(r'^[a-z][a-z0-9+.-]*:', ref, re.I): return None   # web links, data:, mailto: — not files of the export
        for c in (os.path.normpath(os.path.join(os.path.dirname(page['file']), ref)), os.path.normpath(ref.lstrip('/'))):
            c = c.replace(os.sep, '/')
            if c in self.files: return c
        hits = self.by_name.get(Path(ref).name.lower(), [])
        return hits[0] if len(hits) == 1 else None

    # ---- one page
    def page(self, p):
        p['diagrams'], p['images_for_review'] = [], []
        mine = {}  # diagrams of this page: rel -> name
        for ref, text in p['links']:  # links to diagram files (Confluence's Attachments section, or any <a href>)
            t = self.resolve(p, ref)
            if t in self.diagrams: mine.setdefault(t, p['attachment_names'].get(t) or text or Path(t).stem)
        for rel in self.diagrams:  # standard Confluence export: attachments/<pageId>/
            if rel.startswith(f"attachments/{p['page_id']}/"): mine.setdefault(rel, p['attachment_names'].get(rel) or Path(rel).stem)
        n_table, texts, sec_of = 0, [], {}
        for kind, section, x in p['blocks']:
            self.inspect['headings'][(section.split(' / ')[-1] if section else '(no heading)', self.layer_of(section) or '—')] += 1 if kind == 'text' else 0
            if kind == 'table':
                n_table += 1; self.table(p, section, x, n_table)
            elif kind == 'text':
                texts.append((section, x))
            elif kind == 'plantuml':
                n_pu = sum(1 for d in p['diagrams'] if d['file'].startswith(p['file'] + '#')) + 1
                name = f'PlantUML {n_pu}'
                self.read_diagram(p, name, ('plantuml', x), f"PlantUML block {n_pu}" + (f" under '{section}'" if section else ''), section)
                p['diagrams'].append({'name': name, 'file': f"{p['file']}#plantuml-{n_pu}", 'kind': 'plantuml', 'read': True})
            elif kind == 'img':
                src = urllib.parse.unquote(x['src']).split('?')[0]
                if not src or any(s in src for s in self.rules['skip_images']): continue
                t = self.resolve(p, src)
                alias = norm(re.sub(r'\.(png|svg|jpe?g)$', '', x['alias'] or x['alt'], flags=re.I))
                if t in self.diagrams:  # the picture is the diagram (a draw.io PNG or SVG)
                    mine.setdefault(t, Path(t).stem); sec_of[t] = section; self.used_pictures.add(t); continue
                if t: self.used_pictures.add(t)
                folder = os.path.dirname(t) if t else None
                match = next((rel for rel, name in mine.items() if (alias and norm(name) == alias) or norm(Path(rel).stem) == norm(Path(src).stem)), None) \
                    or next((rel for rel in self.diagrams if folder is not None and os.path.dirname(rel) == folder and norm(Path(rel).stem.split('.')[0]) == norm(Path(src).stem.split('.')[0])), None)
                if match: mine.setdefault(match, Path(match).stem); sec_of[match] = section; continue
                self.picture(p, t, src, section, x['alt'])
        for rel, name in mine.items():
            self.read_diagram(p, name, self.diagrams[rel], f"diagram '{name}' ({rel})", sec_of.get(rel, ' / '.join(p['breadcrumb'])))
            p['diagrams'].append({'name': name, 'file': rel, 'kind': self.diagrams[rel][0], 'read': True}); self.linked.add(rel)
        p['_texts'] = texts + p.pop('_texts_extra', [])
        self.stats['pages'] += 1; self.stats['tables'] += n_table

    # ---- the root files: readme, source, evidence — kept as provenance; JSON and CSV lists fill in page ids, links and dates
    def provenance(self, files, root):
        keys = {k: [norm(x) for x in v] for k, v in self.rules.get('manifest_keys', {}).items() if k != 'note'}
        index = collections.defaultdict(list)
        for pg in self.pages:
            for k in {pg['file'], Path(pg['file']).name, Path(pg['file']).stem, pg['title']}:
                if k: index[norm(k)].append(pg)
        out = []
        for f in files:
            data = f.read_bytes(); rel = f.relative_to(root).as_posix(); ext = f.suffix.lower()
            e = {'file': rel, 'kind': ext.lstrip('.') or 'file', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            rows = None
            try:
                if ext == '.json':
                    d = json.loads(data.decode('utf-8-sig'))
                    if isinstance(d, list) and all(isinstance(x, dict) for x in d): rows = d
                    elif isinstance(d, dict):
                        rows = next((v for v in d.values() if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)), None)
                        e['fields'] = sorted(k for k, v in d.items() if not isinstance(v, (list, dict)))
                elif ext in ('.csv', '.tsv'):
                    rows = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig', errors='replace')), delimiter='\t' if ext == '.tsv' else ','))
                elif ext in ('.md', '.markdown', '.txt'):
                    first = next((l for l in data.decode('utf-8', errors='replace').splitlines() if l.strip()), '')
                    e['title'] = clean(first.lstrip('#'))[:120]
            except (ValueError, UnicodeDecodeError) as err:
                e['note'] = f'not read ({err.__class__.__name__})'
            if rows is not None:
                e['entries'] = len(rows); matched = 0
                for r in rows:
                    rn = {norm(k): v for k, v in r.items() if isinstance(v, (str, int)) and str(v).strip()}
                    pages = {id(pg): pg for v in rn.values() for pg in index.get(norm(v), [])}
                    if len(pages) != 1: continue
                    pg = next(iter(pages.values())); matched += 1
                    get = lambda k: next((str(rn[x]).strip() for x in keys.get(k, []) if x in rn), None)
                    if get('page_id') and pg['id_from'] == 'path': pg['page_id'], pg['id_from'] = get('page_id'), rel
                    if get('url') and not pg.get('url'): pg['url'] = get('url')
                    if get('modified') and not pg['modified']: pg['modified'] = parse_date(get('modified'))
                    if get('title') and pg['title'].endswith(Path(pg['file']).stem): pg['title'] = get('title')
                    if get('space') and not pg['space']: pg['space'] = get('space')
                e['pages_matched'] = matched
            out.append(e)
        return out

    def run(self, root):
        root = Path(root)
        if not root.is_dir(): raise ValueError(f'{root}: not a folder')
        sc = scan(root, self.rules)
        if not sc['pages']: raise ValueError(f'{root}: no pages found (.html, .md, .txt or .csv) — is this the export folder?')
        self.root = root; self.layout = sc['layout']; self.diagrams = sc['diagrams']; self.files = set()
        for p in root.rglob('*'):
            if p.is_file(): self.files.add(p.relative_to(root).as_posix())
        self.by_name = collections.defaultdict(list)
        for f in sorted(self.files): self.by_name[f.rsplit('/', 1)[-1].lower()].append(f)
        self.used_pictures, self.linked = set(), set()
        self.pages = [read_page(p, root, self.rules) for p in sc['pages']]
        self.provenance_files = self.provenance(sc['provenance'], root)  # before extraction: page ids and dates from the manifest
        for p in self.pages: self.page(p)
        for rel, xml in self.diagrams.items():  # diagrams no page points to: read with their folder as context
            if rel in self.linked: continue
            if any(os.path.dirname(rel) == os.path.dirname(u) and Path(u).stem.split('.')[0] == Path(rel).stem.split('.')[0] for u in self.used_pictures): continue
            sec = ' / '.join(folder_sections(rel, self.rules))
            pg = {'page_id': rel, 'id_from': 'path', 'title': f'{Path(rel).name} (diagram file)', 'space': '', 'file': rel, 'modified': None,
                  'breadcrumb': folder_sections(rel, self.rules), 'diagrams': [{'name': Path(rel).stem, 'file': rel, 'kind': xml[0], 'read': True}], 'images_for_review': [], 'url': None, 'diagram_only': True}
            self.read_diagram(pg, Path(rel).stem, xml, f"diagram file {rel}", sec)
            self.review.append({'page_id': rel, 'page_title': pg['title'], 'what': 'diagram not linked to a page', 'where': rel, 'name': Path(rel).stem,
                                'why': 'read with its folder as context' + (f" ('{sec}')" if sec else '') + '; check which design it belongs to'})
            pg['_texts'] = []; self.pages.append(pg); self.stats['diagrams not linked'] += 1
        stems = {(os.path.dirname(d), Path(d).stem.split('.')[0].lower()) for d in self.diagrams}
        for rel in sc['pictures']:  # pictures no page shows: maybe the section's content
            if rel in self.used_pictures or rel.startswith('attachments/') or any(s in rel for s in self.rules['skip_images']): continue
            if (os.path.dirname(rel), Path(rel).stem.split('.')[0].lower()) in stems: continue   # a draw.io preview
            sec = ' / '.join(folder_sections(rel, self.rules))
            pg = {'page_id': rel, 'id_from': 'path', 'title': f'{Path(rel).name} (picture file)', 'space': '', 'file': rel, 'modified': None,
                  'breadcrumb': folder_sections(rel, self.rules), 'diagrams': [], 'images_for_review': [], 'url': None, 'diagram_only': True}
            self.picture(pg, rel, rel, sec, Path(rel).name)
            self.review[-1]['what'] = 'picture not shown on any page'
            pg['_texts'] = pg.pop('_texts_extra', []); self.pages.append(pg)
        for p in self.pages: self.narrative(p, p.pop('_texts'))  # after every page: names from all tables and diagrams
        dup = collections.defaultdict(list)
        for r in self.records.values(): dup[norm(r['name'])].append(r)
        for n, rs in dup.items():
            if len(rs) > 1:
                self.review.append({'what': 'same name, different types', 'name': rs[0]['name'], 'where': ', '.join(f"{r['id']} ({r['type']})" for r in rs),
                                    'why': 'one thing or two? keep one type, or rename'})
        for r in self.records.values():
            k = self.known.get(norm(r['name']))
            if k: r['same_as_existing'] = {'id': k[0], 'type': k[1], 'file': k[2]}
        return self

    # ---- outputs
    def datasets(self, model_id):
        out = {}
        for lvl in ('A1', 'A2', 'A3', 'A4'):
            recs = sorted((r for r in self.records.values() if r['type'][:2] == lvl), key=lambda r: r['id'])
            if not recs: continue
            ids = {r['id'] for r in recs}
            inst = []
            for r in recs:
                i = {'id': r['id'], 'type': r['type'], 'version': r['modified'] or '1', 'name': r['name']}
                if r['lifecycle_status']: i['lifecycle_status'] = r['lifecycle_status']
                if r['description']: i['description'] = r['description']
                at = dict(r['attributes'])
                dep = sorted({c['target'] for c in self.cross if c['source'] == r['id'] and c['mapping_type_id'] == 'COMPONENT_DEPLOYED_ON_INFRASTRUCTURE'})
                if dep: at['deployed_on'] = dep   # "deployed on" as data — the form the engine reads (HI-R06)
                pages = sorted({s['page_id'] for s in r['sources']})
                at['source_id'] = 'confluence:' + ','.join(pages)
                if r['modified']: at['modified'] = r['modified']
                i['attributes'] = at
                inst.append(i)
            rels = [{k: l[k] for k in ('source', 'kind', 'target', 'name') if l.get(k)} for l in self.links if l['source'] in ids and l['target'] in ids]
            out[lvl] = {'level': lvl, 'model_id': f'{model_id}-{lvl}-EXTRACT', 'model_version': datetime.date.today().isoformat(),
                        'metamodel_version': self.mm.version, 'source_system': SOURCE_SYSTEM, 'instances': inst, 'relationships': rels}
        return out

    def summary(self):
        by = collections.Counter(r['type'][:2] for r in self.records.values())
        conf = collections.Counter(best(r['sources']) for r in self.records.values())
        return {'pages': self.stats['pages'], 'tables': self.stats['tables'], 'diagrams_read': self.stats['diagrams read'],
                'diagrams_not_linked': self.stats['diagrams not linked'], 'provenance_files': len(getattr(self, 'provenance_files', [])),
                'plantuml_diagrams': self.stats['plantuml diagrams'], 'pictures_read_by_ocr': self.stats['pictures read by OCR'],
                'labels_read_from_pictures': self.stats['labels read from pictures'], 'ocr_engine': getattr(self.ocr, 'engine', 'off') if self.ocr else 'off',
                'pictures_for_a_person': self.stats['pictures for a person'], 'records': dict(sorted(by.items())),
                'records_by_confidence': dict(conf), 'links_within': len(self.links), 'links_between_candidates': len(self.cross),
                'for_review': len(self.review), 'narrative_mentions': self.stats['narrative mentions'], 'bian_mentions': len(self.bian_mentions)}


def best(sources):
    return max((s['confidence'] for s in sources), key=lambda c: RANK[c], default='low')


def _cross_types():
    return json.loads((DATA_ROOT / 'schema' / 'relationship-types.json').read_text(encoding='utf-8'))['relationships']


def _digest(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file(): h.update(p.relative_to(root).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()


def extract(root, out, rules=None, known=(), model_id=None, now=None, ocr='auto'):
    """Read the export at root, write the candidate datasets, extraction.json, design-index.json and
    extraction-report.md to out. Returns (extraction, written datasets, check issues per layer)."""
    from .graph import LevelGraph
    rules_doc = json.loads(Path(rules).read_text(encoding='utf-8')) if rules else None
    x = Extraction(rules_doc, known, ocr=ocr if callable(ocr) else ocr_engine(ocr)).run(root)
    model_id = model_id or (re.sub(r'[^A-Z0-9]+', '-', (x.pages[0]['space'] or Path(root).name).upper()).strip('-') or 'CONFLUENCE')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    ds = x.datasets(model_id); issues = {}
    for lvl, d in ds.items():
        (out / DATASETS[lvl]).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        g = LevelGraph(d, x.mm); issues[lvl] = g.validate(); issues[lvl + ' advice'] = g.warnings
    now = now or datetime.datetime.now().replace(microsecond=0).isoformat()
    meta = {'generated': now, 'export': str(root), 'export_sha256': _digest(root), 'rules': str(rules or RULES.relative_to(DATA_ROOT)),
            'rules_sha256': hashlib.sha256(json.dumps(x.rules, sort_keys=True).encode()).hexdigest(), 'known': [str(k) for k in known],
            'status': 'candidate — not real architecture data until a person confirms each record', 'summary': x.summary(),
            'provenance_files': x.provenance_files}
    records = [{'id': r['id'], 'type': r['type'], 'name': r['name'], 'confidence': best(r['sources']), 'status': 'candidate',
                'sources': r['sources'], **({'same_as_existing': r['same_as_existing']} if r.get('same_as_existing') else {})}
               for r in sorted(x.records.values(), key=lambda r: r['id'])]
    links = [{**l, 'confidence': best(l['sources']), 'status': 'candidate'} for l in x.links]
    (out / 'extraction.json').write_text(json.dumps({**meta, 'records': records, 'links_within': links, 'links_between_candidates': x.cross, 'bian_mentions': x.bian_mentions,
                                                     'for_review': x.review, 'check': issues}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    idx = []
    for p in x.pages:
        ids = sorted({r['id'] for r in x.records.values() if any(s['page_id'] == p['page_id'] for s in r['sources'])})
        idx.append({'page_id': p['page_id'], 'page_id_from': p.get('id_from'), 'title': p['title'], 'space': p['space'], 'url': p.get('url'),
                    'breadcrumb': p['breadcrumb'], 'file': p['file'], 'modified': p['modified'], 'diagram_only': bool(p.get('diagram_only')),
                    'records': ids, 'existing_records_mentioned': sorted(p.get('existing_mentions', ())),
                    'diagrams': p['diagrams'], 'pictures_for_a_person': p['images_for_review']})
    (out / 'design-index.json').write_text(json.dumps({'generated': now, 'export': str(root), 'provenance_files': x.provenance_files, 'designs': idx},
                                                      indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'extraction-report.md').write_text(report(x, meta, records, links, issues, idx), encoding='utf-8')
    return x, ds, issues


def report(x, meta, records, links, issues, idx):
    s = meta['summary']; L = []
    L.append('# Confluence extraction — candidate architecture records\n')
    L.append(f"> Generated {meta['generated']} by `sdem transform run` from `{meta['export']}` (rules `{meta['rules']}`). "
             'Rules only — no AI. **Every record below is a candidate**: check it against the page, then copy what is right into your estate. '
             'Confidence is never above medium.\n')
    L.append('## Summary\n')
    L.append('| Pages | Tables | Diagrams read | Pictures for a person | Records | Links inside | Links between (candidates) | For review |')
    L.append('|---|---|---|---|---|---|---|---|')
    L.append(f"| {s['pages']} | {s['tables']} | {s['diagrams_read']} | {s['pictures_for_a_person']} | "
             + ', '.join(f'{k} {v}' for k, v in s['records'].items()) + f" | {s['links_within']} | {s['links_between_candidates']} | {s['for_review']} |\n")
    L.append('## Check (`sdem check` on the candidate datasets)\n')
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        if lvl in issues:
            e, w = issues[lvl], issues[lvl + ' advice']
            L.append(f"- **{lvl}**: {'no errors' if not e else str(len(e)) + ' error(s)'}" + (f', {len(w)} advice' if w else ''))
            L += [f'  - {i}' for i in e[:20]]
    L.append('')
    L.append('## Records\n')
    L.append('| Id | Type | Name | Confidence | From (page — where — rule) | Why |')
    L.append('|---|---|---|---|---|---|')
    for r in records:
        top = sorted(r['sources'], key=lambda q: -RANK[q['confidence']])
        frm = '<br>'.join(f"{q['page_title']} — {q['where']} — {q['rule']}" for q in top[:3]) + (f'<br>… {len(top) - 3} more' if len(top) > 3 else '')
        same = f"<br>**same name as existing {r['same_as_existing']['id']}**" if r.get('same_as_existing') else ''
        L.append(f"| `{r['id']}` | {r['type']} | {r['name']} | {r['confidence']} | {frm} | {top[0]['reasoning']}{same} |")
    L.append('\n## Links inside an architecture\n')
    L.append('| Source | Kind | Target | Confidence | From | Why |')
    L.append('|---|---|---|---|---|---|')
    for l in links:
        q = l['sources'][0]
        L.append(f"| `{l['source']}` | {l['kind']} | `{l['target']}` | {l['confidence']} | {q['page_title']} — {q['where']} | {q['reasoning']} |")
    L.append('\n## Links between architectures — candidates for the engine and a person\n')
    L.append('These are not written to any dataset. Approve them the usual way (`sdem link`, `sdem approve`) once the records are real.\n')
    L.append('| Source | Target | Link type | Confidence | From | Why |')
    L.append('|---|---|---|---|---|---|')
    for c in x.cross:
        frm = '<br>'.join(f"{q['page_title']} — {q['where']}" for q in c['sources'])
        L.append(f"| `{c['source']}` | `{c['target']}` | {c['mapping_type_id'] or '—'} | {c['confidence']} | {frm} | {'<br>'.join(q['reasoning'] for q in c['sources'])} |")
    L.append('\n## BIAN elements named in the designs — not entities (CTL-17)\n')
    L.append('A2 entities come from the BIAN catalogue only. These names are hints for `sdem link` once the entities are adopted.\n')
    L.append('| Name | Type | Existing record | Page | Where |')
    L.append('|---|---|---|---|---|')
    for m in x.bian_mentions:
        L.append(f"| {m['name']} | {m['type']} | {m['existing_id'] or '—'} | {m['page_title']} | {m['where']} |")
    L.append('\n## For a person\n')
    L.append('| What | Page | Where | Name | Why |')
    L.append('|---|---|---|---|---|')
    for v in x.review:
        L.append(f"| {v['what']} | {v.get('page_title', '—')} | {v.get('where', '')} | {v.get('name', '')} | {v['why']} |")
    L.append('\n## Export provenance (files in the export\'s root)\n')
    L.append('| File | Kind | Entries | Pages matched | SHA-256 |')
    L.append('|---|---|---|---|---|')
    for f in meta.get('provenance_files', []):
        L.append(f"| `{f['file']}` | {f['kind']} | {f.get('entries', '—')} | {f.get('pages_matched', '—')} | `{f['sha256'][:12]}…` |")
    L.append('\n## Designs (the reference index)\n')
    L.append('| Page | Modified | Records | Diagrams read | Pictures for a person |')
    L.append('|---|---|---|---|---|')
    for p in idx:
        L.append(f"| {p['title']} (`{p['file']}`) | {p['modified'] or '—'} | {len(p['records'])} | {len(p['diagrams'])} | {len(p['pictures_for_a_person'])} |")
    L.append('\n## Next\n')
    L.append('1. Read each record against its page; delete what is wrong, fix names and types.')
    L.append('2. Fill required attributes the check reports (LC-04).')
    L.append('3. Load the records you keep: `sdem load <this folder> --estate <estate> --person <you> --exclude <ids you reject>` — then `sdem link`, `sdem approve`, `sdem build`.')
    L.append('4. Tune the rules for the next run: `sdem transform inspect` shows the tables and shapes no rule read.\n')
    return '\n'.join(L)


KEEP_NAMES = {'archives', 'archive', 'attachments', 'images', 'styles', 'diagrams', '.'}


def inspect(root, rules=None, anonymous=False, ocr='auto'):
    """What is in the export and which rule reads it — structure only (folders, headings, column names, shape kinds),
    no records. anonymous: folder names replaced by F1, F2 … (well-known names kept) so the layout can be described safely."""
    rules_doc = json.loads(Path(rules).read_text(encoding='utf-8')) if rules else None
    x = Extraction(rules_doc, ocr=ocr if callable(ocr) else ocr_engine(ocr)).run(root)
    names = {}

    def anon(folder):
        if not anonymous: return folder
        return '/'.join(p if p.lower() in KEEP_NAMES else names.setdefault(p, f'F{len(names) + 1}') for p in folder.split('/'))
    layout = [{'folder': anon(f), 'depth': 0 if f == '.' else f.count('/') + 1, **dict(c)} for f, c in sorted(x.layout.items())]
    if anonymous:
        return {'layout': layout, 'summary': x.summary(), 'for_review': collections.Counter(v['what'] for v in x.review)}
    return {'layout': layout, 'summary': x.summary(),
            'tables': [{'kind': k, 'columns': list(h), 'rule': r, 'count': n} for (k, h, r), n in x.inspect['tables'].most_common()],
            'shapes': [{'shape': s, 'type': t, 'count': n} for (s, t), n in x.inspect['shapes'].most_common()],
            'headings': [{'heading': h, 'layer': l, 'paragraphs': n} for (h, l), n in x.inspect['headings'].most_common() if n],
            'for_review': collections.Counter(v['what'] for v in x.review)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem transform', description='Transform an export of past designs (Confluence) into candidate architecture entities — rules only, no network; text in pictures by on-device OCR (--ocr off to disable).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('inspect', help='what is in the export and which rules read it — structure only')
    i.add_argument('export'); i.add_argument('--rules', help='your copy of metamodel/transform-rules.json'); i.add_argument('--json', action='store_true')
    i.add_argument('--anonymous', action='store_true', help='folder layout only, names replaced by F1, F2 … — safe to describe to others')
    i.add_argument('--ocr', default='auto', choices=['auto', 'vision', 'tesseract', 'off'], help='read text in pictures: macOS Vision (built in), Tesseract (if installed), auto, or off')
    e = sub.add_parser('run', help='transform the export: write candidate datasets, extraction.json, design-index.json and extraction-report.md')
    e.add_argument('export'); e.add_argument('-o', '--out', required=True); e.add_argument('--rules', help='your copy of metamodel/transform-rules.json')
    e.add_argument('--known', nargs='+', default=[], help='existing SDEM datasets: their names are found in the text and flagged as the same record')
    e.add_argument('--model-id', help='name for the candidate datasets (default: the Confluence space)'); e.add_argument('--json', action='store_true')
    e.add_argument('--ocr', default='auto', choices=['auto', 'vision', 'tesseract', 'off'], help='read text in pictures: macOS Vision (built in), Tesseract (if installed), auto, or off')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'inspect':
            r = inspect(a.export, a.rules, a.anonymous, a.ocr)
            if a.json: print(json.dumps({**r, 'for_review': dict(r['for_review'])}, indent=2, ensure_ascii=False)); return 0
            s = r['summary']
            print(f"{s['pages']} pages, {s['tables']} tables, {s['diagrams_read']} diagrams read (draw.io and {s['plantuml_diagrams']} PlantUML; {s['diagrams_not_linked']} not linked to a page), "
                  f"{s['pictures_read_by_ocr']} pictures read by OCR ({s['ocr_engine']}), "
                  f"{s['pictures_for_a_person']} pictures for a person, {s['provenance_files']} provenance files in the root")
            print('\nFolders (what each holds):')
            for f in r['layout']:
                print(f"  {'  ' * f['depth']}{f['folder']}: " + ', '.join(f'{k} {v}' for k, v in f.items() if k not in ('folder', 'depth')))
            if a.anonymous:
                print('\nFor a person: ' + (', '.join(f'{k} {v}' for k, v in r['for_review'].items()) or 'nothing')); return 0
            print('\nTables (columns → rule):')
            for t in r['tables']: print(f"  {t['count']:>3} × [{' | '.join(t['columns'])}] → {t['rule']}")
            print('\nDiagram shapes (draw.io shape → type):')
            for t in r['shapes']: print(f"  {t['count']:>3} × {t['shape']} → {t['type']}")
            print('\nHeadings (→ architecture):')
            for t in r['headings'][:40]: print(f"  {t['paragraphs']:>3} × {t['heading']} → {t['layer']}")
            print('\nFor a person: ' + (', '.join(f'{k} {v}' for k, v in r['for_review'].items()) or 'nothing'))
            print('\nTune: copy metamodel/transform-rules.json, add the column names or shape words marked "no rule"/"unclassified", pass --rules.')
            return 0
        x, ds, issues = extract(a.export, a.out, a.rules, a.known, a.model_id, ocr=a.ocr)
    except (ValueError, OSError) as err:
        print(f'ERROR: {err}', file=sys.stderr); return 2
    s = x.summary(); errs = sum(len(v) for k, v in issues.items() if 'advice' not in k)
    if a.json: print(json.dumps({'out': str(a.out), 'summary': s, 'check_errors': errs}, indent=2)); return 0
    print(f"{s['pages']} pages read: " + (', '.join(f'{k} {v} records' for k, v in s['records'].items()) or 'no records')
          + f", {s['links_within']} links inside, {s['links_between_candidates']} candidate links between, {s['pictures_for_a_person']} pictures for a person")
    print(f"written to {a.out}: " + ', '.join(DATASETS[l] for l in ds) + ', extraction.json, design-index.json, extraction-report.md')
    print('check: ' + ('no errors' if not errs else f'{errs} error(s) — see extraction-report.md'))
    print('All records are candidates (confidence low or medium): review extraction-report.md before using any of them.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
