"""Word (.docx) and Excel (.xlsx) designs as the blocks `sdem transform` reads (HI-F01…HI-F03) — standard library only.

Both formats are zip files of XML (Office Open XML). Read here:

- **Word:** headings (by the paragraph's style, or its outline level), paragraphs, tables (merged cells filled), pictures counted
  (their content is not read);
- **Excel:** every visible sheet, the sheet's name as its heading; the cells, as Excel last saved them (a formula's saved value, a
  shared string); merged cells filled; a sheet's tables split at blank rows; a title line above a table kept as text, not read as its
  header; hidden sheets listed, not read.

The blocks are those of `transform.md_blocks`: ('table', section, ('grid', headers, rows[, row numbers])), ('text', section, str).
Nothing here decides what a row *is* — the transform rules do.
"""
import re
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PR = '{http://schemas.openxmlformats.org/package/2006/relationships}'
DC = '{http://purl.org/dc/elements/1.1/}'
MAX_PART = 50_000_000   # bytes of one XML part, uncompressed — a larger part is not read


class OfficeError(ValueError):
    """The file is not a Word or Excel file SDEM can read."""


def _clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def _part(z, name):
    try: info = z.getinfo(name)
    except KeyError: return None
    if info.file_size > MAX_PART: raise OfficeError(f'{name}: {info.file_size} bytes — larger than SDEM reads')
    return ET.fromstring(z.read(name))


def _open(data):
    import io
    try: return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile: raise OfficeError('not an Office Open XML file (a .docx or .xlsx is a zip) — an older .doc or .xls? Save it as .docx or .xlsx')


def _core_title(z):
    core = _part(z, 'docProps/core.xml')
    t = core.find(f'{DC}title') if core is not None else None
    return _clean(t.text) if t is not None and t.text else ''


# ------------------------------------------------------------------ Word

def _heading_levels(z):
    """styleId → heading level (1–9), 0 for the Title style — by the style's name ('heading 2') or its outline level."""
    st = _part(z, 'word/styles.xml'); out = {}
    if st is None: return out
    for s in st.iter(f'{W}style'):
        sid = s.get(f'{W}styleId'); n = s.find(f'{W}name'); name = (n.get(f'{W}val') if n is not None else '') or ''
        m = re.fullmatch(r'heading\s*(\d)', name.strip().lower())
        ol = s.find(f'{W}pPr/{W}outlineLvl')
        if name.strip().lower() == 'title': out[sid] = 0
        elif m: out[sid] = int(m.group(1))
        elif ol is not None and ol.get(f'{W}val', '').isdigit() and int(ol.get(f'{W}val')) < 9: out[sid] = int(ol.get(f'{W}val')) + 1
    return out


def _w_text(el):
    parts = []
    for n in el.iter():
        if n.tag == f'{W}t' and n.text: parts.append(n.text)
        elif n.tag in (f'{W}tab', f'{W}br', f'{W}cr'): parts.append(' ')
    return ''.join(parts)


def _w_table(tbl):
    """Rows of cell texts; a cell spanning columns repeats its text, a vertically merged cell takes the one above."""
    rows = []
    for tr in tbl.findall(f'{W}tr'):
        row = []
        for tc in tr.findall(f'{W}tc'):
            pr = tc.find(f'{W}tcPr'); span = 1; vmerge = None
            if pr is not None:
                gs = pr.find(f'{W}gridSpan'); vm = pr.find(f'{W}vMerge')
                if gs is not None and gs.get(f'{W}val', '').isdigit(): span = int(gs.get(f'{W}val'))
                if vm is not None: vmerge = vm.get(f'{W}val') or 'continue'
            text = '\n'.join(t for t in (_clean(_w_text(p)) for p in tc.findall(f'{W}p')) if t)
            if vmerge == 'continue' and rows and len(rows[-1]) > len(row): text = rows[-1][len(row)]
            row += [text] * span
        if any(c.strip() for c in row): rows.append(row)
    return rows


def docx_blocks(data, prefix=()):
    """A Word file → (blocks, title, notes). notes: [(kind, where, status, reason, category)] for what is not read."""
    z = _open(data)
    doc = _part(z, 'word/document.xml')
    if doc is None: raise OfficeError('no word/document.xml — not a Word file')
    levels = _heading_levels(z)
    out, heads, notes, title, pictures = [], [], [], '', 0

    def section():
        return ' / '.join(list(prefix) + [h for _, h in heads])

    def walk(parent):
        nonlocal title, pictures
        for el in parent:
            if el.tag == f'{W}p':
                pictures += sum(1 for _ in el.iter(f'{W}drawing')) + sum(1 for _ in el.iter(f'{W}pict'))
                t = _clean(_w_text(el))
                if not t: continue
                ps = el.find(f'{W}pPr/{W}pStyle'); ol = el.find(f'{W}pPr/{W}outlineLvl')
                lvl = levels.get(ps.get(f'{W}val')) if ps is not None else None
                if lvl is None and ol is not None and ol.get(f'{W}val', '').isdigit() and int(ol.get(f'{W}val')) < 9: lvl = int(ol.get(f'{W}val')) + 1
                if lvl == 0: title = title or t; continue
                if lvl: heads[:] = [h for h in heads if h[0] < lvl] + [(lvl, t)]; title = title or (t if lvl == 1 else ''); continue
                out.append(('text', section(), t))
            elif el.tag == f'{W}tbl':
                rows = _w_table(el)
                if rows: out.append(('table', section(), ('grid', [_clean(c) for c in rows[0]], rows[1:])))
            elif el.tag in (f'{W}sdt', f'{W}sdtContent', f'{W}customXml', f'{W}smartTag'):
                walk(el)
    body = doc.find(f'{W}body')
    walk(body if body is not None else doc)
    if pictures:
        notes.append(('picture', f'{pictures} picture(s) in the document', 'not captured',
                      'pictures inside a Word file are not read — a person checks them, or exports a diagram as draw.io and adds it beside the document', 'picture not read'))
    return out, _core_title(z) or title, notes


# ------------------------------------------------------------------ Excel

def _col(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref or '')
    if not m: return None, None
    n = 0
    for ch in m.group(1): n = n * 26 + ord(ch) - 64
    return int(m.group(2)), n


def _shared(z):
    sst = _part(z, 'xl/sharedStrings.xml')
    if sst is None: return []
    return [''.join(t.text or '' for t in si.iter(f'{S}t')) for si in sst.findall(f'{S}si')]


def _value(c, strings):
    t = c.get('t'); v = c.find(f'{S}v')
    if t == 'inlineStr': return ''.join(x.text or '' for x in c.iter(f'{S}t'))
    if v is None or v.text is None: return ''
    if t == 's':
        try: return strings[int(v.text)]
        except (ValueError, IndexError): return ''
    if t == 'b': return 'TRUE' if v.text == '1' else 'FALSE'
    if t == 'e': return ''
    if t in (None, 'n'):
        try: f = float(v.text); return str(int(f)) if f.is_integer() else v.text
        except ValueError: return v.text
    return v.text   # str: a formula's saved text


def _sheets(z):
    """[(name, state, path)] in workbook order."""
    wb = _part(z, 'xl/workbook.xml')
    if wb is None: raise OfficeError('no xl/workbook.xml — not an Excel file')
    rels = _part(z, 'xl/_rels/workbook.xml.rels'); target = {}
    for r in (rels if rels is not None else []):
        t = r.get('Target', ''); target[r.get('Id')] = t.lstrip('/') if t.startswith('/') else 'xl/' + t
    return [(s.get('name'), s.get('state') or 'visible', target.get(s.get(f'{R}id'))) for s in wb.iter(f'{S}sheet')]


def _grid(sheet, strings):
    cells = {}
    for row in sheet.iter(f'{S}row'):
        for c in row.findall(f'{S}c'):
            r, k = _col(c.get('r'))
            if r is None: continue
            v = _clean(_value(c, strings))
            if v: cells[(r, k)] = v
    for m in sheet.iter(f'{S}mergeCell'):   # a merged range shows its first cell's value in every cell
        a, _, b = (m.get('ref') or '').partition(':')
        (r1, c1), (r2, c2) = _col(a), _col(b or a)
        if r1 is None or r2 is None or (r1, c1) not in cells: continue
        for r in range(r1, r2 + 1):
            for k in range(c1, c2 + 1): cells.setdefault((r, k), cells[(r1, c1)])
    return cells


def _tables(cells):
    """A sheet's cells → blocks of consecutive non-empty rows: [(first row number, [(row number, [cells])])]."""
    rows = sorted({r for r, _ in cells}); out, cur = [], []
    for r in rows:
        if cur and r != cur[-1] + 1: out.append(cur); cur = []
        cur.append(r)
    if cur: out.append(cur)
    blocks = []
    for rs in out:
        cols = sorted({k for (r, k) in cells if r in rs}); lo, hi = cols[0], cols[-1]
        blocks.append([(r, [cells.get((r, k), '') for k in range(lo, hi + 1)]) for r in rs])
    return blocks


def xlsx_blocks(data, prefix=()):
    """An Excel file → (blocks, title, notes). Each visible sheet is a section named after it; each table in it a 'grid' block whose
    fourth element is the sheet row number of each data row, so a record cites 'sheet row 7'."""
    z = _open(data)
    strings = _shared(z); out, notes = [], []
    for name, state, path in _sheets(z):
        sec = ' / '.join(list(prefix) + [name])
        if state != 'visible':
            notes.append(('table', f"sheet '{name}'", 'skipped', f'a {state} sheet — not read; unhide it if it holds design data', None)); continue
        sheet = _part(z, path) if path else None
        if sheet is None: notes.append(('table', f"sheet '{name}'", 'not captured', 'the sheet\'s part is missing from the file', 'file not read')); continue
        cells = _grid(sheet, strings)
        if not cells: notes.append(('table', f"sheet '{name}'", 'skipped', 'an empty sheet', None)); continue
        for block in _tables(cells):
            filled = [len({c for c in row if c}) for _, row in block]   # distinct values: a title merged across columns is one
            while len(block) > 1 and filled[0] == 1 and (len(block) == 2 or filled[1] > 1):   # a title line above the table
                out.append(('text', sec, next(c for c in block[0][1] if c))); block, filled = block[1:], filled[1:]
            if len(block) == 1 and filled[0] == 1:
                out.append(('text', sec, next(c for c in block[0][1] if c))); continue
            (_, head), body = block[0], block[1:]
            out.append(('table', sec, ('grid', head, [r for _, r in body], [n for n, _ in body])))
    return out, _core_title(z), notes
