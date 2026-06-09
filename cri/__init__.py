"""
cri/__init__.py
Path shim that maps underscore package aliases to hyphenated directories.
This allows:
    from cri.belief_engine.store import BeliefStore
    from cri.runtime_core.classifiers import classify_shell
    etc.
"""
from __future__ import annotations
import sys, os
from importlib import import_module
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec
import importlib.util

# Mapping: Python underscore name → actual directory name
_ALIAS_MAP = {
    "cri.belief_engine":        "cri/belief-engine",
    "cri.runtime_core":         "cri/runtime-core",
    "cri.semantic_state":       "cri/semantic-state",
    "cri.checkpoint_engine":    "cri/checkpoint-engine",
    "cri.verification_runtime": "cri/verification-runtime",
    "cri.rollback_engine":      "cri/rollback-engine",
    "cri.agent_runtime":        "cri/agent-runtime",
}

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _HyphenFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        # Direct alias match
        for alias, real_dir in _ALIAS_MAP.items():
            if fullname == alias or fullname.startswith(alias + "."):
                suffix = fullname[len(alias):]           # e.g. ".store"
                real_pkg = real_dir.replace("/", os.sep)
                pkg_path = os.path.join(_ROOT, real_pkg)
                if not os.path.isdir(pkg_path):
                    return None

                if suffix == "":
                    # It's the package itself
                    init = os.path.join(pkg_path, "__init__.py")
                    spec = importlib.util.spec_from_file_location(
                        fullname, init,
                        submodule_search_locations=[pkg_path]
                    )
                    return spec
                else:
                    # It's a sub-module
                    mod_name = suffix.lstrip(".")
                    mod_file = os.path.join(pkg_path, mod_name + ".py")
                    if os.path.isfile(mod_file):
                        spec = importlib.util.spec_from_file_location(fullname, mod_file)
                        return spec
        return None


# Register the finder once
if not any(isinstance(f, _HyphenFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _HyphenFinder())
