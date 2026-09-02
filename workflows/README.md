# Example workflows

Drop a file on the ComfyUI canvas to load it. All six were run on the machine they were built on
before being included here; none is a sketch.

| File | What it does | Cost |
|---|---|---|
| `136_r2v_cut-rewrite-from-mp4` | Rewrite a rectangle of one cut, taken from a finished mp4 | ~200 s at 39 frames, 1.5 MP, 8 steps |
| `137_i2v_cut-rewrite-from-mp4` | Same, conditioned on a first and last frame instead of references | ~205 s |
| `138_t2v_cut-rewrite-from-mp4` | Same, prompt only. **It broke the artwork** - see the note in the file | ~120 s |
| `139_r2v_clip-extend-from-mp4` | Continue a clip by growing its latent along time | ~400 s, 39 -> 73 frames |
| `134_contex-loop_latent-rewrite_scene1` | Rewrite a region of a Contex Loop chain clip, from its saved checkpoint | ~700 s at 107 frames |
| `135_contex-loop_latent-rewrite_scene4` | Same, later in the chain | ~700 s |

## Running them

`assets/` holds the material four of these workflows expect. Copy it into ComfyUI's `input/`
directory and `136`, `137`, `138` and `139` run unchanged:

```
cp workflows/assets/* /path/to/ComfyUI/input/
```

| File | 640x352 unless noted | What it is |
|---|---|---|
| `r2v_cut_src.mp4` | 1664x928, 39 frames | The cut being rewritten. This is what gets VAE-encoded into the latent. |
| `r2v_cut_ref.mp4` | 42 frames | The same cut, small, as a motion reference. |
| `extend_ref.mp4` | 116 frames | Covers the whole *extended* span, for `139`. |
| `pc_kv_taipa_new.png` | 1672x941 | The picture reference for `136`. |
| `pc_kv10.png` | 1672x941 | The picture reference for `139`. |
| `i2v_cut_first.png` / `i2v_cut_last.png` | 1664x928 | First and last frame, for `137`. |

`134` and `135` are not runnable from this repository: they read a Contex Loop chain checkpoint,
which is several gigabytes and belongs to a specific run. They are here as a record of how the
chain path is wired, not as something to execute.

### Two rules the loaders will not tell you about

- **A reference video must carry an audio track.** Without one,
  `MiniMaxH3ReferenceVideoPrepare` stops with
  `H3 reference-video prep requires source audio`.
- **A reference video must be at least as long as the generated length**, and it measures a file
  one frame short of its real count - so leave a couple of frames of slack.

### Nothing is tied to this material

The workflows were also run end to end against a synthetic clip generated with ffmpeg, at the
same 39-frame length. They depend on the shapes, not on the footage.

### Licensing of the sample media

The two licences in this repository cover the **code**. The clips and stills in `assets/` are
sample material, included so the workflows run out of the box. They are not covered by the code
licences, and they are not offered for reuse in your own work.

### Using your own material instead

Nothing is hard-coded to an absolute path - every reference is a plain filename that ComfyUI
resolves inside its own `input/` directory. Put your own clip and stills there and repoint the
`LoadVideo` and `LoadImage` nodes. Keep the length rule in mind: a clip encoded into a latent has
to satisfy `length % 17 == 5` (5, 22, 39, 56, 73, 90, 107 ...), and an invalid length silently
comes back shorter.
