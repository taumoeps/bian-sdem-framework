"""SDEM entity metamodel: the A1-A4 entity catalogue, its hierarchy, and within-level relationship rules.

The catalogue is the public vocabulary (metamodel/*.json). It holds no institutional content.
"""
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
from pathlib import Path
import json

from sdem.paths import DATA_ROOT as ROOT  # repository folders, or bundled copies when installed
MM_DIR = ROOT / 'metamodel'
LEVEL_FILES = ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json']


PROJECTED_PREFIXES = ('PRJ-', 'DSN-')  # AID projections and target designs (CTL-16)


def is_projection_dataset(doc):
    """A dataset that declares itself a target design or an AID projection — never real architecture data."""
    return str(doc.get('source_system', '')).startswith(('DESIGN-PROPOSAL', 'AID-PROJECTION')) or str(doc.get('model_id', '')).endswith(('-TARGET-DESIGN', '-PROJECTION'))


class Metamodel:
    def __init__(self, entities, relationships, version):
        self.entities = {e['type']: e for e in entities}
        self.relationships = relationships
        self.version = version

    @classmethod
    def load(cls, mm_dir=MM_DIR):
        """SDEM's metamodel — with the active organisation profile applied, when a workspace has one (sdem/profile.py)."""
        base = cls.base(mm_dir)
        from . import profile as _p
        if _p.ACTIVE is None or mm_dir != MM_DIR: return base
        cache = getattr(cls, '_merged_cache', None)
        if cache is None: cache = {}; setattr(cls, '_merged_cache', cache)
        from . import parts
        key = (_p.digest(_p.ACTIVE), parts.bian_on(), parts.migrated())   # DL-12: the workspace's form decides the layers too
        if key not in cache:
            cache.clear(); cache[key] = _p.apply(base, _p.ACTIVE)
            cache[key].trace = {'rules': base.trace['rules'] + list(_p.ACTIVE.get('trace_rules') or []),   # MID-08: an extension's pack declares its own
                                'information': base.trace['information'] + list(_p.ACTIVE.get('information_types') or [])}
        return cache[key]

    @classmethod
    def base(cls, mm_dir=MM_DIR):
        """SDEM's own metamodel, as shipped — no profile."""
        from . import parts
        ents, versions, trace = [], set(), {'rules': [], 'information': []}
        for name in LEVEL_FILES:
            doc = _jload(Path(mm_dir) / name)
            versions.add(doc['metamodel_version'])
            if name == parts.A2_FILE and not parts.bian_on(): continue   # BX-02, BX-13: BIAN's types belong to ext:bian
            t = doc.get('trace') or {}
            if name == parts.A2_FILE: doc = parts.metamodel_doc(doc); t = doc.get('trace') or t   # BP-02: the installed sdem-bian's, if any (its own trace, else the shipped one)
            ents += doc['entities']   # MID-08: how the trace walks this layer's own links — declared by the layer, not written into the trace
            trace['rules'] += t.get('rules') or []; trace['information'] += t.get('information') or []
        rels = _jload(Path(mm_dir) / 'level-relationships.json')
        versions.add(rels['metamodel_version'])
        rels = {**rels, 'constraints': parts.splice(rels.get('constraints', []), parts.bian_constraint, lambda c: c.get('id'), 'within')}   # BP-02
        if not parts.bian_on():   # its within-layer rules too
            rels = {**rels, 'constraints': [c for c in rels.get('constraints', []) if c.get('level') != parts.a2_code() and not parts.a2(c.get('source_type')) and not parts.a2(c.get('target_type'))]}
        if len(versions) != 1:
            raise ValueError(f'metamodel files disagree on metamodel_version: {sorted(versions)}')
        from .identity import layer_of_type   # DL-02: a type's layer is its id's — Data's types in Data where it is in use
        ents = [{**e, 'level': layer_of_type(e['type']) or e['level']} for e in ents]
        cons = []
        for c in rels.get('constraints', []):
            ls, lt = layer_of_type(c.get('source_type')), layer_of_type(c.get('target_type'))
            if ls and lt and ls != lt: continue   # DL-04: its ends are in two layers now — a link between them (ACCESSED_BY, Data → Application), not a rule inside one
            cons.append({**c, 'level': ls} if ls else c)
        rels = {**rels, 'constraints': cons}
        m = cls(ents, rels, versions.pop()); m.trace = trace
        return m

    # ---- hierarchy
    def known(self, t):
        return t in self.entities

    def ancestors(self, t):
        out, cur = [], self.entities.get(t)
        while cur and cur.get('extends'):
            out.append(cur['extends']); cur = self.entities.get(cur['extends'])
        return out

    def is_a(self, t, ancestor):
        if t == ancestor: return True
        cache = self.__dict__.setdefault('_is_a', {})   # the catalogue does not change once loaded
        k = (t, ancestor)
        if k not in cache: cache[k] = ancestor in self.ancestors(t)
        return cache[k]

    def level(self, t):
        e = self.entities.get(t)
        return e['level'] if e else None

    def is_abstract(self, t):
        return bool(self.entities.get(t, {}).get('abstract'))

    def is_artefact(self, t):
        return bool(self.entities.get(t, {}).get('artefact'))

    # ---- within-level relationship rules
    def relationship_issue(self, level, source_type, kind, target_type):
        """Return an issue string if a within-level relationship is not permitted, else None."""
        kinds = {k['kind'] for k in self.relationships['kinds']}
        if kind not in kinds:
            return f'relationship kind {kind!r} is not catalogued'
        for t in (source_type, target_type):
            if not self.known(t):
                return f'entity {t!r} is not in the metamodel'
            if self.level(t) != level:
                return f'entity {t!r} is not an {level} entity'
        if kind == 'association':
            return None  # ArchiMate's generic relationship: permitted between any two entities of one level
        ok = any(c['level'] == level and self.is_a(source_type, c['source_type']) and c['kind'] == kind and self.is_a(target_type, c['target_type'])
                 for c in self.relationships['constraints'])
        if not ok:
            basis = 'BIAN structure' if level == _L('bian') else 'ArchiMate 3.2 / TOGAF'
            return f'{level} relationship {source_type} -{kind}-> {target_type} does not match the {basis} constraints (metamodel/level-relationships.json)'
        return None

    # ---- self-check
    def validate(self):
        issues = []
        for t, e in self.entities.items():
            if e['level'] != (t.split('.')[1] if t.count('.') == 2 else t.split('.')[0]):   # ORG.<layer>.Name for a profile type
                issues.append(f'{t}: level {e["level"]} does not match prefix')
            p = e.get('extends')
            if p is not None:
                if p not in self.entities:
                    issues.append(f'{t}: extends unknown entity {p!r}')
                elif self.entities[p]['level'] != e['level']:
                    issues.append(f'{t}: extends {p!r} from a different level')
            if e.get('artefact') and e.get('abstract'):
                issues.append(f'{t}: an artefact cannot be abstract')
            if e['definition_source'] == 'bian_reference' and e['evidence_status'] == 'confirmed_in_official_source':
                issues.append(f'{t}: bian_reference entities may only be confirmed through the verification register')
            seen, cur = {t}, p
            while cur:
                if cur in seen:
                    issues.append(f'{t}: extends cycle through {cur!r}'); break
                seen.add(cur); cur = self.entities.get(cur, {}).get('extends')
        for c in self.relationships['constraints']:
            for key in ('source_type', 'target_type'):
                if c[key] not in self.entities:
                    issues.append(f'constraint {c}: unknown entity {c[key]!r}')
        return issues
