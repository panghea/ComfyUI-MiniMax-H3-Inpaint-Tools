# ComfyUI-MiniMax-H3-Inpaint-Tools

[日本語](README.ja.md)

Rewrite part of a finished MiniMax H3 clip instead of regenerating it. Ten nodes.

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/logo-fix.webp" width="760" alt="The emblem before and after: an extra glyph in the curved lettering, then the corrected version">

The logo in this spot came back with an extra glyph in it. Regenerating would have fixed the
glyph and changed the camera drift, the sparkles and the take along with it, so the latent was
reloaded and only that rectangle was resampled.

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/diff-highlight.webp" width="700" alt="The commercial with changed pixels highlighted in red">

Red is every pixel that differs between the two renders.
[Full clips with sound](docs/media). The footage is sample material and is not covered by the
licences here.

## What it does

**Inpaint a region.** A rectangle, a time span, or both. Feather the edges or the seam shows.

**Replace the audio only.** 845 s for a full generation, 360 s for an audio re-roll on the same
shot (1664x928, 107 frames, RTX 3090). The picture is bit-preserved, and because the pinned
video is attended at every step the new take is written against the mouth movements already on
screen rather than laid over them.

**Extend a clip.** The original span stays pinned while the continuation is generated. 39 to 73
frames worked, held part at 37.3 dB, seam continuous. One success is not reproducibility, and I
have not run it enough times to claim any.

### How

H3 returns a `comfy.nested_tensor.NestedTensor` wrapping `[video, audio]` rather than one
tensor, and ComfyUI's sampler already accepts a nested denoise mask:

```python
out = out * denoise_mask + latent_image * (1 - denoise_mask)
```

A mask of `0` pins that region to the latent it started from, at every step rather than as a
composite at the end. That is why untouched areas come back identical instead of similar. These
nodes build the masks and move latents around. None of them touch the denoising.

The two tracks are separate tensors, so `[zeros_like(video), ones_like(audio)]` holds the
picture completely still and resamples only the soundtrack. Audio length does not scale with
resolution: 0.4 MP and 1.5 MP runs of the same shot both give `(1, 32, 2, 178)`.

### Nodes

| Node | What it does |
|---|---|
| **Partial Denoise Mask** | The main one. Pin a latent and free part of it: track, time span, rectangle. |
| **Time Range (frames)** | Frame numbers in, percentages out. Shows which frames will actually move. |
| **Region Picker** | Drag the rectangle on the image. Reads the frame in the browser when the upstream node is `LoadImage` or `LoadVideo`. |
| **Save / Load Latent** | safetensors, bf16 by default. Original dtype is restored on load. |
| **Pack Latent** | Build a nested latent from separately encoded video and audio latents. |
| **Latent Composite** | Blend two finished latents. Post-hoc; prefer the mask. |
| **Latent Spatial Resize** | Resize spatially, leaving audio alone. |
| **Latent Extend** | Stretch along time and generate the continuation. |
| **Latent Inspect** | Shapes and dtypes. |

Wire the mask between the latent you are keeping and the sampler:

```
finished latent ──► Partial Denoise Mask ──► SamplerCustomAdvanced.latent_image
RandomNoise(new seed) ────────────────────► SamplerCustomAdvanced.noise
```

### Things that cost me time

- **The audio latent is 4-D**, same rank as an image latent. Anything that resizes "whatever is
  4-D or 5-D" stretches the soundtrack. Touch only the 5-D tensor.
- **A masked pass needs real noise.** `DisableNoise` collapses the inpaint term and the region
  comes back as coloured blocks. This rules out the two-phase PDD warmup, whose second phase
  runs on `DisableNoise` by design.
- **PDD works alongside a mask, but not for fine detail.** A shortened schedule
  (`BasicScheduler` with `denoise < 1`) lands off the trained grid and raises `not a trained PDD
  block boundary`. On a text repair the distilled pass came back worse than the plain model at
  the same step count.
- `BasicScheduler` still runs `steps` iterations when `denoise < 1`. It shortens the sigma
  range, not the step count.
- Encoding an mp4 back into a latent needs `length % 17 == 5`. An invalid length silently comes
  back shorter.
- **Generate small, upscale the latent, finish at full size does not pay off here.** H3's sample
  depends on resolution, so you get a different clip rather than a cheaper version of the same
  one. 0.4 MP to 1.5 MP took 705 s against 845 s direct, and legible Japanese never formed.
- 25 steps came back worse than 8.

## Workflows

Six in `workflows/`, all run before being included: a region rewrite driven from an mp4 (R2V,
I2V, and a T2V variant that failed instructively), a clip extension, and two working from a
Contex Loop chain checkpoint. `136_r2v_cut-rewrite-from-mp4.json` is the closest to the clip
above. `workflows/README.md` has the costs and what to repoint.

### Install

Through ComfyUI Manager: search **MiniMax H3 Inpaint Tools**. The dependency comes with it.

By hand:

```
cd ComfyUI/custom_nodes
git clone https://github.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools
cd ComfyUI-MiniMax-H3-Inpaint-Tools && pip install -r requirements.txt
```

Use the Python that runs ComfyUI for the second line. Restart, and the nodes appear under
**MiniMax H3/latent**.

Needs ComfyUI with MiniMax H3 support (the nodes import `comfy.nested_tensor`) and
[`minimax-h3-latent-core`](https://pypi.org/project/minimax-h3-latent-core/), which holds the
algorithms. Everything else ships with ComfyUI.

### Saving latents

The Contex Loop chain already stores per-clip latents in its checkpoints. Single-shot R2V / I2V
/ T2V graphs do not, so add **Save Latent** next to SaveVideo. If you lost the latent,
`LoadVideo` into `VAEEncode` and `VAEEncodeAudio`, then **Pack Latent**. That costs one VAE
round trip across the whole clip, so untouched regions degrade slightly too.

Latent geometry is `pixels / 16` spatially. 107 frames became `T = 32`, so one latent frame is
about 3.3 rendered frames, or 0.14 s at 24 fps. That is the finest slice a mask can address.

## Licence and contributing

This repository is GPL-3.0 and stays free whatever the size of your company. So do the
workflows. Nothing here is gated.

It depends on [`minimax-h3-latent-core`](https://github.com/panghea/minimax-h3-latent-core),
which is not GPL. That library is PolyForm Small Business 1.0.0: free for individuals and for
companies with fewer than 100 people and under USD 1,000,000 revenue in the prior tax year,
commercial work included, and paid above that line. See [COMMERCIAL.md](COMMERCIAL.md).
Installing this node pack installs that library, so the threshold applies once the nodes run.
Neither licence makes any claim on what you generate.

[LICENSING.md](LICENSING.md) explains why the two are split, and `LICENSE-EXCEPTION.txt` is the
GPL section 7 permission that lets them be distributed together.

Pull requests welcome here, with a DCO sign-off (`git commit -s`). The core library takes issues
only, not pull requests; the reason is in [CONTRIBUTING.md](CONTRIBUTING.md).
