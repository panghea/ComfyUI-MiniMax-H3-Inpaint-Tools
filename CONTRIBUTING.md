# Contributing

## Two layers, two rules

```
minimax_h3_latent_core/     issues only, no pull requests
everything else     pull requests welcome, DCO sign-off
```

### `minimax_h3_latent_core/` - issues only

This directory is dual licensed (PolyForm Small Business plus a commercial licence), and that
only works while the copyright is held by one person. A single merged contribution from someone
who later cannot be reached would make the commercial licence impossible to grant, and it cannot
be undone after the fact.

So: **please do not send pull requests against `minimax_h3_latent_core/`.** Open an issue instead.

Issues that are especially useful:

- a case where a mask, a resize or a save/load round trip gives the wrong result, with the
  tensor shapes involved
- measurements - timings, PSNR, thresholds - that contradict or extend what the README claims
- a latent layout from a different H3 build that this code fails to read

If you have already written a fix, describe it in the issue in prose or paste a diff there and
say it is yours to give. It will be credited in the commit message.

### The ComfyUI adapter - pull requests welcome

Everything outside `minimax_h3_latent_core/` is GPL-3.0: the node classes, `_comfy_bridge.py`, the
web extension. Normal pull requests, with a DCO sign-off:

```
git commit -s -m "..."
```

That line certifies that you wrote the patch and may submit it under the project's licence. No
CLA, no copyright assignment.

## House rules for code

- The core must never import ComfyUI. There is a test for this - it loads `minimax_h3_latent_core`
  with `comfy` and `folder_paths` forced to fail, and everything must still work. If a change needs
  something from ComfyUI, it belongs in `_comfy_bridge.py`.
- Prefer a measurement to an assertion. The README's numbers were all produced on one machine
  and are stated as such; add yours the same way.
