"""Turn unittest failures into GitHub annotations (one per failing test, its last traceback lines), so a failure can be read
without downloading the job log. Usage: python ci/annotate_failures.py <unittest output file>"""
import re, sys

text = open(sys.argv[1], encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
blocks = re.split(r'\n={50,}\n', text)
n = 0
for b in blocks:
    m = re.match(r'(FAIL|ERROR): (\S+) \(([^)]+)\)', b)
    if not m: continue
    tail = [l for l in b.split('-' * 70)[-1 if b.count('-' * 70) == 1 else 1].splitlines() if l.strip()][-6:]
    msg = f"{m.group(1)} {m.group(3)}: " + ' | '.join(l.strip()[:300] for l in tail)
    print(f"::error title={m.group(2)}::{msg.replace('%', '%25').replace(chr(10), ' ')}")
    n += 1
    if n >= 10: break
if not n and 'OK' not in text.splitlines()[-1:]:   # no failure blocks found (e.g. the run stopped early): the end of the log
    print('::error title=unittest::' + ' | '.join(l.strip()[:200] for l in text.splitlines()[-15:] if l.strip()).replace('%', '%25'))
