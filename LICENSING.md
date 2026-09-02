# Licensing

This project is deliberately split into two repositories with different licences.

```
this repository     the ComfyUI node classes, _comfy_bridge.py, web/js
                    -> GPL-3.0-or-later

minimax-h3-latent-core   pure PyTorch. Imports nothing from ComfyUI.
                    -> PolyForm Small Business 1.0.0  +  commercial licence
                    (free for individuals and small companies; paid above the threshold)
                    https://github.com/panghea/minimax-h3-latent-core
```

The core is an ordinary PyPI dependency of this package, named in `requirements.txt`.

## Why the split exists

ComfyUI is GPL-3.0. The node classes import `comfy.nested_tensor` and `folder_paths` and are
loaded into the ComfyUI process, so they are best treated as a derivative work and are released
under GPL-3.0 to match.

`minimax_h3_latent_core` imports nothing from ComfyUI. It is a standalone PyTorch library that
happens to have this ComfyUI adapter built on it, and it is licensed separately. Install it on
its own and use it from a plain script with ComfyUI absent from the path to confirm this for
yourself - the core is tested that way on purpose.

This is a structuring choice, not a legal opinion. Whether a Python plugin is a derivative work
of its host has never been settled in court.

## The licence texts

- `LICENSE` in this repository - GPL-3.0, copied verbatim from
  <https://www.gnu.org/licenses/gpl-3.0.txt> (35,149 bytes)
- `LICENSE` in the core repository - PolyForm Small Business 1.0.0, taken from the SPDX licence
  list (<https://spdx.org/licenses/PolyForm-Small-Business-1.0.0.json>), which mirrors
  <https://polyformproject.org/licenses/small-business/1.0.0>

PolyForm's own site returned 404 for every URL when these were fetched, so SPDX was used as the
source instead. Both files were checked against their published length and opening text.

The threshold in PolyForm Small Business 1.0.0, in the licence's own words: a company may use
the software for free if it has **fewer than 100 total individuals** working as employees and
independent contractors, **and less than USD 1,000,000 (2019, inflation-adjusted) total revenue**
in the prior tax year. Read the licence itself rather than this summary.

`LICENSE-EXCEPTION.txt` grants the GPL section 7 additional permission that lets this GPL-3.0
work be combined with and distributed alongside the non-free core. It is still required now that
the core is a pip dependency rather than a vendored copy - the combination is what the exception
covers, not the file layout.

## Contributions

**The core does not take pull requests.** Copyright in it is held by one person on purpose: a
commercial licence can only be granted by someone who holds all of the copyright, and a single
merged contribution from someone unreachable would end that permanently.

Bug reports, measurements and feature requests for the core are very welcome as issues on
<https://github.com/panghea/minimax-h3-latent-core/issues> - open one and the change will be
written there. Nothing is being hoarded; the constraint is legal, not territorial.

This repository is GPL-3.0 and takes pull requests normally. Sign off your commits
(`git commit -s`) to certify under the Developer Certificate of Origin that you wrote the code
and may submit it.
