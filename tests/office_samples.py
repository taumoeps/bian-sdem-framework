"""Made-up Word and Excel design files for the tests — written with the standard library, as Office writes them (Office Open XML)."""
import zipfile
from xml.sax.saxutils import escape

_RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="{main}"/>'
         '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
         '</Relationships>')
_CORE = ('<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
         'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title></cp:coreProperties>')
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(path, title, body):
    """body: [('h1'…'h3', text) | ('p', text) | ('table', [[cells]]) | ('picture', None)]."""
    def run(t): return f'<w:r><w:t xml:space="preserve">{escape(t)}</w:t></w:r>'
    def para(t, style=None):
        pr = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else ''
        return f'<w:p>{pr}{run(t)}</w:p>'
    parts = []
    for kind, x in body:
        if kind.startswith('h'): parts.append(para(x, f'Heading{kind[1]}'))
        elif kind == 'title': parts.append(para(x, 'Title'))
        elif kind == 'p': parts.append(para(x))
        elif kind == 'picture': parts.append('<w:p><w:r><w:drawing/></w:r></w:p>')
        elif kind == 'table':
            parts.append('<w:tbl>' + ''.join('<w:tr>' + ''.join(f'<w:tc>{para(c)}</w:tc>' for c in row) + '</w:tr>' for row in x) + '</w:tbl>')
    styles = ''.join(f'<w:style w:type="paragraph" w:styleId="Heading{n}"><w:name w:val="heading {n}"/></w:style>' for n in (1, 2, 3))
    styles += '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/></w:style>'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr('_rels/.rels', _RELS.format(main='word/document.xml'))
        z.writestr('docProps/core.xml', _CORE.format(title=escape(title)))
        z.writestr('word/styles.xml', f'<?xml version="1.0"?><w:styles {W}>{styles}</w:styles>')
        z.writestr('word/document.xml', f'<?xml version="1.0"?><w:document {W}><w:body>{"".join(parts)}</w:body></w:document>')


def _ref(r, c):
    s = ''
    while c: c, m = divmod(c - 1, 26); s = chr(65 + m) + s
    return f'{s}{r}'


def make_xlsx(path, title, sheets):
    """sheets: [{'name', 'rows': {row number: [cells]}, 'hidden': bool, 'merge': ['A1:C1'], 'formula': {(row, col): saved value}}].
    Text goes into the shared strings (as Excel writes it); numbers are numbers."""
    strings, idx = [], {}
    def sid(t):
        if t not in idx: idx[t] = len(strings); strings.append(t)
        return idx[t]
    S = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr('_rels/.rels', _RELS.format(main='xl/workbook.xml'))
        z.writestr('docProps/core.xml', _CORE.format(title=escape(title)))
        wb = ''.join(f'<sheet name="{escape(s["name"])}" sheetId="{i}" r:id="rId{i}"' + (' state="hidden"' if s.get('hidden') else '') + '/>'
                     for i, s in enumerate(sheets, 1))
        z.writestr('xl/workbook.xml', f'<?xml version="1.0"?><workbook {S}><sheets>{wb}</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                             for i in range(1, len(sheets) + 1)) + '</Relationships>')
        for i, s in enumerate(sheets, 1):
            rows = []
            for r, cells in sorted(s['rows'].items()):
                cs = []
                for c, v in enumerate(cells, 1):
                    if v is None or v == '': continue
                    if (r, c) in s.get('formula', {}):
                        cs.append(f'<c r="{_ref(r, c)}" t="str"><f>CONCAT(A1)</f><v>{escape(s["formula"][(r, c)])}</v></c>')
                    elif isinstance(v, (int, float)): cs.append(f'<c r="{_ref(r, c)}"><v>{v}</v></c>')
                    else: cs.append(f'<c r="{_ref(r, c)}" t="s"><v>{sid(v)}</v></c>')
                rows.append(f'<row r="{r}">{"".join(cs)}</row>')
            merge = ''.join(f'<mergeCell ref="{m}"/>' for m in s.get('merge', []))
            z.writestr(f'xl/worksheets/sheet{i}.xml', f'<?xml version="1.0"?><worksheet {S}><sheetData>{"".join(rows)}</sheetData>'
                       + (f'<mergeCells>{merge}</mergeCells>' if merge else '') + '</worksheet>')
        z.writestr('xl/sharedStrings.xml', f'<?xml version="1.0"?><sst {S}>' + ''.join(f'<si><t>{escape(t)}</t></si>' for t in strings) + '</sst>')


def ledger_workbook(path):
    """A made-up general-ledger design workbook: a cover tab, inventories on separate tabs, links across tabs, a hidden tab."""
    make_xlsx(path, 'General Ledger design (made up)', [
        {'name': 'Cover', 'rows': {1: ['General Ledger — solution design'], 3: ['Owner: finance architecture (made up)']}},
        {'name': 'Applications', 'merge': ['A1:C1'], 'rows': {
            1: ['Application inventory', None, None],
            2: ['Application', 'Description', 'Status'],
            3: ['Ledger Core', 'Posts journal entries', 'planned'],
            4: ['Reporting Hub', 'Builds financial reports', 'active'],
            5: ['', 'a row with no name', '']},
         'formula': {(4, 2): 'Builds financial reports'}},
        {'name': 'Infrastructure', 'rows': {
            3: ['Server', 'Description'],
            4: ['Finance Kubernetes cluster', 'Runs the finance services'],
            7: ['Database', 'Description'],
            8: ['Ledger DB', 'Holds the ledger'] }},
        {'name': 'Interfaces', 'rows': {
            1: ['Source', 'Target', 'Data'],
            2: ['Ledger Core', 'Reporting Hub', 'Posted journals'],
            3: ['Ledger Core', 'Recon Engine', 'Balances']}},
        {'name': 'Deployment', 'rows': {
            1: ['Application', 'Runs on', 'Environment'],
            2: ['Ledger Core', 'Finance Kubernetes cluster', 'production']}},
        {'name': 'Risks', 'rows': {1: ['Risk', 'Mitigation'], 2: ['Vendor lock-in', 'Open formats']}},
        {'name': 'Old', 'hidden': True, 'rows': {1: ['Application'], 2: ['Retired App']}},
    ])


def ledger_document(path):
    """A made-up general-ledger solution design in Word: headings, a paragraph, an application table, a picture."""
    make_docx(path, 'General Ledger Solution Design (made up)', [
        ('title', 'General Ledger Solution Design'),
        ('h1', 'Business context'),
        ('p', 'Finance closes the books every month.'),
        ('table', [['Capability', 'Description'], ['General Ledger Management', 'Keeps the books of account']]),
        ('h1', 'Application architecture'),
        ('table', [['Application', 'Description', 'Status'], ['Ledger Core', 'Posts journal entries', 'planned']]),
        ('p', 'Ledger Core sends posted journals to Reporting Hub.'),
        ('h2', 'Integration'),
        ('table', [['Source', 'Target', 'Data'], ['Ledger Core', 'Reporting Hub', 'Posted journals']]),
        ('picture', None),
    ])
