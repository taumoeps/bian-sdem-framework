"""The agent-CLI assessment (docs/evidence/agent-cli-readiness.md): runs real sdem commands on copies of the made-up examples and
records, for each, the command, exit code, a sample of the output and pass/fail.

  python scripts/agent_cli_assess.py <sdem executable> <SDEM repository> <empty work folder> <label>

Run it once with a checkout's sdem and once with an installed one (from outside the repository) — the results must match."""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

SD, REPO, WORK, LABEL = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
WORK.mkdir(parents=True, exist_ok=True)
EX = WORK / 'pay'; shutil.copytree(REPO / 'examples' / 'payment-initiation', EX, dirs_exist_ok=True)
G = EX / 'graph'
results = []


def run(args, cwd=WORK, env=None):
    t = time.time()
    r = subprocess.run([SD, *map(str, args)], cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, timeout=600)
    try: data = json.loads(r.stdout)
    except ValueError: data = None
    return r.returncode, data, r.stdout, r.stderr, round(time.time() - t, 1)


def case(no, name, args, check, cwd=WORK, env=None):
    code, data, out, err, secs = run(args, cwd, env)
    try: ok, note = check(code, data, out, err)
    except Exception as e: ok, note = False, f'check raised {e!r}'
    sample = (json.dumps(data, ensure_ascii=False)[:180] if data is not None else (out or err).strip()[:180]).replace('\n', ' ')
    results.append({'no': no, 'name': name, 'cmd': 'sdem ' + ' '.join(str(a).replace(str(WORK), '$W').replace(str(REPO), '$REPO') for a in args),
                    'exit': code, 'secs': secs, 'json': data is not None, 'pass': ok, 'note': note, 'sample': sample})
    return code, data


def h(d): return hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(d).rglob('*')) if p.is_file())).hexdigest()
def marker(d, cmd): return isinstance(d, dict) and d.get('sdem', {}).get('command') == cmd


# 1 discovery
case('1a', 'command discovery', ['commands', '--json'], lambda c, d, o, e: (c == 0 and len(d['commands']) > 50 and 'trace' in d['commands'], f"{len(d['commands'])} entries; exit/error codes {sorted(d['exit_codes'])}"))
case('1b', 'version', ['--version'], lambda c, d, o, e: (c == 0 and '0.9.13' in o, o.strip()))
# 2 validation
case('2a', 'check a valid workspace', ['check', '--workspace', EX, '--json'], lambda c, d, o, e: (c == 0 and d['ok'] is True and marker(d, 'check'), 'ok true'))
bad = WORK / 'bad'; shutil.copytree(EX, bad, ignore=shutil.ignore_patterns('graph'))
a3 = json.loads((bad / 'a3-application.json').read_text()); a3['instances'][0]['type'] = 'A3.NoSuchThing'; (bad / 'a3-application.json').write_text(json.dumps(a3))
case('2b', 'check an invalid workspace', ['check', '--workspace', bad, '--json'], lambda c, d, o, e: (c == 1 and d['ok'] is False, f"exit 1; issues reported in JSON: {sum(len(v) for v in d['report'].values())}"))
# 3 graph and trace
case('3a', 'query records', ['query', '--graph', G, '--level', 'A3', '--json'], lambda c, d, o, e: (c == 0 and marker(d, 'query') and d['count'] == len(d['items']), f"object: {d['count']} items"))
case('3b', 'trace one record', ['trace', 'INF-K8S-PAY-PROD', '--direction', 'up', '--graph', G, '--json'], lambda c, d, o, e: (c == 0 and marker(d, 'trace'), 'object with marker'))
case('3c', 'trace a whole layer', ['trace', 'A2', '--direction', 'both', '--graph', G, '--json'], lambda c, d, o, e: (c == 0 and marker(d, 'trace') and 'items' in d, f"object with marker: {d['count']} items"))
# 4 impact
case('4a', 'impact of a rehost', ['impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--graph', G, '--json'], lambda c, d, o, e: (c == 0 and marker(d, 'impact'), ', '.join(f"{k}" for k in list(d)[:6])))
# 5 inference
before = h(EX)
case('5a', 'link: structured proposals', ['link', '--workspace', EX, '--out', WORK / 'links', '--json'], lambda c, d, o, e: (c == 0 and d['count'] == len(d['proposals']), f"{d['count']} proposals, weakest first; next given: {bool(d.get('next'))}"))
case('5b', 'review proposals', ['review', WORK / 'links' / 'proposals.json', '--json'], lambda c, d, o, e: (c == 0 and marker(d, 'review'), f"object: {d['count']} items"))
case('5c', 'link leaves the workspace unchanged', ['check', '--workspace', EX, '--json'], lambda c, d, o, e: (h(EX) == before, 'workspace hash unchanged'))
# 6 read-only and dry-run
before = h(EX)
case('6a', 'build --dry-run (sandbox)', ['build', '--workspace', EX, '--out', G, '--json', '--dry-run'], lambda c, d, o, e: (c == 0 and d.get('dry_run') and h(EX) == before, f"would_write {len(d.get('would_write', []))}; workspace unchanged: {h(EX) == before}"))
ws = WORK / 'ws'
case('6b', 'new --dry-run (native)', ['new', '--workspace', ws, '--person', 'jane.architect', '--json', '--dry-run'], lambda c, d, o, e: (c == 0 and not ws.exists(), 'nothing created'))
case('6c', 'dashboard --json is read-only and small', ['dashboard', '--workspace', EX, '--json'], lambda c, d, o, e: (c == 0 and len(o) < 40000 and h(EX) == before, f'{len(o)} bytes'))
# 7 errors
case('7a', 'unknown record', ['trace', 'NOPE', '--graph', G, '--json'], lambda c, d, o, e: (c == 1 and d['error']['code'] == 'not_found' and d['error']['hint'], d['error']['hint']))
case('7b', 'bad option value', ['trace', 'A4', '--graph', G, '--direction', 'sideways', '--json'], lambda c, d, o, e: (c == 2 and d['error']['code'] == 'usage', d['error']['message'][:80]))
(WORK / 'broken.json').write_text('{ not json')
case('7c', 'malformed input file', ['validate', WORK / 'broken.json', '--json'], lambda c, d, o, e: (c == 2 and d['error']['code'] == 'invalid_input' and d['error']['hint'], d['error']['code'] + ' | ' + d['error']['hint']))
case('7d', 'missing file', ['review', WORK / 'nope.json', '--json'], lambda c, d, o, e: (c == 2 and d is not None and d.get('error', {}).get('code') == 'not_found', (d or {}).get('error', {}).get('code')))
case('7e', 'unknown command', ['frobnicate', '--json'], lambda c, d, o, e: (c == 2 and d is not None and 'error' in d, (d or {}).get('error', {}).get('message', 'NOT JSON')[:80]))
# 8 governance
case('8a', 'approve as an agent name', ['approve', 'P-X', '--proposals', WORK / 'links' / 'proposals.json', '--workspace', EX, '--reviewer', 'sdem-a3-application', '--evidence', 'x:y', '--json'],
     lambda c, d, o, e: (c != 0 and h(EX) == before, f"exit {c}; {(d or {}).get('error', {}).get('code')}: {(d or {}).get('error', {}).get('message', '')[:90]}"))
case('8b', 'start a workspace as an agent', ['new', '--workspace', WORK / 'ws2', '--person', 'sdem-agent', '--json'], lambda c, d, o, e: (c == 2 and d['error']['code'] == 'needs_person', d['error']['code']))
cs = REPO / '.github' / 'skills' / 'sdem-change-sets' / 'example-a4-rehost.json'
case('8c', 'A3 agent changes the A4 layer', ['change', 'propose', cs, '--workspace', EX, '--agent', 'sdem-a3-application', '--person', 'jane.architect', '--json'],
     lambda c, d, o, e: (c != 0 and h(EX) == before, f"exit {c}: {((d or {}).get('error') or {}).get('message', o[:90])[:110]}"))
case('8d', 'orchestrator changes a layer', ['change', 'propose', cs, '--workspace', EX, '--agent', 'sdem-orchestrator', '--person', 'jane.architect', '--json'],
     lambda c, d, o, e: (c != 0 and h(EX) == before, f"exit {c}: {((d or {}).get('error') or {}).get('message', '')[:110]}"))
# 8e: an agent edits the registry directly, bypassing approve — detected?
tam = WORK / 'tamper'; shutil.copytree(EX, tam, ignore=shutil.ignore_patterns('graph'))
reg = json.loads((tam / 'mappings.json').read_text()); m = reg['mappings'][0]
for k in ('reviewer_id', 'approved_at'): m.pop(k, None)
m['evidence'] = []
(tam / 'mappings.json').write_text(json.dumps(reg))
case('8e', 'registry edited by hand (approval removed)', ['validate', '--strict', '--workspace', tam, '--json'], lambda c, d, o, e: (c == 1, f'exit {c}: detected after the fact'))
case('8f', 'person name typed by an agent', ['new', '--workspace', WORK / 'ws3', '--person', 'jane.architect', '--json'], lambda c, d, o, e: (c == 0, 'accepted — SDEM cannot tell who typed the name (by design; needs repository review)'))
# 5d/8g/9 added after the fixes
ev = WORK / 'ev'; subprocess.run([sys.executable, str(REPO / 'scripts' / 'agent_eval.py'), 'prepare', str(ev)], capture_output=True, env={**os.environ, 'PYTHONPATH': str(REPO)})
code, d = case('5d', 'link ids usable by approve', ['link', '--workspace', ev / 'workspaces/payments', '--out', ev / 'l', '--json'], lambda c, d, o, e: (c == 0 and all(p['mapping_id'] for p in d['proposals']), f"{d['count']} proposal(s), ids {[p['mapping_id'] for p in d['proposals']]}"))
mid = d['proposals'][0]['mapping_id']
case('5e', 'approve with the id link returned', ['approve', mid, '--proposals', ev / 'l' / 'proposals.json', '--workspace', ev / 'workspaces/payments', '--reviewer', 'jane.architect', '--evidence', 'application_architecture_document:AA-PAYHUB-HLD#s3', '--json'],
     lambda c, d, o, e: (c == 0 and d['count'] == 1, f"approved as {d['items'][0]['mapping_id']} by {d['items'][0]['reviewer_id']}"))
a3 = ev / 'workspaces/payments/a3-application.json'; x = json.loads(a3.read_text()); x['instances'][0]['name'] = 'edited directly'; a3.write_text(json.dumps(x))
case('8g', 'direct layer edit noticed', ['check', '--workspace', ev / 'workspaces/payments', '--json'], lambda c, d, o, e: (c == 0 and [u['file'] for u in d['unrecorded_edits']] == ['a3-application.json'], f"unrecorded_edits: {[u['file'] for u in d['unrecorded_edits']]}"))
case('8h', 'CI mode fails on it', ['check', '--workspace', ev / 'workspaces/payments', '--require-recorded', '--json'], lambda c, d, o, e: (c == 1 and d['ok'] is False, 'exit 1'))
case('8i', 'an agent cannot accept it', ['change', 'adopt', '--workspace', ev / 'workspaces/payments', '--layer', 'A3', '--person', 'sdem-a3-application', '--reason', 'x', '--json'], lambda c, d, o, e: (c != 0 and d['error']['code'] == 'needs_person', d['error']['code']))
inst = WORK / 'inst-agents'; inst.mkdir()
case('9b', 'agents install (all four platforms)', ['agents', 'install', '--to', inst, '--json'], lambda c, d, o, e: (c == 0 and (inst / 'AGENTS.md').exists() and (inst / '.claude/skills').exists() and (inst / '.agents/skills').exists() and (inst / '.gemini/settings.json').exists() and (inst / '.github/copilot-instructions.md').exists(), f"{len(d['written'])} + {len(d['copilot']['written'])} Copilot files"))

# 10 consistency
case('10a', 'stdout is JSON only (notes on stderr)', ['trace', 'INF-K8S-PAY-PROD', '--graph', G, '--json'], lambda c, d, o, e: (d is not None and 'baseline:' in e, 'baseline note on stderr, JSON on stdout'))
case('10b', 'no prompt when stdin is closed', ['aid', '--workspace', WORK / 'ws3', '--person', 'jane.architect', '--json', '--dry-run'], lambda c, d, o, e: (c in (0, 2) and d is not None, f'exit {c}, JSON'))

json.dump(results, open(WORK / f'results-{LABEL}.json', 'w'), indent=1)
for r in results:
    print(f"{r['no']:<4} {'PASS' if r['pass'] else 'FAIL'}  exit {r['exit']:<3} {r['secs']:>5}s  {r['name']:<44} | {r['note']}")
print(f"{sum(bool(r['pass']) for r in results)} of {len(results)} pass")
