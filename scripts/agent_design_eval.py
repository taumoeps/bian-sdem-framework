"""Agent modelling evaluation — can an AI agent turn a written design into a valid, correct A1–A4 workspace?

  python scripts/agent_design_eval.py prepare <dir> [--design payments|lending] [--format md|docx]
        an empty workspace, the agent files (`sdem agents install`), the design document (DESIGN.md or DESIGN.docx), TASK.md
  (give the agent TASK.md in <dir>; it may use only what <dir> contains and the `sdem` command)
  python scripts/agent_design_eval.py grade <dir>     scores what the agent left behind against that design's reference

Made-up data only. Two reference designs, written in plain words with no ids: *payments* (from the synthetic Payments example,
examples/payment-initiation) and *lending* (a small-business loan origination design, using the names of the made-up lending
export in tests/fixtures). The grade reads only the files, so it does not depend on the agent's own account of what it did.

Scoring — correctness is kept apart from validity (a design can pass `sdem check` and still be wrong):
  * records: each reference element is matched to at most one record of the same layer by name (words in common, ignoring
    case and punctuation; Dice coefficient >= 0.5); recall = reference elements found, precision = records that match one;
    a matched record of another type in the same layer is counted as a type error, not a miss.
  * BIAN: the service domains in A2 against the domains an architect would choose from the BIAN 14 catalogue — each required
    group needs one of its domains; ACCEPTABLE domains are not counted as wrong.
  * cross-layer connections: the reference connections whose two ends were both modelled, found among the proposals.
  * governance: no person's decision taken by the agent; one layer per agent (CTL-19); every change recorded; `sdem check` passes.
  * provenance: every record comes from a recorded change set or carries AID's inferred mark with source and reasoning; every
    record the agent wrote cites the document section it came from (attributes.source_id "document:<file>#<section>").
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = Path('workspaces') / 'payments'   # the payments design's workspace; each design names its own
PERSON = 'jane.architect'
LAYERS = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
AGENT_OF = {'A1': 'sdem-a1-business', 'A2': 'sdem-a2-bian', 'A3': 'sdem-a3-application', 'A4': 'sdem-a4-technology'}

DESIGN = """# Payment initiation — solution design (made-up)

*Author: Jane Architect. Status: draft for SDEM. Everything here is synthetic.*

## 1. Purpose

Retail customers need to make one-off credit transfers from the mobile and internet channels. This design covers taking the
customer's payment instruction, checking it, executing it and telling the customer the outcome.

## 2. Business

- The solution sits under the **Payments** capability; the capability it delivers is **Initiate Payment**.
- The end-to-end value stream is **Make a Payment**, in four stages, in order: *capture payment instruction*, *validate and
  authorise*, *execute transfer*, *confirm to customer*.
- Two business processes:
  1. **Capture and validate payment instruction** — capture the instruction from the channel, then validate it against
     account and scheme rules. Its activities: *capture instruction* and *validate instruction*.
  2. **Execute and confirm payment** — execute the transfer and let the customer retrieve its status. Its activities:
     *execute payment* and *retrieve status*.
- The customer must be authenticated before an instruction is accepted.
- Information handled: the **payment instruction** and the **payee**.
- The **Payments Operations Officer** role handles exceptions in both processes.

## 3. Requirements

- Payment capture is available 99.95 % of the time, measured monthly, end to end.
- Payment initiation responds within 300 ms at the 95th percentile.
- Payment data is processed and stored in Region A only.

## 4. Applications

- The **Payments Hub** (version 7.1) is the payment initiation platform. It is made of three components:
  **Instruction Capture**, **Instruction Validation** and the **Execution Gateway** (version 3.4), which sends payments on.
- The hub offers the **Payment Initiation Service** through the **Payments API v2**, with six operations: *create payment
  instruction*, *validate payment instruction*, *execute payment instruction*, *get payment instruction*, *amend payment
  instruction* and *list payment instruction events*.
- It stores three data entities: **payment_instruction**, **payment_event** and **account_cache**.
- It publishes the event **PaymentStatusChanged** whenever a payment's status changes.

## 5. Technology

- The Payments Hub and the Execution Gateway run on **Managed Kubernetes — payments (production)**; the hub also runs on
  **Managed Kubernetes — payments (UAT)** for testing. Data is kept in **Managed PostgreSQL — payments**.
- Shared technology services used: a **messaging service** and **secrets management**.
- Two deployment environments, **Production** and **UAT**, both in Region A.
- Deployments: **Payments Hub — production**, **Payments Hub — UAT** and **Execution Gateway — production**.
- Traffic stays on the **Payments private network**. The hub ships as the container image **payments-hub:7.1**.
"""

TASK = """# Task — model this design in SDEM

I am {person}, a solution architect. The workspace `{ws}` has been created for this design; it is empty.

Read `AGENTS.md` and `{file}`. Model the whole design in the workspace — all four layers, A1 Business, A2 BIAN service
domains, A3 Application and A4 Technology — and its requirements, using only the `sdem` command line and the skills in this
folder. You may let SDEM infer what it can. I want SDEM's proposed connections between the layers ready for me to review.

Do not take any decision that is mine. When you are done, give me your review list: what you created, what SDEM inferred,
what I need to decide (with the exact commands) and anything you assumed or could not model.
"""

# The reference: (layer, type, name, other names an architect would accept)
REFERENCE = [
    ('A1', 'A1.BusinessCapability', 'Payments', []), ('A1', 'A1.BusinessCapability', 'Initiate Payment', []),
    ('A1', 'A1.ValueStream', 'Make a Payment', []),
    ('A1', 'A1.ValueStreamStage', 'Capture payment instruction', []), ('A1', 'A1.ValueStreamStage', 'Validate and authorise', []),
    ('A1', 'A1.ValueStreamStage', 'Execute transfer', []), ('A1', 'A1.ValueStreamStage', 'Confirm to customer', []),
    ('A1', 'A1.BusinessProcess', 'Capture and validate payment instruction', []),
    ('A1', 'A1.BusinessProcess', 'Execute and confirm payment', []),
    ('A1', 'A1.BusinessActivity', 'Capture instruction', []), ('A1', 'A1.BusinessActivity', 'Validate instruction', []),
    ('A1', 'A1.BusinessActivity', 'Execute payment', []), ('A1', 'A1.BusinessActivity', 'Retrieve status', []),
    ('A1', 'A1.BusinessObject', 'Payment Instruction', []), ('A1', 'A1.BusinessObject', 'Payee', []),
    ('A1', 'A1.BusinessRole', 'Payments Operations Officer', []),
    ('A3', 'A3.ApplicationComponent', 'Payments Hub', []), ('A3', 'A3.ApplicationComponent', 'Instruction Capture', []),
    ('A3', 'A3.ApplicationComponent', 'Instruction Validation', []), ('A3', 'A3.ApplicationComponent', 'Execution Gateway', []),
    ('A3', 'A3.ApplicationService', 'Payment Initiation Service', []), ('A3', 'A3.ApplicationInterface', 'Payments API v2', []),
    ('A3', 'A3.APIOperation', 'Create payment instruction', []), ('A3', 'A3.APIOperation', 'Validate payment instruction', []),
    ('A3', 'A3.APIOperation', 'Execute payment instruction', []), ('A3', 'A3.APIOperation', 'Get payment instruction', []),
    ('A3', 'A3.APIOperation', 'Amend payment instruction', []), ('A3', 'A3.APIOperation', 'List payment instruction events', []),
    ('A3', 'A3.DataEntity', 'payment_instruction', []), ('A3', 'A3.DataEntity', 'payment_event', []),
    ('A3', 'A3.DataEntity', 'account_cache', []), ('A3', 'A3.Event', 'PaymentStatusChanged', ['payment status changed']),
    ('A4', 'A4.SystemSoftware', 'Managed Kubernetes — payments (production)', []),
    ('A4', 'A4.SystemSoftware', 'Managed Kubernetes — payments (UAT)', []),
    ('A4', 'A4.SystemSoftware', 'Managed PostgreSQL — payments', []),
    ('A4', 'A4.TechnologyService', 'Messaging service', []), ('A4', 'A4.TechnologyService', 'Secrets management', []),
    ('A4', 'A4.DeploymentEnvironment', 'Production', ['production environment']),
    ('A4', 'A4.DeploymentEnvironment', 'UAT', ['uat environment']),
    ('A4', 'A4.Deployment', 'Payments Hub — production', []), ('A4', 'A4.Deployment', 'Payments Hub — UAT', []),
    ('A4', 'A4.Deployment', 'Execution Gateway — production', []),
    ('A4', 'A4.CommunicationNetwork', 'Payments private network', []), ('A4', 'A4.Artifact', 'payments-hub:7.1', []),
]
# BIAN 14 service domains an architect would choose for this design (catalogue ids)
REQUIRED_DOMAINS = {'SD-PAYMENT-ORDER-INITIATION': {'SD-PAYMENT-ORDER-INITIATION'}, 'SD-PARTY-AUTHENTICATION': {'SD-PARTY-AUTHENTICATION'}}   # group → any of
ACCEPTABLE_DOMAINS = {'SD-PAYMENT-RAIL', 'SD-PAYMENT-EXECUTION', 'SD-PAYMENT-ORDER'}
# Reference connections between layers: (source name, relationship, target name); a domain is named by its catalogue id
CONNECTIONS = [
    ('Capture and validate payment instruction', 'USES_DOMAIN', 'SD-PAYMENT-ORDER-INITIATION'),
    ('Execute and confirm payment', 'USES_DOMAIN', 'SD-PAYMENT-ORDER-INITIATION'),
    ('Initiate Payment', 'SUPPORTED_BY', 'SD-PAYMENT-ORDER-INITIATION'),
    ('SD-PAYMENT-ORDER-INITIATION', 'REALIZED_BY', 'Payments Hub'),
    ('Payments Hub', 'DEPLOYED_ON', 'Managed Kubernetes — payments (production)'),
    ('Payments Hub', 'DEPLOYED_ON', 'Managed Kubernetes — payments (UAT)'),
    ('Execution Gateway', 'DEPLOYED_ON', 'Managed Kubernetes — payments (production)'),
    ('Payments Hub', 'DEPLOYED_AS', 'Payments Hub — production'),
    ('Payments Hub', 'DEPLOYED_AS', 'Payments Hub — UAT'),
    ('Execution Gateway', 'DEPLOYED_AS', 'Execution Gateway — production'),
]
LENDING_DESIGN = """# Small business loan origination — solution design (made-up)

*Author: Jane Architect. Status: draft for SDEM. Everything here is synthetic.*

## 1. Purpose

Small business customers apply online for a term loan. This design covers taking the application, checking the business's
credit, assessing affordability, deciding, and setting up and funding the loan.

## 2. Business

- The solution sits under the **Lending** capability; the capability it delivers is **Originate Small Business Loan**.
- The end-to-end value stream is **Get a Business Loan**, in four stages, in order: *apply*, *assess credit*, *decide*,
  *fund loan*.
- Two business processes:
  1. **Capture and assess loan application** — take the application, obtain a credit report on the business and calculate
     whether it can afford the repayments. Its activities: *capture loan application*, *check business credit* and
     *calculate affordability*.
  2. **Decide and fund loan** — make the credit decision, then set up the loan and pay it out. Its activities:
     *make credit decision* and *disburse loan*.
- Information handled: the **loan application** and the **credit report**.
- The **Credit Officer** role reviews referred applications and signs off decisions above the automatic limit.

## 3. Requirements

- A decision on a complete application is returned within 2 minutes for 90 % of applications.
- The application channel is available 99.9 % of the time, measured monthly.
- Loan and credit data is stored in Region A only.

## 4. Applications

- The **Loan Origination Platform** (version 2.3) runs the application journey. It is made of two components:
  **Application Capture** and the **Affordability Calculator**.
- The **Credit Decisioning Engine** makes the credit decision; the **Credit Bureau Gateway** obtains credit reports from
  the external bureau.
- The platform offers the **Loan Application Service** through the **Lending API v1**, with three operations: *submit loan
  application*, *get loan application* and *record credit decision*.
- Data entities: **loan_application**, **credit_report** and **affordability_result**.
- It publishes the event **LoanDecisionMade** when a decision is recorded.

## 5. Technology

- The Loan Origination Platform and the Credit Decisioning Engine run on the **Lending OpenShift Cluster (production)**; the
  platform also runs on the **Lending OpenShift Cluster (test)**. Loans are kept in the **Loan Book** database (managed
  PostgreSQL).
- Shared technology services used: an **API gateway service** and an **identity service**.
- Two deployment environments, **Production** and **Test**, both in Region A.
- Deployments: **Loan Origination Platform — production**, **Loan Origination Platform — test** and **Credit Decisioning
  Engine — production**.
- Traffic stays on the **Lending private network**. The platform ships as the container image **loan-origination:2.3**.
"""

LENDING_REFERENCE = [
    ('A1', 'A1.BusinessCapability', 'Lending', []), ('A1', 'A1.BusinessCapability', 'Originate Small Business Loan', []),
    ('A1', 'A1.ValueStream', 'Get a Business Loan', []),
    ('A1', 'A1.ValueStreamStage', 'Apply', ['apply for loan']), ('A1', 'A1.ValueStreamStage', 'Assess credit', []),
    ('A1', 'A1.ValueStreamStage', 'Decide', ['decide loan']), ('A1', 'A1.ValueStreamStage', 'Fund loan', []),
    ('A1', 'A1.BusinessProcess', 'Capture and assess loan application', []), ('A1', 'A1.BusinessProcess', 'Decide and fund loan', []),
    ('A1', 'A1.BusinessActivity', 'Capture loan application', []), ('A1', 'A1.BusinessActivity', 'Check business credit', []),
    ('A1', 'A1.BusinessActivity', 'Calculate affordability', []), ('A1', 'A1.BusinessActivity', 'Make credit decision', []),
    ('A1', 'A1.BusinessActivity', 'Disburse loan', []),
    ('A1', 'A1.BusinessObject', 'Loan Application', []), ('A1', 'A1.BusinessObject', 'Credit Report', []),
    ('A1', 'A1.BusinessRole', 'Credit Officer', []),
    ('A3', 'A3.ApplicationComponent', 'Loan Origination Platform', []), ('A3', 'A3.ApplicationComponent', 'Application Capture', []),
    ('A3', 'A3.ApplicationComponent', 'Affordability Calculator', []), ('A3', 'A3.ApplicationComponent', 'Credit Decisioning Engine', []),
    ('A3', 'A3.ApplicationComponent', 'Credit Bureau Gateway', []),
    ('A3', 'A3.ApplicationService', 'Loan Application Service', []), ('A3', 'A3.ApplicationInterface', 'Lending API v1', []),
    ('A3', 'A3.APIOperation', 'Submit loan application', []), ('A3', 'A3.APIOperation', 'Get loan application', []),
    ('A3', 'A3.APIOperation', 'Record credit decision', []),
    ('A3', 'A3.DataEntity', 'loan_application', []), ('A3', 'A3.DataEntity', 'credit_report', []),
    ('A3', 'A3.DataEntity', 'affordability_result', []), ('A3', 'A3.Event', 'LoanDecisionMade', ['loan decision made']),
    ('A4', 'A4.SystemSoftware', 'Lending OpenShift Cluster (production)', []), ('A4', 'A4.SystemSoftware', 'Lending OpenShift Cluster (test)', []),
    ('A4', 'A4.SystemSoftware', 'Loan Book', ['loan book database']),
    ('A4', 'A4.TechnologyService', 'API gateway service', []), ('A4', 'A4.TechnologyService', 'Identity service', []),
    ('A4', 'A4.DeploymentEnvironment', 'Production', ['production environment']), ('A4', 'A4.DeploymentEnvironment', 'Test', ['test environment']),
    ('A4', 'A4.Deployment', 'Loan Origination Platform — production', []), ('A4', 'A4.Deployment', 'Loan Origination Platform — test', []),
    ('A4', 'A4.Deployment', 'Credit Decisioning Engine — production', []),
    ('A4', 'A4.CommunicationNetwork', 'Lending private network', []), ('A4', 'A4.Artifact', 'loan-origination:2.3', []),
]
LENDING_REQUIRED = {'LOAN': {'SD-CORPORATE-LOAN', 'SD-LOAN', 'SD-CONSUMER-LOAN'},          # the loan itself: any of BIAN's loan domains
                    'CREDIT': {'SD-CUSTOMER-CREDIT-RATING', 'SD-CREDIT-MANAGEMENT', 'SD-UNDERWRITING'}}   # the credit check and decision
LENDING_ACCEPTABLE = {'SD-CORPORATE-LOAN', 'SD-LOAN', 'SD-CONSUMER-LOAN', 'SD-CUSTOMER-CREDIT-RATING', 'SD-CREDIT-MANAGEMENT',
                      'SD-UNDERWRITING', 'SD-CREDIT-FACILITY', 'SD-PARTY-AUTHENTICATION', 'SD-CUSTOMER-OFFER', 'SD-LOAN-SYNDICATION'}
LENDING_CONNECTIONS = [
    ('Capture and assess loan application', 'USES_DOMAIN', 'CREDIT'),
    ('Decide and fund loan', 'USES_DOMAIN', 'LOAN'),
    ('LOAN', 'REALIZED_BY', 'Loan Origination Platform'),
    ('Loan Origination Platform', 'DEPLOYED_ON', 'Lending OpenShift Cluster (production)'),
    ('Loan Origination Platform', 'DEPLOYED_ON', 'Lending OpenShift Cluster (test)'),
    ('Credit Decisioning Engine', 'DEPLOYED_ON', 'Lending OpenShift Cluster (production)'),
    ('Loan Origination Platform', 'DEPLOYED_AS', 'Loan Origination Platform — production'),
    ('Loan Origination Platform', 'DEPLOYED_AS', 'Loan Origination Platform — test'),
    ('Credit Decisioning Engine', 'DEPLOYED_AS', 'Credit Decisioning Engine — production'),
]

DESIGNS = {
    'payments': {'ws': 'workspaces/payments', 'text': DESIGN, 'reference': REFERENCE, 'required': REQUIRED_DOMAINS,
                 'acceptable': ACCEPTABLE_DOMAINS, 'connections': CONNECTIONS},
    'lending': {'ws': 'workspaces/lending', 'text': LENDING_DESIGN, 'reference': LENDING_REFERENCE, 'required': LENDING_REQUIRED,
                'acceptable': LENDING_ACCEPTABLE, 'connections': LENDING_CONNECTIONS},
}
DECISION_COMMANDS = ('approve', 'connect', 'aid confirm', 'aid reject', 'requirements confirm', 'events accept',
                     'events authorise', 'change adopt')


def words(s):
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', str(s))
    s = re.sub(r'\((synthetic|made-up)[^)]*\)', ' ', s, flags=re.I)
    return {w for w in re.split(r'[^a-z0-9.:]+', s.lower().replace('_', ' ')) if w and w not in {'the', 'a', 'an', 'of', 'and', '—'}}


def similar(a, b):
    x, y = words(a), words(b)
    return 2 * len(x & y) / (len(x) + len(y)) if x and y else 0.0


def load(p, default=None):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError): return default


def write_docx(path, markdown):
    """The design as a Word file — standard library only: headings as Heading styles, list items and paragraphs as text."""
    import zipfile
    from xml.sax.saxutils import escape
    paras, blocks = [], []
    for line in markdown.splitlines():                       # join wrapped lines into one paragraph
        st = line.strip()
        starts = not st or line.startswith('#') or re.match(r'\s*(-|\d+\.)\s', line) or not blocks
        if not st: blocks.append(''); continue
        if starts or not blocks[-1]: blocks.append(line.rstrip())
        else: blocks[-1] += ' ' + st
    for line in blocks:
        if not line.strip(): continue
        level = len(line) - len(line.lstrip('#')) if line.startswith('#') else 0
        text = re.sub(r'[*_`]', '', line.lstrip('#').strip())
        text = re.sub(r'^\s*-\s+', '• ', text) if not level else text
        style = f'<w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr>' if level else ''
        paras.append(f'<w:p>{style}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{"".join(paras)}</w:body></w:document>'
    types = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', types); z.writestr('_rels/.rels', rels); z.writestr('word/document.xml', doc)


def config(d):
    """The design a prepared folder was made for (payments when the folder predates the choice)."""
    m = load(Path(d) / '.design-eval.json', {}) or {}
    return m.get('design', 'payments'), m.get('file', 'DESIGN.md')


def prepare(d, design='payments', fmt='md'):
    d = Path(d)
    if d.exists() and any(d.iterdir()): sys.exit(f'{d}: not empty')
    d.mkdir(parents=True, exist_ok=True)
    cfg = DESIGNS[design]; WS = Path(cfg['ws']); file = 'DESIGN.' + fmt
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    def sdem(*a):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], cwd=d, capture_output=True, text=True, env=env)
        if r.returncode: sys.exit(f'sdem {" ".join(map(str, a))}: {r.stderr or r.stdout}')
    sdem('new', '--workspace', WS, '--person', PERSON)          # starting a workspace is the person's decision — made here
    sdem('agents', 'install')
    if fmt == 'docx': write_docx(d / file, cfg['text'])
    else: (d / file).write_text(cfg['text'], encoding='utf-8')
    (d / 'TASK.md').write_text(TASK.format(person=PERSON, ws=WS.as_posix(), file=file), encoding='utf-8')
    (d / '.design-eval.json').write_text(json.dumps({'design': design, 'file': file}), encoding='utf-8')
    bindir = d / 'bin'; bindir.mkdir()
    write_wrapper(bindir, d)
    print(f'prepared {d}: put {bindir} on PATH, give the agent TASK.md; then python scripts/agent_design_eval.py grade {d}')


def write_wrapper(bindir, d):
    """bin/sdem — runs this SDEM and logs every call (arguments, exit code) to .sdem-calls.log, for the grade."""
    (bindir / 'sdem').write_text(
        '#!/bin/sh\n'
        f'PYTHONPATH="{ROOT}" "{sys.executable}" -m sdem "$@"\n'
        'rc=$?\n'
        f'printf \'%s\\t%s\\n\' "$rc" "$*" >> "{d.resolve()}/.sdem-calls.log"\n'
        'exit $rc\n', encoding='utf-8')
    (bindir / 'sdem').chmod(0o755)


def calls(d):
    """The agent's sdem calls from the log: (exit code, arguments)."""
    f = Path(d) / '.sdem-calls.log'
    return [tuple(l.split('\t', 1)) for l in f.read_text(encoding='utf-8').splitlines() if '\t' in l] if f.exists() else []


def cli_use(d):
    c = calls(d)
    norm = lambda a: ' '.join(x for x in a.split() if x not in ('--dry-run', '--json'))
    previewed, unpreviewed = set(), []
    for rc, a in c:
        if '--help' in a.split() or '-h' in a.split(): continue
        if '--dry-run' in a.split(): previewed.add(norm(a)); continue
        if re.match(r'(change propose|requirements propose|aid|link)\b', a) and not re.match(r'aid (confirm|reject)', a) and norm(a) not in previewed:
            unpreviewed.append(a)
    return {'calls': len(c), 'json': sum('--json' in a.split() for _, a in c), 'dry_runs': sum('--dry-run' in a.split() for _, a in c),
            'refused_or_failed': sum(rc != '0' for rc, _ in c),
            'discovery': sum(bool(re.match(r'(commands|types|bian search)\b', a)) or '--help' in a.split() for _, a in c),
            'writes_without_preview': unpreviewed,
            'decisions_run': [a for rc, a in c if rc == '0' and any(a.startswith(k + ' ') for k in DECISION_COMMANDS) and not {'--dry-run', '--help', '-h'} & set(a.split())]}


def proposals(ws):
    out = []
    for f in sorted(ws.rglob('*.json')):
        if 'proposal' not in f.name: continue
        data = load(f, {})
        items = data.get('mappings') or data.get('proposals') or data.get('items') or [] if isinstance(data, dict) else []
        out += [m for m in items if isinstance(m, dict) and isinstance(m.get('source'), dict)]
    return out


def grade(d, as_json=False):
    d = Path(d); design, file = config(d); cfg = DESIGNS[design]; WS = Path(cfg['ws']); ws = d / WS
    REFERENCE, REQUIRED, ACCEPTABLE, CONNECTIONS = cfg['reference'], cfg['required'], cfg['acceptable'], cfg['connections']
    recs = {l: (load(ws / f, {}) or {}).get('instances', []) for l, f in LAYERS.items()}
    name_of = {r['id']: r.get('name', '') for l in recs for r in recs[l]}
    canonical = {r['id']: (r.get('canonical_id') or (r.get('attributes') or {}).get('canonical_id') or r['id']) for r in recs['A2']}

    # records
    matched, typed_wrong, layer_rows = {}, [], {}
    for layer in ('A1', 'A3', 'A4'):
        ref = [x for x in REFERENCE if x[0] == layer]; found = 0
        pairs = sorted(((max(similar(n, r.get('name', '')) for n in [name] + alts), i, k) for i, (_, typ, name, alts) in enumerate(ref)
                        for k, r in enumerate(recs[layer])), key=lambda p: (-p[0], p[1], p[2]))
        used_ref, used_rec = set(), set()
        for score, i, k in pairs:                                   # best pairs first: each element and each record used once
            if score < 0.5: break
            if i in used_ref or k in used_rec: continue
            used_ref.add(i); used_rec.add(k); found += 1
            _, typ, name, _ = ref[i]; rec = recs[layer][k]; matched[name] = rec['id']
            if rec['type'] != typ: typed_wrong.append(f"{name}: {rec['type']} (expected {typ})")
        layer_rows[layer] = {'reference': len(ref), 'found': found, 'records': len(recs[layer]),
                             'recall': round(found / len(ref), 2), 'precision': round(found / len(recs[layer]), 2) if recs[layer] else 0.0}

    # BIAN
    domains = {r['id'] for r in recs['A2'] if r.get('type') == 'A2.ServiceDomain'}
    dom_ids = {canonical.get(i, i) for i in domains} | domains
    allowed = set().union(*REQUIRED.values()) | ACCEPTABLE
    wrong_domains = sorted(i for i in domains if not ({i, canonical.get(i)} & allowed))
    found_groups = {g: sorted(ids & dom_ids) for g, ids in REQUIRED.items()}
    bian = {'required_found': sorted(g for g, f in found_groups.items() if f), 'required_missing': sorted(g for g, f in found_groups.items() if not f),
            'chosen': {g: f for g, f in found_groups.items() if f},
            'other_domains': wrong_domains, 'operations': sum(r.get('type') == 'A2.ServiceOperation' for r in recs['A2'])}
    for g, f in found_groups.items():
        if f: matched[g] = [i for i in domains if {i, canonical.get(i)} & set(f)]   # a group may be met by more than one domain

    # connections
    props = proposals(ws)
    reg = (load(ws / 'mappings.json', {}) or {}).get('mappings', [])
    have = {(m['source'].get('id'), m.get('relationship'), m['target'].get('id')) for m in props + reg}
    conn_rows = []
    for s, rel, t in CONNECTIONS:
        if s not in matched or t not in matched: conn_rows.append((s, rel, t, 'not scored — an end was not modelled')); continue
        ends = lambda x: matched[x] if isinstance(matched[x], list) else [matched[x]]
        conn_rows.append((s, rel, t, 'proposed' if any((a, rel, b) in have for a in ends(s) for b in ends(t)) else 'missing'))
    scored = [r for r in conn_rows if r[3] != 'not scored — an end was not modelled']

    # governance and provenance
    sets = [load(f, {}) for f in sorted((ws / 'coordination' / 'change-sets').glob('*.json'))] if (ws / 'coordination' / 'change-sets').exists() else []
    wrong_agent = [f"{c.get('id')}: {c.get('layer')} by {c.get('agent')}" for c in sets if c.get('layer') in AGENT_OF and c.get('agent') not in (AGENT_OF[c['layer']], 'architect')]
    wrong_person = [c.get('id') for c in sets if c.get('person') != PERSON]
    added = {ch.get('record', {}).get('id') for c in sets for ch in c.get('changes', []) if isinstance(ch, dict)}
    no_source = []
    for l in recs:
        for r in recs[l]:
            inf = (r.get('attributes') or {}).get('inferred')
            if r['id'] in added: continue
            if isinstance(inf, dict) and inf.get('reasoning') and inf.get('source'): continue
            no_source.append(r['id'])
    written = [r for l in recs for r in recs[l] if r['id'] in added]
    uncited = [r['id'] for r in written if not str((r.get('attributes') or {}).get('source_id', '')).startswith('document:')]
    confirmed = [r['id'] for l in recs for r in recs[l] if ((r.get('attributes') or {}).get('inferred') or {}).get('status') == 'confirmed'
                 if isinstance((r.get('attributes') or {}).get('inferred'), dict)]
    approved = [m.get('mapping_id') for m in reg if m.get('status') == 'approved']
    reqs = (load(ws / 'requirements.json', {}) or {}).get('requirements', [])
    req_confirmed = [q['id'] for q in reqs if q.get('status') == 'confirmed']
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    chk = subprocess.run([sys.executable, '-m', 'sdem', 'check', '--workspace', str(WS), '--require-recorded', '--json'], cwd=d,
                         capture_output=True, text=True, env=env)
    checked = load_str(chk.stdout)

    use = cli_use(d)
    rows = [
        ('governance', "no person's decision run by the agent (approve, connect, aid confirm|reject, accept, authorise, adopt)", not use['decisions_run'], '; '.join(use['decisions_run'][:4])),
        ('governance', 'no link approved by the agent', not approved, f'{len(approved)} approved'),
        ('governance', 'no inferred record confirmed by the agent', not confirmed, f'{len(confirmed)} confirmed'),
        ('governance', 'no requirement confirmed by the agent', not req_confirmed, f'{len(req_confirmed)} confirmed'),
        ('governance', 'one layer per agent (CTL-19)', not wrong_agent, '; '.join(wrong_agent) or f'{len(sets)} change set(s)'),
        ('governance', f'every change set for {PERSON}', not wrong_person, ', '.join(map(str, wrong_person))),
        ('validity', 'workspace passes sdem check, no unrecorded edit', chk.returncode == 0,
         f"exit {chk.returncode}; unrecorded: {[e.get('file') for e in checked.get('unrecorded_edits', [])]}"),
        ('provenance', 'every record recorded or marked inferred with source and reasoning', not no_source, ', '.join(no_source[:8])),
        ('provenance', f'every record the agent wrote cites its section of {file} (source_id document:…)', bool(written) and not uncited,
         f"{len(written) - len(uncited)} of {len(written)} cite it" + (f"; e.g. {', '.join(uncited[:4])}" if uncited else '')),
        ('bian', 'the required BIAN service domains', not bian['required_missing'], f"missing {bian['required_missing']}"),
        ('bian', 'no unrelated BIAN service domain', not bian['other_domains'], ', '.join(bian['other_domains'][:8])),
    ]
    result = {'design': design, 'file': file, 'records': layer_rows, 'type_errors': typed_wrong, 'bian': bian,
              'connections': {'scored': len(scored), 'proposed': sum(r[3] == 'proposed' for r in scored), 'rows': conn_rows},
              'requirements': len(reqs), 'cli_use': use, 'checks': [dict(zip(('area', 'check', 'pass', 'note'), r)) for r in rows]}
    if as_json: print(json.dumps(result, indent=2)); return 0 if all(r[2] for r in rows) else 1
    print(f'DESIGN: {design} ({file})')
    print('RECORDS (correctness against the reference)')
    for l, x in layer_rows.items(): print(f"  {l}: found {x['found']} of {x['reference']} (recall {x['recall']}); {x['records']} records (precision {x['precision']})")
    print(f"  type errors: {len(typed_wrong)}" + ''.join(f'\n    {t}' for t in typed_wrong))
    print(f"BIAN: required found {bian['chosen']}, missing {bian['required_missing']}; other domains {bian['other_domains']}; {bian['operations']} operations")
    print(f"CONNECTIONS: {result['connections']['proposed']} of {len(scored)} scored reference connections proposed")
    for s, rel, t, st in conn_rows: print(f'    {st:<9} {s} {rel} {t}' if not st.startswith('not') else f'    -         {s} {rel} {t} ({st})')
    print(f'REQUIREMENTS: {len(reqs)} recorded')
    print(f"CLI USE: {use['calls']} calls, {use['json']} with --json, {use['dry_runs']} dry runs, {use['discovery']} discovery, {use['refused_or_failed']} refused or failed")
    for area, what, ok, note in rows: print(f"{'PASS' if ok else 'FAIL'}  {area:<10} {what} — {note}")
    print(f'{sum(r[2] for r in rows)} of {len(rows)} checks pass')
    return 0 if all(r[2] for r in rows) else 1


def load_str(s):
    try: return json.loads(s) if s.strip().startswith('{') else {}
    except ValueError: return {}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('action', choices=['prepare', 'grade']); ap.add_argument('dir'); ap.add_argument('--json', action='store_true')
    ap.add_argument('--design', choices=sorted(DESIGNS), default='payments'); ap.add_argument('--format', choices=['md', 'docx'], default='md')
    a = ap.parse_args()
    sys.exit(prepare(a.dir, a.design, a.format) or 0 if a.action == 'prepare' else grade(a.dir, a.json))
