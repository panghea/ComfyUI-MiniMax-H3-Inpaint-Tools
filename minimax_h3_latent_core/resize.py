# -*- coding: utf-8 -*-
"""Spatial resize for H3 latents. Pure tensor code, no ComfyUI import.

The trap this exists for: H3 stores audio as (B, C, 2, L), which is 4-D just like an image
latent. Resizing "anything 4-D or 5-D" therefore stretches the soundtrack. Only the 5-D video
tensor may be touched.
"""
import torch
import torch.nn.functional as F

SPATIAL_DOWNSCALE = 16          # H3 video VAE: 16x in H and W
METHODS = ['bicubic', 'bilinear', 'nearest-exact', 'area']


def resize_tensor(t, h, w, method='bicubic'):
    """Resize the last two dims of a 4-D/5-D tensor, leaving batch, channel and time alone."""
    kw = {} if method in ('nearest-exact', 'area') else {'align_corners': False}
    if t.ndim == 5:                                  # B C T H W
        b, c, f, _, _ = t.shape
        x = t.permute(0, 2, 1, 3, 4).reshape(b * f, c, t.shape[-2], t.shape[-1])
        x = F.interpolate(x.float(), size=(h, w), mode=method, **kw).to(t.dtype)
        return x.reshape(b, f, c, h, w).permute(0, 2, 1, 3, 4).contiguous()
    if t.ndim == 4:                                  # B C H W
        return F.interpolate(t.float(), size=(h, w), mode=method, **kw).to(t.dtype)
    return t


def latent_size(width_px, height_px):
    """Pixel size -> latent grid size."""
    return (max(1, height_px // SPATIAL_DOWNSCALE), max(1, width_px // SPATIAL_DOWNSCALE))


def resize_video_only(tensors, h, w, method='bicubic'):
    """Resize every 5-D tensor in the list; pass everything else through untouched."""
    return [resize_tensor(t, h, w, method) if t.ndim == 5 else t for t in tensors]
