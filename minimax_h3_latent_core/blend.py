# -*- coding: utf-8 -*-
"""Post-hoc blending of two H3 latents. Pure tensor code, no ComfyUI import.

Prefer a denoise mask over this: a mask lets the rewritten region see the pinned region at every
step, so it is written *against* its surroundings. Blending happens after both clips exist and
cannot do that - it is for combining two finished results.
"""
import torch

from .masks import ramp


def mix_audio(base_others, overlay_others, mode='keep base', amount=0.5):
    if mode == 'keep base' or not base_others or not overlay_others:
        return list(base_others)
    if len(base_others) != len(overlay_others):
        raise ValueError('the two latents carry different non-video tensors')
    out = []
    for a, b in zip(base_others, overlay_others):
        if a.shape != b.shape:
            raise ValueError('audio latents differ in shape %s vs %s - the two runs must have '
                             'the same length' % (tuple(a.shape), tuple(b.shape)))
        out.append(b if mode == 'take overlay' else a * (1.0 - amount) + b.to(a.dtype) * amount)
    return out


def blend_video(base, overlay, x_pct=0.0, y_pct=0.0, w_pct=100.0, h_pct=100.0, feather_pct=6.0,
                t_start_pct=0.0, t_end_pct=100.0, t_feather_pct=4.0):
    if base.shape != overlay.shape:
        raise ValueError('video latents differ in shape %s vs %s - resize one first'
                         % (tuple(base.shape), tuple(overlay.shape)))
    _, _, T, H, W = base.shape
    dev, dt = base.device, base.dtype

    def cells(p, n):
        return p / 100.0 * n

    mx = ramp(W, cells(x_pct, W), cells(x_pct + w_pct, W), cells(feather_pct, W), dev, dt)
    my = ramp(H, cells(y_pct, H), cells(y_pct + h_pct, H), cells(feather_pct, H), dev, dt)
    mt = ramp(T, cells(t_start_pct, T), cells(t_end_pct, T), cells(t_feather_pct, T), dev, dt)
    mask = mt.view(1, 1, T, 1, 1) * my.view(1, 1, 1, H, 1) * mx.view(1, 1, 1, 1, W)
    return base * (1.0 - mask) + overlay.to(dt) * mask
