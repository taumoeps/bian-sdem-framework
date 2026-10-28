"""`sdem bian` — the BIAN (A2) layer from BIAN's public Semantic APIs (docs/design/sdem-bian-import-design.md, -spec.md).

BIAN publishes one OpenAPI file per service domain (github.com/bian-official/public, Apache-2.0). `sdem bian list` shows
what a downloaded release holds; `sdem bian import` turns the service domains you choose into an A2 dataset — service
domain, operations with their input and output fields, control record, behaviour qualifiers, the service groups that
hold the operations, and the asset type and functional pattern the rulebook requires — checked before it is written.

  sdem bian list --base                       # the base BIAN that ships with SDEM (BIAN's Semantic APIs 14.0.0)
  sdem bian import --base --only "Payment Order Initiation" -o work/bian/a2-service-domain.json
  sdem bian pack ~/acme-bian -o bian/acme-bian.json      # your own BIAN, packed the same way; then --base bian/acme-bian.json

Offline: it reads the base, a pack, or a folder you downloaded. BIAN's descriptions are left out unless you ask
(--descriptions, from BIAN's files). Base BIAN: docs/design/sdem-bian-base-design.md.
"""
import argparse, csv, difflib, json, re, sys
from collections import Counter
from pathlib import Path

# BIAN Semantic API Practitioner Guide v8.1 ([SAPG]) §3.2.1, Figure 9: each functional pattern's generic artifact.
# A control record is named asset type + generic artifact (e.g. PaymentOrderInitiation + Transaction), so the artifact
# at the end of its name gives the domain's functional pattern (BI-W02).
PATTERNS = {'DIRECT': 'Strategy', 'MANAGE': 'Management Plan', 'ADMINISTER': 'Administrative Plan', 'DESIGN': 'Specification',
            'DEVELOP': 'Development', 'PROCESS': 'Procedure', 'OPERATE': 'Operating Session', 'MAINTAIN': 'Maintenance Arrangement',
            'FULFILL': 'Arrangement', 'TRANSACT': 'Transaction', 'ADVISE': 'Advice', 'MONITOR': 'State', 'TRACK': 'Log Record',
            'CATALOG': 'Directory Entry', 'ENROLL': 'Membership', 'AGREE TERMS': 'Agreement', 'ASSESS': 'Assessment',
            'ANALYSE': 'Analysis', 'ALLOCATE': 'Allocation'}
_BY_ARTIFACT = sorted(((a.replace(' ', ''), p) for p, a in PATTERNS.items()), key=lambda ap: -len(ap[0]))
PATTERN_SOURCE = 'BIAN Semantic API Practitioner Guide v8.1 §3.2.1, Figure 9'
METHODS = ('get', 'put', 'post', 'patch', 'delete')


PACK_FORMAT = 'sdem-bian-pack/1'


class BianError(ValueError):
    """The input cannot be read or the request is wrong (exit 2)."""


# ---------------------------------------------------------------- reading BIAN's files (BI-C04, BI-C05)
def _scalar(v, where):
    v = v.strip()
    if v in ('', '~', 'null'): return None
    if v in ('{}', '{ }'): return {}
    if v in ('[]', '[ ]'): return []
    if v[0] in '[{|>&*!%@`':
        raise BianError(f'{where}: a YAML form SDEM does not read ({v[:30]!r}) — is this a BIAN Semantic API file?')
    if v[0] == "'":
        if len(v) < 2 or not v.endswith("'"): raise BianError(f'{where}: unclosed quote')
        return v[1:-1].replace("''", "'")
    if v[0] == '"':
        try: return json.loads(v)
        except ValueError: raise BianError(f'{where}: a quoted value SDEM cannot read')
    return re.sub(r'\s+#.*$', '', v)


_KEY = re.compile(r"""^('(?:[^']|'')*'|"(?:[^"\\]|\\.)*"|[^'"\s\-?](?:[^:]|:(?!\s|$))*?|-[^\s](?:[^:]|:(?!\s|$))*?):(?:\s+(.*))?$""")


def read_yaml(text, name):
    """The block-style YAML that BIAN's OpenAPI files use: mappings, lists, quoted and plain values, empty {} and [].
    Anything else is refused — never guessed (BI-C05)."""
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.rstrip()
        if not s.strip() or s.lstrip().startswith('#') or s.strip() in ('---', '...'): continue
        lead = s[:len(s) - len(s.lstrip())]
        if '\t' in lead: raise BianError(f'{name}:{n}: tab indentation')
        lines.append([len(lead), s.strip(), n])
    pos = 0

    def where(): return f'{name}:{lines[pos][2]}' if pos < len(lines) else name

    def key_value(body, n):
        m = _KEY.match(body)
        if not m: raise BianError(f'{name}:{n}: not a "key: value" line ({body[:40]!r})')
        k = m.group(1)
        return (_scalar(k, f'{name}:{n}') if k[0] in '\'"' else k), (m.group(2) or '')

    def node(ind):
        return seq(ind) if lines[pos][1] == '-' or lines[pos][1].startswith('- ') else mapping(ind)

    def mapping(ind):
        nonlocal pos
        out = {}
        while pos < len(lines) and lines[pos][0] == ind and not (lines[pos][1] == '-' or lines[pos][1].startswith('- ')):
            _, body, n = lines[pos]
            if body.startswith('? '):                     # a complex key: "? key" then ": value" (BIAN 10.0 writes long paths so)
                k = _scalar(body[2:], f'{name}:{n}'); pos += 1
                if pos >= len(lines) or lines[pos][0] != ind or not lines[pos][1].startswith(': '):
                    raise BianError(f'{name}:{n}: "? key" without its ": value" line')
                lines[pos] = [ind + 2, lines[pos][1][2:].strip(), lines[pos][2]]
                out[k] = node(ind + 2) if _KEY.match(lines[pos][1]) or lines[pos][1].startswith('- ') else _scalar(lines[pos][1], where())
                if not isinstance(out[k], (dict, list)): pos += 1
                continue
            k, v = key_value(body, n); pos += 1
            if v.strip():
                out[k] = _scalar(v, f'{name}:{n}')
            elif pos < len(lines) and (lines[pos][0] > ind or (lines[pos][0] == ind and lines[pos][1].startswith('- '))):
                out[k] = node(lines[pos][0])
            else:
                out[k] = None
        if pos < len(lines) and lines[pos][0] > ind: raise BianError(f'{where()}: unexpected indentation')
        return out

    def seq(ind):
        nonlocal pos
        out = []
        while pos < len(lines) and lines[pos][0] == ind and (lines[pos][1] == '-' or lines[pos][1].startswith('- ')):
            _, body, n = lines[pos]
            item = body[1:].strip()
            if not item:
                pos += 1
                if pos >= len(lines) or lines[pos][0] <= ind: raise BianError(f'{name}:{n}: empty list item')
                out.append(node(lines[pos][0]))
            elif _KEY.match(item) and not item.startswith(("'", '"')) or (item[0] in '\'"' and _KEY.match(item)):
                lines[pos] = [ind + 2, item, n]           # "- key: value" starts a mapping one level in
                out.append(mapping(ind + 2))
            else:
                out.append(_scalar(item, f'{name}:{n}')); pos += 1
        return out

    if not lines: raise BianError(f'{name}: empty file')
    doc = node(lines[0][0])
    if pos != len(lines): raise BianError(f'{where()}: could not read the rest of the file')
    return doc


def _ref(doc, ref, kinds):
    m = re.match(r'#/components/(\w+)/(.+)$', ref or '')
    if not m or m.group(1) not in kinds: return None, None
    return m.group(2), ((doc.get('components') or {}).get(m.group(1)) or {}).get(m.group(2))


def _schema_of(doc, holder):
    """The schema name behind a requestBody or response (followed through $ref), or None."""
    if not isinstance(holder, dict): return None
    if '$ref' in holder:
        _, holder = _ref(doc, holder['$ref'], ('requestBodies', 'responses'))
        if not isinstance(holder, dict): return None
    schema = (((holder.get('content') or {}).get('application/json') or {}).get('schema')) or {}
    name, _ = _ref(doc, schema.get('$ref'), ('schemas',))
    return name


def _props(doc, schema_name):
    s = (((doc.get('components') or {}).get('schemas')) or {}).get(schema_name) or {}
    return list((s.get('properties') or {}).keys())


def _words(camel):
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', camel).strip()


def _key(name):
    return re.sub(r'[^A-Z0-9]+', '-', _words(name).upper()).strip('-')


def read_domain(path):
    """One BIAN service-domain file → its facts (BI-C04: OpenAPI 3, releases 10.0 and later)."""
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.json':
        try: doc = json.loads(text)
        except ValueError: raise BianError(f'{path.name}: not valid JSON')
    else:
        doc = read_yaml(text, path.name)
    if not isinstance(doc, dict) or 'openapi' not in doc:
        if isinstance(doc, dict) and 'swagger' in doc:
            raise BianError(f'{path.name}: a Swagger 2 file (BIAN release 9.1 or earlier) — use BIAN release 10.0.0 or later')
        raise BianError(f'{path.name}: not an OpenAPI file')
    info = doc.get('info') or {}
    if not info.get('title'): raise BianError(f'{path.name}: no info.title — not a BIAN service-domain file')
    ops, cr, bqs = [], None, []
    for p, item in (doc.get('paths') or {}).items():
        for method in METHODS:
            op = (item or {}).get(method)
            if not isinstance(op, dict) or not op.get('operationId'): continue
            tags = [t for t in (op.get('tags') or []) if isinstance(t, str)]
            kind = next((t.split(' - ', 1) for t in tags if t.startswith(('CR - ', 'BQ - '))), [None, None])
            if kind[0] == 'CR': cr = cr or kind[1].strip()
            if kind[0] == 'BQ' and kind[1].strip() not in bqs: bqs.append(kind[1].strip())
            ops.append({'path': p, 'method': method.upper(), 'operation_id': op['operationId'], 'group': kind[1].strip() if kind[1] else None,
                        'qualifier': kind[1].strip() if kind[0] == 'BQ' else None,
                        'inputs': _props(doc, _schema_of(doc, op.get('requestBody'))),
                        'outputs': _props(doc, _schema_of(doc, (op.get('responses') or {}).get('200')))})
    schemas = ((doc.get('components') or {}).get('schemas')) or {}
    return {'file': path.name, 'name': str(info['title']).strip(), 'release': str(info.get('version') or '').strip(),
            'description': info.get('description'), 'operations': ops, 'control_record': cr, 'qualifiers': bqs,
            'control_record_fields': _props(doc, cr) if cr else [],
            'objects': {n: list((s.get('properties') or {}).keys()) for n, s in schemas.items()
                        if isinstance(s, dict) and s.get('properties') and n != 'HTTPError'}}


def read_release(folder):
    """Every service-domain file in a release folder (searched below it). Returns (domains, refused)."""
    folder = Path(folder)
    if not folder.is_dir(): raise BianError(f'{folder}: no such folder')
    files = sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.yaml', '.yml', '.json') and 'asyncapi' not in str(p).lower())
    if not files: raise BianError(f'{folder}: no BIAN service-domain files (.yaml) found')
    domains, refused = [], []
    for f in files:
        try: domains.append(read_domain(f))
        except BianError as e: refused.append(str(e))
    if not domains: raise BianError(f'{folder}: no file could be read — ' + '; '.join(refused[:3]))
    return domains, refused


# ---------------------------------------------------------------- the base and packs (BB-*)
def base_file():
    """The base BIAN that ships with SDEM — the newest bian/base-<release>.json (BB-S01, BB-S03)."""
    from .paths import DATA_ROOT
    found = sorted((DATA_ROOT / 'bian').glob('base-*.json'), key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r'[.-]', p.stem)])
    if not found: raise BianError('the base BIAN is not installed with this SDEM (bian/base-*.json) — import from a folder of BIAN files instead')
    return found[-1]


def pack(domains):
    """A packed BIAN: what the import uses, without descriptions or object schemas (BB-D1, BB-D2)."""
    releases = sorted({d['release'] for d in domains})
    keep = ('file', 'name', 'release', 'operations', 'control_record', 'qualifiers', 'control_record_fields')
    return {'format': PACK_FORMAT, 'release': releases[-1] if releases else '', 'domains': [{k: d[k] for k in keep} for d in domains]}


def dump_pack(p):
    """One service domain per line, so a new release shows as a readable diff."""
    head = json.dumps({k: v for k, v in p.items() if k != 'domains'}, ensure_ascii=False)[:-1]
    return head + ', "domains": [\n' + ',\n'.join(json.dumps(d, ensure_ascii=False, separators=(',', ':')) for d in p['domains']) + '\n]}\n'


def read_pack(path):
    """A packed BIAN (the base, or your own from `sdem bian pack`) → its service domains, as read_release gives them."""
    path = Path(path)
    try: p = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e: raise BianError(f'{path}: not a readable BIAN pack ({e})')
    if not isinstance(p, dict) or p.get('format') != PACK_FORMAT:
        raise BianError(f'{path}: not a BIAN pack (expected format {PACK_FORMAT}) — make one with `sdem bian pack <folder> -o <file>`')
    return [{**d, 'description': None, 'objects': {}} for d in p['domains']]


# ---------------------------------------------------------------- building the A2 dataset (BI-W01…W07)
def derive(control_record):
    """(asset type, functional pattern) from a control record's name, or (None, None) — BI-W02."""
    for artifact, pattern in _BY_ARTIFACT:
        if control_record and control_record.endswith(artifact) and len(control_record) > len(artifact):
            return _words(control_record[:-len(artifact)]), pattern
    return None, None


def build(domains, metamodel_version, descriptions=False, objects=False, patterns=None):
    """The A2 dataset and the facts for the report. `patterns`: {service domain name: (asset type, functional pattern)}."""
    patterns = {k.lower(): v for k, v in (patterns or {}).items()}
    releases = sorted({d['release'] for d in domains})
    release = releases[-1] if releases else ''
    inst, rels, report, cr_names = {}, [], {'derived': [], 'from_table': [], 'not_read': [], 'shared_control_records': []}, {}

    def add(rec):
        inst.setdefault(rec['id'], rec)
        return rec['id']

    def rec(id_, type_, name, version, desc=None, attrs=None, canonical=None, source=None):
        r = {'id': id_, 'type': type_, 'version': version or '1.0', 'name': name, 'lifecycle_status': 'active'}
        if canonical: r['canonical_id'] = canonical
        r['description'] = desc or f"From BIAN's Semantic API {version} — see BIAN for its definition."
        a = dict(attrs or {})
        if source: a.update({'source_id': source, 'conforms_to': [f'BIAN {version}']})
        if a: r['attributes'] = a
        return r

    missing = [d for d in domains if d['name'].lower() not in patterns and not derive(d['control_record'])[0]]
    if missing:
        raise BianError(f"{len(missing)} service domain(s) whose asset type and functional pattern cannot be derived — their control record's "
                        f"name does not end in one of BIAN's generic artifacts ({PATTERN_SOURCE}). Give them in a --patterns file "
                        "(CSV: service domain, asset type, functional pattern — from the BIAN portal):\n"
                        + '\n'.join(f"  {d['name']},<asset type>,<functional pattern>      # control record: {d['control_record'] or 'none'}" for d in missing))
    for d in domains:
        ver, sd_key, src = d['release'], _key(d['name']), f"bian-semantic-api:{d['release']}:{d['file']}"
        table = patterns.get(d['name'].lower())
        if table:
            asset, pattern = table; how = 'table'
        else:
            asset, pattern = derive(d['control_record']); how = 'derived'
        pattern = pattern.upper()
        if pattern not in PATTERNS: raise BianError(f"{d['name']}: {pattern!r} is not a BIAN functional pattern ({', '.join(PATTERNS)})")
        (report['from_table'] if how == 'table' else report['derived']).append((d['name'], asset, pattern.title()))
        at = add(rec(f'AT-{_key(asset)}', 'A2.AssetType', asset, ver, f"Asset type of {d['name']} — {how} ({PATTERN_SOURCE if how == 'derived' else 'your table'}); confirm."))
        fp = add(rec(f"FP-{_key(pattern)}", 'A2.FunctionalPattern', pattern.title(), ver,
                     f'A BIAN functional pattern ({PATTERN_SOURCE}).', {'generic_artefact': PATTERNS[pattern]}))
        sd = add(rec(f'SD-{sd_key}', 'A2.ServiceDomain', d['name'], ver, d['description'] if descriptions else None,
                     {'asset_type': at, 'functional_pattern': fp}, canonical=f'BIAN-{sd_key}', source=src))
        rels += [{'source': sd, 'kind': 'association', 'target': at}, {'source': sd, 'kind': 'association', 'target': fp}]
        cr = None
        if d['control_record']:
            cr_names.setdefault(d['control_record'], []).append(d['name'])
            cr = add(rec(f'CR-{sd_key}', 'A2.ControlRecord', _words(d['control_record']), ver,
                         attrs={'attributes': d['control_record_fields']}, source=src))
            rels.append({'source': sd, 'kind': 'aggregation', 'target': cr})
        bq_ids = {}
        for q in d['qualifiers']:
            bq_ids[q] = add(rec(f'BQ-{sd_key}-{_key(q)}', 'A2.BehaviorQualifier', f"{_words(q)} ({d['name']})", ver, source=src))
            if cr: rels.append({'source': cr, 'kind': 'composition', 'target': bq_ids[q]})
        groups = {}
        for op in d['operations']:
            g = op['group'] or 'Operations'
            if g not in groups:
                groups[g] = add(rec(f'SG-{sd_key}-{_key(g)}', 'A2.ServiceGroup', f"{d['name']} — {_words(g)}", ver,
                                    f"The operations BIAN tags {g!r} in {d['name']}.", source=src))
                rels.append({'source': sd, 'kind': 'composition', 'target': groups[g]})
            action = _words(op['operation_id']).split(' ')[0]
            attrs = {'action_term': action, 'http_method': op['method'], 'input_attributes': op['inputs'], 'output_attributes': op['outputs']}
            if op['qualifier']: attrs['behavior_qualifier'] = bq_ids[op['qualifier']]
            so = add(rec(f"SO-{sd_key}-{_key(op['operation_id'])}", 'A2.ServiceOperation', f"{d['name']}: {_words(op['operation_id'])}", ver,
                         f"{op['method']} {op['path']} in BIAN's Semantic API {ver}.", attrs, canonical=f"BIAN-{sd_key}-{_key(op['operation_id'])}", source=src))
            rels.append({'source': groups[g], 'kind': 'composition', 'target': so})
            if cr: rels.append({'source': so, 'kind': 'access', 'target': cr})
            if op['qualifier']: rels.append({'source': so, 'kind': 'association', 'target': bq_ids[op['qualifier']]})
        if objects:
            for name, fields in d['objects'].items():
                if name == d['control_record'] or name.lower().endswith('typevalues'): continue
                bo = add(rec(f'BBO-{_key(name)}', 'A2.BusinessObject', _words(name), ver, attrs={'attributes': fields},
                             canonical=f'BIAN-BO-{_key(name)}', source=src))
                if cr and name in set(d['control_record_fields']) | set(_words(f).replace(' ', '') for f in d['control_record_fields']):
                    rels.append({'source': cr, 'kind': 'association', 'target': bo})
    report['shared_control_records'] = sorted((n, ds) for n, ds in cr_names.items() if len(ds) > 1)
    seen, uniq = set(), []
    for r in rels:
        k = (r['source'], r['kind'], r['target'])
        if k not in seen: seen.add(k); uniq.append(r)
    dataset = {'level': 'A2', 'model_id': f'bian-semantic-api-{release}', 'model_version': release, 'metamodel_version': metamodel_version,
               'source_system': f'BIAN-SEMANTIC-API-{release}', 'instances': list(inst.values()), 'relationships': uniq}
    return dataset, report


def check(dataset):
    """Errors and warnings from the rulebook for one A2 dataset (BI-W07)."""
    from .graph import LevelGraph, estate_index
    from .metamodel import Metamodel
    g = LevelGraph(dataset, Metamodel.load())
    g.estate = estate_index([dataset])
    return g.validate(), list(g.warnings or [])


def select(domains, only=None, from_file=None, all_=False):
    """The domains to import (BI-C06): by name or file name, case-insensitive; a miss lists the closest names."""
    if not (only or from_file or all_):
        raise BianError('choose the service domains: --only <names>, --from <file of names> or --all (see them with `sdem bian list <folder>`)')
    if all_: return domains
    names = list(only or [])
    if from_file:
        names += [l.strip() for l in Path(from_file).read_text(encoding='utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#')]
    by = {}
    for d in domains:
        by[d['name'].lower()] = d; by[Path(d['file']).stem.lower()] = d
    out, missing = [], []
    for n in names:
        d = by.get(n.strip().lower())
        if d is None: missing.append(n)
        elif d not in out: out.append(d)
    if missing:
        hints = {n: difflib.get_close_matches(n, [d['name'] for d in domains], n=3, cutoff=0.5) for n in missing}
        raise BianError('not in this BIAN release: ' + '; '.join(f"{n!r}" + (f" (did you mean {', '.join(h)}?)" if h else '') for n, h in hints.items()))
    return out


def compare(previous, dataset):
    """BI-R01: what changed against a previous A2 dataset — added, dropped, renamed (same id, new name)."""
    old = {i['id']: i for i in previous.get('instances', [])}
    new = {i['id']: i for i in dataset['instances']}
    return {'added': sorted(set(new) - set(old)), 'dropped': sorted(set(old) - set(new)),
            'renamed': sorted((i, old[i]['name'], new[i]['name']) for i in set(old) & set(new) if old[i]['name'] != new[i]['name'])}


def report_md(dataset, report, refused, warnings, changes=None, descriptions=False, source='the BIAN files you downloaded'):
    c = Counter(i['type'] for i in dataset['instances'])
    L = [f"# BIAN import — {dataset['source_system']}", '',
         f"{len(dataset['instances'])} records, {len(dataset['relationships'])} links inside A2, from BIAN's Semantic API release {dataset['model_version']}. "
         f'Read from {source}; nothing was fetched. ' + ('BIAN descriptions included (--descriptions).' if descriptions else 'BIAN descriptions left out.'), '',
         '| Kind | Records |', '|---|---|'] + [f'| {t} | {n} |' for t, n in sorted(c.items())]
    L += ['', '## Asset type and functional pattern — confirm', '',
          f'BIAN\'s API files do not state them. **Derived** values come from the control record\'s name ({PATTERN_SOURCE}: a control record is named asset type + generic artifact); '
          'check each against the BIAN portal and correct any in a `--patterns` file (CSV: service domain, asset type, functional pattern).', '',
          '| Service domain | Asset type | Functional pattern | From |', '|---|---|---|---|']
    L += [f'| {d} | {a} | {p} | derived — confirm |' for d, a, p in report['derived']] + [f'| {d} | {a} | {p} | your table |' for d, a, p in report['from_table']]
    if report.get('shared_control_records'):
        L += ['', '## Control records with the same name', '', "BIAN's files give these service domains the same control record name; each domain keeps its own record (the rulebook allows one domain per control record). Check with BIAN which is intended.", '']
        L += [f"- `{n}`: {', '.join(ds)}" for n, ds in report['shared_control_records']]
    if changes:
        L += ['', '## Against the previous A2 dataset', '', f"Added {len(changes['added'])} · dropped {len(changes['dropped'])} · renamed {len(changes['renamed'])}. "
              'A dropped record is **not** removed from your estate — check whether approved links point to it.', '']
        L += [f'- dropped: `{i}`' for i in changes['dropped']] + [f'- renamed: `{i}` {a!r} → {b!r}' for i, a, b in changes['renamed']]
    if warnings:
        L += ['', '## Advice from the rulebook', ''] + [f'- {w}' for w in warnings[:50]] + ([f'- … {len(warnings) - 50} more'] if len(warnings) > 50 else [])
    if refused:
        L += ['', '## Files not read', ''] + [f'- {r}' for r in refused]
    L += ['', '## Next', '', '1. Confirm the asset types and functional patterns above.',
          '2. Use the file as your BIAN layer: `sdem load <candidates> --estate <estate> --person <you> --a2 <this file>`, or copy it into the estate as `a2-service-domain.json`.',
          '3. Approve connections that rest on BIAN guidance with `--bian-release ' + dataset['model_version'] + '`.', '']
    return '\n'.join(L)


# ---------------------------------------------------------------- command line
def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem bian', description="The BIAN (A2) layer from BIAN's public Semantic APIs (github.com/bian-official/public, Apache-2.0): "
                                 'list what a downloaded release holds; import the service domains you choose as a checked A2 dataset.',
                                 epilog='Examples:\n  sdem bian list ~/bian/release14.0.0\n'
                                        '  sdem bian import ~/bian/release14.0.0 --only "Payment Order Initiation" "Payment Execution" -o work/bian/a2-service-domain.json',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    src = argparse.ArgumentParser(add_help=False)
    src.add_argument('folder', nargs='?', help='a folder of BIAN-format files (e.g. a release downloaded from BIAN\'s GitHub)')
    src.add_argument('--base', nargs='?', const='', metavar='FILE', help='the base BIAN that ships with SDEM — or, with FILE, your own packed BIAN')
    ls = sub.add_parser('list', parents=[src], help='the service domains in the base, a pack or a folder; writes nothing')
    ls.add_argument('--json', action='store_true')
    pk = sub.add_parser('pack', help='pack a folder of BIAN-format files into one file — your own base')
    pk.add_argument('folder'); pk.add_argument('-o', '--out', required=True, metavar='FILE')
    im = sub.add_parser('import', parents=[src], help='write an A2 dataset for the service domains you choose — checked first')
    im.add_argument('-o', '--out', required=True, metavar='FILE')
    im.add_argument('--only', nargs='+', metavar='NAME', help='service domains by name (or file name)')
    im.add_argument('--from', dest='from_file', metavar='FILE', help='a file of service-domain names, one per line')
    im.add_argument('--all', action='store_true', help='every service domain in the release (about 3,000 records for release 14)')
    im.add_argument('--patterns', metavar='CSV', help='service domain, asset type, functional pattern — overrides the derived values')
    im.add_argument('--descriptions', action='store_true', help="include BIAN's descriptions (left out by default)")
    im.add_argument('--objects', action='store_true', help='also write BIAN business objects (many)')
    im.add_argument('--previous', metavar='FILE', help='a previous A2 dataset: report what was added, dropped or renamed')
    im.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'pack':
        domains, refused = read_release(a.folder)
        from .files import write_text
        write_text(Path(a.out), dump_pack(pack(domains)))
        print(f"packed {len(domains)} service domain(s) of BIAN release {pack(domains)['release']} into {a.out}" + (f'; {len(refused)} file(s) not read' if refused else ''))
        for r in refused: print(f'  not read: {r}')
        print(f'next: sdem bian import --base {a.out} --only "<name>" … -o <file>')
        return 0
    if (a.folder is None) == (a.base is None):
        raise BianError('name one BIAN source: --base (the base that ships with SDEM), --base <your pack>, or a folder of BIAN files')
    if a.base is not None:
        source = Path(a.base) if a.base else base_file()
        domains, refused, where = read_pack(source), [], f'--base {a.base}' if a.base else '--base'
        described = f'your BIAN pack {a.base}' if a.base else f"the base BIAN that ships with SDEM ({source.name})"
        if a.cmd == 'import' and (a.descriptions or a.objects):
            raise BianError('the base leaves out BIAN\'s descriptions and object schemas — for --descriptions or --objects, import from BIAN\'s files (a downloaded release folder)')
    else:
        domains, refused = read_release(a.folder); where = a.folder; described = f'the BIAN files in {a.folder}'
    if a.cmd == 'list':
        rows = [{'name': d['name'], 'release': d['release'], 'operations': len(d['operations']), 'control_record': d['control_record'], 'file': d['file'],
                 'needs_pattern': not derive(d['control_record'])[0]} for d in sorted(domains, key=lambda d: d['name'].lower())]
        if a.json: print(json.dumps({'domains': rows, 'not_read': refused}, indent=2)); return 0
        rel = sorted({r['release'] for r in rows}); need = sum(r['needs_pattern'] for r in rows)
        print(f"{len(rows)} service domains in BIAN release {', '.join(rel)}" + (f'; {len(refused)} file(s) not read' if refused else '')
              + (f"; {need} marked 'needs your pattern' (give it with --patterns)" if need else ''))
        for r in rows: print(f"  {r['name']:<45} {r['operations']:>3} operations   control record {r['control_record'] or '—'}" + ('   needs your pattern' if r['needs_pattern'] else ''))
        for r in refused: print(f'  not read: {r}')
        print(f'next: sdem bian import {where} --only "<name>" … -o <file>')
        return 0
    from .metamodel import Metamodel
    chosen = select(domains, a.only, a.from_file, a.all)
    patterns = None
    if a.patterns:
        with open(a.patterns, encoding='utf-8', newline='') as fh:
            patterns = {r[0].strip(): (r[1].strip(), r[2].strip()) for r in csv.reader(fh)
                        if len(r) >= 3 and r[0].strip() and not r[0].lstrip().startswith('#') and r[0].strip().lower() != 'service domain'}
    dataset, rep = build(chosen, Metamodel.load().version, a.descriptions, a.objects, patterns)
    errors, warnings = check(dataset)
    if errors:
        print('ERROR: refused — the A2 dataset would not pass the rulebook; nothing written:', file=sys.stderr)
        for e in errors[:20]: print(f'  {e}', file=sys.stderr)
        return 1
    changes = compare(json.loads(Path(a.previous).read_text(encoding='utf-8')), dataset) if a.previous else None
    out = Path(a.out); report_path = out.with_name(out.stem + '.report.md')
    from .files import Batch
    b = Batch(); b.json(out, dataset); b.text(report_path, report_md(dataset, rep, refused, warnings, changes, a.descriptions, described)); b.commit()
    c = Counter(i['type'].split('.')[1] for i in dataset['instances'])
    res = {'out': str(out), 'report': str(report_path), 'release': dataset['model_version'], 'domains': len(chosen), 'records': dict(c),
           'derived_to_confirm': len(rep['derived']), 'warnings': len(warnings), 'changes': changes}
    if a.json: print(json.dumps(res, indent=2)); return 0
    print(f"wrote {out}: {len(chosen)} service domain(s) from BIAN release {dataset['model_version']} — " + ', '.join(f'{k} {v}' for k, v in sorted(c.items())))
    print(f"checked: no errors ({len(warnings)} advice); report {report_path}")
    if rep['derived']: print(f"confirm: {len(rep['derived'])} derived asset type(s) and functional pattern(s) — listed in the report")
    print(f"next: sdem load <candidates> --estate <estate> --person <you> --a2 {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
