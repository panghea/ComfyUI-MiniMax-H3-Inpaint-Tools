# minimax-h3-latent-core

Partial rewriting of MiniMax H3 latents. Pure PyTorch - nothing here imports ComfyUI.

An H3 latent is two tensors:

```
video   (B, 24, T, H, W)     H, W = pixels / 16
audio   (B, 32, 2, L)        L does not depend on resolution
```

Because they are separate, one can be pinned while the other is resampled - which is what makes
an audio-only re-roll cost a fraction of a full generation, and what lets a rectangle of the
picture be rewritten without disturbing the lettering around it.

## Use

```python
import torch
from minimax_h3_latent_core import build_masks, resize_video_only, save_tensors, load_tensors

video = torch.randn(1, 24, 8, 12, 20)
audio = torch.randn(1, 32, 2, 300)

# free the right half of the frame, only in the middle of the clip; pin the soundtrack
masks = build_masks([video, audio], track='video only', strength=0.9,
                    t_start_pct=25, t_end_pct=75, t_feather_pct=0,
                    x_pct=50, y_pct=0, w_pct=50, h_pct=100, feather_pct=0)

small = resize_video_only([video, audio], 6, 10)   # audio is left alone
save_tensors('clip.safetensors', [video, audio])
tensors, nested, prompt, meta = load_tensors('clip.safetensors')
```

## Traps this library exists to avoid

- **The audio tensor is 4-D, like an image latent.** Resizing "anything 4-D or 5-D" stretches the
  soundtrack. `resize_video_only` touches only the 5-D tensor.
- **A masked pass needs real noise.** Disabling noise collapses the inpaint term and the region
  comes back as blocks.
- **Time resolution is one latent frame**, roughly four rendered frames. A span cannot be
  selected more finely, and the frames at either end of a selection move with it.
- **Length must satisfy `length % 17 == 5`** when a latent is produced by encoding a video. An
  invalid length silently comes back shorter.

## Licence

PolyForm Small Business 1.0.0 - free for individuals and for companies with **fewer than 100
people** and **less than USD 1,000,000 (2019, inflation-adjusted) revenue** in the prior tax
year. `LICENSE` has the exact wording; the summary here is not the licence.

Above that threshold, see `COMMERCIAL.md`.

This library imports nothing from ComfyUI, which is why it can be licensed separately from the
ComfyUI nodes that use it. Those live in `ComfyUI-MiniMax-H3-Inpaint-Tools` under GPL-3.0.

## Contributing

Issues only, no pull requests - `CONTRIBUTING.md` explains why.
