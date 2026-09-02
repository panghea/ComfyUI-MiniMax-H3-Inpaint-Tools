# -*- coding: utf-8 -*-
"""The only file that knows about ComfyUI internals.

Everything else in this package either builds node metadata or calls `minimax_h3_latent_core`, which is
pure PyTorch. Keeping the coupling in one small file makes the boundary between the two obvious,
and means the core can be used - and licensed - on its own.
"""
try:
    from comfy import nested_tensor
    NestedTensor = nested_tensor.NestedTensor
except Exception:                                    # pragma: no cover - running outside ComfyUI
    NestedTensor = None

try:
    import folder_paths
except Exception:                                    # pragma: no cover
    folder_paths = None


def is_nested(lat):
    return NestedTensor is not None and isinstance(lat, NestedTensor)


def tensors_of(lat):
    """-> (list of tensors, was_nested)."""
    return (list(lat.tensors), True) if is_nested(lat) else ([lat], False)


def rewrap(template, tensors):
    """Rebuild a nested latent shaped like `template`.

    Uses the incoming object's own class rather than the imported one where possible, so a
    latent produced by a differently-packaged ComfyUI still round-trips.
    """
    if is_nested(template):
        out = template._copy()
        out.tensors = list(tensors)
        return out
    return tensors[0]


def make_nested(tensors):
    """Build a nested latent with no template to copy - used when loading from disk."""
    if NestedTensor is None:
        raise RuntimeError('comfy.nested_tensor is unavailable')
    return NestedTensor(list(tensors))


def output_directory():
    if folder_paths is None:
        raise RuntimeError('folder_paths is unavailable outside ComfyUI')
    return folder_paths.get_output_directory()


def save_path(filename_prefix, output_dir, suffix='.safetensors'):
    """Next free numbered path. Note the unpack order - it is not what the name suggests."""
    full, filename, counter, _subfolder, _prefix = folder_paths.get_save_image_path(
        filename_prefix, output_dir)
    return full, '%s_%05d_%s' % (filename, counter, suffix.lstrip('.'))
