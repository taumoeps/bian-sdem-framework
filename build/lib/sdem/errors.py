"""An error with its code and next step, raised where it happens (docs/design/sdem-agent-cli-spec.md, AF-05). `sdem` prints it as one
`ERROR:` line; with --json it becomes {"error": {"code", "message", "hint"}} without guessing the code from the words."""

CODES = ('usage', 'not_found', 'invalid_input', 'needs_person', 'exists', 'refused', 'input', 'internal')


class SdemError(ValueError):
    def __init__(self, code, message, hint=None, exit=2):
        assert code in CODES, code
        super().__init__(message)
        self.code, self.hint, self.exit = code, hint, exit

LAST = None   # (code, hint) of the error just reported — read by sdem/agent.py for --json


def report(e):
    """Print an SdemError as one ERROR line and remember its code; return its exit code."""
    import sys
    global LAST
    LAST = (e.code, e.hint)
    print(f'ERROR: {e}', file=sys.stderr)
    return e.exit


def note(code, hint=None):
    global LAST
    LAST = (code, hint)
