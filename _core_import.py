# -*- coding: utf-8 -*-
"""Find `minimax_h3_latent_core`, whether it is pip-installed or sitting in this directory.

The core lives in its own repository and is published to PyPI, because it is licensed
differently from the ComfyUI adapter around it (see LICENSING.md). A copy is also vendored here
so a plain `git clone` of this repository runs without a second install step.

The installed package wins when both are present: it is the one the user chose, and it is the one
that gets updated.
"""
import importlib
import os
import sys


def load():
    try:
        return importlib.import_module('minimax_h3_latent_core')
    except ImportError:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(here, 'minimax_h3_latent_core')):
        if here not in sys.path:
            sys.path.insert(0, here)
        return importlib.import_module('minimax_h3_latent_core')
    raise ImportError(
        'minimax_h3_latent_core is missing. Install it with `pip install minimax-h3-latent-core`, or check out '
        'this repository with its vendored copy intact.')


core = load()
