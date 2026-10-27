"""Write tests/fixtures/confluence-export-sample/: a synthetic Confluence HTML space export for testing `sdem history`.

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


if __name__ == '__main__':
    main()
