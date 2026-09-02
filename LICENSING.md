# Licensing

This project is deliberately split into two layers with different licences.

```
minimax_h3_latent_core/     pure PyTorch. Imports nothing from ComfyUI.
                    -> PolyForm Small Business 1.0.0  +  commercial licence
                    (free for individuals and small companies; paid above the threshold)

everything else     the ComfyUI node classes, _comfy_bridge.py, web/js
                    -> GPL-3.0-or-later
```

## Why the split exists

ComfyUI is GPL-3.0. The node classes import `comfy.nested_tensor` and `folder_paths` and are
loaded into the ComfyUI process, so they are best treated as a derivative work and are released
under GPL-3.0 to match.

`minimax_h3_latent_core` imports nothing from ComfyUI. It is a standalone PyTorch library that
happens to have a ComfyUI adapter in this repository, and it is licensed separately. Run
`python -m pytest` (or the snippet in `minimax_h3_latent_core/README.md`) with ComfyUI absent from
the path to confirm this for yourself - the core is tested that way on purpose.

This is a structuring choice, not a legal opinion. Whether a Python plugin is a derivative work
of its host has never been settled in court.

## The licence texts

Both are in the repository, copied verbatim from their canonical sources:

- `LICENSE` - GPL-3.0, from <https://www.gnu.org/licenses/gpl-3.0.txt> (35,149 bytes)
- `minimax_h3_latent_core/LICENSE` - PolyForm Small Business 1.0.0, taken from the SPDX licence
  list (<https://spdx.org/licenses/PolyForm-Small-Business-1.0.0.json>), which mirrors
  <https://polyformproject.org/licenses/small-business/1.0.0>

PolyForm's own site returned 404 for every URL when these were fetched, so SPDX was used as the
source instead. Both files were checked against their published length and opening text.

The threshold in PolyForm Small Business 1.0.0, in the licence's own words: a company may use
the software for free if it has **fewer than 100 total individuals** working as employees and
independent contractors, **and less than USD 1,000,000 (2019, inflation-adjusted) total revenue**
in the prior tax year. Read the licence itself rather than this summary.

## Contributions

**`minimax_h3_latent_core/` does not take pull requests.** Copyright in it is held by one person on
purpose: a commercial licence can only be granted by someone who holds all of the copyright, and
a single merged contribution from someone unreachable would end that permanently.

Bug reports, measurements and feature requests for the core are very welcome as issues - open
one and the change will be written here. Nothing is being hoarded; the constraint is legal, not
territorial.

The ComfyUI adapter layer (everything outside `minimax_h3_latent_core/`) is GPL-3.0 and takes pull
requests normally. Sign off your commits (`git commit -s`) to certify under the Developer
Certificate of Origin that you wrote the code and may submit it.
