# -*- coding: utf-8 -*-
"""Denoise masks for MiniMax H3 latents.

Pure tensor code: nothing here imports ComfyUI. An H3 latent is a pair of tensors - video as
(B, C, T, H, W) and audio as (B, C, 2, L) - and the sampler honours a per-tensor mask where 0
pins a region to the original and 1 lets it move. That makes three independent selections
possible: which track, which time span, and (for video) which rectangle.
"""
import torch

TRACK_AUDIO = 'audio only'
TRACK_VIDEO = 'video only'
TRACK_BOTH = 'both'


def ramp(n, lo, hi, feather, device=None, dtype=torch.float32):
    """1 inside [lo, hi), fading to 0 across `feather` cells on both sides.

    Sizes are in cells, not percent - the caller converts. A feather of 0 gives a hard edge,
    which shows as a seam on video and as a click on audio.
    """
    idx = torch.arange(n, device=device, dtype=torch.float32)
    if hi <= lo:
        return torch.zeros(n, device=device, dtype=dtype)
    if feather <= 0:
        m = ((idx >= lo) & (idx < hi)).to(torch.float32)
    else:
        rise = ((idx - (lo - feather)) / feather).clamp(0, 1)
        fall = (((hi + feather) - idx) / feather).clamp(0, 1)
        m = torch.minimum(rise, fall)
    return m.to(dtype)


def is_video(t):
    """H3 keeps video as the only 5-D tensor; audio is 4-D and must never be resized or boxed."""
    return t.ndim == 5


def track_is_free(t, track):
    if track == TRACK_BOTH:
        return True
    return is_video(t) == (track == TRACK_VIDEO)


def build_masks(tensors, track=TRACK_AUDIO, strength=1.0,
                t_start_pct=0.0, t_end_pct=100.0, t_feather_pct=4.0,
                x_pct=0.0, y_pct=0.0, w_pct=100.0, h_pct=100.0, feather_pct=6.0):
    """One mask per tensor, same shape and device, ready to hand to the sampler.

    Percentages are of each tensor's own axes, so the same numbers describe the same region
    whatever the resolution. Note the time resolution of the video mask is one latent frame,
    which is roughly four rendered frames - a span cannot be selected more finely than that.
    """
    masks = []
    for t in tensors:
        if not track_is_free(t, track):
            masks.append(torch.zeros_like(t, dtype=torch.float32))
            continue
        dev = t.device

        def cells(pct, n):
            return pct / 100.0 * n

        if is_video(t):
            _, _, T, H, W = t.shape
            mt = ramp(T, cells(t_start_pct, T), cells(t_end_pct, T), cells(t_feather_pct, T), dev)
            my = ramp(H, cells(y_pct, H), cells(y_pct + h_pct, H), cells(feather_pct, H), dev)
            mx = ramp(W, cells(x_pct, W), cells(x_pct + w_pct, W), cells(feather_pct, W), dev)
            m = mt.view(1, 1, T, 1, 1) * my.view(1, 1, 1, H, 1) * mx.view(1, 1, 1, 1, W)
        else:
            # audio is (B, C, 2, L): time is the last axis and there is no rectangle
            L = t.shape[-1]
            m = ramp(L, cells(t_start_pct, L), cells(t_end_pct, L), cells(t_feather_pct, L), dev)
            m = m.view(*([1] * (t.ndim - 1)), L)
        masks.append((m * strength).expand_as(t).contiguous().to(torch.float32))
    return masks
