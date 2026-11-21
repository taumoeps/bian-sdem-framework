"""The 16 things design.md does not say, decided by the AI as a designer would — each one recorded as an AI decision with its reasoning,
kept apart from what the document states or implies. No sdem aid."""
import json, sys
P = sys.argv[1].rstrip('/') + '/'
L = lambda f: json.load(open(P + f, encoding='utf-8'))
def S(f, d): json.dump(d, open(P + f, 'w', encoding='utf-8'), indent=1)
a1, a4, bian, sug = L('a1-business.json'), L('a4-technology.json'), L('BIAN-DOMAINS.json'), L('CROSS-LAYER-SUGGESTIONS.json')
D = []
def link(doc, s, k, t, why): doc['relationships'].append({'source': s, 'kind': k, 'target': t, 'source_id': 'ai-decision'}); D.append({'what': f'{s} {k} {t}', 'why': why})
def x(s, r, t, why): sug['suggestions'].append({'source': s, 'link_type': r, 'target': t, 'design_section': 'ai-decision', 'basis': 'decision', 'reason': why}); D.append({'what': f'{s} {r} {t}', 'why': why})
for r, src, why in (
    ('R-13', 'SVC-INIT', 'availability of the payment API is a property of the initiation service the bank offers'),
    ('R-14', 'PROC-STATUS', 'the read latency target applies to the status reads'),
    ('R-15', 'SVC-INIT', 'recovery time and point are targets of the service as a whole'),
    ('R-16', 'PROC-AUTH', 'authorisation is what scopes access to consent and payment resources'),
    ('R-17', 'PROC-RISK', 'the risk decision is the decision that must be correlated and auditable; consent decisions are recorded with it'),
    ('R-18', 'SVC-INIT', 'one API version across consent and payment is a property of the service'),
    ('R-20', 'CAP-RISK', 'segment boundaries, private persistence routes and managed secrets are controls of the payment risk capability'),
    ('R-22', 'SVC-INIT', 'throttling and participant identification apply to every call on the service'),
    ('R-24', 'PROC-STATUS', 'the debtor-account read is one of the reads the status process answers')):
    link(a1, src, 'realization', r, why)
link(a1, 'PROD-ACCOUNT', 'aggregation', 'SVC-INIT', 'the document names the retail account product and the initiation service the bank offers side by side, without saying one includes the other; payment initiation is offered on the account')
link(a1, 'SVC-INIT', 'serving', 'ACTOR-MERCHANT', "the merchant's checkout payment is what the initiation service exists for")
link(a4, 'NODE-APP', 'assignment', 'SYS-MQ', 'durable events are produced and consumed by the applications on the application compute')
link(a4, 'NODE-SEC', 'assignment', 'SYS-OBS', 'audit evidence is kept apart from the applications, with identity and secrets')
x('DATA-AUDIT', 'STORED_IN', 'SYS-OBS', 'the security event log is audit data; SYS-OBS is the audit/metrics platform')
bian['service_domains'].append({'name': 'Fraud Evaluation', 'source': 'ai-decision'})
D.append({'what': 'BIAN Fraud Evaluation', 'why': 'the design screens each payment for fraud before the debit (PROC-RISK, APP-RISK); Fraud Evaluation is the BIAN service domain for that'})
x('PROC-RISK', 'USES_DOMAIN', 'Fraud Evaluation', 'fraud screening evaluates the payment for fraud')
x('Fraud Evaluation', 'REALIZED_BY', 'APP-RISK', 'APP-RISK returns the risk decision')
next(i for i in a4['instances'] if i['id'] == 'SYS-KMS')['attributes']['conforms_to'] = ['PAT-PAYMENT-INITIATION#key-store']
D.append({'what': 'SYS-KMS is the key store of the payment initiation pattern', 'why': 'the document calls SYS-KMS "managed key custody"; AD-06 says independent key custody'})
S('a1-business.json', a1); S('a4-technology.json', a4); S('BIAN-DOMAINS.json', bian); S('CROSS-LAYER-SUGGESTIONS.json', sug); S('NOT-STATED.json', {'items': []})
json.dump(D, open(P + '../decided-by-ai.json', 'w', encoding='utf-8'), indent=1); print(len(D), 'decisions')
