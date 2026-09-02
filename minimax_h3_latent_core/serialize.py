# -*- coding: utf-8 -*-
"""Read and write H3 latents as safetensors. Pure tensor code, no ComfyUI import.

Two on-disk shapes are understood:

  * this library's own - `t0`, `t1`, ... in order, with the packing recorded in metadata
  * a Contex Loop chain checkpoint - `video` / `audio`, plus keys that are not part of the
    latent, and the scene prompt carried in metadata

Latents are stored in bf16 by default: it halves the file, it is what the model runs in anyway,
and the dtype the sampler produced is recorded so it can be restored on load.
"""
import json
import os

import torch
import safetensors.torch

DTYPES = {'bf16': torch.bfloat16, 'fp16': torch.float16, 'fp32': torch.float32}
_BACK = {'bfloat16': torch.bfloat16, 'float16': torch.float16, 'float32': torch.float32}


def save_tensors(path, tensors, nested=True, dtype='bf16', extra_keys=(), metadata=None):
    """Write the tensors and enough metadata to reconstruct the latent exactly."""
    want = DTYPES[dtype]
    payload = {'t%d' % i: t.to(want).contiguous().cpu() for i, t in enumerate(tensors)}
    meta = {'h3_nested': '1' if nested else '0',
            'count': str(len(tensors)),
            'dtype': dtype,
            'orig_dtype': str(tensors[0].dtype).replace('torch.', ''),
            'shapes': json.dumps([list(t.shape) for t in tensors]),
            'extra_keys': json.dumps(sorted(extra_keys))}
    meta.update(metadata or {})
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    safetensors.torch.save_file(payload, path, metadata=meta)
    return os.path.getsize(path)


def load_tensors(path):
    """-> (tensors, nested, prompt, metadata). Restores the dtype the sampler produced."""
    with safetensors.torch.safe_open(path, framework='pt') as f:
        meta = dict(f.metadata() or {})
        keys = set(f.keys())
        if 'video' in keys:                          # a Contex Loop chain checkpoint
            tensors = [f.get_tensor('video')]
            if 'audio' in keys:
                tensors.append(f.get_tensor('audio'))
            meta.setdefault('h3_nested', '1')
            meta.setdefault('orig_dtype', str(tensors[0].dtype).replace('torch.', ''))
        else:                                        # written by save_tensors
            ordered = sorted((k for k in keys if k[1:].isdigit()), key=lambda k: int(k[1:]))
            tensors = [f.get_tensor(k) for k in ordered]
    back = _BACK.get(meta.get('orig_dtype'), torch.float32)
    tensors = [t.to(back) for t in tensors]
    prompt = meta.get('scene_prompt') or meta.get('prompt') or ''
    return tensors, meta.get('h3_nested') == '1', prompt, meta


def split_video_audio(tensors):
    """-> (video tensor, [everything else]) using H3's 5-D/4-D distinction."""
    video = next((t for t in tensors if t.ndim == 5), None)
    others = [t for t in tensors if t.ndim != 5]
    return video, others
