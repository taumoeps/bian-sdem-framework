"""AID carries the information model (metamodel 0.15.0; docs/design/sdem-full-design-metamodel-design.md IM-10).

AID-I01  For each A2 business object the workspace holds with typed field records (sdem bian import --objects, or written by a person)
         and no data entity mapped to it yet: an A3 data entity, marked inferred, with one A3 data attribute per field — its physical type
         from a fixed table (TYPES), required as the field is, the identifier as the primary key.
AID-I02  A field that refers to another business object becomes a foreign key to that object's data entity (inferred here, or already
         mapped) — an association, marked inferred.
AID-I03  The links between layers are proposed, never approved: MAPPED_TO (business object → data entity) and FIELD_MAPPED_TO (each
         BIAN attribute → its data attribute), confidence low — a person approves them with data_model evidence.
AID-I04  Only what a person wrote or confirmed is read (AID-W08); a rejected record is never inferred again.
"""
import re

TYPES = {'string': 'varchar(140)', 'text': 'text', 'integer': 'integer', 'decimal': 'numeric(18,6)', 'amount': 'numeric(18,2)',
         'currency_code': 'char(3)', 'date': 'date', 'datetime': 'timestamp', 'boolean': 'boolean', 'identifier': 'varchar(35)',
         'enum': 'varchar(35)', 'reference': 'varchar(35)'}   # SDEM's default physical type for each logical type — the architect changes it


def _snake(name):
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', str(name)).replace(' ', '_').replace('-', '_')
    return re.sub(r'_+', '_', s).strip('_').lower()


def _key(name):
    return re.sub(r'[^A-Z0-9]+', '-', str(name).upper()).strip('-')


def propose_information(a2, a3, mappings, mark, rejected=frozenset(), is_inferred=lambda r: False):
    """Returns (instances, relationships, links): new A3 records, A3 links, and (source, relationship, target, why) to propose.
    `mark(rule, reasoning, frm)` gives the `inferred` block every new record carries."""
    a2i = {i['id']: i for i in (a2 or {}).get('instances', []) if not is_inferred(i)}
    a3i = {i['id']: i for i in (a3 or {}).get('instances', [])}
    fields = {}
    for r in (a2 or {}).get('relationships', []):
        if r.get('kind') == 'composition' and r['source'] in a2i and a2i.get(r['target'], {}).get('type') == 'A2.BusinessObjectAttribute':
            fields.setdefault(r['source'], []).append(a2i[r['target']])
    refers = {r['source']: r['target'] for r in (a2 or {}).get('relationships', [])
              if r.get('kind') == 'association' and a2i.get(r['source'], {}).get('type') == 'A2.BusinessObjectAttribute'}
    mapped = {}
    for m in mappings:
        if m.get('relationship') == 'MAPPED_TO' and m.get('status') != 'rejected':
            mapped.setdefault(m['source']['id'], m['target']['id'])
    entity_of = dict(mapped)
    for bo, fs in fields.items():   # AID-I01: the entities first, so a foreign key can point at one inferred in the same run
        if bo in mapped or a2i[bo].get('type') != 'A2.BusinessObject': continue
        eid = f"AID-ENT-{_key(a2i[bo]['name'])}"
        if eid not in rejected: entity_of[bo] = eid
    inst, rels, links = [], [], []
    for bo, fs in sorted(fields.items()):
        if bo in mapped or bo not in entity_of: continue
        o, eid = a2i[bo], entity_of[bo]
        if eid not in a3i:
            names = [_snake(f['name']) for f in fs]
            inst.append({'id': eid, 'type': 'A3.DataEntity', 'version': '1', 'name': f"{_snake(o['name'])} (inferred)", 'lifecycle_status': 'planned',
                         'description': f"Inferred: the data entity that stores the business object {o['name']} ({bo}).",
                         'attributes': {'attributes': names, 'inferred': mark('AID-I01', f"one data entity per business object with typed fields — {o['name']} has {len(fs)}", bo)}})
            rels_from = []
            for f in fs:
                a = f.get('attributes') or {}
                fid = f"AID-ENTF-{_key(o['name'])}-{_key(f['name'])}"
                if fid in rejected or fid in a3i: continue
                lt = a.get('data_type') or 'string'
                fa = {'physical_type': TYPES.get(lt, 'varchar(140)'), 'required': bool(a.get('required'))}
                if a.get('identifier'): fa['primary_key'] = True
                if a.get('allowed_values'): fa['allowed_values'] = list(a['allowed_values'])
                if a.get('personal_information') is not None: fa['personal_information'] = a['personal_information']
                fa['inferred'] = mark('AID-I01', f"the field {f['name']} ({lt}) as {fa['physical_type']}" + (', the primary key' if fa.get('primary_key') else ''), f['id'])
                inst.append({'id': fid, 'type': 'A3.DataAttribute', 'version': '1', 'name': _snake(f['name']), 'lifecycle_status': 'planned', 'attributes': fa})
                rels.append({'source': eid, 'kind': 'composition', 'target': fid})
                target = entity_of.get(refers.get(f['id']))
                if target and target != eid:   # AID-I02: a reference becomes a foreign key
                    rels.append({'source': fid, 'kind': 'association', 'target': target})
                links.append((f['id'], 'FIELD_MAPPED_TO', fid, f"the data attribute {_snake(f['name'])} stores the BIAN attribute {f['name']} (AID-I03)"))
                rels_from.append(fid)
            links.insert(len(links) - len(rels_from), (bo, 'MAPPED_TO', eid, f"the data entity stores the business object {o['name']} (AID-I03)"))
    return inst, rels, links


def propose_access(docs, mappings, mm, mark):
    """AID-I07 (found in v2: inferred tables nobody used): a data entity no component accesses is accessed by the one component that realises
    the BIAN service domain whose control record is associated with the business object the entity stores. A link inside A3, marked inferred."""
    a2, a3 = docs.get('A2') or {}, docs.get('A3') or {}
    i3 = {i['id']: i for i in a3.get('instances', [])}
    accessed = {r['target'] for r in a3.get('relationships', []) if r.get('kind') == 'access'}
    live = [m for m in mappings if m.get('status') in ('approved', 'proposed')]
    stores = {}
    for m in live:
        if m['relationship'] == 'MAPPED_TO': stores.setdefault(m['target']['id'], set()).add(m['source']['id'])
    realised = {}
    for m in live:
        if m['relationship'] == 'REALIZED_BY' and mm.is_a(m['source'].get('type') or '', 'A2.ServiceDomain'):
            realised.setdefault(m['source']['id'], set()).add(m['target']['id'])
    cr_of = {}
    for r in a2.get('relationships', []):
        if r.get('kind') == 'association': cr_of.setdefault(r['target'], set()).add(r['source'])
    sd_of = {r['target']: r['source'] for r in a2.get('relationships', []) if r.get('kind') == 'aggregation'}
    out = []
    for e, rec in i3.items():
        if not mm.is_a(rec['type'], 'A3.DataEntity') or e in accessed: continue
        comps = {c for bo in stores.get(e, ()) for cr in cr_of.get(bo, ()) for c in realised.get(sd_of.get(cr), ())}
        if len(comps) == 1:
            c = next(iter(comps))
            out.append({'source': c, 'kind': 'access', 'target': e,
                        'inferred': mark('AID-I07', f'{e} stores a business object the control record of a domain {c} realises works on, and nothing accesses {e}', e)})
    return out
