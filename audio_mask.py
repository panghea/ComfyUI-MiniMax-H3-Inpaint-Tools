# -*- coding: utf-8 -*-
"""Resample only part of a MiniMax H3 latent - one track, one time span, one rectangle.

The sampler already understands a nested mask:

    comfy/samplers.py
        if denoise_mask.is_nested:
            denoise_masks = denoise_mask.unbind()
        ...
        x   = x   * denoise_mask + scale_latent_inpaint(...) * (1 - denoise_mask)
        out = out * denoise_mask + latent_image            * (1 - denoise_mask)

A mask of 0 pins that region to `latent_image` at every step; a mask of 1 lets it move. Because
H3 keeps video and audio as two separate tensors inside the NestedTensor, they can be masked
independently - and because the video tensor is an ordinary (B, C, T, H, W) grid, the mask can
also select a time span and a rectangle.

Measured on CM scene 1 (1664x928, 107 frames): holding the video and resampling only the audio
for 4 steps cost 360 s against 845 s for a full generation, and the picture came back at 40 dB
PSNR against the original - identical to the eye.

This is not the same as compositing two finished clips. The pinned region is present at every
step, so whatever is being rewritten is written *against* it: new audio lands on the mouth
movements already on screen, and a rewritten time span sees the frames on both sides of it.

Wire it as:

    finished latent -> Partial Denoise Mask -> SamplerCustomAdvanced.latent_image
    RandomNoise(new seed) ------------------> SamplerCustomAdvanced.noise

PDD cannot drive this pass: its sigma grid is fixed and a shortened schedule is off-grid. Use the
plain model, which is why the step count is the main cost lever.
"""
import torch

from . import _comfy_bridge as bridge
from ._core_import import core

build_masks = core.build_masks


class MiniMaxH3DenoiseMask:
    @classmethod
    def INPUT_TYPES(cls):
        pct = {'min': 0.0, 'max': 100.0, 'step': 0.5}
        return {'required': {
            'samples': ('LATENT',),
            'track': (['audio only', 'video only', 'both'], {'default': 'audio only'}),
            'strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.05,
                                   'tooltip': 'How free the selected region is. 1.0 = fully '
                                              'resampled; lower values keep pulling it back '
                                              'toward the original.'}),
            't_start_pct': ('FLOAT', dict(pct, default=0.0,
                                          tooltip='Start of the rewritten span, % of the clip. '
                                                  'Leave 0-100 to rewrite the whole thing.')),
            't_end_pct': ('FLOAT', dict(pct, default=100.0)),
            't_feather_pct': ('FLOAT', dict(pct, default=4.0, max=50.0,
                                            tooltip='Soft edge in time. Without it the seam '
                                                    'shows.')),
            'x_pct': ('FLOAT', dict(pct, default=0.0,
                                    tooltip='Rectangle for the video track only.')),
            'y_pct': ('FLOAT', dict(pct, default=0.0)),
            'w_pct': ('FLOAT', dict(pct, default=100.0)),
            'h_pct': ('FLOAT', dict(pct, default=100.0)),
            'feather_pct': ('FLOAT', dict(pct, default=6.0, max=50.0)),
        }}

    RETURN_TYPES = ('LATENT',)
    RETURN_NAMES = ('samples',)
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    DESCRIPTION = ('Pin most of an H3 latent and resample a chosen part of it: one track, a time '
                   'span, a rectangle. The pinned part is attended at every step, so the rewrite '
                   'matches what is around it.')

    def run(self, samples, track, strength, t_start_pct, t_end_pct, t_feather_pct,
            x_pct, y_pct, w_pct, h_pct, feather_pct):
        lat = samples['samples']
        if not bridge.is_nested(lat):
            raise TypeError('expected a MiniMax H3 nested latent, got %s' % type(lat).__name__)
        tensors, _ = bridge.tensors_of(lat)
        masks = build_masks(tensors, track=track, strength=strength,
                            t_start_pct=t_start_pct, t_end_pct=t_end_pct,
                            t_feather_pct=t_feather_pct,
                            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct,
                            feather_pct=feather_pct)
        out = dict(samples)
        out['noise_mask'] = bridge.rewrap(lat, masks)
        return (out,)


NODE_CLASS_MAPPINGS = {'MiniMaxH3DenoiseMask': MiniMaxH3DenoiseMask}
NODE_DISPLAY_NAME_MAPPINGS = {'MiniMaxH3DenoiseMask': 'MiniMax H3 Partial Denoise Mask'}
