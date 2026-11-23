"""sdem.api — the one code interface an extension may use (docs/design/sdem-stable-identity-spec.md, ST-20, ST-21).

An extension uses SDEM through its commands, or through this module — never through any other of SDEM's modules (EXT-02 as amended).
Its version is VERSION; an extension says which it supports in its manifest ("api": ">=0.1,<0.2"). Through 0.20 it is 0.x — it may
still change; 1.0 when SDEM 0.20 is released.

    the metamodel      Metamodel, T, layer, type_id, layer_id, F (a layer's file in the workspace at hand), live, ROOT, DATA_ROOT
    a workspace        estate_docs, estate_errors, activate, profile, parts, catalogue_dir
    the graph          LevelGraph, estate_index
    the rules engine   CoreRun, GraphReader, estate_files, store_names, read_names, and its helpers — an extension's own steps run with
                       the core's (0.22, MX-47)
    reading            load, loads — a design's file, its names as a person reads them (ids or 0.19's in the file, DL-11)
    writing            Batch, write_json, write_text, relink, for_file — every write through SDEM's own writer (atomic, LF, UTF-8),
                       holding the names the file's workspace stores
    checks             is_person
    0.19's form        export_019(workspace, folder) — a 0.20 workspace as 0.19 held it, for a consumer not yet on 0.20 (DL-23)
    commands           run(command, main, argv) — an extension's code for one of SDEM's commands, run the way SDEM runs its own
                       (its --json, --dry-run, errors and exit codes)
"""
import importlib

VERSION = '0.1'

_EXPORTS = {
    'Metamodel': ('metamodel', 'Metamodel'), 'ROOT': ('metamodel', 'ROOT'), 'DATA_ROOT': ('paths', 'DATA_ROOT'),
    'T': ('identity', 'T'), 'layer': ('identity', 'layer'), 'F': ('identity', 'F'), 'live': ('identity', 'live'), 'type_id': ('identity', 'type_id'), 'layer_id': ('identity', 'layer_id'),
    'estate_docs': ('connect', 'estate_docs'), 'estate_errors': ('connect', 'estate_errors'), 'activate': ('profile', 'activate_from'),
    'catalogue_dir': ('parts', 'catalogue_dir'), 'LevelGraph': ('graph', 'LevelGraph'), 'estate_index': ('graph', 'estate_index'),
    'Batch': ('files', 'Batch'), 'write_json': ('files', 'write_json'), 'write_text': ('files', 'write_text'), 'relink': ('docmap', 'relink'),
    'is_person': ('validate', 'is_person'),
    'export_019': ('migrate20', 'export_019'), 'layers_in_use': ('identity', 'layers_in_use'), 'view_019': ('identity', 'view_019'),   # DL-23: a 0.20 workspace for a consumer built on 0.19's form
    'load': ('identity', 'load'), 'loads': ('identity', 'loads'), 'for_file': ('identity', 'for_file'),   # DL-11: a design's files, read and written
    # 0.22 step 3b (MX-47): the rules engine, for an extension's own steps run with the core's — CoreRun, a workspace's reader, its helpers
    'CoreRun': ('rules_engine', 'CoreRun'), 'GraphReader': ('store', 'GraphReader'), 'estate_files': ('cli', '_estate_files'),
    'store_names': ('identity', 'store_names'), 'read_names': ('identity', 'read_names'),
    'BAND': ('rules_engine', 'BAND'), 'HTTP': ('rules_engine', 'HTTP'), 'METHODS': ('rules_engine', 'METHODS'), '_list': ('rules_engine', '_list'),
    'norm': ('rules_engine', 'norm'), 'stems': ('rules_engine', 'stems'), 'tokens': ('rules_engine', 'tokens'), 'weakest': ('rules_engine', 'weakest'),
}
_MODULES = {'profile', 'parts'}   # whole modules an extension may use: the profile (activate, include) and BIAN's on-or-off (parts)
__all__ = sorted(_EXPORTS) + sorted(_MODULES) + ['VERSION', 'run']


def __getattr__(name):   # lazily, so `import sdem.api` loads nothing it does not need
    if name in _MODULES: return importlib.import_module(f'sdem.{name}')
    if name in _EXPORTS:
        mod, attr = _EXPORTS[name]
        return getattr(importlib.import_module(f'sdem.{mod}'), attr)
    raise AttributeError(f'sdem.api has no {name!r} — an extension may use only: {", ".join(__all__)}')


def run(command, main, argv):
    """Run an extension's `main` as SDEM's command `command` (e.g. 'bian'), through SDEM's own command line — the same --json header,
    --dry-run, errors and exit codes as SDEM's built-in code would give (BP-01, ST-22)."""
    from . import cli
    cli.PROVIDED[command] = main
    return cli.main([command, *argv])
