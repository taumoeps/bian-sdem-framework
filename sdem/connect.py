"""`sdem connect` — a person states a connection between layers that the engine did not propose
(docs/design/sdem-bian-update-and-connect-design.md, SC-*).

The record goes through the same approval as `sdem approve` (a person, the evidence its type requires, one of the nine
connection types, the BIAN release where needed); both ends must exist in the estate and the whole estate must pass
before anything is written. The record says it was stated by a person (`created_by: sdem connect`).

  sdem connect SD-PAYMENT-ORDER-INITIATION REALIZED_BY HIS-A3-PAYMENTS-HUB --estate estates/payments \\
       --reviewer jane.architect --evidence application_architecture_document:PAYHUB-HLD#s2 \\
       --rationale "The Payments Hub design names it as the payment-order initiation service"
"""
import argparse, json, sys
from pathlib import Path

from .approve import ApproveError, approve

DATASETS = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')


def estate_docs(estate):
    estate = Path(estate)
    docs = {f: json.loads((estate / f).read_text(encoding='utf-8')) for f in DATASETS if (estate / f).exists()}
    if not (estate / 'mappings.json').exists() or not docs:
        raise ValueError(f'{estate}: not an estate folder (it needs mappings.json and at least one of {", ".join(DATASETS)})')
    return docs, json.loads((estate / 'mappings.json').read_text(encoding='utf-8'))


def estate_errors(docs, registry):
    """Errors from checking a whole estate as it would be (datasets + registry)."""
    from .graph import FederatedGraph, LevelGraph
    from .metamodel import Metamodel
    mm = Metamodel.load()
    report = FederatedGraph([LevelGraph(d, mm) for d in docs.values()], [registry], mm).check()
    return [f'{k}: {i}' for k, v in report.items() for i in v]


def connect(estate, source, relationship, target, reviewer, evidence, rationale, bian_release=None, new_id=None, date=None):
    """Returns (new registry, the record); raises ApproveError when refused (SC-02…SC-04)."""
    docs, registry = estate_docs(estate)
    records = {i['id']: i for d in docs.values() for i in d.get('instances', [])}
    for end, rid in (('source', source), ('target', target)):
        if rid not in records: raise ApproveError(f'{end} {rid!r} is not a record in {estate} — check the id (`sdem query` or the dashboard lists them)')
    if not (rationale or '').strip(): raise ApproveError('--rationale is required: say in a sentence why this connection is true')

    def end(rid):
        i = records[rid]
        return {k: i[k] for k in ('id', 'type', 'version', 'canonical_id') if k in i}

    rel = relationship.strip().upper()
    stated = {'mapping_id': 'P-STATED-1', 'source': end(source), 'relationship': rel, 'target': end(target), 'status': 'proposed',
              'evidence': [], 'rationale': f'Stated by {reviewer.strip()} (not proposed by the engine): {rationale.strip()}',
              'baseline_id': 'PERSON-STATED', 'created_by': 'sdem connect'}
    new, recs = approve(registry, {'mappings': [stated]}, ['P-STATED-1'], reviewer, evidence, None, new_id, date, bian_release)
    errors = estate_errors(docs, new)
    if errors:
        raise ApproveError('the estate would not pass its checks with this connection — nothing was written:\n  ' + '\n  '.join(errors[:10]))
    return new, recs[0]


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem connect', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='A person states a connection between layers that the engine did not propose — with the same checks as '
                                             '`sdem approve`: a person, the evidence its type requires, one of the nine connection types, both ends in the estate. '
                                             'Final when its pull request is merged. Agents never run this.',
                                 epilog='Example:\n  sdem connect SD-PAYMENT-ORDER-INITIATION REALIZED_BY HIS-A3-PAYMENTS-HUB --estate estates/payments \\\n'
                                        '       --reviewer jane.architect --evidence application_architecture_document:PAYHUB-HLD#s2 \\\n'
                                        '       --rationale "The Payments Hub design names it as the payment-order initiation service"\n\n'
                                        'The nine connection types and the evidence each needs: the rulebook guide (docs/sdem-rulebook-guide.md).')
    ap.add_argument('source', help='the record the connection starts from, e.g. a BIAN service domain id')
    ap.add_argument('relationship', help='one of the nine connection types, e.g. REALIZED_BY, SUPPORTED_BY, DEPLOYED_ON')
    ap.add_argument('target', help='the record it goes to')
    ap.add_argument('--estate', required=True, metavar='DIR')
    ap.add_argument('--reviewer', '--person', dest='reviewer', required=True, help='your name — a person (CTL-21)')
    ap.add_argument('--evidence', action='append', default=[], metavar='KIND:REF', help='the document that proves it (repeatable; every kind the type needs)')
    ap.add_argument('--rationale', required=True, help='one sentence: why this connection is true')
    ap.add_argument('--bian-release', metavar='RELEASE', help='for a connection resting on BIAN guidance: the BIAN release (e.g. 14.0.0)')
    ap.add_argument('--id', dest='new_id', metavar='MAPPING_ID'); ap.add_argument('--date')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        new, r = connect(a.estate, a.source, a.relationship, a.target, a.reviewer, a.evidence, a.rationale, a.bian_release, a.new_id, a.date)
    except ApproveError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    if a.json: print(json.dumps(r, indent=2, ensure_ascii=False))
    else: print(f"{'would connect' if a.dry_run else 'connected'} {r['mapping_id']}: {r['source']['id']} -{r['relationship']}-> {r['target']['id']}  "
                f"(stated by {r['reviewer_id']}, {r['approved_at']}, evidence {'; '.join(r['evidence'])})")
    if a.dry_run: return 0
    from .files import write_json
    write_json(Path(a.estate) / 'mappings.json', new)
    if not a.json: print('mappings.json updated and checked. Next: commit on a branch and open a pull request; then rebuild the graph (sdem build --estate … --out …).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
