# -*- coding: utf-8 -*-
"""Continue a finished clip by growing its latent, instead of restarting from its last frame.

Image-to-video sees one still and has to invent the motion that produced it. Here the whole clip
stays in the tensor and is pinned by the mask, so the sampler attends to the entire run-up at
every step - camera move, speed, direction of travel - and writes the continuation against it.

This is the same mechanism as the region rewrites in this pack, pointed along time rather than
across the frame.

UNTESTED against the model's training distribution. H3 was trained on fixed lengths and nothing
promises it behaves at a seam manufactured this way. Treat a good result as luck until it repeats.
"""
import torch

from . import _comfy_bridge as bridge
from ._core_import import core


class MiniMaxH3LatentExtend:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'samples': ('LATENT', {'tooltip': 'The finished clip to continue.'}),
                'extra_frames': ('INT', {'default': 34, 'min': 1, 'max': 3600, 'step': 1,
                                         'tooltip': 'Rendered frames to add. The total is '
                                                    'rounded up onto H3\'s 17k+5 grid, so the '
                                                    'tail may come out a little longer than '
                                                    'asked.'}),
                'strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.05,
                                       'tooltip': '1.0 builds the tail from noise. Lower values '
                                                  'have nothing to pull back toward - the new '
                                                  'region starts empty - so keep this at 1.0 '
                                                  'unless you are experimenting.'}),
                'feather_latent_frames': ('FLOAT', {
                    'default': 0.5, 'min': 0.0, 'max': 8.0, 'step': 0.5,
                    'tooltip': 'Softens the join, in latent frames. One latent frame is about '
                               'three rendered frames.'}),
            },
            'optional': {
                'reference': ('VIDEO', {
                    'tooltip': 'The video reference this run will use, if any. A reference has '
                               'to cover the whole generated length, so connecting it here caps '
                               'the extension at what the reference can supply instead of '
                               'letting the run fail at the prep node.'}),
                'reference_frames': ('INT', {
                    'default': 0, 'min': 0, 'max': 100000,
                    'tooltip': 'Same cap, typed in, for when the reference is not a VIDEO. '
                               '0 means no cap.'}),
            },
        }

    RETURN_TYPES = ('LATENT', 'INT', 'STRING')
    RETURN_NAMES = ('samples', 'length', 'report')
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    OUTPUT_NODE = True
    DESCRIPTION = ('Pad an H3 latent along time and mask the new tail free, so the model '
                   'continues the clip while seeing all of it. Feed `length` to the '
                   'conditioning node - it will not match the source clip any more.')

    def run(self, samples, extra_frames, strength, feather_latent_frames,
            reference=None, reference_frames=0):
        lat = samples['samples']
        if not bridge.is_nested(lat):
            raise TypeError('expected a MiniMax H3 nested latent, got %s' % type(lat).__name__)
        tensors, _ = bridge.tensors_of(lat)
        video = next((t for t in tensors if t.ndim == 5), None)
        if video is None:
            raise ValueError('no video tensor in this latent')

        old_T = int(video.shape[2])
        old_frames = core.frames_for_latent(old_T)
        length, new_T = core.extend_plan(old_T, extra_frames)

        # A video reference must cover the whole generated length. Rather than let the prep node
        # refuse the run after the fact, cap the extension here and say so - the constraint
        # belongs in the graph, not in the operator's head.
        cap = int(reference_frames)
        if reference is not None:
            try:
                cap = min(cap, int(reference.get_components().images.shape[0])) if cap                     else int(reference.get_components().images.shape[0])
            except Exception:
                pass
        capped = ''
        if cap:
            # the prep node measures a file one frame short of its count, so leave a frame spare
            usable = core.snap_length(max(5, cap - 1), 'down')
            if usable < length:
                capped = ('\ncapped at %d: the reference holds %d frames and has to cover the '
                          'whole length. Asked for %d.' % (usable, cap, length))
                length = usable
                new_T = core.latent_frames_for(length)
        if length <= old_frames:
            raise ValueError(
                'nothing to extend: the reference allows at most %d frames and the clip is '
                'already %d. Supply a longer reference, or disconnect it.'
                % (length, old_frames))

        grown = core.extend_tensors(tensors, new_T)
        grown = core.scale_audio(grown, old_T, new_T)
        masks = core.extend_masks(grown, old_T, new_T,
                                  feather=feather_latent_frames, strength=strength)

        report = ('%d frames (T=%d) -> %d frames (T=%d), adding %d\n'
                  'the first %d frames are pinned; the sampler sees them at every step\n'
                  'set the conditioning length to %d, or it will not match'
                  % (old_frames, old_T, length, new_T, length - old_frames, old_frames, length))
        report += capped
        print('[H3LatentExtend] ' + report.replace('\n', ' | '))

        out = dict(samples)
        out['samples'] = bridge.rewrap(lat, grown)
        out['noise_mask'] = bridge.rewrap(lat, masks)
        return {'ui': {'text': [report]},
                'result': (out, int(length), report)}


NODE_CLASS_MAPPINGS = {'MiniMaxH3LatentExtend': MiniMaxH3LatentExtend}
NODE_DISPLAY_NAME_MAPPINGS = {'MiniMaxH3LatentExtend': 'MiniMax H3 Latent Extend (continue clip)'}
