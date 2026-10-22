"""Evaluation harness: score an engine's proposed mappings against approved ones.

Gold = approved records in the gold documents. Proposals = proposed records in the proposal documents.
A proposal is a hit when (source.id, relationship, target.id) matches a gold record. Reported per
relationship type and overall. This is the acceptance test for any mapping engine.
"""
from pathlib import Path
import argparse, json, sys


def key(m):
    return (m['source']['id'], m['relationship'], m['target']['id'])


def evaluate(gold_docs, proposal_docs):
    gold = {key(m): m for d in gold_docs for m in d.get('mappings', []) if m.get('status') == 'approved'}
    props = {key(m): m for d in proposal_docs for m in d.get('mappings', []) if m.get('status') == 'proposed'}
    rels = sorted({k[1] for k in gold} | {k[1] for k in props})
    def score(g, p):
        tp = len(g & p); fp = len(p - g); fn = len(g - p)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        return {'gold': len(g), 'proposed': len(p), 'tp': tp, 'fp': fp, 'fn': fn,
                'precision': round(prec, 3), 'recall': round(rec, 3), 'f1': round(f1, 3)}
    by_rel = {r: score({k for k in gold if k[1] == r}, {k for k in props if k[1] == r}) for r in rels}
    overall = score(set(gold), set(props))
    return {'overall': overall, 'by_relationship': by_rel,
            'missed': [list(k) for k in sorted(set(gold) - set(props))],
            'false_proposals': [{'key': list(k), 'confidence': props[k].get('confidence'), 'rationale': props[k].get('rationale')} for k in sorted(set(props) - set(gold))]}


def render(result):
    lines = [f"{'relationship':<16} {'gold':>4} {'prop':>4} {'tp':>3} {'fp':>3} {'fn':>3}  {'prec':>5} {'rec':>5} {'f1':>5}"]
    for r, s in list(result['by_relationship'].items()) + [('OVERALL', result['overall'])]:
        lines.append(f"{r:<16} {s['gold']:>4} {s['proposed']:>4} {s['tp']:>3} {s['fp']:>3} {s['fn']:>3}  {s['precision']:>5.2f} {s['recall']:>5.2f} {s['f1']:>5.2f}")
    if result['missed']:
        lines.append('\nmissed (approved, not proposed):'); lines += [f"  {s} -{r}-> {t}" for s, r, t in result['missed']]
    if result['false_proposals']:
        lines.append('\nfalse proposals (proposed, not approved):'); lines += [f"  {fp['key'][0]} -{fp['key'][1]}-> {fp['key'][2]}  conf={fp['confidence']}  {fp['rationale']}" for fp in result['false_proposals']]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-eval', description='Score proposed mappings against approved ones.')
    parser.add_argument('gold', nargs='+', help='mapping document(s) whose approved records are the gold set')
    parser.add_argument('--proposals', nargs='+', required=True, help='document(s) of proposed records to score')
    parser.add_argument('--min-f1', type=float, help='exit 1 if overall F1 is below this')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        gold = [json.loads(Path(p).read_text(encoding='utf-8')) for p in args.gold]
        props = [json.loads(Path(p).read_text(encoding='utf-8')) for p in args.proposals]
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 2
    result = evaluate(gold, props)
    print(json.dumps(result, indent=2) if args.json else render(result))
    if args.min_f1 is not None and result['overall']['f1'] < args.min_f1:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
