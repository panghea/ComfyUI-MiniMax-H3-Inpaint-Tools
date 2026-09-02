# Contributing

## Two repositories, two rules

```
this repository            pull requests welcome, DCO sign-off
minimax-h3-latent-core     issues only, no pull requests
```

### The core - issues only

The core library is dual licensed (PolyForm Small Business plus a commercial licence), and that
only works while the copyright is held by one person. A single merged contribution from someone
who later cannot be reached would make the commercial licence impossible to grant, and it cannot
be undone after the fact.

So: **please do not send pull requests against
[minimax-h3-latent-core](https://github.com/panghea/minimax-h3-latent-core).** Open an issue
there instead.

Issues that are especially useful:

- a case where a mask, a resize or a save/load round trip gives the wrong result, with the
  tensor shapes involved
- measurements - timings, PSNR, thresholds - that contradict or extend what the README claims
- a latent layout from a different H3 build that this code fails to read

If you have already written a fix, describe it in the issue in prose or paste a diff there and
say it is yours to give. It will be credited in the commit message.

### The ComfyUI adapter - pull requests welcome

Everything here is GPL-3.0: the node classes, `_comfy_bridge.py`, the web extension. Normal
pull requests, with a DCO sign-off:

```
git commit -s -m "..."
```

That line certifies that you wrote the patch and may submit it under the project's licence. No
CLA, no copyright assignment.

## House rules for code

- The core must never import ComfyUI. It is a separate package for that reason, and it is
  tested with `comfy` and `folder_paths` absent. If a change needs something from ComfyUI, it
  belongs in `_comfy_bridge.py`, not upstream.
- Prefer a measurement to an assertion. The README's numbers were all produced on one machine
  and are stated as such; add yours the same way.
