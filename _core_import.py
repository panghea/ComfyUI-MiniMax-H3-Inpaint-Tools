# -*- coding: utf-8 -*-
"""Find `minimax_h3_latent_core`.

The core lives in its own repository and is published to PyPI, because it is licensed
differently from the ComfyUI adapter around it (see LICENSING.md). It is an ordinary
dependency: `requirements.txt` names it, which is what ComfyUI Manager installs.
"""
import importlib


def load():
    try:
        return importlib.import_module('minimax_h3_latent_core')
    except ImportError as exc:
        raise ImportError(
            'minimax_h3_latent_core is missing. Install it with '
            '`pip install minimax-h3-latent-core` into the same Python that runs ComfyUI, or '
            'install this node pack through ComfyUI Manager, which reads requirements.txt.'
        ) from exc


core = load()
