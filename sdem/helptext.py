"""CR-04: what the common options mean, in one place — given to every `sdem` command's option that does not say it itself, so `--help`,
`sdem commands --json` and the CLI reference never leave an option undescribed. An option's own help always wins."""
import argparse

COMMON = {
    '--workspace': 'the workspace folder — found from the current folder when you are inside one (WS-11)',
    '--root': 'a folder of workspaces (e.g. workspaces) — every workspace in it',
    '--graph': 'a graph store folder written by sdem build',
    '--person': "your name — a person's own, never an agent's (CTL-21)",
    '--reviewer': "the reviewer's name — a person's own, never an agent's (CTL-21)",
    '--agent': 'the agent acting, by its name (e.g. sdem-a3-agent)',
    '--reason': 'why — recorded with the decision',
    '--note': 'a note, recorded with it',
    '--layer': 'the layer: A1 business, A2 BIAN, A3 application, A4 technology (or a layer your profile adds)',
    '--out': 'where to write the result (a file or folder)',
    '--profile': "the organisation profile to use (otherwise the workspace's sdem-profile.json)",
    '--patterns': 'a table of service domain → functional pattern, asset type (CSV: Service Domain, pattern, asset type)',
    '--inferences': "SDEM's record of inferred asset types and patterns to apply (default: the one for the BIAN release)",
    '--no-inferences': "do not apply SDEM's accepted inferences",
    '--catalogue': 'an entity catalogue (entities.json): the ids and names records must use',
    '--registry': 'the registry of approved connections (mappings.json)',
    '--proposals': 'a proposals file written by sdem link (proposals.json)',
    '--event': 'a change event id (e.g. EVT-001)',
    '--status': 'only those with this status',
    '--format': 'the output format',
    '--title': 'a title',
    '--id': 'its id',
    '--file': 'the file to read',
    '--confidence': 'how sure, from 0 to 1',
    '--version': 'its version',
    '--as-of': 'evaluate as of this date (YYYY-MM-DD) — for a reproducible run',
    '--limit': 'with --json: at most N items in each list',
    '--direction': 'down: what it depends on · up: what depends on it',
    '--change': 'the kind of change: modify, rehost, replace or retire',
    '--evidence': 'the evidence, as kind:reference (e.g. deployment_design:PAY-REHOST#cutover)',
    '--date': 'the date (YYYY-MM-DD)',
    '--expires': 'when it ends (YYYY-MM-DD) — it is time-limited',
    '--rule': 'the rule id',
    '--record': 'the record id',
    '--records': 'the record ids',
    '--source': "where it came from, as kind:reference",
    '--from': 'read from this file or folder',
    'event': 'the change event id (e.g. EVT-001)',
    'projection': 'a projection file written by sdem aid project',
    'export': 'the export folder (e.g. a Confluence space export)',
    'folder': "a folder of BIAN-format files (e.g. a release downloaded from BIAN's GitHub)",
    'name': 'its name',
}
_ALIASES = {'-o': '--out'}


def describe(option_strings, dest):
    for s in list(option_strings) or [dest]:
        s = _ALIASES.get(s, s)
        if s in COMMON: return COMMON[s]
    return None


_installed = False


def install():
    """Give every option added from now on its common description when it has none of its own."""
    global _installed
    if _installed: return
    _installed = True
    original = argparse._ActionsContainer.add_argument

    def add_argument(self, *args, **kwargs):
        action = original(self, *args, **kwargs)
        if action.help is None:
            h = describe(action.option_strings, action.dest)
            if h: action.help = h
        return action
    argparse._ActionsContainer.add_argument = add_argument
