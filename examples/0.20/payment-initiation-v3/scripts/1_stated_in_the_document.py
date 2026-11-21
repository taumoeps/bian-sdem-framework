"""Payment Initiation v3, RUN 2 (after the fixes of 2026-11-17 — flat zones, planned records with values left out, statuses and API fields recorded): the frozen design.md → one change set per layer. Only what the document states;
every record and link cites its section. Written by the SDEM operator; the reference's hidden files were not read."""
import json, sys
OUT = sys.argv[1]
DOC = 'document:design.md#'
def rec(i, t, name, sec, desc=None, **attrs):
    a = {k: v for k, v in attrs.items() if v is not None}; a['source_id'] = ','.join(DOC + s for s in str(sec).split(','))
    r = {'id': i, 'type': t, 'version': '1', 'name': name, 'lifecycle_status': 'planned', 'attributes': a}
    if desc: r['description'] = desc
    return r
def link(s, k, t, sec): return {'source': s, 'kind': k, 'target': t, 'source_id': DOC + str(sec)}
def cs(layer, records, links): return {'layer': layer, 'reason': f'Payment Initiation v3 — the {layer} design as the frozen reference design document states it (design.md; the public twin, PT-20)',
                                       'changes': [{'op': 'add', 'record': r} for r in records], 'relationships': {'add': links}}

# ---------------- A1 (design.md #1, #2, #3) ----------------
A1, L1 = [], []
A1 += [rec('CAP-PAY', 'A1.BusinessCapability', 'Domestic payment initiation', 3, level=1),
       rec('CAP-CONSENT', 'A1.BusinessCapability', 'Customer payment consent', 3, level=2),
       rec('CAP-RISK', 'A1.BusinessCapability', 'Payment risk control', 3, level=2),
       rec('VS-MERCHANT', 'A1.ValueStream', 'Merchant payment', 3, stages=['ST-CONSENT', 'ST-SUBMIT', 'ST-STATUS']),
       rec('ST-CONSENT', 'A1.ValueStreamStage', 'Consent', 3), rec('ST-SUBMIT', 'A1.ValueStreamStage', 'Payment submission', 3),
       rec('ST-STATUS', 'A1.ValueStreamStage', 'Status enquiry', 3),
       rec('PROD-ACCOUNT', 'A1.Product', 'Retail account', 3, 'The invented retail account product the bank offers.'),
       rec('SVC-INIT', 'A1.BusinessService', 'Business initiation service', 3, channels=['IF-TPP'], consumers=['ACTOR-TPP']),
       rec('SVC-AUTH', 'A1.BusinessService', 'Consent authorisation service', 3, channels=['IF-WEB'], consumers=['ACTOR-CUSTOMER']),
       rec('ACTOR-CUSTOMER', 'A1.BusinessActor', 'Retail customer', '1,3', actor_kind='person', external=True),
       rec('ACTOR-MERCHANT', 'A1.BusinessActor', 'Merchant', '1,3', actor_kind='formal organisation', external=True),
       rec('ACTOR-TPP', 'A1.BusinessActor', 'Accredited third-party provider', '1,3', actor_kind='formal organisation', external=True),
       rec('ROLE-BANK', 'A1.BusinessRole', 'Bank — account servicing role', '1,3', role_kind='role'),
       rec('IF-TPP', 'A1.BusinessInterface', 'Provider API channel', 3, channel_kind='api', customer_facing=False),
       rec('IF-WEB', 'A1.BusinessInterface', 'Redirected authorisation web channel', 3, channel_kind='web', customer_facing=True)]
PROCS = [('PROC-CONSENT', 'Capture consent', None), ('PROC-AUTH', 'Authenticate and authorise', ['SO-PARTY-AUTHENTICATION-EVALUATE']),
         ('PROC-SUBMIT', 'Receive the payment', ['SO-PAYMENT-ORDER-INITIATION-INITIATE']), ('PROC-VALIDATE', 'Validate data and account', None),
         ('PROC-RISK', 'Screen fraud', None), ('PROC-DEBIT', 'Post one debit', None), ('PROC-HANDOFF', 'Hand off for execution', None),
         ('PROC-STATUS', 'Respond to status enquiries', ['SO-PAYMENT-ORDER-INITIATION-RETRIEVE'])]
for i, n, inv in PROCS:
    A1.append(rec(i, 'A1.BusinessProcess', n, '3,4' if inv else 3, invokes=inv, automation_level='automated'))
    L1.append(link('ROLE-BANK', 'assignment', i, 3))
for a, b in zip(PROCS[:6], PROCS[1:7]): L1.append(link(a[0], 'flow', b[0], 3))
REQS = [('R-01', 'S', 'The accredited third party can create a one-off domestic payment consent and receive a bank-generated identifier.'),
        ('R-02', 'S', 'The bank uses the redirect authorisation flow to authenticate the customer and accept or reject the complete consent.'),
        ('R-03', 'S', 'Unauthorised domestic consent is time-limited to 24 hours; expired consent cannot be used to initiate payment.'),
        ('R-04', 'S', 'Only an authorised domestic consent may be used to submit one domestic payment.'),
        ('R-05', 'D', 'The same payment request will not create a second debit under supported idempotent replay.'),
        ('R-06', 'S', 'Payment data use NZD and valid domestic account identification; invalid data are rejected.'),
        ('R-07', 'D', 'The bank checks debtor account eligibility and available funds before posting.'),
        ('R-08', 'D', 'The bank applies a risk screening decision before debit and execution handoff.'),
        ('R-09', 'D', 'The bank commits exactly one ledger debit per successfully accepted payment.'),
        ('R-10', 'D', 'After the initial checks, the bank hands the accepted instruction to its execution boundary.'),
        ('R-11', 'S', 'The third party can retrieve the bank payment resource and its reported status.'),
        ('R-12', 'D', 'Customer decline, failed authentication or expired consent do not debit accounts.'),
        ('R-13', 'D', 'Payment API is available at least 99.95% monthly (fictional target).'),
        ('R-14', 'D', 'Read p95 response latency at most 500 ms at 200 requests per second (fictional target).'),
        ('R-15', 'D', 'Payments platform recovery time at most 30 minutes and recovery point at most 5 minutes (fictional target).'),
        ('R-16', 'D', 'Personal and account information is protected and access to consent and payment resources is scoped.'),
        ('R-17', 'D', 'Payment and consent decisions are correlated and auditable.'),
        ('R-18', 'S', 'The bank uses version 2.3.3 consistently for consent and payment API resources.'),
        ('R-19', 'S', 'A payment accepted for execution is not represented as completed at another bank.'),
        ('R-20', 'D', 'Deployments have explicit segment boundaries, private persistence routes and managed secrets.'),
        ('R-21', 'S', 'A regulated deployment must support hybrid redirect and decoupled (CIBA) authorisation; only redirect is designed in S1, so the full regulated implementation remains outside S1.'),
        ('R-22', 'S', 'API request throttling (429) and participant identification follow the MBIE-modified v2.3.3 requirements, not the superseded onboarding and register clauses.'),
        ('R-23', 'S', 'An unauthorised domestic payment consent is valid for 24 hours, and status and expiry are checked before submission.'),
        ('R-24', 'S', 'A payment debtor-account read is only returned where DebtorAccountRelease is true.')]
for i, basis, text in REQS:
    A1.append(rec(i, 'A1.BusinessRequirement', text if len(text) <= 80 else text[:77].rsplit(' ', 1)[0] + '…', 2, text + f' (basis {basis} in the design document)',
                  requirement_kind='requirement', priority='must'))
L1 += [link('CAP-PAY', 'aggregation', 'CAP-CONSENT', 3), link('CAP-PAY', 'aggregation', 'CAP-RISK', 3),
       link('VS-MERCHANT', 'composition', 'ST-CONSENT', 3), link('VS-MERCHANT', 'composition', 'ST-SUBMIT', 3), link('VS-MERCHANT', 'composition', 'ST-STATUS', 3),
       link('ST-CONSENT', 'flow', 'ST-SUBMIT', 3), link('ST-SUBMIT', 'flow', 'ST-STATUS', 3),
       link('IF-TPP', 'serving', 'ACTOR-TPP', 3), link('IF-WEB', 'serving', 'ACTOR-CUSTOMER', 3)]

# ---------------- A3 (design.md #5) ----------------
A3, L3 = [], []
COMPS = [('APP-EDGE', 'API ingress', 'Terminates the accredited provider API channel and produces correlated security events.', 'DEP-EDGE'),
         ('APP-IDENT', 'Identity', 'Handles customer authentication.', 'DEP-IDENT'),
         ('APP-CONSENT', 'Consent processing', 'Controls the consent lifecycle and its persistence.', 'DEP-CONSENT'),
         ('APP-PAYHUB', 'Payments hub', 'Validates and orchestrates initiation, idempotency, risk, status and retries.', 'DEP-PAYHUB'),
         ('APP-RISK', 'Fraud service', 'Returns a risk decision.', 'DEP-RISK'),
         ('APP-LEDGER', 'Account ledger', 'Owns account eligibility and posting; rejects repeated posting ids.', 'DEP-LEDGER'),
         ('APP-OUTBOUND', 'Outbound connector', 'Performs the accepted-instruction handoff.', 'DEP-OUT'),
         ('APP-NOTIFY', 'Notification service', 'A non-critical downstream notification component.', 'DEP-NOTIFY')]
for i, n, d, dep in COMPS: A3.append(rec(i, 'A3.ApplicationComponent', n, '5,6', d, deployed_as=[dep], sources={'deployed_as': DOC + '6'}))
TABLES = {
 'DATA-CONSENT': ('ConsentLedger', 'CONSENT', [('consent_id', 'uuid', 'PK'), ('third_party_id', 'varchar(64)', ''), ('customer_id', 'uuid', 'PII'), ('status', 'varchar(32)', ''),
                  ('instruction_identification', 'varchar(36)', ''), ('end_to_end_identification', 'varchar(36)', ''), ('amount', 'numeric(18,2)', ''), ('currency', 'char(3)', ''),
                  ('creditor_account', 'varchar(32)', 'PII'), ('debtor_account', 'varchar(32)', 'PII'), ('expires_at', 'timestamptz', '')]),
 'DATA-PAYMENT': ('PaymentLedger', 'PAYMENT', [('payment_id', 'uuid', 'PK'), ('consent_id', 'uuid', 'FK'), ('instruction_identification', 'varchar(36)', ''), ('amount', 'numeric(18,2)', ''),
                  ('currency', 'char(3)', ''), ('payment_status', 'varchar(40)', ''), ('ledger_posting_id', 'uuid', ''), ('handoff_id', 'uuid', ''), ('created_at', 'timestamptz', '')]),
 'DATA-IDEMP': ('IdempotencyRegistry', 'IDEMP', [('key_hash', 'char(64)', 'PK'), ('third_party_id', 'varchar(64)', ''), ('request_hash', 'char(64)', ''), ('resource_id', 'uuid', ''), ('expires_at', 'timestamptz', '')]),
 'DATA-AUDIT': ('SecurityEventLog', 'AUDIT', [('event_id', 'uuid', 'PK'), ('actor_ref', 'varchar(64)', 'PII'), ('action', 'varchar(64)', ''), ('correlation_id', 'uuid', ''), ('recorded_at', 'timestamptz', '')])}
STATUSES = {('CONSENT', 'status'): ['AwaitingAuthorisation', 'Authorised', 'Rejected', 'Consumed'],
            ('PAYMENT', 'payment_status'): ['Pending', 'Rejected', 'AcceptedSettlementInProcess', 'AcceptedSettlementCompleted']}
F = lambda key, col: f"F-{key}-{col.upper().replace('_', '-')}"
STORED = {'DATA-CONSENT': ['SYS-DB'], 'DATA-PAYMENT': ['SYS-DB'], 'DATA-IDEMP': ['SYS-DB']}
for eid, (name, key, cols) in TABLES.items():
    A3.append(rec(eid, 'A3.DataEntity', name, '5,6' if eid in STORED else 5, attributes=[c for c, _, _ in cols], stored_in=STORED.get(eid),
                  personal_information=any(h == 'PII' for _, _, h in cols) or None, sources={'stored_in': DOC + '6'} if eid in STORED else None))
    for c, t, h in cols:
        A3.append(rec(F(key, c), 'A3.DataAttribute', c, '5,3' if (key, c) in STATUSES else 5, physical_type=t, primary_key=True if h == 'PK' else None, personal_information=True if h == 'PII' else None,
                      classification='confidential' if h == 'PII' else 'internal', allowed_values=STATUSES.get((key, c))))
        L3.append(link(eid, 'composition', F(key, c), 5))
L3.append(link(F('PAYMENT', 'consent_id'), 'association', 'DATA-CONSENT', 5))   # the FK
ALIASES = {'ConsentId': 'consent_id', 'NZDomesticConsent1/InstructionIdentification': 'instruction_identification',
           'NZDomesticConsent1/EndToEndIdentification': 'end_to_end_identification', 'NZDomesticConsent1/InstructedAmount/Amount': 'amount',
           'NZDomesticConsent1/InstructedAmount/Currency': 'currency', 'Status': 'status', 'DomesticPaymentId': 'payment_id'}
A3.append(rec('IFC-PAYMENT-INITIATION', 'A3.ApplicationInterface', 'Payment Initiation API v2.3.3', '5,6',
              'The provider-facing API: domestic payment consents and domestic payments, as the NZ Banking Data standard v2.3.3 defines them.',
              security_scheme='oauth2', protocol='https', internet_facing=True, field_aliases=ALIASES))
C, P = (lambda c: F('CONSENT', c)), (lambda c: F('PAYMENT', c))
OPS = [('API-CONSENT-CREATE', 'Create domestic payment consent', 'POST', '/domestic-payment-consents',
        ['InstructionIdentification', 'EndToEndIdentification', 'InstructedAmount/Amount', 'InstructedAmount/Currency', 'CreditorAccount/SchemeName', 'CreditorAccount/Identification',
         'CreditorAccount/Name', 'DebtorAccount/Identification', 'DebtorAccountRelease', 'RemittanceInformation/Reference', 'ConsentId', 'Status'],
        [C('instruction_identification'), C('end_to_end_identification'), C('amount'), C('currency')], [C('consent_id'), C('status')], 'DATA-CONSENT'),
       ('API-CONSENT-READ', 'Read domestic payment consent', 'GET', '/domestic-payment-consents/{ConsentId}', ['ConsentId', 'Status'], [C('consent_id')], [C('consent_id'), C('status')], 'DATA-CONSENT'),
       ('API-PAYMENT-CREATE', 'Create domestic payment', 'POST', '/domestic-payments', ['ConsentId', 'DomesticPaymentId', 'Status'],
        [P('consent_id')], [P('payment_id'), P('payment_status')], 'DATA-PAYMENT'),
       ('API-PAYMENT-READ', 'Read domestic payment', 'GET', '/domestic-payments/{DomesticPaymentId}', ['DomesticPaymentId', 'Status'], [P('payment_id')], [P('payment_id'), P('payment_status')], 'DATA-PAYMENT')]
for i, n, m, path, payload, rq, rs, ent in OPS:
    A3.append(rec(i, 'A3.APIOperation', n, 5, method=m, path=path, payload_fields=payload, request_fields=rq, response_fields=rs))
    L3 += [link('IFC-PAYMENT-INITIATION', 'composition', i, 5), link(i, 'access', ent, 5)]
A3.append(rec('API-DEBTOR-READ', 'A3.APIOperation', 'Read payment debtor account', '5,2', 'Returned only where DebtorAccountRelease is true (R-24). The document gives no path.', method='GET'))
L3 += [link('IFC-PAYMENT-INITIATION', 'composition', 'API-DEBTOR-READ', 5)]
A3.append(rec('EVT-HANDOFF', 'A3.Event', 'Durable handoff event', 5, 'Emitted by the hub when a payment is recorded as accepted for execution.', event_source='APP-PAYHUB'))
L3 += [link('APP-EDGE', 'composition', 'IFC-PAYMENT-INITIATION', 5),
       link('APP-CONSENT', 'access', 'DATA-CONSENT', 5),
       link('APP-PAYHUB', 'access', 'DATA-CONSENT', 5), link('APP-PAYHUB', 'access', 'DATA-PAYMENT', 5), link('APP-PAYHUB', 'access', 'DATA-IDEMP', 5),
       link('APP-PAYHUB', 'flow', 'APP-RISK', 5), link('APP-PAYHUB', 'flow', 'APP-LEDGER', 5), link('APP-PAYHUB', 'flow', 'APP-OUTBOUND', 5)]

# ---------------- A4 (design.md #6) ----------------
A4, L4 = [], []
A4.append(rec('LOC-NZ', 'A4.Location', 'NZ production location', 6, 'A fictional New Zealand production location.', location_kind='site', country='NZ'))
A4.append(rec('ENV-PROD', 'A4.DeploymentEnvironment', 'Production', 6, environment_kind='production', location='LOC-NZ'))
ZN = [('EDGE', 'Edge zone', 'dmz', 'NODE-EDGE', 'Redundant API ingress'), ('APP', 'Application zone', 'internal', 'NODE-APP', 'Three-node application compute'),
      ('DATA', 'Data zone', 'private', 'NODE-DATA', 'Database nodes'), ('SEC', 'Security zone', 'private', 'NODE-SEC', 'Identity and secrets'),
      ('INTEG', 'Integration zone', 'internal', 'NODE-INT', 'Ledger and execution integration')]
# Flat zones (ZF-01): the five zones as design.md names them — nothing added. Edge is the DMZ; application and integration are internal; data and security are private.
for z, zn, kind, node, nn in ZN:
    A4.append(rec('ZONE-' + z, 'A4.NetworkZone', zn, 6, zone_level=2 if kind == 'private' else 1, zone_kind=kind))
    A4.append(rec(node, 'A4.Node', nn, 6, location='LOC-NZ', internet_facing=True if z == 'EDGE' else None))
    L4 += [link('ZONE-' + z, 'aggregation', node, 6), link('LOC-NZ', 'aggregation', node, 6), link('ENV-PROD', 'aggregation', node, 6)]
for i, n, d in [('SYS-DB', 'Managed database', 'A fictional PostgreSQL-compatible managed database with a synchronous local standby and a tested recovery procedure.'),
                ('SYS-MQ', 'Durable events', None), ('SYS-KMS', 'Managed key custody', None), ('SYS-OBS', 'Audit and metrics', None)]:
    A4.append(rec(i, 'A4.SystemSoftware', n, 6, d, location='LOC-NZ'))
A4 += [rec('PATH-EDGE', 'A4.Path', 'External boundary path', 6, 'HTTPS/TLS across the external boundary.', to='NODE-EDGE', protocol='https', encrypted=True, location='LOC-NZ'),
       rec('PATH-DATA', 'A4.Path', 'Application to database path', 6, 'Application-to-SQL traffic.', **{'from': 'NODE-APP'}, to='NODE-DATA', location='LOC-NZ'),
       rec('PATH-KEY', 'A4.Path', 'Secret retrieval path', 6, to='NODE-SEC', location='LOC-NZ'),
       rec('PATH-HANDOFF', 'A4.Path', 'Payment handoff path', 6, 'Mutually authenticated TLS for the payment handoff.', protocol='tls', encrypted=True, location='LOC-NZ')]
PLAT = {'DEP-EDGE': ('APP-EDGE', 'NODE-EDGE'), 'DEP-IDENT': ('APP-IDENT', 'NODE-SEC'), 'DEP-CONSENT': ('APP-CONSENT', None), 'DEP-PAYHUB': ('APP-PAYHUB', None),
        'DEP-RISK': ('APP-RISK', None), 'DEP-LEDGER': ('APP-LEDGER', 'NODE-INT'), 'DEP-NOTIFY': ('APP-NOTIFY', None), 'DEP-OUT': ('APP-OUTBOUND', 'NODE-INT')}
for dep, (comp, node) in PLAT.items():
    A4.append(rec(dep, 'A4.Deployment', f'{comp} — production', 6, component_id=comp, environment_id='ENV-PROD', platform_id=node, location='LOC-NZ'))
    L4.append(link('ENV-PROD', 'aggregation', dep, 6))

json.dump(cs('A1', A1, L1), open(OUT + '/v3-a1.json', 'w'), indent=1, ensure_ascii=False)
json.dump(cs('A3', A3, L3), open(OUT + '/v3-a3.json', 'w'), indent=1, ensure_ascii=False)
json.dump(cs('A4', A4, L4), open(OUT + '/v3-a4.json', 'w'), indent=1, ensure_ascii=False)
EV = ['design_document:design.md#2']
RQ = [{'id': 'REQ-PI-AVAIL-01', 'name': 'Payment API availability', 'statement': 'Payment API is available at least 99.95% monthly (fictional target; design.md R-13).', 'owner_layer': 'A1', 'category': 'availability',
       'scope': 'end_to_end', 'subject': 'SVC-INIT', 'derived_from': ['R-13'], 'condition': {'metric': 'availability_pct', 'operator': '>=', 'value': 99.95, 'unit': '%', 'period': 'month'}, 'evidence': EV},
      {'id': 'REQ-PI-PERF-01', 'name': 'Read response time', 'statement': 'Read p95 response latency at most 500 ms at 200 requests per second (fictional target; design.md R-14).', 'owner_layer': 'A1', 'category': 'performance',
       'scope': 'end_to_end', 'subject': 'PROC-STATUS', 'derived_from': ['R-14'], 'condition': {'metric': 'response_time_p95_ms', 'operator': '<=', 'value': 500, 'unit': 'ms'}, 'evidence': EV},
      {'id': 'REQ-PI-RTO-01', 'name': 'Payments platform recovery time', 'statement': 'Payments platform recovery time at most 30 minutes (fictional target; design.md R-15).', 'owner_layer': 'A1', 'category': 'recovery',
       'scope': 'end_to_end', 'subject': 'CAP-PAY', 'derived_from': ['R-15'], 'condition': {'metric': 'recovery_time_minutes', 'operator': '<=', 'value': 30, 'unit': 'min'}, 'evidence': EV},
      {'id': 'REQ-PI-RPO-01', 'name': 'Payments platform recovery point', 'statement': 'Payments platform recovery point at most 5 minutes (fictional target; design.md R-15).', 'owner_layer': 'A1', 'category': 'recovery',
       'scope': 'end_to_end', 'subject': 'CAP-PAY', 'derived_from': ['R-15'], 'condition': {'metric': 'recovery_point_minutes', 'operator': '<=', 'value': 5, 'unit': 'min'}, 'evidence': EV},
      {'id': 'REQ-PI-CONSENT-01', 'name': 'Unauthorised consent lifetime', 'statement': 'An unauthorised domestic payment consent is valid for 24 hours (design.md R-03, R-23).', 'owner_layer': 'A1', 'category': 'compliance',
       'scope': 'end_to_end', 'subject': 'PROC-CONSENT', 'derived_from': ['R-03', 'R-23'], 'condition': {'metric': 'unauthorised_consent_lifetime_hours', 'operator': '<=', 'value': 24, 'unit': 'h'}, 'evidence': EV}]
json.dump({'requirements': RQ}, open(OUT + '/v3-requirements.json', 'w'), indent=1, ensure_ascii=False)
print('A1', len(A1), 'records', len(L1), 'links | A3', len(A3), len(L3), '| A4', len(A4), len(L4), '| requirements', len(RQ))
