# -*- coding: utf-8 -*-
"""Spatial resize for MiniMax H3 latents.

H3 packs its video and audio latents into `comfy.nested_tensor.NestedTensor`, which is a thin
wrapper around a plain list of tensors. Core `LatentUpscale` calls `.reshape` on the latent and
dies. This node unwraps the list, resizes only the spatial dimensions of the video tensor, leaves
the audio tensor alone, and wraps it back up.

Intended for a two-stage run: sample small, resize the latent here, then sample again at the
target size with denoise < 1 - no decode, no per-frame image upscaler in between.
"""
import torch

from . import _comfy_bridge as bridge
from ._core_import import core

METHODS = core.METHODS
SPATIAL_DOWNSCALE = core.SPATIAL_DOWNSCALE
latent_size = core.latent_size
resize_tensor = core.resize_tensor

class MiniMaxH3LatentSpatialResize:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'samples': ('LATENT',),
            'width': ('INT', {'default': 1664, 'min': 64, 'max': 8192, 'step': 32,
                              'tooltip': 'Target width in PIXELS; divided by 16 for the latent.'}),
            'height': ('INT', {'default': 928, 'min': 64, 'max': 8192, 'step': 32}),
            'method': (METHODS, {'default': 'bicubic'}),
        }}

    RETURN_TYPES = ('LATENT',)
    RETURN_NAMES = ('samples',)
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    DESCRIPTION = ('Resize an H3 latent spatially, keeping its NestedTensor packing and its '
                   'audio channel intact. Core LatentUpscale cannot do this.')

    def run(self, samples, width, height, method):
        out = dict(samples)
        lat = samples['samples']
        h, w = latent_size(width, height)

        if bridge.is_nested(lat):
            # H3 packs [video (B C T H W), audio (B C 2 L)]. The audio tensor is 4-D too, so
            # resizing "anything 4-D or 5-D" would stretch the audio - only touch the 5-D one.
            tensors, _ = bridge.tensors_of(lat)
            out['samples'] = bridge.rewrap(
                lat, [resize_tensor(t, h, w, method) if t.ndim == 5 else t for t in tensors])
        elif torch.is_tensor(lat):
            out['samples'] = resize_tensor(lat, h, w, method)
        else:
            raise TypeError('unsupported latent payload: %s' % type(lat))

        for key in ('noise_mask',):
            if key in out and torch.is_tensor(out[key]):
                out[key] = resize_tensor(out[key], h, w, 'nearest-exact')
        return (out,)


class MiniMaxH3LatentInspect:
    """Prints what is actually inside the latent - shapes, dtypes, how many tensors."""

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'samples': ('LATENT',)}}

    RETURN_TYPES = ('LATENT', 'STRING')
    RETURN_NAMES = ('samples', 'report')
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    OUTPUT_NODE = True

    def run(self, samples):
        lat = samples['samples']
        lines = ['type: %s' % type(lat).__name__]
        ts, _ = bridge.tensors_of(lat)
        for i, t in enumerate(ts):
            lines.append('  [%d] shape=%s dtype=%s' % (i, tuple(t.shape), t.dtype))
        lines += ['other keys: %s' % sorted(k for k in samples if k != 'samples')]
        report = '\n'.join(lines)
        print('[H3LatentInspect]\n' + report)
        return (samples, report)


from .composite import (NODE_CLASS_MAPPINGS as _COMP_CLASSES,
                        NODE_DISPLAY_NAME_MAPPINGS as _COMP_NAMES)
from .audio_mask import (NODE_CLASS_MAPPINGS as _MASK_CLASSES,
                         NODE_DISPLAY_NAME_MAPPINGS as _MASK_NAMES)
from .io_nodes import (NODE_CLASS_MAPPINGS as _IO_CLASSES,
                       NODE_DISPLAY_NAME_MAPPINGS as _IO_NAMES)
from .extend_node import (NODE_CLASS_MAPPINGS as _EXT_CLASSES,
                          NODE_DISPLAY_NAME_MAPPINGS as _EXT_NAMES)
from .timing_node import (NODE_CLASS_MAPPINGS as _TIME_CLASSES,
                          NODE_DISPLAY_NAME_MAPPINGS as _TIME_NAMES)
from .region_picker import (NODE_CLASS_MAPPINGS as _PICK_CLASSES,
                            NODE_DISPLAY_NAME_MAPPINGS as _PICK_NAMES)

NODE_CLASS_MAPPINGS = {
    'MiniMaxH3LatentSpatialResize': MiniMaxH3LatentSpatialResize,
    'MiniMaxH3LatentInspect': MiniMaxH3LatentInspect,
}
NODE_CLASS_MAPPINGS.update(_COMP_CLASSES)
NODE_CLASS_MAPPINGS.update(_TIME_CLASSES)
NODE_CLASS_MAPPINGS.update(_EXT_CLASSES)
NODE_CLASS_MAPPINGS.update(_MASK_CLASSES)
NODE_CLASS_MAPPINGS.update(_IO_CLASSES)
NODE_CLASS_MAPPINGS.update(_PICK_CLASSES)
NODE_DISPLAY_NAME_MAPPINGS = {
    'MiniMaxH3LatentSpatialResize': 'MiniMax H3 Latent Spatial Resize',
    'MiniMaxH3LatentInspect': 'MiniMax H3 Latent Inspect',
}
NODE_DISPLAY_NAME_MAPPINGS.update(_COMP_NAMES)
NODE_DISPLAY_NAME_MAPPINGS.update(_MASK_NAMES)
NODE_DISPLAY_NAME_MAPPINGS.update(_IO_NAMES)
NODE_DISPLAY_NAME_MAPPINGS.update(_TIME_NAMES)
NODE_DISPLAY_NAME_MAPPINGS.update(_EXT_NAMES)
NODE_DISPLAY_NAME_MAPPINGS.update(_PICK_NAMES)

# the rectangle picker needs its javascript half
WEB_DIRECTORY = './web/js'

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
