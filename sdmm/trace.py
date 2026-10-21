"""SDMM traceability: walk approved cross-layer mappings downstream (L0 -> L3) or upstream (L3 -> L0).

Edges are stored once, in their registry direction. Upstream traversal walks them backwards;
no inverse edges exist. Every reported hop carries the mapping_id that justifies it, so a
level-skipping answer (L0 -> L3) is always a derived path with provenance, never a stored record.
"""
from pathlib import Path
import argparse, json, sys

EXIT_OK, EXIT_NOT_FOUND, EXIT_USAGE = 0, 1, 2
DEFAULT_STATUSES = ('approved',)


def load_edges(payloads, statuses=DEFAULT_STATUSES):
    """Flatten mapping documents into edge dicts, keeping only the given statuses."""
    edges = []
    for payload in payloads:
        for m in (payload.get('mappings') or []) if isinstance(payload, dict) else []:
            if not isinstance(m, dict) or m.get('status') not in statuses:
                continue
            s, t = m.get('source') or {}, m.get('target') or {}
            if not (s.get('id') and t.get('id')):
                continue
            edges.append({'mapping_id': m.get('mapping_id'), 'relationship': m.get('relationship'),
                          'status': m.get('status'), 'baseline_id': m.get('baseline_id'),
                          'source': {'id': s['id'], 'type': s.get('type'), 'version': s.get('version')},
                          'target': {'id': t['id'], 'type': t.get('type'), 'version': t.get('version')}})
    return edges


def known_entities(edges):
    ents = {}
    for e in edges:
        for end in ('source', 'target'):
            ents.setdefault(e[end]['id'], e[end])
    return ents


def walk(edges, start, direction='down'):
    """Return a tree: {'id', 'type', 'children': [{'via': edge, 'node': subtree}, ...]}.

    Cycles are cut at the first repeat along a path; a node may legitimately appear on several branches.
    """
    ents = known_entities(edges)
    forward = direction == 'down'
    def node(eid, seen):
        here = {'id': eid, 'type': (ents.get(eid) or {}).get('type'), 'children': []}
        for e in edges:
            a, b = (e['source'], e['target']) if forward else (e['target'], e['source'])
            if a['id'] == eid and b['id'] not in seen:
                here['children'].append({'via': e, 'node': node(b['id'], seen | {b['id']})})
        return here
    return node(start, {start})


def paths(tree):
    """All root-to-leaf paths as lists of (entity_id, via_edge) with via=None for the root."""
    out = []
    def rec(n, acc):
        if not n['children']:
            out.append(acc)
        for c in n['children']:
            rec(c['node'], acc + [(c['node']['id'], c['via'])])
    rec(tree, [(tree['id'], None)])
    return out


def render(tree, direction):
    arrow = '-' if direction == 'down' else '<-'
    lines = [f"{tree['id']}  [{tree['type'] or '?'}]"]
    def rec(n, prefix):
        for i, c in enumerate(n['children']):
            last = i == len(n['children']) - 1
            e = c['via']
            tag = f"{arrow}{e['relationship']}{'->' if direction == 'down' else '-'}"
            lines.append(f"{prefix}{'└─ ' if last else '├─ '}{tag} {c['node']['id']}  [{c['node']['type'] or '?'}]  ({e['mapping_id']})")
            rec(c['node'], prefix + ('   ' if last else '│  '))
    rec(tree, '')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-trace', description='Trace approved SDMM mappings up or down the L0-L3 chain.')
    parser.add_argument('entity', help='entity id to start from, e.g. CAP-310 or INF-CLOUD-K8S-PROD')
    parser.add_argument('paths', nargs='+', help='mapping JSON file(s)')
    parser.add_argument('--direction', choices=['down', 'up', 'both'], default='both',
                        help='down = what this depends on (toward L3); up = what depends on this (toward L0)')
    parser.add_argument('--status', default=','.join(DEFAULT_STATUSES),
                        help='comma-separated statuses to include (default: approved)')
    parser.add_argument('--json', action='store_true', help='emit trees and derived paths as JSON')
    args = parser.parse_args(argv)
    try:
        payloads = [json.loads(Path(p).read_text(encoding='utf-8')) for p in args.paths]
    except (OSError, ValueError) as exc:
        print(f'ERROR: cannot read inputs: {exc}', file=sys.stderr)
        return EXIT_USAGE
    edges = load_edges(payloads, tuple(s.strip() for s in args.status.split(',') if s.strip()))
    if args.entity not in known_entities(edges):
        print(f'ERROR: {args.entity!r} does not appear in any {args.status} mapping', file=sys.stderr)
        return EXIT_NOT_FOUND
    directions = ['down', 'up'] if args.direction == 'both' else [args.direction]
    result = {d: walk(edges, args.entity, d) for d in directions}
    if args.json:
        out = {'entity': args.entity, 'statuses': args.status.split(','), 'edges_considered': len(edges)}
        for d, tree in result.items():
            out[d] = {'tree': tree, 'paths': [[{'id': i, 'via': (v or {}).get('mapping_id')} for i, v in p] for p in paths(tree)]}
        print(json.dumps(out, indent=2))
    else:
        for d, tree in result.items():
            title = 'DOWNSTREAM (depends on)' if d == 'down' else 'UPSTREAM (depended on by)'
            print(f'{title}:')
            print(render(tree, d) if tree['children'] else f"{tree['id']}  (no {d}stream mappings)")
            print()
    return EXIT_OK


if __name__ == '__main__':
    raise SystemExit(main())
