# -*- coding: utf-8 -*-
"""Frame numbers to the percentages the mask wants. Pure tensor code, no ComfyUI import.

Percentages are awkward to get right by hand, and getting them wrong is expensive: a mask that
opens two frames late leaves the first frames of a cut untouched, which looks like the rewrite
failed rather than like an off-by-one.

The conversion itself is only a division. What this module adds is the part that is easy to
forget: the mask lands on the latent's time axis, which is much coarser than the rendered frame
rate, so the range you asked for is not the range you get.
"""


def frames_to_pct(total_frames, start_frame, end_frame):
    """-> (start_pct, end_pct). `end_frame` is exclusive, like a Python slice."""
    if total_frames <= 0:
        raise ValueError('total_frames must be positive')
    start = max(0, min(int(total_frames), int(start_frame)))
    end = max(start, min(int(total_frames), int(end_frame)))
    return (start / total_frames * 100.0, end / total_frames * 100.0)


def snap_to_latent(total_frames, start_pct, end_pct, latent_frames):
    """What the mask will actually cover, in rendered frames.

    The mask is built on the latent's time axis, so both edges move outwards to the nearest
    latent frame boundary. With 107 rendered frames packed into 32 latent frames that is about
    3.3 frames of slack at each end - enough to pull in the last frame of the previous cut.
    """
    if latent_frames <= 0:
        return (0.0, float(total_frames), 0.0)
    per = total_frames / float(latent_frames)
    lo = int(start_pct / 100.0 * latent_frames)
    hi = min(latent_frames, int(round(end_pct / 100.0 * latent_frames)))
    return (lo * per, hi * per, per)


def describe(total_frames, start_frame, end_frame, latent_frames=0):
    """A line to print next to the numbers, so the snapping is visible before the run, not after."""
    sp, ep = frames_to_pct(total_frames, start_frame, end_frame)
    line = ('frames %d-%d of %d  ->  %.2f%% - %.2f%%'
            % (start_frame, end_frame, total_frames, sp, ep))
    if latent_frames > 0:
        a, b, per = snap_to_latent(total_frames, sp, ep, latent_frames)
        line += ('\nlatent T=%d, %.2f rendered frames per latent frame'
                 '\nactually covers frames %.1f-%.1f' % (latent_frames, per, a, b))
        if a > start_frame + 0.01 or b < end_frame - 0.01:
            line += '  <- narrower than asked'
        elif a < start_frame - 0.01 or b > end_frame + 0.01:
            line += '  <- wider than asked'
    return line


GRID = 17          # H3 accepts a length only when length % 17 == 5


def valid_length(frames):
    """True when H3 will accept this many frames."""
    return frames >= 5 and frames % GRID == 5


def snap_length(frames, mode='down'):
    """Nearest length H3 accepts.

    'down' is the safe direction when the frames have to come from an existing clip: asking for
    more than the source holds is rejected outright, and asking for fewer only wastes the tail.
    """
    frames = int(frames)
    if frames < 5:
        return 5
    k = (frames - 5) // GRID
    lo = 5 + k * GRID
    hi = lo + GRID
    if mode == 'down':
        return lo
    if mode == 'up':
        return hi if lo < frames else lo
    return lo if frames - lo <= hi - frames else hi


def latent_frames_for(frames):
    """Latent time steps H3 packs `frames` rendered frames into.

    Measured, not assumed: 107 rendered frames come back as T=32 and 39 as T=12, and
    T = 5(F-5)/17 + 2 fits both. Only valid lengths have an answer.
    """
    if not valid_length(frames):
        raise ValueError('%d is not a valid H3 length (needs %% 17 == 5)' % frames)
    return 5 * (frames - 5) // GRID + 2


def frames_for_latent(latent_frames):
    """The inverse, for reading a length back off a tensor."""
    return GRID * (int(latent_frames) - 2) // 5 + 5
