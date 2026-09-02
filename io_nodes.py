# -*- coding: utf-8 -*-
"""Save, load and build MiniMax H3 latents.

Core `SaveLatent` writes `samples["samples"]` as one tensor. An H3 latent is a NestedTensor
holding two of them (video and audio), so it has to be flattened on the way out and rebuilt on
the way in. These nodes do that with plain safetensors plus a small JSON sidecar recording how
many tensors there were and what shapes they had.

Why bother: a partial rewrite (see `MiniMaxH3DenoiseMask`) needs the ORIGINAL latent as its
`latent_image`. Nothing in the single-shot R2V / I2V / T2V graphs keeps it - only the Contex Loop
chain does, in its checkpoints. Adding `MiniMaxH3SaveLatent` next to the SaveVideo node means a
clip can be reopened and edited later without regenerating it.

Saved in bf16 by default: that is the precision the model runs in, and it halves a file
that is otherwise ~430 MB for a 4.5-second 1.5 MP clip. The original dtype is recorded in the
metadata and restored on load, so downstream nodes see what they expect.

`MiniMaxH3PackLatent` is the fallback for clips whose latent was never saved: encode the mp4 with
`VAEEncode` (video VAE) and its sound with `VAEEncodeAudio` (audio VAE), then pack the two here.
That round-trips through the VAE, so it is not identical to the latent the sampler produced and
it costs one generation of VAE loss across the whole clip - fine for editing, not for archiving.
"""
import json
import os

import torch

from . import _comfy_bridge as bridge
from ._core_import import core

DTYPES = core.DTYPES
load_tensors = core.load_tensors
save_tensors = core.save_tensors


class MiniMaxH3SaveLatent:
    def __init__(self):
        self.output_dir = bridge.output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'samples': ('LATENT',),
            'filename_prefix': ('STRING', {'default': 'h3_latents/clip'}),
            'dtype': (['bf16', 'fp16', 'fp32'], {'default': 'bf16',
                                                 'tooltip': 'bf16 halves the file and is what '
                                                            'the model runs in anyway. fp32 only '
                                                            'if you want the sampler output back '
                                                            'bit-for-bit.'}),
        }}

    RETURN_TYPES = ()
    FUNCTION = 'run'
    OUTPUT_NODE = True
    CATEGORY = 'MiniMax H3/latent'
    DESCRIPTION = ('Write an H3 latent (video + audio) to disk so the clip can be partially '
                   'rewritten later without regenerating it.')

    def run(self, samples, filename_prefix, dtype='bf16'):
        full, name = bridge.save_path(filename_prefix, self.output_dir)
        path = os.path.join(full, name)
        tensors, nested = bridge.tensors_of(samples['samples'])
        size = save_tensors(path, tensors, nested=nested, dtype=dtype,
                            extra_keys=[k for k in samples if k != 'samples'])
        print('[H3SaveLatent] %s  (%d tensors, %s, %.0f MB)'
              % (path, len(tensors), dtype, size / (1024 ** 2)))
        return {'ui': {'text': [name]}}


class MiniMaxH3LoadLatent:
    """Reads this pack's own files and the Contex Loop chain's checkpoints.

    The chain writes `video` / `audio` (plus `context_frames` and `delivered_audio`, which are
    not part of the latent) and carries the scene prompt in the file's metadata - so a finished
    chain clip can be reopened and edited without hunting for the prompt that made it.
    """

    @classmethod
    def INPUT_TYPES(cls):
        out = bridge.output_directory()
        files = []
        for root, _, names in os.walk(out):
            r = root.replace('\\', '/')
            if 'h3_latent' not in r and '/checkpoints' not in r:
                continue
            for n in names:
                if n.endswith('.safetensors'):
                    files.append(os.path.relpath(os.path.join(root, n), out).replace('\\', '/'))
        return {'required': {'latent': (sorted(files) or ['(none saved yet)'],)}}

    RETURN_TYPES = ('LATENT', 'STRING')
    RETURN_NAMES = ('samples', 'prompt')
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    DESCRIPTION = ('Read back a latent - either one written by MiniMax H3 Save Latent, or a '
                   'Contex Loop chain checkpoint. Chain checkpoints also carry the scene prompt, '
                   'which comes out of the second output.')

    @classmethod
    def IS_CHANGED(cls, latent):
        return latent

    @staticmethod
    def _resolve(name):
        """Keep the chosen file inside the output directory.

        The widget is a dropdown, but a graph POSTed to /prompt can carry any string in its
        place, and `os.path.join` discards the base entirely when the second argument is
        absolute. Resolve both sides and require containment.
        """
        root = os.path.realpath(bridge.output_directory())
        path = os.path.realpath(os.path.join(root, name))
        r, p = os.path.normcase(root), os.path.normcase(path)
        if p != r and not p.startswith(r + os.sep):
            raise ValueError('%r is outside the output directory' % (name,))
        return path

    def run(self, latent):
        path = self._resolve(latent)
        tensors, nested, prompt, _meta = load_tensors(path)
        if nested:
            return ({'samples': bridge.make_nested(tensors)}, prompt)
        return ({'samples': tensors[0]}, prompt)


class MiniMaxH3PackLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'video_latent': ('LATENT', {'tooltip': 'From VAEEncode with the H3 VIDEO vae.'}),
            'audio_latent': ('LATENT', {'tooltip': 'From VAEEncodeAudio with the H3 AUDIO vae.'}),
        }}

    RETURN_TYPES = ('LATENT',)
    RETURN_NAMES = ('samples',)
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    DESCRIPTION = ('Pack a separately-encoded video and audio latent into the nested form H3 '
                   'expects. Use this to edit a clip whose latent was never saved - it costs one '
                   'VAE round trip across the whole clip.')

    def run(self, video_latent, audio_latent):
        v = video_latent['samples']
        a = audio_latent['samples']
        if bridge.is_nested(v):
            v = next(t for t in v.tensors if t.ndim == 5)
        if bridge.is_nested(a):
            a = next(t for t in a.tensors if t.ndim != 5)
        if v.ndim != 5:
            raise ValueError('video latent should be (B, C, T, H, W), got %s' % (tuple(v.shape),))
        return ({'samples': bridge.make_nested([v, a])},)


NODE_CLASS_MAPPINGS = {
    'MiniMaxH3SaveLatent': MiniMaxH3SaveLatent,
    'MiniMaxH3LoadLatent': MiniMaxH3LoadLatent,
    'MiniMaxH3PackLatent': MiniMaxH3PackLatent,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'MiniMaxH3SaveLatent': 'MiniMax H3 Save Latent',
    'MiniMaxH3LoadLatent': 'MiniMax H3 Load Latent',
    'MiniMaxH3PackLatent': 'MiniMax H3 Pack Latent (video + audio)',
}
