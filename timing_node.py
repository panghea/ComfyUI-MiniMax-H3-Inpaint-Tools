# -*- coding: utf-8 -*-
"""Give the denoise mask a time range in frames instead of percentages.

Percentages are what the mask takes, but nobody thinks in them. Every timing mistake in this
project came from the conversion: a mask asked for 18% when the subject appeared at frame 22 of
107 (20.6%), so it was still ramping when she arrived and the first frames kept the old look.

This node does the division, and - more usefully - reports what the mask will *actually* cover
once it lands on the latent's much coarser time axis. Connect `samples` and the report appears
before the run rather than being discovered in the output.
"""
import torch

from ._core_import import core

frames_to_pct = core.frames_to_pct
describe = core.describe
snap_length = core.snap_length
valid_length = core.valid_length

LABEL_H = 26


def _strip(images, a, b):
    """Two frames side by side, each with its number written under it.

    Server-side so it still works with the JavaScript half missing - and after a run it shows the
    frames that were actually used, not the ones the browser guessed at.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    n = images.shape[0]
    picks = [(max(0, min(n - 1, a)), 'start %d' % a),
             (max(0, min(n - 1, b)), 'end %d (last)' % b)]
    tiles = []
    for idx, caption in picks:
        arr = (images[idx].clamp(0, 1) * 255).to(torch.uint8).cpu().numpy()
        im = Image.fromarray(arr)
        w, h = im.size
        canvas = Image.new('RGB', (w, h + LABEL_H), (18, 18, 22))
        canvas.paste(im, (0, 0))
        d = ImageDraw.Draw(canvas)
        d.text((6, h + 6), caption, fill=(255, 120, 60))
        tiles.append(canvas)
    w = sum(t.size[0] for t in tiles) + 8
    h = max(t.size[1] for t in tiles)
    out = Image.new('RGB', (w, h), (18, 18, 22))
    x = 0
    for t in tiles:
        out.paste(t, (x, 0))
        x += t.size[0] + 8
    import numpy as np
    return torch.from_numpy(np.array(out).astype('float32') / 255.0).unsqueeze(0)


class MiniMaxH3TimeRange:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'samples': ('LATENT', {'tooltip': 'The latent the mask will be built on. Its '
                                                  'time axis is what the frame numbers are '
                                                  'measured against - there is nothing to type '
                                                  'in, and nothing that can fall out of sync.'}),
                'start_frame': ('INT', {'default': 0, 'min': 0, 'max': 100000,
                                        'tooltip': 'First frame to rewrite.'}),
                'end_frame': ('INT', {'default': 107, 'min': 0, 'max': 100000,
                                      'tooltip': 'One past the last frame to rewrite, like a '
                                                 'Python slice.'}),
            },
            'optional': {
                'video': ('VIDEO', {'tooltip': 'Only for the thumbnails - the clip being '
                                               'rewritten, so you can see which frames you are '
                                               'choosing. It has no say in the numbers.'}),
                'images': ('IMAGE', {'tooltip': 'Same, if the frames are already decoded.'}),
            },
        }

    RETURN_TYPES = ('FLOAT', 'FLOAT', 'INT', 'STRING', 'IMAGE')
    RETURN_NAMES = ('t_start_pct', 't_end_pct', 'length', 'report', 'preview')
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    OUTPUT_NODE = True
    DESCRIPTION = ('Convert a frame range into the percentages the Partial Denoise Mask wants, '
                   'and report how far the latent grid widens it.')

    def run(self, samples, start_frame, end_frame, video=None, images=None):
        if images is None and video is not None:
            images = video.get_components().images

        from . import _comfy_bridge as bridge
        tensors, _ = bridge.tensors_of(samples['samples'])
        v = next((t for t in tensors if t.ndim == 5), None)
        if v is None:
            raise ValueError('no video tensor in this latent')
        latent_frames = int(v.shape[2])
        # The latent is the only source. It is the tensor the mask is built on, so a number
        # taken from anywhere else - a file, a widget - could only ever disagree with it.
        total_frames = core.frames_for_latent(latent_frames)

        sp, ep = frames_to_pct(total_frames, start_frame, end_frame)
        # what H3 will accept for a clip this long. Snapping down, never up: asking for more
        # frames than the source holds is refused outright
        length = snap_length(total_frames, 'down')
        report = describe(total_frames, start_frame, end_frame, latent_frames)
        if not valid_length(total_frames):
            report += ('\nlength %d - the clip is %d frames, which is not a valid H3 length '
                       '(needs %% 17 == 5), so the last %d are dropped'
                       % (length, total_frames, total_frames - length))
        else:
            report += '\nlength %d' % length
        report = ('%d frames in the latent (T=%d)' % (total_frames, latent_frames)) + '\n' + report
        if images is not None and int(images.shape[0]) != total_frames:
            report += ('\nthe clip has %d frames but the latent holds %d - following the latent'
                       % (int(images.shape[0]), total_frames))
        print('[H3TimeRange] ' + report.replace('\n', ' | '))

        preview = None
        if images is not None:
            preview = _strip(images, int(start_frame), max(int(start_frame), int(end_frame) - 1))
        if preview is None:
            preview = torch.zeros((1, 8, 8, 3))
        return {'ui': {'text': [report]},
                'result': (float(sp), float(ep), int(length), report, preview)}


NODE_CLASS_MAPPINGS = {'MiniMaxH3TimeRange': MiniMaxH3TimeRange}
NODE_DISPLAY_NAME_MAPPINGS = {'MiniMaxH3TimeRange': 'MiniMax H3 Time Range (frames)'}
