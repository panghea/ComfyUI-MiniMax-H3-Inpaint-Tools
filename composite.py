# -*- coding: utf-8 -*-
"""Composite two MiniMax H3 latents - swap the audio, or rewrite part of the picture.

H3's latent is a `NestedTensor` holding two independent tensors:

    [0] video   (B, 24, T, H, W)   H,W = pixels/16, T = latent frames
    [1] audio   (B, 32, 2, L)      L does NOT depend on resolution

Because the two are separate, the audio can be taken from a different run entirely. And because
the video tensor is an ordinary grid, a rectangle of it can be replaced by the same rectangle
from another run and feathered at the edges.

Two things this buys:

  audio re-roll        Sample a cheap 0.4 MP pass with a new seed, keep only its audio, put it
                       on the finished 1.5 MP video. The audio is identical in shape either way,
                       so nothing has to be resized.
  partial rewrite      Sample the same shot twice with different seeds (or a changed prompt),
                       then keep B only inside a rectangle and/or a time span. Everything the
                       two runs share stays bit-identical, so the seam has little to hide.

Both are post-sampling composites: the sampler still runs in full. `noise_mask` would be the
cheaper route but the mask gets broadcast onto the audio tensor too and the shapes do not match.
"""
import torch

from . import _comfy_bridge as bridge
from ._core_import import core

blend_video = core.blend_video
mix_audio = core.mix_audio
split_video_audio = core.split_video_audio


def _split(latent):
    lat = latent['samples']
    tensors, nested = bridge.tensors_of(lat)
    if not nested:
        return None, lat, []
    video, others = split_video_audio(tensors)
    return lat, video, others


class MiniMaxH3LatentComposite:
    @classmethod
    def INPUT_TYPES(cls):
        pct = {'default': 0.0, 'min': 0.0, 'max': 100.0, 'step': 0.5}
        return {
            'required': {
                'base': ('LATENT', {'tooltip': 'The clip you are keeping.'}),
                'overlay': ('LATENT', {'tooltip': 'The clip you are taking from.'}),
                'audio': (['keep base', 'take overlay', 'mix'], {'default': 'keep base'}),
                'audio_mix': ('FLOAT', {'default': 0.5, 'min': 0.0, 'max': 1.0, 'step': 0.05,
                                        'tooltip': '0 = base, 1 = overlay. Only used for "mix".'}),
                'video': (['keep base', 'take overlay', 'region'], {'default': 'keep base'}),
                'x_pct': ('FLOAT', dict(pct, tooltip='Left edge of the rewritten rectangle, %.')),
                'y_pct': ('FLOAT', pct),
                'w_pct': ('FLOAT', dict(pct, default=100.0)),
                'h_pct': ('FLOAT', dict(pct, default=100.0)),
                'feather_pct': ('FLOAT', {'default': 6.0, 'min': 0.0, 'max': 50.0, 'step': 0.5,
                                          'tooltip': 'Soft edge on the rectangle, % of frame.'}),
                't_start_pct': ('FLOAT', dict(pct, tooltip='Start of the rewritten span, % of '
                                                           'the clip.')),
                't_end_pct': ('FLOAT', dict(pct, default=100.0)),
                't_feather_pct': ('FLOAT', {'default': 4.0, 'min': 0.0, 'max': 50.0,
                                            'step': 0.5}),
            }
        }

    RETURN_TYPES = ('LATENT',)
    RETURN_NAMES = ('samples',)
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    DESCRIPTION = ('Take the audio and/or a rectangle-and-time-span of the picture from a second '
                   'H3 latent. Use it to re-roll audio cheaply, or to rewrite part of a shot.')

    def run(self, base, overlay, audio, audio_mix, video,
            x_pct, y_pct, w_pct, h_pct, feather_pct,
            t_start_pct, t_end_pct, t_feather_pct):
        tmpl_a, vid_a, oth_a = _split(base)
        _tmpl_b, vid_b, oth_b = _split(overlay)
        if vid_a is None or vid_b is None:
            raise ValueError('both inputs must carry a video latent')

        out_others = mix_audio(oth_a, oth_b, audio, audio_mix)

        out_video = vid_a
        if video == 'take overlay':
            if vid_a.shape != vid_b.shape:
                raise ValueError('video latents differ in shape %s vs %s'
                                 % (tuple(vid_a.shape), tuple(vid_b.shape)))
            out_video = vid_b
        elif video == 'region':
            out_video = blend_video(vid_a, vid_b, x_pct, y_pct, w_pct, h_pct, feather_pct,
                                    t_start_pct, t_end_pct, t_feather_pct)

        out = dict(base)
        if tmpl_a is None:
            out['samples'] = out_video
        else:
            rebuilt, oi = [], 0
            for t in tmpl_a.tensors:
                if t.ndim == 5:
                    rebuilt.append(out_video)
                else:
                    rebuilt.append(out_others[oi])
                    oi += 1
            out['samples'] = bridge.rewrap(tmpl_a, rebuilt)
        return (out,)


NODE_CLASS_MAPPINGS = {'MiniMaxH3LatentComposite': MiniMaxH3LatentComposite}
NODE_DISPLAY_NAME_MAPPINGS = {'MiniMaxH3LatentComposite': 'MiniMax H3 Latent Composite'}
