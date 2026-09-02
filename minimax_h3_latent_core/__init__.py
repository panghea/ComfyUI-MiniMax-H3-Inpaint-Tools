# -*- coding: utf-8 -*-
"""minimax-h3-latent-core - partial rewriting of MiniMax H3 latents.

Pure PyTorch. Nothing in this package imports ComfyUI, so it can be used from a plain script,
a test, or any other host. The ComfyUI nodes in the enclosing package are a thin adapter over
what is here.

An H3 latent is two tensors:

    video   (B, 24, T, H, W)     H, W = pixels / 16
    audio   (B, 32, 2, L)        L does not depend on resolution

Both are addressable independently, which is what makes audio-only re-rolls and region rewrites
possible without regenerating the clip.
"""
from .masks import (ramp, build_masks, is_video, track_is_free,
                    TRACK_AUDIO, TRACK_VIDEO, TRACK_BOTH)
from .blend import mix_audio, blend_video
from .resize import (resize_tensor, resize_video_only, latent_size,
                     SPATIAL_DOWNSCALE, METHODS)
from .serialize import save_tensors, load_tensors, split_video_audio, DTYPES
from .timing import (frames_to_pct, snap_to_latent, describe, snap_length,
                     valid_length, latent_frames_for, frames_for_latent)
from .extend import extend_tensors, scale_audio, extend_masks, plan as extend_plan

__version__ = '0.1.0'
__all__ = [
    'ramp', 'build_masks', 'is_video', 'track_is_free',
    'TRACK_AUDIO', 'TRACK_VIDEO', 'TRACK_BOTH',
    'mix_audio', 'blend_video',
    'resize_tensor', 'resize_video_only', 'latent_size', 'SPATIAL_DOWNSCALE', 'METHODS',
    'save_tensors', 'load_tensors', 'split_video_audio', 'DTYPES',
    'frames_to_pct', 'snap_to_latent', 'describe', 'snap_length', 'valid_length',
    'latent_frames_for', 'frames_for_latent',
    'extend_tensors', 'scale_audio', 'extend_masks', 'extend_plan',
]
