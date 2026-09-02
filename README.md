# comfyui-minimax-h3-inpaint-tools

**English** · [日本語](README.ja.md)

Latent-level editing for **MiniMax H3** in ComfyUI: rewrite the audio of a finished clip without
touching the picture, rewrite one time span of a shot, or resize a latent spatially — all without
decoding to frames and re-encoding.

Nothing here is a model or a sampler. It is ten small nodes that work around one fact about H3's
latent format, plus one thing ComfyUI already supports that nobody seems to use.

---

## What a rewrite looks like

A finished 15-second commercial came back with a broken logo. The curved lettering on the emblem
had grown an extra, malformed glyph — 価◯格比較 where it should read 価格比較 — in the one part of
the frame a client is guaranteed to read.

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/logo-fix.webp" width="820" alt="The emblem, old above and new below: an extra glyph in the curved lettering, then the corrected version">

Regenerating the shot would have fixed the glyph and changed everything else with it. H3's sample
follows the seed and the resolution, not how close the previous attempt was, so a re-run is a
different clip - different camera drift, different sparkles, a different take. On a spot that has
already been approved, that is not a fix.

So the shot was not regenerated. Its latent was loaded back, a rectangle was drawn over the
emblem, and the sampler was allowed to move **only inside that rectangle**.

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/logo-zoom.webp" width="700" alt="Zooming into the emblem, old above and new below">

### Everything outside the mask is the same clip

Red marks where the two renders differ.

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/diff-highlight.webp" width="760" alt="The commercial with changed pixels highlighted in red; only the rewritten regions light up">

The regions that were freed light up. The sky, the price cards, the body copy - none of it is
regenerated, because none of it was ever handed to the sampler. Outside the mask the original
latent is written back at every step:

```python
out = out * denoise_mask + latent_image * (1 - denoise_mask)
```

A mask of `0` pins a region to the latent it started from. That is not a blend at the end, it is
enforced at every step of the schedule, which is why the untouched area comes back identical
rather than merely similar.

### It is not only lettering

The same mechanism with the rectangle over a person instead of an emblem. Only the right-hand
side of the frame was freed here: the outfit changes, and the caption at bottom left and the sky
behind it stay where they were.

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/scene-swap.webp" width="560" alt="One cut before and after: the character's outfit changes, the caption does not">

### The whole spot, before and after

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/before-after.webp" width="460" alt="The full 15-second commercial, original above and rewritten below">

Full quality, with sound:
[logo](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/compare-logo-zoom.mp4) ·
[diff](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/diff-highlight.mp4) ·
[cut](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/compare-scene3.mp4) ·
[whole spot](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/compare-final-vs-r2v.mp4)

The clips above are sample material, shown to explain what the nodes do. They are not covered by
the licences in this repository and are not offered for reuse.

## Why these nodes exist

H3 does not hand you a plain latent tensor. It hands you a `comfy.nested_tensor.NestedTensor`,
which is a thin wrapper around a **list** of tensors:

```
[0] video   (B, 24, T, H, W)     H,W = pixels / 16
[1] audio   (B, 32, 2, L)        L does NOT depend on resolution
```

Two consequences follow, and both are useful.

**Core latent nodes break on it.** `LatentUpscale` calls `.reshape` on the latent and dies with
`'NestedTensor' object has no attribute 'reshape'`. Anything that assumes one tensor will do the
same.

**The two tracks are independent.** The audio latent is a separate tensor of its own, so it can
be replaced, masked or resampled without the video tensor being involved at all. Its length does
not change with resolution — a 0.4 MP run and a 1.5 MP run of the same shot both produce
`(1, 32, 2, 178)`.

And the thing ComfyUI already supports:

```python
# comfy/samplers.py
if denoise_mask.is_nested:
    denoise_masks = denoise_mask.unbind()
...
x   = x   * denoise_mask + scale_latent_inpaint(...) * (1 - denoise_mask)
out = out * denoise_mask + latent_image              * (1 - denoise_mask)
```

The sampler accepts a **nested** denoise mask and applies each part to the matching tensor. A
mask of `0` pins that region to `latent_image` at every step; `1` lets it move freely. So a mask
of `[zeros_like(video), ones_like(audio)]` holds the picture perfectly still and resamples only
the soundtrack — with the real video attended at every step, so the new audio is written against
the mouth movements that are already on screen.

That is the whole idea. The nodes just build the masks and move latents around.

---

## Nodes

| Node | What it does |
|---|---|
| **Partial Denoise Mask** | Pin most of a latent and resample a chosen part: one track (audio / video / both), a time span, a rectangle. This is the main one. |
| **Time Range (frames)** | Frame numbers in, percentages out, with the frames that will actually move shown on the node. Time resolution is one latent frame, so the ends snap. |
| **Region Picker** | Drag a rectangle on the image instead of typing four percentages. Reads the frame in the browser when the upstream node is `LoadImage` or `LoadVideo`, without running the graph. |
| **Save Latent** | Write an H3 latent to safetensors. bf16 by default. |
| **Load Latent** | Read one back. |
| **Pack Latent** | Build a nested latent from a separately-encoded video latent and audio latent — for clips whose latent was never saved. |
| **Latent Composite** | Blend two finished latents over a rectangle and/or time span. Post-hoc; prefer the mask. |
| **Latent Spatial Resize** | Resize a latent spatially, keeping the nesting and leaving audio alone. |
| **Latent Extend** | Stretch a latent along time and generate the continuation, with the original span pinned. Worked on the first attempt (39 to 73 frames, 37.3 dB on the fixed part) but has not been run enough times to call reproducible. |
| **Latent Inspect** | Print the shapes and dtypes inside a nested latent. |

### Partial Denoise Mask

The one that matters. Wire it between the latent you are keeping and the sampler:

```
finished latent ──► Partial Denoise Mask ──► SamplerCustomAdvanced.latent_image
RandomNoise(new seed) ────────────────────► SamplerCustomAdvanced.noise
```

| Input | Notes |
|---|---|
| `track` | `audio only` / `video only` / `both` |
| `strength` | `1.0` = the selected region is fully free. Lower values pull it back toward the original each step. |
| `t_start_pct`, `t_end_pct` | The span to rewrite, as a percentage of the clip. |
| `t_feather_pct` | Soft edge in time. Without it the seam shows. |
| `x/y/w/h_pct`, `feather_pct` | A rectangle, video track only. Audio has no geometry. |

The pinned region is present at every sampling step, so whatever is being rewritten is written
*against* it. This is not the same as generating twice and compositing: a rewritten time span
sees the frames on both sides of it while it is being made.

**The pass must be given real noise.** The mask is applied as
`x = x*mask + scale_latent_inpaint(x, sigma, noise, latent_image)*(1-mask)`, so the pinned region
is rebuilt at the current sigma *from the sampler's noise*. Hand the sampler `DisableNoise` and
that term collapses: the pinned region gets noise-free values while the sampler is still at a
high sigma, and the output is garbage - a field of coloured blocks, not a picture. This rules out
the two-phase PDD warmup (workflow 005), whose second phase runs on `DisableNoise` by design.
Measured: the warmup version of a text fix came back completely destroyed while the same mask on
a single plain pass was clean.

**PDD runs with a mask, but do not use it for detail.** The mask does not touch the schedule, so
`MiniMaxH3PDDAccApply` driving its own 8-step sigmas is perfectly legal alongside one - that was
measured, not assumed. What is illegal is a *shortened* schedule: `BasicScheduler` with
`denoise < 1` lands off the trained grid and raises `model evaluated at sigma …, which is not a
trained PDD block boundary`. And on a text repair the distilled pass came back visibly worse than
the plain model at the same step count, with characters malformed again. Plain model for
fine detail; PDD only if the rewritten region is coarse.

---

## Measured

CM scene 1, 1664×928, 107 frames, RTX 3090.

| | Time |
|---|---|
| Full generation, PDD 8-step | **845 s** |
| Audio-only re-roll, 4 steps, plain model | **360 s** (−57%) |

The picture came back at **PSNR ≈ 40 dB** against the original — indistinguishable by eye, and
the difference is VAE decode noise rather than the latent moving.

### What did not work

A two-stage "generate small, upscale the latent, finish at full size" pass — the trick that
motivated `Latent Spatial Resize` — **is not worth it on this model**:

| | Time |
|---|---|
| Direct 1.5 MP | 845 s |
| 0.4 MP → 1.5 MP, 4 finishing steps | 705 s, but a **different shot** |
| 0.75 MP → 1.5 MP, 4 finishing steps | 820 s, only 3% saved |

Two reasons. Stage 2 has to run on the plain model (see the PDD note above) at ~90 s/step, which
eats the saving. And H3's sample depends on resolution, so starting small does not produce a
cheaper version of the same clip — it produces a different one. Small detail such as legible
Japanese text simply never appears if stage 1 was too small to form it.

Also worth knowing: **`BasicScheduler` still runs `steps` iterations when `denoise < 1`.** It
shortens the sigma range, not the step count. Set the step count explicitly.

---

## Recipes

**Re-roll the audio of a finished clip.** Load its latent, mask `audio only`, sample 4 steps with
a new seed. The picture is bit-preserved; only the soundtrack changes, and it is written against
the existing mouth movements.

**Rewrite seconds 3–5 of a 15-second shot.** Mask `both`, `t_start_pct` / `t_end_pct` over the
span, feather 4–6%. Everything outside stays exactly as it was.

**Fix one corner of the frame.** Mask `video only`, set the rectangle, feather 6%.

**Nudge rather than replace.** Drop `strength` to 0.4–0.6, or lower the scheduler's `denoise`.
`strength` blends toward the original every step; `denoise` starts from a partially noised
version. They are not the same lever.

**Edit a clip whose latent was lost.** `LoadVideo` → `VAEEncode` (video VAE) and `VAEEncodeAudio`
(audio VAE) → **Pack Latent**. Costs one VAE round trip across the whole clip, so the untouched
regions degrade slightly too. Saving the latent at generation time is better.

---

## Notes

- The Contex Loop chain (`MiniMaxH3ChainSegmentSave`) already stores per-clip latents in its
  checkpoints. Single-shot R2V / I2V / T2V graphs do not — add **Save Latent** next to your
  SaveVideo node.
- bf16 halves the file (~215 MB for 4.5 s at 1.5 MP) and is the precision the model runs in. The
  original dtype is recorded and restored on load.
- Latent geometry is `pixels / 16` spatially. Temporally, 107 frames became `T = 32`, so one
  latent frame is roughly 3.3 real frames — about 0.14 s at 24 fps. That is the finest time slice
  a mask can address.

## Requirements

ComfyUI with MiniMax H3 support (the nodes import `comfy.nested_tensor`), plus one Python
package: [`minimax-h3-latent-core`](https://pypi.org/project/minimax-h3-latent-core/), which
holds the algorithms these nodes wrap. Everything else comes with ComfyUI.

## Install

```
git clone <this repo> ComfyUI/custom_nodes/comfyui-minimax-h3-inpaint-tools
pip install -r ComfyUI/custom_nodes/comfyui-minimax-h3-inpaint-tools/requirements.txt
```

Use the same Python that runs ComfyUI for the second line. Installing through ComfyUI Manager
does both steps for you.

Restart ComfyUI. The nodes appear under **MiniMax H3/latent**.

## Example workflows

`workflows/` holds six that were run before being included - a region rewrite driven from an
mp4 (R2V, I2V and a T2V variant that failed instructively), a clip extension, and two that work
from a Contex Loop chain checkpoint. `workflows/README.md` says what each costs and what to
repoint before running it.

## Licence

This repository is GPL-3.0 throughout. The library the nodes depend on,
[`minimax-h3-latent-core`](https://github.com/panghea/minimax-h3-latent-core), is PolyForm Small
Business 1.0.0 - free for individuals and for companies with **fewer than 100 people** and
**under USD 1,000,000 revenue** in the prior tax year. Above that threshold see
[COMMERCIAL.md](COMMERCIAL.md). [LICENSING.md](LICENSING.md) explains why the two are split.
