# -*- coding: utf-8 -*-
"""Grow an H3 latent along time, so a finished clip can be continued rather than restarted.

Pure tensor code, no ComfyUI import.

The point of doing this in latent space instead of handing the last frame to an image-to-video
pass: I2V sees one still and has to invent the motion that led to it. Here every latent frame of
the original stays in the tensor and is pinned by the mask, so the sampler attends to the whole
run-up at every step - the camera move, the speed, the direction of travel - and writes the
continuation against it.

Untested against the model's training distribution. H3 was trained on fixed lengths, and nothing
guarantees it behaves at a seam that was manufactured this way.
"""
import torch

from .masks import ramp
from .timing import latent_frames_for, frames_for_latent


def extend_tensors(tensors, new_latent_frames):
    """Pad every tensor's time axis out to `new_latent_frames`, leaving the original untouched.

    The padding value does not matter: the mask frees that region completely, so the sampler
    replaces it from noise. Zeros keep it obvious in an inspector.
    """
    out = []
    for t in tensors:
        if t.ndim == 5:                                  # video (B, C, T, H, W)
            grow = new_latent_frames - t.shape[2]
            if grow <= 0:
                out.append(t)
                continue
            pad = torch.zeros((t.shape[0], t.shape[1], grow) + tuple(t.shape[3:]),
                              dtype=t.dtype, device=t.device)
            out.append(torch.cat([t, pad], dim=2))
        else:                                            # audio (B, C, 2, L)
            out.append(t)
    return out


def scale_audio(tensors, old_latent_frames, new_latent_frames):
    """Stretch the audio tensor by the same proportion, so the two tracks stay the same length."""
    out = []
    for t in tensors:
        if t.ndim == 5:
            out.append(t)
            continue
        new_len = int(round(t.shape[-1] * new_latent_frames / float(old_latent_frames)))
        grow = new_len - t.shape[-1]
        if grow <= 0:
            out.append(t)
            continue
        pad = torch.zeros(tuple(t.shape[:-1]) + (grow,), dtype=t.dtype, device=t.device)
        out.append(torch.cat([t, pad], dim=-1))
    return out


def extend_masks(tensors, kept_latent_frames, new_latent_frames, feather=0.0, strength=1.0):
    """0 over the original span, `strength` over the new tail.

    The audio tensor has its own, longer time axis, so the boundary is placed proportionally
    rather than at the same index - putting it at the video's index would free most of the
    existing soundtrack.

    A feather across the join softens the step from 'reproduce this exactly' to 'invent this',
    which is where a hard boundary tends to show as a jump.
    """
    masks = []
    for t in tensors:
        if t.ndim == 5:
            n = t.shape[2]
            kept = kept_latent_frames
            axis = 2
        else:
            n = t.shape[-1]
            kept = int(round(n * kept_latent_frames / float(new_latent_frames)))
            axis = t.ndim - 1
        m = ramp(n, kept, n, feather, t.device)
        shape = [1] * t.ndim
        shape[axis] = n
        masks.append((m.view(*shape) * strength).expand_as(t).contiguous().to(torch.float32))
    return masks


def plan(old_latent_frames, extra_frames):
    """-> (new rendered length, new latent frames). `extra_frames` is in rendered frames."""
    old_frames = frames_for_latent(old_latent_frames)
    target = old_frames + int(extra_frames)
    # round up onto the grid: a continuation may as well use the whole step
    from .timing import snap_length, valid_length
    if not valid_length(target):
        target = snap_length(target, 'up')
    return target, latent_frames_for(target)
