# -*- coding: utf-8 -*-
"""Import `minimax_h3_latent_core`, with an install hint if it is not there.

The core lives in its own repository and is published to PyPI, because it is licensed
differently from the ComfyUI adapter around it (see LICENSING.md). It is an ordinary
dependency: `requirements.txt` names it, which is what ComfyUI Manager installs.
"""
try:
    import minimax_h3_latent_core as core
except ImportError as exc:  # pragma: no cover - depends on the install, not the code
    raise ImportError(
        'minimax_h3_latent_core is missing. Install it with '
        '`pip install minimax-h3-latent-core` into the same Python that runs ComfyUI, or '
        'install this node pack through ComfyUI Manager, which reads requirements.txt.'
    ) from exc
