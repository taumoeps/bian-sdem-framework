"""Governed decisions and how far each can be trusted (docs/design/sdem-governance.md, GV-01…GV-07).

A decision only a person may take — approving or stating a link, confirming or retiring a requirement, accepting a change event's
impact or a residual risk, authorising implementation, adopting an edit, establishing a baseline — is written as one decision record,
`<workspace>/decisions/GD-….json`, append-only. When `sdem` writes it, it is **attributed**: a typed name, with what the machine
reports (OS and git user). That is attribution, never authentication: an agent running the same command can type the same name.

A decision is **verified** only when the commit that added its record carries a valid SSH signature by the approver the workspace's
`governance.json` maps that person to (`git verify-commit` against the allowed-signers file). An agent cannot produce that unless it
can use the person's signing key — keep the key passphrase- or hardware-protected and out of the agent's reach; protect
`governance.json` and the allowed-signers file with code owners. With `require_verified_decisions: true`, `sdem work plan` refuses an
acceptance that is not verified and `sdem governance verify --require-verified` (in CI, on the protected branch) fails on any
unverified decision. Without a policy file nothing is verified, and SDEM never says otherwise.
"""
import argparse, datetime, json, re, secrets, subprocess, sys
from pathlib import Path

DIR = 'decisions'
POLICY = 'governance.json'
KINDS = ('approve_link', 'state_link', 'confirm_requirement', 'retire_requirement', 'accept_impact', 'accept_residual_risk',
         'authorise_implementation', 'adopt_edit', 'establish_baseline', 'adopt_profile')
NOTE = 'a typed name — attribution, not authentication; verified only by a signed commit from the approver (sdem governance verify)'


def _now(): return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def identity():
    """What the machine reports about who ran the command — a claim for the audit, not proof."""
    import getpass
    git = {}
    for k in ('user.name', 'user.email'):
        try: git[k] = subprocess.run(['git', 'config', k], capture_output=True, text=True, timeout=5).stdout.strip() or None
        except (OSError, subprocess.SubprocessError): git[k] = None
    try: os_user = getpass.getuser()
    except Exception: os_user = None
    return {'os_user': os_user, 'git_user': git.get('user.name'), 'git_email': git.get('user.email')}


def record(workspace, kind, person, subject, details=None):
    """GV-01: write one decision record — attributed. Returns it (its id goes into the governed record where that has room)."""
    assert kind in KINDS, kind
    from .files import write_json
    gd = {'id': f"GD-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%S}-{secrets.token_hex(3)}", 'kind': kind, 'subject': subject,
          'named_person': person, 'at': _now(), 'recorded_by': identity(), 'level': 'attributed', 'note': NOTE, **({'details': details} if details else {})}
    write_json(Path(workspace) / DIR / f"{gd['id']}.json", gd)
    return gd


def decisions(workspace):
    d = Path(workspace) / DIR
    return [json.loads(f.read_text(encoding='utf-8')) for f in sorted(d.glob('GD-*.json'))] if d.exists() else []


def policy(workspace):
    f = Path(workspace) / POLICY
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None


def _git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, timeout=30)


def verify(workspace):
    """GV-03: each decision — verified, or why not. Never 'verified' without a valid signature by the mapped approver."""
    ws = Path(workspace).resolve(); pol = policy(ws) or {}
    approvers = {a['person']: a['signer'] for a in pol.get('approvers', [])}
    top = _git(ws, 'rev-parse', '--show-toplevel')
    root = Path(top.stdout.strip()).resolve() if top.returncode == 0 else None
    signers = None
    if root and pol.get('allowed_signers'):
        cand = [(ws / pol['allowed_signers']), (root / pol['allowed_signers'])]
        signers = next((c.resolve() for c in cand if c.exists()), None)
    out = []
    for gd in decisions(ws):
        row = {'id': gd['id'], 'kind': gd['kind'], 'subject': gd['subject'], 'named_person': gd['named_person'], 'status': None, 'signer': None, 'commit': None}
        if not pol: row['status'] = 'no_policy'
        elif not root: row['status'] = 'not_in_git'
        elif not signers: row['status'] = 'no_allowed_signers'
        elif gd['named_person'] not in approvers: row['status'] = 'not_an_approver'
        else:
            rel = (ws / DIR / f"{gd['id']}.json").relative_to(root).as_posix()
            sha = _git(root, 'log', '--diff-filter=A', '--format=%H', '--', rel).stdout.split()
            if not sha: row['status'] = 'not_committed'
            else:
                row['commit'] = sha[-1]
                v = _git(root, '-c', f'gpg.ssh.allowedSignersFile={signers}', 'verify-commit', sha[-1])
                m = re.search(r'Good "git" signature for (\S+)', v.stdout + v.stderr)
                if v.returncode != 0 or not m: row['status'] = 'unsigned_or_invalid'
                else:
                    row['signer'] = m.group(1)
                    row['status'] = 'verified' if m.group(1) == approvers[gd['named_person']] else 'signer_mismatch'
        out.append(row)
    return out


def require_verified(workspace, kind, subject):
    """GV-04: under a policy that requires it, the decision of `kind` on `subject` must be verified. Returns None, or why not."""
    pol = policy(workspace)
    if not (pol and pol.get('require_verified_decisions')): return None
    rows = [r for r in verify(workspace) if r['kind'] == kind and r['subject'] == subject]
    if not rows: return f'no {kind} decision recorded for {subject}'
    if not any(r['status'] == 'verified' for r in rows):
        return f"the {kind} decision on {subject} is not verified ({', '.join(sorted({r['status'] for r in rows}))}) — the person commits it with their own signing key (git commit -S)"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem governance', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Governed decisions — who was named, and whether a signed commit by that approver verifies it. A typed --person is attribution, not authentication.',
                                 epilog='Examples:\n  sdem governance verify --workspace workspaces/payments\n  sdem governance verify --workspace workspaces/payments --require-verified   # CI, protected branch')
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('verify', help='every decision record: verified by a signed commit from its approver, or why not')
    v.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); v.add_argument('--require-verified', action='store_true', help='exit 1 unless every decision is verified')
    v.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rows = verify(a.estate); pol = policy(a.estate)
    bad = [r for r in rows if r['status'] != 'verified']
    if a.json: print(json.dumps({'policy': bool(pol), 'require_verified_decisions': bool(pol and pol.get('require_verified_decisions')), 'decisions': rows,
                                 'verified': len(rows) - len(bad), 'unverified': len(bad)}, indent=2)); return 1 if a.require_verified and bad else 0
    if not pol: print(f'NOTE: {a.estate} has no {POLICY} — every decision is attribution only (a typed name), none can be verified')
    for r in rows: print(f"{r['id']}  {r['kind']:<25} {r['subject']:<26} {r['named_person']:<18} {r['status']}" + (f"  ({r['signer']}, {r['commit'][:10]})" if r['signer'] else ''))
    print(f"{len(rows) - len(bad)} of {len(rows)} decision(s) verified")
    return 1 if a.require_verified and bad else 0
