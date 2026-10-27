"""Write tests/fixtures/confluence-export-sample/ (Confluence's standard HTML export) and
tests/fixtures/confluence-folder-export/ (a prepared export: provenance files in the root, raw HTML and diagrams in
archives/, sections as folders) — synthetic exports for testing `sdem history`. First:
tests/fixtures/confluence-export-sample/: a synthetic Confluence HTML space export for testing `sdem history`.

Everything here is made up (a fictional bank's past designs). It follows the layout of a Confluence HTML export:
one .html file per page (`Title_<pageId>.html`, or `<pageId>.html` in older exports), the page body in
div#main-content, page metadata ("last modified on …"), an Attachments section, and attachments/<pageId>/<file>.
The diagrams cover the ways draw.io diagrams arrive: a plain .drawio XML file with no extension, a compressed one,
and a PNG with the diagram inside it; plus a pasted screenshot that cannot be read without AI.

    python scripts/make_confluence_sample.py
"""
import base64, struct, urllib.parse, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / 'fixtures' / 'confluence-export-sample'
SPACE = 'Payments Architecture'


def png(text_chunks=()):
    """A tiny valid 2×2 PNG, with optional tEXt chunks (draw.io puts the diagram in one named 'mxfile')."""
    def chunk(kind, data): return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    raw = b''.join(b'\x00' + b'\xff\xff\xff' * 2 for _ in range(2))
    body = chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0))
    for k, v in text_chunks: body += chunk(b'tEXt', k.encode('latin-1') + b'\0' + v.encode('latin-1'))
    return b'\x89PNG\r\n\x1a\n' + body + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def compress(model_xml):
    """draw.io's compressed form: URL-encode, raw deflate, base64."""
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return base64.b64encode(c.compress(urllib.parse.quote(model_xml, safe='').encode()) + c.flush()).decode()


def page(title, page_id, modified, body, attachments):
    att = ''.join(f'<img src="images/icons/bullet_blue.gif" height="8" width="8" alt=""/> <a href="attachments/{page_id}/{f}">{name}</a> ({mime})<br/>\n'
                  for f, name, mime in attachments)
    return f'''<!DOCTYPE html>
<html>
    <head>
        <title>{SPACE} : {title}</title>
        <link rel="stylesheet" href="styles/site.css" type="text/css" />
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body class="theme-default aui-theme-default">
        <div id="page">
            <div id="main" class="aui-page-panel">
                <div id="main-header">
                    <div id="breadcrumb-section">
                        <ol id="breadcrumbs">
                            <li class="first"><span><a href="index.html">{SPACE}</a></span></li>
                            <li><span><a href="Solution-Designs_900.html">Solution Designs</a></span></li>
                        </ol>
                    </div>
                    <h1 id="title-heading" class="pagetitle"><span id="title-text"> {SPACE} : {title} </span></h1>
                </div>
                <div id="content" class="view">
                    <div class="page-metadata">Created by <span class='author'> Sample Author</span>, last modified on {modified}</div>
                    <div id="main-content" class="wiki-content group">
{body}
                    </div>
                    <div class="pageSection group">
                        <div class="pageSectionHeader"><h2 id="attachments" class="pageSectionTitle">Attachments:</h2></div>
                        <div class="greybox" align="left">
{att}                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
</html>
'''


def table(headers, rows):
    h = ''.join(f'<th class="confluenceTh">{x}</th>' for x in headers)
    r = ''.join('<tr>' + ''.join(f'<td class="confluenceTd">{c}</td>' for c in row) + '</tr>' for row in rows)
    return f'<div class="table-wrap"><table class="confluenceTable"><tbody><tr>{h}</tr>{r}</tbody></table></div>'


# ---- page 1001: Payments Hub solution design (2021) — tables, a plain .drawio attachment, a pasted screenshot
APP_VIEW = '''<mxfile host="Confluence" type="device"><diagram id="d1" name="Application view"><mxGraphModel dx="1000" dy="600" grid="1"><root>
<mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="title" value="Payments Hub — application view" style="text;html=1;" vertex="1" parent="1"><mxGeometry x="20" y="0" width="300" height="20" as="geometry"/></mxCell>
<mxCell id="ch" value="Mobile Banking App" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="20" y="40" width="150" height="60" as="geometry"/></mxCell>
<mxCell id="hub" value="&lt;b&gt;Payments Hub&lt;/b&gt;&lt;br&gt;captures and validates instructions" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="220" y="40" width="150" height="60" as="geometry"/></mxCell>
<mxCell id="svc" value="Payment Initiation Service" style="shape=mxgraph.archimate3.application;appType=serv;archiType=rounded;html=1;" vertex="1" parent="1"><mxGeometry x="220" y="140" width="150" height="60" as="geometry"/></mxCell>
<mxCell id="gw" value="Execution Gateway" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="420" y="40" width="150" height="60" as="geometry"/></mxCell>
<mxCell id="k8s" value="Payments Kubernetes Cluster" style="shape=mxgraph.archimate3.tech;techType=node;html=1;" vertex="1" parent="1"><mxGeometry x="400" y="240" width="260" height="140" as="geometry"/></mxCell>
<mxCell id="ledger" value="Ledger Posting Service" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;" vertex="1" parent="k8s"><mxGeometry x="20" y="40" width="140" height="50" as="geometry"/></mxCell>
<mxCell id="e1" value="payment instruction" style="endArrow=block;html=1;" edge="1" parent="1" source="ch" target="hub"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e2" value="" style="endArrow=block;html=1;" edge="1" parent="1" source="hub" target="gw"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e2l" value="sends authorised instructions" style="edgeLabel;html=1;" vertex="1" connectable="0" parent="e2"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e3" value="" style="endArrow=block;dashed=1;html=1;" edge="1" parent="1" source="hub" target="svc"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e4" value="runs on" style="endArrow=block;html=1;" edge="1" parent="1" source="gw" target="k8s"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e5" value="" style="endArrow=block;html=1;" edge="1" parent="1" source="gw" target="nowhere"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="blank" value="" style="rounded=0;html=1;" vertex="1" parent="1"><mxGeometry x="700" y="40" width="40" height="40" as="geometry"/></mxCell>
<mxCell id="cloud" value="Partner Bank" style="ellipse;shape=cloud;html=1;" vertex="1" parent="1"><mxGeometry x="700" y="100" width="120" height="80" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>'''

P1 = f'''<h1 id="PaymentsHubSolutionDesign-Context">1. Business context</h1>
<p>This design replaces the branch payment forms with a single Payments Hub. Customers start payments in the Mobile Banking App.</p>
{table(['Capability', 'Description'], [['Payment Initiation', 'Accept and validate a customer&#39;s instruction to pay'], ['Payment Execution', 'Send the payment through the scheme']])}
<h1 id="PaymentsHubSolutionDesign-Application">2. Application architecture</h1>
<p>The Payments Hub sends authorised instructions to the Execution Gateway. The Mobile Banking App calls the Payments Hub for every new payment.</p>
<p><span class="confluence-embedded-file-wrapper"><img class="confluence-embedded-image" src="attachments/1001/1001-preview.png" data-linked-resource-default-alias="payments-application-view.png" alt="payments-application-view"></span></p>
{table(['Application', 'Description', 'Vendor', 'Status'], [['Payments Hub', 'Captures, validates and authorises payment instructions', 'in-house', 'Live'], ['Execution Gateway', 'Hands instructions to scheme execution', 'in-house', 'Live'], ['Fraud Screening', 'Scores each payment for fraud before release', 'VendorCo', 'Planned'], ['Legacy Payment Forms', 'Branch payment entry', 'in-house', 'Decommissioned']])}
<h2 id="PaymentsHubSolutionDesign-Integrations">2.1 Integrations</h2>
{table(['Source System', 'Target System', 'Interface', 'Protocol'], [['Payments Hub', 'Fraud Screening', 'Payment score request', 'REST'], ['Execution Gateway', 'Scheme Connector', 'Scheme message', 'MQ']])}
<h1 id="PaymentsHubSolutionDesign-Infrastructure">3. Infrastructure</h1>
<p>The Execution Gateway is hosted on Payments Kubernetes Cluster. The old server room photo below shows the current racks.</p>
<p><span class="confluence-embedded-file-wrapper"><img class="confluence-embedded-image" src="attachments/1001/1003.png" data-linked-resource-default-alias="rack-photo.png" alt="rack-photo"></span></p>
{table(['Server', 'Environment', 'Status'], [['Payments Kubernetes Cluster', 'Production', 'Live'], ['PAYDB01', 'Production', 'Live']])}
{table(['Database', 'Description'], [['Payments Store (PostgreSQL)', 'Holds instructions and their status']])}
<table class="confluenceTable"><tbody><tr><th class="confluenceTh">Owner</th><td class="confluenceTd">Payments team</td></tr><tr><th class="confluenceTh">Review date</th><td class="confluenceTd">2021-03-01</td></tr></tbody></table>
<p><img class="emoticon emoticon-tick" src="images/icons/emoticons/check.svg" alt="(tick)"> Approved by the design authority.</p>'''

# ---- page 1002: Card fraud alerts design (2019, older file name) — a compressed .drawio and a PNG with the diagram inside
FRAUD_MODEL = '''<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="f1" value="Fraud Scoring Engine" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="40" y="40" width="140" height="60" as="geometry"/></mxCell>
<mxCell id="f2" value="Alerts DB" style="shape=cylinder3;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="260" y="40" width="80" height="80" as="geometry"/></mxCell>
<mxCell id="f3" value="Case Management System" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="40" y="160" width="140" height="60" as="geometry"/></mxCell>
<object label="Card Authorisation Switch" id="f4" owner="cards"><mxCell style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="-160" y="40" width="140" height="60" as="geometry"/></mxCell></object>
<mxCell id="f5" value="triggers" style="endArrow=block;html=1;" edge="1" parent="1" source="f1" target="f3"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="f6" value="calls" style="endArrow=block;html=1;" edge="1" parent="1" source="f4" target="f1"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel>'''
FRAUD = f'<mxfile host="Confluence"><diagram id="x" name="Fraud flow">{compress(FRAUD_MODEL)}</diagram></mxfile>'

DEPLOY_MODEL = '''<mxfile host="Confluence"><diagram id="y" name="Deployment"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="d1" value="Fraud AWS EKS Cluster" style="shape=mxgraph.aws4.group;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="300" height="200" as="geometry"/></mxCell>
<mxCell id="d2" value="Fraud Scoring Engine" style="rounded=1;html=1;" vertex="1" parent="d1"><mxGeometry x="20" y="40" width="140" height="60" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>'''

P2 = f'''<h2 id="CardFraudAlerts-Overview">Overview</h2>
<p>Card Authorisation Switch calls the Fraud Scoring Engine for each card transaction. The Fraud Scoring Engine triggers the Case Management System when a score is high.</p>
<p><span class="confluence-embedded-file-wrapper"><img class="confluence-embedded-image" src="attachments/1002/3010.png" data-linked-resource-default-alias="fraud-flow.png" alt="fraud-flow"></span></p>
<h2 id="CardFraudAlerts-Deployment">Deployment view</h2>
<p><span class="confluence-embedded-file-wrapper"><img class="confluence-embedded-image" src="attachments/1002/3002.png" data-linked-resource-default-alias="deployment.png" alt="deployment"></span></p>
<p>The Payments Hub is not changed by this design.</p>'''

INDEX = f'''<!DOCTYPE html><html><head><title>{SPACE} : Space home</title></head><body><div id="main-content">
<h2>Available Pages:</h2><ul><li><a href="Payments-Hub-Solution-Design_1001.html">Payments Hub Solution Design</a></li><li><a href="1002.html">Card Fraud Alerts Design</a></li></ul>
</div></body></html>'''


def main():
    files = {
        'index.html': INDEX,
        'Payments-Hub-Solution-Design_1001.html': page('Payments Hub Solution Design', '1001', 'Mar 12, 2021', P1,
                                                       [('1001', 'payments-application-view', 'application/vnd.jgraph.mxfile'), ('1001-preview.png', 'payments-application-view.png', 'image/png'), ('1003.png', 'rack-photo.png', 'image/png')]),
        '1002.html': page('Card Fraud Alerts Design', '1002', 'Jun 03, 2019', P2,
                          [('3001.drawio', 'fraud-flow', 'application/vnd.jgraph.mxfile'), ('3010.png', 'fraud-flow.png', 'image/png'), ('3002.png', 'deployment.png', 'image/png')]),
        'attachments/1001/1001': APP_VIEW,
        'attachments/1002/3001.drawio': FRAUD,
        'styles/site.css': 'body { font-family: sans-serif; }\n',
    }
    binaries = {
        'attachments/1001/1001-preview.png': png(),                                   # draw.io's preview picture (the diagram is the attachment 1001)
        'attachments/1001/1003.png': png([('Software', 'phone camera')]),             # a pasted photo: cannot be read
        'attachments/1002/3010.png': png(),                                           # preview of the compressed fraud-flow diagram
        'attachments/1002/3002.png': png([('mxfile', urllib.parse.quote(DEPLOY_MODEL, safe=''))]),  # a draw.io PNG with the diagram inside
        'images/icons/bullet_blue.gif': b'GIF89a\x01\x00\x01\x00\x00\x00\x00;',
    }
    for rel, text in files.items():
        p = OUT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding='utf-8')
    for rel, data in binaries.items():
        p = OUT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    (OUT / 'README.md').write_text('# Synthetic Confluence export\n\nMade-up pages in the layout of a Confluence HTML space export, for testing `sdem history`. '
                                   'Regenerate with `python scripts/make_confluence_sample.py`. No real designs.\n', encoding='utf-8')
    print(f'written {OUT}')



# ---- the prepared layout: readme/source/evidence in the root, raw HTML and diagrams in archives/, sections as folders
FOLDER = ROOT / 'tests' / 'fixtures' / 'confluence-folder-export'

CONTEXT_MODEL = """<mxfile host="Confluence"><diagram id="c" name="Context"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="a" value="Payments Hub" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="b" value="Clearing Gateway" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="200" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="c" value="Payment Order" style="shape=mxgraph.archimate3.application;appType=passive;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="100" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="e" value="clearing file" style="endArrow=block;html=1;" edge="1" parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>"""

NETWORK_MODEL = """<mxfile host="Confluence"><diagram id="n" name="Network"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="n1" value="Payments DMZ" style="rounded=0;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="n2" value="Edge Firewall" style="rounded=0;html=1;" vertex="1" parent="1"><mxGeometry x="200" y="0" width="120" height="60" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>"""

INFRA_MODEL = """<mxfile host="Confluence"><diagram id="i" name="Infrastructure"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="s1" value="Core Switch" style="rounded=0;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="s2" value="PAYAPP01" style="rounded=0;html=1;" vertex="1" parent="1"><mxGeometry x="200" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="s3" value="" style="endArrow=none;html=1;" edge="1" parent="1" source="s1" target="s2"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>"""

_P64 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'


def plantuml_encode(text):
    """PlantUML's text encoding: raw deflate, then its own base64 alphabet (3 bytes → 4 characters)."""
    c = zlib.compressobj(9, zlib.DEFLATED, -15); data = c.compress(text.encode('utf-8')) + c.flush()
    out = []
    for i in range(0, len(data), 3):
        b = data[i:i + 3] + bytes(3 - len(data[i:i + 3]))
        n = (b[0] << 16) | (b[1] << 8) | b[2]
        out += [_P64[(n >> 18) & 63], _P64[(n >> 12) & 63], _P64[(n >> 6) & 63], _P64[n & 63]]
    return ''.join(out)


COMPONENTS_PUML = """@startuml
title Payments components
actor "Retail Customer" as cust
node "Payments Kubernetes Cluster" as k8s {
  [Payments Hub] as hub
  component "Sanctions Screening" as sanc
}
database "Payments Store" as store
cust --> hub : submits payment
hub --> sanc : calls
hub ..> store : writes to
@enduml
"""

SEQUENCE_PUML = """@startuml
participant "Payments Hub" as P
participant "Clearing Gateway" as C
participant "Scheme Adapter" as S
P -> C : sends cleared payments
C -> S : sends clearing file
S --> C : acknowledgement
@enduml
"""

C4_MD = """# Container view

The container view, drawn in PlantUML (C4).

```plantuml
@startuml
!include <C4/C4_Container>
Person(cust, "Retail Customer")
System_Boundary(bank, "Bank") {
  Container(mob, "Mobile Banking App", "Swift")
  Container(hub, "Payments Hub", "Java")
  ContainerDb(store, "Payments Store", "PostgreSQL")
}
Rel(cust, mob, "Uses")
Rel(mob, hub, "Sends payment to")
Rel(hub, store, "Reads from and writes to")
@enduml
```
"""

DEPLOY_PUML = """@startuml
archimate #Technology "Payments Kubernetes Cluster" as k8s <<technology-node>>
archimate #Technology "Edge Firewall" as fw <<technology-device>>
archimate #Technology "PostgreSQL 15" as pg <<technology-system-software>>
fw --> k8s
@enduml
"""

WHITEBOARD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500" viewBox="0 0 900 500">
<rect width="900" height="500" fill="#ffffff"/>
<rect x="40" y="60" width="240" height="90" fill="#dae8fc" stroke="#333"/><text x="160" y="112" font-family="Helvetica" font-size="24" text-anchor="middle">Payments Hub</text>
<rect x="520" y="60" width="300" height="90" fill="#dae8fc" stroke="#333"/><text x="670" y="112" font-family="Helvetica" font-size="24" text-anchor="middle">Sanctions Checker</text>
<line x1="280" y1="105" x2="520" y2="105" stroke="#333" stroke-width="2"/><text x="400" y="95" font-family="Helvetica" font-size="16" text-anchor="middle">screening request</text>
<rect x="40" y="300" width="780" height="140" fill="#d5e8d4" stroke="#333"/><text x="430" y="330" font-family="Helvetica" font-size="22" text-anchor="middle">Payments Kubernetes Cluster</text>
<rect x="80" y="350" width="260" height="70" fill="#ffffff" stroke="#333"/><text x="210" y="393" font-family="Helvetica" font-size="20" text-anchor="middle">Ledger Posting Service</text>
</svg>
"""

RAW_PAGE = """<html><head><title>Payments Hub Design</title></head><body>
<h1>Payments Hub Design</h1>
<p>Last updated by the payments architecture team.</p>
<h2>Solution overview</h2>
<p>The Payments Hub sends cleared payments to the Clearing Gateway every hour.</p>
<p><img src="../Payments%20Hub%20Design/2.%20Application%20Architecture/whiteboard.png" alt="whiteboard"></p>
<p><img src="diagrams/hub-context.png" alt="hub context"></p>
<p><img src="diagrams/payments-components.png" alt="payments components"></p>
<p><img src="diagrams/payment-sequence.svg" alt="payment sequence"></p>
<h2>Applications</h2>
<table><tr><th>Application</th><th>Purpose</th><th>Status</th></tr>
<tr><td>Payments Hub</td><td>Captures and validates payment instructions</td><td>Live</td></tr>
<tr><td>Clearing Gateway</td><td>Builds clearing files for the scheme</td><td>Live</td></tr></table>
</body></html>
"""

OVERVIEW_MD = """# Business context

The bank wants one place to start every payment.

| Capability | Description |
|---|---|
| Payment Initiation | Accept a customer's instruction to pay |
| Payment Clearing | Exchange payments with the scheme |

![customer journey sketch](journey-sketch.jpg)
"""

INTEGRATIONS_HTML = """<h3>Interfaces</h3>
<table><tr><th>Source</th><th>Target</th><th>Interface</th></tr>
<tr><td>Payments Hub</td><td>Clearing Gateway</td><td>Clearing file (SFTP)</td></tr>
<tr><td>Clearing Gateway</td><td>Scheme Adapter</td><td>ISO 20022 pacs.008</td></tr></table>
"""

NOTES_TXT = """Design notes

The Clearing Gateway is hosted on PAYAPP01.

The Scheme Adapter is out of scope for this release.
"""


def folder_export():
    import csv as _csv, html as _h, io as _io, json as _json
    text = {
        'README.md': '# Export of the Payments Architecture space\n\nPrepared export: raw pages and diagrams in archives/, section content in folders.\n',
        'source.json': _json.dumps({'space': 'PAYARCH', 'exported': '2026-10-01', 'pages': [
            {'id': '55501', 'title': 'Payments Hub Design', 'file': 'archives/payments-hub-design.html',
             'url': 'https://confluence.example.com/spaces/PAYARCH/pages/55501', 'last_modified': '2022-05-10'}]}, indent=2) + '\n',
        'archives/payments-hub-design.html': RAW_PAGE,
        'archives/diagrams/network-zones.drawio': NETWORK_MODEL,
        'Payments Hub Design/1. Business Context/overview.md': OVERVIEW_MD,
        'Payments Hub Design/2. Application Architecture/integrations.html': INTEGRATIONS_HTML,
        'Payments Hub Design/2. Application Architecture/notes.txt': NOTES_TXT,
        'Payments Hub Design/2. Application Architecture/container-view.md': C4_MD,
        'Payments Hub Design/3. Infrastructure/deployment.puml': DEPLOY_PUML,
        'archives/diagrams/payment-sequence.svg': f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><?plantuml-src {plantuml_encode(SEQUENCE_PUML)}?><rect width="10" height="10"/></svg>\n',
        'Payments Hub Design/3. Infrastructure/infrastructure.svg':
            f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" content="{_h.escape(INFRA_MODEL)}"><rect width="10" height="10"/></svg>\n',
    }
    buf = _io.StringIO(); w = _csv.writer(buf, lineterminator='\n')
    w.writerows([['Server', 'Environment', 'Status'], ['PAYAPP01', 'Production', 'Live'], ['PAYAPP02', 'Disaster recovery', 'Live']])
    text['Payments Hub Design/3. Infrastructure/servers.csv'] = buf.getvalue()
    buf = _io.StringIO(); w = _csv.writer(buf, lineterminator='\n')
    w.writerows([['page_id', 'file', 'check', 'checked_on'], ['55501', 'archives/payments-hub-design.html', 'exported and opened', '2026-10-01']])
    text['evidence.csv'] = buf.getvalue()
    binary = {'archives/diagrams/hub-context.png': png([('mxfile', urllib.parse.quote(CONTEXT_MODEL, safe=''))]),
              'archives/diagrams/payments-components.png': png([('plantuml', COMPONENTS_PUML)]),
              'Payments Hub Design/1. Business Context/journey-sketch.jpg': b'\xff\xd8\xff\xe0 synthetic jpeg \xff\xd9',
              'Payments Hub Design/3. Infrastructure/rack-photo.jpg': b'\xff\xd8\xff\xe0 synthetic jpeg \xff\xd9'}
    for rel, t in text.items():
        p = FOLDER / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t, encoding='utf-8')
    for rel, b in binary.items():
        p = FOLDER / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b)
    # a real picture of a diagram, for OCR: rendered with macOS Quick Look where available; elsewhere the committed copy is kept
    wb = FOLDER / 'Payments Hub Design' / '2. Application Architecture' / 'whiteboard.png'
    import shutil, subprocess, sys, tempfile
    if sys.platform == 'darwin' and shutil.which('qlmanage'):
        tmp = Path(tempfile.mkdtemp()); (tmp / 'whiteboard.svg').write_text(WHITEBOARD_SVG, encoding='utf-8')
        subprocess.run(['qlmanage', '-t', '-s', '900', '-o', str(tmp), str(tmp / 'whiteboard.svg')], capture_output=True)
        if (tmp / 'whiteboard.svg.png').exists(): shutil.copyfile(tmp / 'whiteboard.svg.png', wb)
    print(f'written {FOLDER}')


if __name__ == '__main__':
    main()
    folder_export()
