# -*- coding: utf-8 -*-
"""Pick a rectangle on a frame and get it back as percentages.

`MiniMaxH3DenoiseMask` wants `x_pct / y_pct / w_pct / h_pct`, and guessing those from a video by
eye is tedious. This node shows one frame on the node body and lets you drag a rectangle over it;
the four widgets update as you drag, and the same four values come out of the outputs so they can
be wired straight into the mask.

It also returns the frame with the rectangle burned into it. That output is the fallback: even
with the JavaScript half missing, the numbers can be typed in and checked visually.

It takes either an `IMAGE` batch or a `VIDEO` straight from `LoadVideo`, so it can be dropped
next to the loader in a cut-rewrite workflow without decoding anything first.

Run the graph once to get a frame onto the node, then drag. The values persist in the workflow
like any other widget.
"""
import torch

MARK = (1.0, 0.25, 0.1)      # the rectangle colour, RGB 0-1


def _draw_rect(img, x0, y0, x1, y1, thickness=3):
    """Burn an outline into a (H, W, 3) float tensor, in place on a copy."""
    out = img.clone()
    h, w, _ = out.shape
    x0 = max(0, min(w - 1, int(x0)))
    x1 = max(0, min(w, int(x1)))
    y0 = max(0, min(h - 1, int(y0)))
    y1 = max(0, min(h, int(y1)))
    if x1 <= x0 or y1 <= y0:
        return out
    col = torch.tensor(MARK, dtype=out.dtype, device=out.device)
    t = max(1, int(thickness))
    out[y0:y0 + t, x0:x1] = col
    out[max(y0, y1 - t):y1, x0:x1] = col
    out[y0:y1, x0:x0 + t] = col
    out[y0:y1, max(x0, x1 - t):x1] = col
    return out


class MiniMaxH3RegionPicker:
    @classmethod
    def INPUT_TYPES(cls):
        pct = {'min': 0.0, 'max': 100.0, 'step': 0.5}
        return {
            'required': {
                'frame': ('INT', {'default': 0, 'min': 0, 'max': 100000,
                                  'tooltip': 'Which frame to show. Percentages do not depend on '
                                             'it - it only changes what you are looking at.'}),
                'x_pct': ('FLOAT', dict(pct, default=25.0)),
                'y_pct': ('FLOAT', dict(pct, default=25.0)),
                'w_pct': ('FLOAT', dict(pct, default=50.0)),
                'h_pct': ('FLOAT', dict(pct, default=50.0)),
            },
            'optional': {
                'images': ('IMAGE', {'tooltip': 'A decoded clip, or any image batch.'}),
                'video': ('VIDEO', {'tooltip': 'A VIDEO straight from LoadVideo - saves having '
                                               'to decode the clip just to pick a rectangle.'}),
            },
        }

    RETURN_TYPES = ('FLOAT', 'FLOAT', 'FLOAT', 'FLOAT', 'IMAGE')
    RETURN_NAMES = ('x_pct', 'y_pct', 'w_pct', 'h_pct', 'preview')
    FUNCTION = 'run'
    CATEGORY = 'MiniMax H3/latent'
    OUTPUT_NODE = True
    DESCRIPTION = ('Drag a rectangle on a frame and read it out as percentages for the Partial '
                   'Denoise Mask. The preview output shows the rectangle burned in.')

    def run(self, frame, x_pct, y_pct, w_pct, h_pct, images=None, video=None):
        if images is None and video is not None:
            # a VIDEO carries its own frames; pulling them here means the picker can sit next to
            # LoadVideo instead of behind a decode
            images = video.get_components().images
        if images is None:
            raise ValueError('connect either images or video')

        n = images.shape[0]
        idx = max(0, min(n - 1, int(frame)))
        img = images[idx]
        h, w, _ = img.shape
        x0 = w * x_pct / 100.0
        y0 = h * y_pct / 100.0
        x1 = x0 + w * w_pct / 100.0
        y1 = y0 + h * h_pct / 100.0
        preview = _draw_rect(img, x0, y0, x1, y1, thickness=max(2, int(min(w, h) * 0.004)))
        return {
            'ui': {'h3_region': [{'x': x_pct, 'y': y_pct, 'w': w_pct, 'h': h_pct,
                                  'frames': n, 'width': w, 'height': h}]},
            'result': (float(x_pct), float(y_pct), float(w_pct), float(h_pct),
                       preview.unsqueeze(0)),
        }


NODE_CLASS_MAPPINGS = {'MiniMaxH3RegionPicker': MiniMaxH3RegionPicker}
NODE_DISPLAY_NAME_MAPPINGS = {'MiniMaxH3RegionPicker': 'MiniMax H3 Region Picker'}
