"""The v3 design translated by the AI reading design.md — what it states AND what follows from its own sentences — with no sdem transform
and no sdem aid. Starts from the stated-only translation of run 2 and adds each link the document implies, with the section and the
sentence it follows from. Where the document is silent, nothing is written."""
import json, sys
P = sys.argv[1].rstrip('/') + '/'
L = lambda f: json.load(open(P + f, encoding='utf-8'))
def S(f, d): json.dump(d, open(P + f, 'w', encoding='utf-8'), indent=1)
a1, a3, a4, sug = L('a1-business.json'), L('a3-application.json'), L('a4-technology.json'), L('CROSS-LAYER-SUGGESTIONS.json')
log = []
def link(doc, s, k, t, sec, basis, why):
    if any((r['source'], r['kind'], r['target']) == (s, k, t) for r in doc['relationships']): return
    doc['relationships'].append({'source': s, 'kind': k, 'target': t, 'source_id': f'document:design.md#{sec}'}); log.append((s, k, t, sec, basis, why))
def x(s, r, t, sec, basis, why):
    sug['suggestions'].append({'source': s, 'link_type': r, 'target': t, 'design_section': str(sec), 'basis': basis, 'reason': why}); log.append((s, r, t, sec, basis, why))

# ---- A1 (§1, §2, §3) ----
for p, st in (('PROC-CONSENT', 'ST-CONSENT'), ('PROC-AUTH', 'ST-CONSENT'), ('PROC-SUBMIT', 'ST-SUBMIT'), ('PROC-VALIDATE', 'ST-SUBMIT'), ('PROC-RISK', 'ST-SUBMIT'),
              ('PROC-DEBIT', 'ST-SUBMIT'), ('PROC-HANDOFF', 'ST-SUBMIT'), ('PROC-STATUS', 'ST-STATUS')):
    link(a1, p, 'realization', st, 3, 'implied', 'the value stream moves through consent, payment submission and status enquiry; the processes are listed in that order')
for p, c in (('PROC-CONSENT', 'CAP-CONSENT'), ('PROC-AUTH', 'CAP-CONSENT'), ('PROC-RISK', 'CAP-RISK'), ('PROC-SUBMIT', 'CAP-PAY'), ('PROC-VALIDATE', 'CAP-PAY'),
             ('PROC-DEBIT', 'CAP-PAY'), ('PROC-HANDOFF', 'CAP-PAY'), ('PROC-STATUS', 'CAP-PAY')):
    link(a1, p, 'realization', c, 3, 'implied', 'the capability named for what the process does: customer payment consent, payment risk control, domestic payment initiation')
link(a1, 'PROC-AUTH', 'realization', 'SVC-AUTH', 3, 'implied', 'the consent authorisation service is what authenticating and authorising provides')
for p in ('PROC-CONSENT', 'PROC-SUBMIT', 'PROC-STATUS'): link(a1, p, 'realization', 'SVC-INIT', 3, 'implied', 'the business initiation service is what the provider-facing steps provide')
link(a1, 'PROC-HANDOFF', 'flow', 'PROC-STATUS', 3, 'implied', 'the processes are listed in order; status enquiries follow the handoff')
link(a1, 'SVC-INIT', 'serving', 'ACTOR-TPP', 1, 'implied', 'the accredited third-party provider is the one that creates consents and submits payments (R-01, R-11)')
link(a1, 'SVC-AUTH', 'serving', 'ACTOR-CUSTOMER', 1, 'implied', 'the customer is redirected to the bank to authenticate and authorise')
for r, p, why in (('R-01', 'PROC-CONSENT', 'creating the consent is capturing it'), ('R-02', 'PROC-AUTH', 'the redirect flow authenticates the customer and accepts or rejects the consent'),
                  ('R-03', 'PROC-SUBMIT', 'section 5: on submission one transaction checks the authorised and unconsumed consent'), ('R-04', 'PROC-SUBMIT', 'section 5: submission checks the consent is authorised'),
                  ('R-05', 'PROC-SUBMIT', 'section 5: submission records the idempotency key scoped to the third party'), ('R-06', 'PROC-VALIDATE', 'validates data/account'),
                  ('R-07', 'PROC-VALIDATE', 'section 5: before debit the hub validates account eligibility'), ('R-08', 'PROC-RISK', 'screens fraud before the debit'),
                  ('R-09', 'PROC-DEBIT', 'posts one debit'), ('R-10', 'PROC-HANDOFF', 'hands off for execution'), ('R-11', 'PROC-STATUS', 'responds to status enquiries'),
                  ('R-12', 'PROC-AUTH', 'section 7: a decline or failed authentication leaves no usable consent, so no payment and no debit'),
                  ('R-19', 'PROC-STATUS', 'section 3: AcceptedSettlementInProcess is reported as acceptance for execution, not completion'),
                  ('R-21', 'PROC-AUTH', 'only the redirect flow is designed in S1'), ('R-23', 'PROC-SUBMIT', 'status and expiry are checked before submission')):
    link(a1, p, 'realization', r, 2, 'implied', why)
# ---- A3 (§5) ----
link(a3, 'APP-EDGE', 'access', 'DATA-AUDIT', 5, 'implied', 'APP-EDGE produces correlated security events; SecurityEventLog is where security events are kept')
link(a3, 'APP-EDGE', 'flow', 'APP-PAYHUB', 5, 'implied', 'the ingress terminates the provider channel; the hub orchestrates initiation')
link(a3, 'APP-EDGE', 'flow', 'APP-CONSENT', 5, 'implied', 'consent creation and read arrive at the ingress; APP-CONSENT controls the consent lifecycle')
link(a3, 'APP-IDENT', 'flow', 'APP-CONSENT', 5, 'implied', 'authentication accepts or rejects the consent that APP-CONSENT holds')
link(a3, 'APP-PAYHUB', 'flow', 'APP-NOTIFY', 5, 'implied', 'APP-NOTIFY is a downstream notification component')
link(a3, 'API-DEBTOR-READ', 'access', 'DATA-CONSENT', 5, 'implied', 'the debtor account is a column of the ConsentLedger')
# ---- A4 (§6) ----
for p, a, b, why in (('PATH-EDGE', 'NODE-EDGE', None, 'HTTPS/TLS crosses the external boundary at the API ingress'),
                     ('PATH-DATA', 'NODE-APP', 'NODE-DATA', 'application-to-SQL traffic: application compute to the database nodes'),
                     ('PATH-KEY', 'NODE-APP', 'NODE-SEC', 'secret retrieval: by the applications, from identity/secrets'),
                     ('PATH-HANDOFF', 'NODE-APP', 'NODE-INT', 'payment handoff: to ledger/execution integration')):
    for n in (a, b):
        if n: link(a4, p, 'association', n, 6, 'implied', why)
link(a4, 'NODE-DATA', 'assignment', 'SYS-DB', 6, 'implied', 'the managed database is what the database nodes run')
link(a4, 'NODE-SEC', 'assignment', 'SYS-KMS', 6, 'implied', 'managed key custody is on the identity/secrets node')
for d, n, why in (('DEP-EDGE', 'NODE-EDGE', 'the API ingress'), ('DEP-IDENT', 'NODE-SEC', 'identity is on the identity/secrets node'), ('DEP-CONSENT', 'NODE-APP', 'application compute'),
                  ('DEP-PAYHUB', 'NODE-APP', 'application compute'), ('DEP-RISK', 'NODE-APP', 'application compute'), ('DEP-NOTIFY', 'NODE-APP', 'application compute'),
                  ('DEP-LEDGER', 'NODE-INT', 'ledger/execution integration'), ('DEP-OUT', 'NODE-INT', 'ledger/execution integration')):
    link(a4, n, 'assignment', d, 6, 'implied', why)
# ---- between layers ----
x('PROC-SUBMIT', 'USES_DOMAIN', 'Payment Order Initiation', 4, 'implied', 'receiving the payment is initiating the payment order')
x('PROC-STATUS', 'USES_DOMAIN', 'Payment Order Initiation', 4, 'implied', 'status enquiries retrieve the payment order initiation transaction')
x('PROC-AUTH', 'USES_DOMAIN', 'Party Authentication', 4, 'stated', 'we align the customer authentication concern to that domain')
x('CAP-PAY', 'SUPPORTED_BY', 'Payment Order Initiation', 4, 'implied', 'the service domain for the capability of the same name')
x('Payment Order Initiation', 'REALIZED_BY', 'APP-PAYHUB', 5, 'implied', 'APP-PAYHUB validates and orchestrates initiation; AD-02: a single payment orchestrator')
x('Party Authentication', 'REALIZED_BY', 'APP-IDENT', 5, 'implied', 'APP-IDENT handles customer authentication')
x('Payment Order Initiation: Initiate', 'IMPLEMENTED_BY', 'API-PAYMENT-CREATE', 5, 'implied', 'POST /domestic-payments initiates the payment')
x('Payment Order Initiation: Retrieve', 'IMPLEMENTED_BY', 'API-PAYMENT-READ', 5, 'implied', 'GET /domestic-payments/{id} retrieves it')
x('IF-TPP', 'REALIZED_BY', 'IFC-PAYMENT-INITIATION', 5, 'implied', 'the provider API channel is the Payment Initiation API')
x('IFC-PAYMENT-INITIATION', 'EXPOSED_THROUGH', 'NODE-EDGE', 6, 'implied', 'HTTPS crosses the external boundary at the redundant API ingress')
for c, d in (('APP-EDGE', 'DEP-EDGE'), ('APP-IDENT', 'DEP-IDENT'), ('APP-CONSENT', 'DEP-CONSENT'), ('APP-PAYHUB', 'DEP-PAYHUB'), ('APP-RISK', 'DEP-RISK'), ('APP-LEDGER', 'DEP-LEDGER'),
             ('APP-NOTIFY', 'DEP-NOTIFY'), ('APP-OUTBOUND', 'DEP-OUT')):
    x(c, 'DEPLOYED_AS', d, 6, 'stated', 'every application component has a named deployment')
for c, n in (('APP-EDGE', 'NODE-EDGE'), ('APP-IDENT', 'NODE-SEC'), ('APP-CONSENT', 'NODE-APP'), ('APP-PAYHUB', 'NODE-APP'), ('APP-RISK', 'NODE-APP'), ('APP-NOTIFY', 'NODE-APP'),
             ('APP-LEDGER', 'NODE-INT'), ('APP-OUTBOUND', 'NODE-INT')):
    x(c, 'DEPLOYED_ON', n, 6, 'implied', 'the node its deployment runs on')
for e, why, basis in (('DATA-CONSENT', 'the consent and payment tables share a restricted storage service', 'stated'), ('DATA-PAYMENT', 'the consent and payment tables share a restricted storage service', 'stated'),
                      ('DATA-IDEMP', 'section 5: the same database transaction records the idempotency key', 'implied')):
    x(e, 'STORED_IN', 'SYS-DB', 6, basis, why)
S('a1-business.json', a1); S('a3-application.json', a3); S('a4-technology.json', a4); S('CROSS-LAYER-SUGGESTIONS.json', sug); S('NOT-STATED.json', {'items': []})
json.dump([dict(zip(('source', 'link', 'target', 'section', 'basis', 'why'), l)) for l in log], open(P + '../added-by-reading.json', 'w', encoding='utf-8'), indent=1)
import collections; print(len(log), collections.Counter(l[4] for l in log))
