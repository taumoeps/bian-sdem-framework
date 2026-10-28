"""Write tests/fixtures/lending-folder-export/ — a made-up lending design, exported the same way as the payments one
(provenance files in the root, raw HTML and diagrams in archives/, sections as folders), to test design onboarding on a
domain other than payments. Its text deliberately uses lending's general words (loan, lending, credit) the way real
designs do. Everything here is fictional.

    python scripts/make_lending_export.py
"""
import csv, html, io, json, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from make_confluence_sample import plantuml_encode, png  # noqa: E402

OUT = ROOT / 'tests' / 'fixtures' / 'lending-folder-export'

CONTEXT_MODEL = """<mxfile host="Confluence"><diagram id="c" name="Lending context"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="a" value="Loan Origination Platform" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="b" value="Credit Decisioning Engine" style="shape=mxgraph.archimate3.application;appType=comp;archiType=square;html=1;" vertex="1" parent="1"><mxGeometry x="200" y="0" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="c" value="Loan Application" style="shape=mxgraph.archimate3.application;appType=passive;html=1;" vertex="1" parent="1"><mxGeometry x="0" y="100" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="e" value="credit check request" style="endArrow=block;html=1;" edge="1" parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>"""

COMPONENTS_PUML = """@startuml
title Lending components
actor "Small Business Customer" as cust
node "Lending OpenShift Cluster" as ocp {
  [Loan Origination Platform] as lop
  component "Affordability Calculator" as aff
}
database "Loan Book" as book
cust --> lop : applies for a loan
lop --> aff : calls
lop ..> book : writes to
@enduml
"""

SEQUENCE_PUML = """@startuml
participant "Loan Origination Platform" as L
participant "Credit Bureau Gateway" as G
participant "Credit Decisioning Engine" as D
L -> G : requests credit report
G --> L : credit report
L -> D : sends application for decision
@enduml
"""

C4_MD = """# Container view

```plantuml
@startuml
!include <C4/C4_Container>
Person(cust, "Small Business Customer")
Person(broker, "Mortgage Broker")
System_Boundary(bank, "Bank") {
  Container(portal, "Broker Portal", "React")
  Container(lop, "Loan Origination Platform", "Java")
  ContainerDb(book, "Loan Book", "Oracle")
}
Rel(broker, portal, "Uses")
Rel(portal, lop, "Submits loan application to")
Rel(lop, book, "Reads from and writes to")
@enduml
```
"""

DEPLOY_PUML = """@startuml
archimate #Technology "Lending OpenShift Cluster" as ocp <<technology-node>>
archimate #Technology "Oracle 19c" as ora <<technology-system-software>>
archimate #Technology "Branch Firewall" as fw <<technology-device>>
fw --> ocp
@enduml
"""

RAW_PAGE = """<html><head><title>Loan Origination Design</title></head><body>
<h1>Loan Origination Design</h1>
<p>Last updated by the lending architecture team.</p>
<h2>Solution overview</h2>
<p>Every Loan starts in the Loan Origination Platform. The Loan Origination Platform sends each application to the Credit Decisioning Engine for a decision.</p>
<p>Lending to small businesses grows every year, so Credit decisions must take minutes, not days. The Credit Decisioning Engine reads the credit report from the Credit Bureau Gateway.</p>
<p>Once approved, the Loan is booked in the Loan Book and the Collateral Register records any security.</p>
<p><img src="diagrams/lending-context.png" alt="lending context"></p>
<p><img src="diagrams/lending-components.png" alt="lending components"></p>
<p><img src="diagrams/credit-sequence.svg" alt="credit sequence"></p>
<table><tr><th>Owner</th><td>Lending architecture team</td></tr><tr><th>Review date</th><td>2023-03-14</td></tr><tr><th>Approval</th><td>Design authority, approved with conditions</td></tr></table>
<h2>Risks</h2>
<table><tr><th>Risk</th><th>Impact</th><th>Mitigation</th></tr>
<tr><td>Credit bureau unavailable</td><td>Applications wait for a decision</td><td>Queue and retry; manual referral after 2 hours</td></tr></table>
<h2>Applications</h2>
<table><tr><th>Application</th><th>Purpose</th><th>Status</th><th>Data classification</th></tr>
<tr><td>Loan Origination Platform</td><td>Captures loan applications from branches and brokers</td><td>Live</td><td>Confidential</td></tr>
<tr><td>Credit Decisioning Engine</td><td>Scores applications and returns a decision</td><td>Live</td><td>Confidential</td></tr>
<tr><td>Collateral Register</td><td>Records security held against loans</td><td>Live</td><td>Internal</td></tr></table>
</body></html>
"""

OVERVIEW_MD = """# Business context

The bank wants small businesses to get a lending decision the same day.

| Capability | Description |
|---|---|
| Loan Origination | Take and check a customer's application for a loan |
| Credit Decisioning | Decide whether to lend, how much, and at what price |
| Collateral Management | Record and value the security behind a loan |

![process sketch](process-sketch.jpg)
"""

INTEGRATIONS_HTML = """<h3>Interfaces</h3>
<table><tr><th>Source</th><th>Target</th><th>Interface</th></tr>
<tr><td>Loan Origination Platform</td><td>Credit Bureau Gateway</td><td>Credit report request (REST)</td></tr>
<tr><td>Loan Origination Platform</td><td>Credit Decisioning Engine</td><td>Decision request (MQ)</td></tr></table>
"""

NOTES_TXT = """Design notes

The Credit Decisioning Engine is hosted on LENDAPP01.

The loan servicing system is out of scope for this release.
"""


def main():
    text = {
        'README.md': '# Export of the Lending Architecture space\n\nPrepared export: raw pages and diagrams in archives/, section content in folders.\n',
        'source.json': json.dumps({'space': 'LENDARCH', 'exported': '2026-10-29', 'pages': [
            {'id': '77701', 'title': 'Loan Origination Design', 'file': 'archives/loan-origination-design.html',
             'url': 'https://confluence.example.com/spaces/LENDARCH/pages/77701', 'last_modified': '2023-03-20'}]}, indent=2) + '\n',
        'archives/loan-origination-design.html': RAW_PAGE,
        'Loan Origination Design/1. Business Context/overview.md': OVERVIEW_MD,
        'Loan Origination Design/2. Application Architecture/integrations.html': INTEGRATIONS_HTML,
        'Loan Origination Design/2. Application Architecture/notes.txt': NOTES_TXT,
        'Loan Origination Design/2. Application Architecture/container-view.md': C4_MD,
        'Loan Origination Design/3. Infrastructure/deployment.puml': DEPLOY_PUML,
        'archives/diagrams/credit-sequence.svg': f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><?plantuml-src {plantuml_encode(SEQUENCE_PUML)}?><rect width="10" height="10"/></svg>\n',
    }
    buf = io.StringIO(); w = csv.writer(buf, lineterminator='\n')
    w.writerows([['Server', 'Environment', 'Status'], ['LENDAPP01', 'Production', 'Live'], ['LENDAPP02', 'Disaster recovery', 'Live']])
    text['Loan Origination Design/3. Infrastructure/servers.csv'] = buf.getvalue()
    binary = {'archives/diagrams/lending-context.png': png([('mxfile', urllib.parse.quote(CONTEXT_MODEL, safe=''))]),
              'archives/diagrams/lending-components.png': png([('plantuml', COMPONENTS_PUML)]),
              'Loan Origination Design/1. Business Context/process-sketch.jpg': b'\xff\xd8\xff\xe0 synthetic jpeg \xff\xd9'}
    for rel, t in text.items():
        p = OUT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t, encoding='utf-8')
    for rel, b in binary.items():
        p = OUT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b)
    print(f'written {OUT}')


if __name__ == '__main__':
    main()
