"""Architecture Relationship Inference Engine: the interface and a baseline, for the rule-based engine (v0.9) to plug into.

An engine reads a FederatedGraph and returns *proposed* mapping records. It never writes approved
records; everything it returns goes through sdem-validate and an architect. The baseline here exists
to exercise the evaluation harness; it is not the rule-based engine specified in docs/relationship-rules-spec.md.
"""
from pathlib import Path
import argparse, json, re, sys
from typing import Protocol
from sdem.graph import FederatedGraph
from sdem.validate import load_registry

STOP = {'the', 'and', 'of', 'for', 'a', 'an', 'to', 'in', 'on', 'synthetic', 'selection', 'stand', 'bian'}


class RelationshipInferenceEngine(Protocol):
    name: str
    def propose(self, graph: FederatedGraph) -> list: ...


def proposal(mapping_id, src, rel, tgt, confidence, rationale, engine, baseline_id='ENGINE-RUN'):
    """Shape every engine output the same way: a valid record with status proposed."""
    def ref(i):
        r = {'id': i['id'], 'type': i['type'], 'version': i['version']}
        if i.get('canonical_id'): r['canonical_id'] = i['canonical_id']   # carried from the level export, never invented
        return r
    return {'mapping_id': mapping_id, 'source': ref(src), 'relationship': rel, 'target': ref(tgt),
            'status': 'proposed', 'confidence': round(confidence, 2),
            'evidence': [f'engine_rationale:{rationale}'],
            'rationale': rationale, 'baseline_id': baseline_id, 'created_by': engine}


def _words(*texts):
    return {w for t in texts if t for w in re.findall(r'[a-z]+', t.lower()) if len(w) > 2 and w not in STOP}


# Deprecated name, kept for one release (SDMM → SDEM, v0.7.0).
MappingEngine = RelationshipInferenceEngine


class NameOverlapBaseline:
    """Proposes an arrow for every registry rule where the two instances' names/descriptions share enough words
    (overlap coefficient = shared / smaller vocabulary).

    Deterministic, explainable, and deliberately naive: it is the floor an engine must beat.
    """
    name = 'baseline-name-overlap/0.5'

    def __init__(self, threshold=0.2):
        self.threshold = threshold

    def propose(self, graph):
        registry = load_registry()
        mm = graph.mm
        out, n = [], 0
        instances = [i for g in graph.levels.values() for i in g.doc.get('instances', [])]
        for rule in registry['relationships']:
            srcs = [i for i in instances if mm.is_a(i['type'], rule['source_type'])]
            tgts = [i for i in instances if mm.is_a(i['type'], rule['target_type'])]
            for s in srcs:
                ws = _words(s['name'], s.get('description'))
                for t in tgts:
                    wt = _words(t['name'], t.get('description'))
                    if not ws or not wt:
                        continue
                    shared = ws & wt
                    score = len(shared) / min(len(ws), len(wt))   # overlap coefficient
                    if score >= self.threshold:
                        n += 1
                        out.append(proposal(f'PROP-{n:04d}', s, rule['relationship'], t, min(0.95, 0.4 + score),
                                            f"shared terms {sorted(shared)} between '{s['name']}' and '{t['name']}'", self.name))
        return out


ENGINES = {'baseline': NameOverlapBaseline}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdem-infer', description='Run a mapping engine over level exports and emit a document of proposed mappings.')
    parser.add_argument('engine', choices=sorted(ENGINES))
    parser.add_argument('paths', nargs='+', help='level exports (and optionally existing mapping documents)')
    parser.add_argument('--threshold', type=float, default=0.2)
    args = parser.parse_args(argv)
    try:
        graph = FederatedGraph.load(args.paths)
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 2
    engine = ENGINES[args.engine](args.threshold) if args.engine == 'baseline' else ENGINES[args.engine]()
    props = engine.propose(graph)
    print(json.dumps({'registry_version': load_registry()['$schema_version'], 'metamodel_version': graph.mm.version,
                      'engine': engine.name, 'mappings': props}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
