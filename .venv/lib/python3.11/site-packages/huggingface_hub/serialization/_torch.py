# Copyright 2024 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Contains pytorch-specific helpers."""

import importlib
import json
import os
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

from .. import constants, logging
from ._base import MAX_SHARD_SIZE, StateDictSplit, split_state_dict_into_shards_factory


logger = logging.get_logger(__file__)

if TYPE_CHECKING:
    import torch


def save_torch_model(
    model: "torch.nn.Module",
    save_directory: Union[str, Path],
    *,
    filename_pattern: Optional[str] = None,
    force_contiguous: bool = True,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
    metadata: Optional[Dict[str, str]] = None,
    safe_serialization: bool = True,
):
    """
    Saves a given torch model to disk, handling sharding and shared tensors issues.

    See also [`save_torch_state_dict`] to save a state dict with more flexibility.

    For more information about tensor sharing, check out [this guide](https://huggingface.co/docs/safetensors/torch_shared_tensors).

    The model state dictionary is split into shards so that each shard is smaller than a given size. The shards are
    saved in the `save_directory` with the given `filename_pattern`. If the model is too big to fit in a single shard,
    an index file is saved in the `save_directory` to indicate where each tensor is saved. This helper uses
    [`split_torch_state_dict_into_shards`] under the hood. If `safe_serialization` is `True`, the shards are saved as
    safetensors (the default). Otherwise, the shards are saved as pickle.

    Before saving the model, the `save_directory` is cleaned from any previous shard files.

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    Args:
        model (`torch.nn.Module`):
            The model to save on disk.
        save_directory (`str` or `Path`):
            The directory in which the model will be saved.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"` or `pytorch_model{suffix}.bin` depending on `safe_serialization`
            parameter.
        force_contiguous (`boolean`, *optional*):
            Forcing the state_dict to be saved as contiguous tensors. This has no effect on the correctness of the
            model, but it could potentially change performance if the layout of the tensor was chosen specifically for
            that reason. Defaults to `True`.
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.
        metadata (`Dict[str, str]`, *optional*):
            Extra information to save along with the model. Some metadata will be added for each dropped tensors.
            This information will not be enough to recover the entire shared structure but might help understanding
            things.
        safe_serialization (`bool`, *optional*):
            Whether to save as safetensors, which is the default behavior. If `False`, the shards are saved as pickle.
            Safe serialization is recommended for security reasons. Saving as pickle is deprecated and will be removed
            in a future version.

    Example:

    ```py
    >>> from huggingface_hub import save_torch_model
    >>> model = ... # A PyTorch model

    # Save state dict to "path/to/folder". The model will be split into shards of 5GB each and saved as safetensors.
    >>> save_torch_model(model, "path/to/folder")

    # Load model back
    >>> from huggingface_hub import load_torch_model  # TODO
    >>> load_torch_model(model, "path/to/folder")
    >>>
    ```
    """
    save_torch_state_dict(
        state_dict=model.state_dict(),
        filename_pattern=filename_pattern,
        force_contiguous=force_contiguous,
        max_shard_size=max_shard_size,
        metadata=metadata,
        safe_serialization=safe_serialization,
        save_directory=save_directory,
    )


def save_torch_state_dict(
    state_dict: Dict[str, "torch.Tensor"],
    save_directory: Union[str, Path],
    *,
    filename_pattern: Optional[str] = None,
    force_contiguous: bool = True,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
    metadata: Optional[Dict[str, str]] = None,
    safe_serialization: bool = True,
) -> None:
    """
    Save a model state dictionary to the disk, handling sharding and shared tensors issues.

    See also [`save_torch_model`] to directly save a PyTorch model.

    For more information about tensor sharing, check out [this guide](https://huggingface.co/docs/safetensors/torch_shared_tensors).

    The model state dictionary is split into shards so that each shard is smaller than a given size. The shards are
    saved in the `save_directory` with the given `filename_pattern`. If the model is too big to fit in a single shard,
    an index file is saved in the `save_directory` to indicate where each tensor is saved. This helper uses
    [`split_torch_state_dict_into_shards`] under the hood. If `safe_serialization` is `True`, the shards are saved as
    safetensors (the default). Otherwise, the shards are saved as pickle.

    Before saving the model, the `save_directory` is cleaned from any previous shard files.

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    Args:
        state_dict (`Dict[str, torch.Tensor]`):
            The state dictionary to save.
        save_directory (`str` or `Path`):
            The directory in which the model will be saved.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"` or `pytorch_model{suffix}.bin` depending on `safe_serialization`
            parameter.
        force_contiguous (`boolean`, *optional*):
            Forcing the state_dict to be saved as contiguous tensors. This has no effect on the correctness of the
            model, but it could potentially change performance if the layout of the tensor was chosen specifically for
            that reason. Defaults to `True`.
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.
        metadata (`Dict[str, str]`, *optional*):
            Extra information to save along with the model. Some metadata will be added for each dropped tensors.
            This information will not be enough to recover the entire shared structure but might help understanding
            things.
        safe_serialization (`bool`, *optional*):
            Whether to save as safetensors, which is the default behavior. If `False`, the shards are saved as pickle.
            Safe serialization is recommended for security reasons. Saving as pickle is deprecated and will be removed
            in a future version.

    Example:

    ```py
    >>> from huggingface_hub import save_torch_state_dict
    >>> model = ... # A PyTorch model

    # Save state dict to "path/to/folder". The model will be split into shards of 5GB each and saved as safetensors.
    >>> state_dict = model_to_save.state_dict()
    >>> save_torch_state_dict(state_dict, "path/to/folder")
    ```
    """
    save_directory = str(save_directory)

    if filename_pattern is None:
        filename_pattern = (
            constants.SAFETENSORS_WEIGHTS_FILE_PATTERN
            if safe_serialization
            else constants.PYTORCH_WEIGHTS_FILE_PATTERN
        )

    # Imports correct library
    if safe_serialization:
        try:
            from safetensors.torch import save_file as save_file_fn
        except ImportError as e:
            raise ImportError(
                "Please install `safetensors` to use safe serialization. "
                "You can install it with `pip install safetensors`."
            ) from e

    else:
        from torch import save as save_file_fn  # type: ignore[assignment]

        logger.warning(
            "You are using unsafe serialization. Due to security reasons, it is recommended not to load "
            "pickled models from untrusted sources. If you intend to share your model, we strongly recommend "
            "using safe serialization by installing `safetensors` with `pip install safetensors`."
        )

    # Clean state dict for safetensors
    if metadata is None:
        metadata = {}
    if safe_serialization:
        state_dict = _clean_state_dict_for_safetensors(state_dict, metadata, force_contiguous=force_contiguous)

    # Split dict
    state_dict_split = split_torch_state_dict_into_shards(
        state_dict, filename_pattern=filename_pattern, max_shard_size=max_shard_size
    )

    # Clean the folder from previous save
    existing_files_regex = re.compile(filename_pattern.format(suffix=r"(-\d{5}-of-\d{5})?") + r"(\.index\.json)?")
    for filename in os.listdir(save_directory):
        if existing_files_regex.match(filename):
            try:
                logger.debug(f"Removing existing file '{filename}' from folder.")
                os.remove(os.path.join(save_directory, filename))
            except Exception as e:
                logger.warning(f"Error when trying to remove existing '{filename}' from folder: {e}. Continuing...")

    # Save each shard
    per_file_metadata = {"format": "pt"}
    if not state_dict_split.is_sharded:
        per_file_metadata.update(metadata)
    safe_file_kwargs = {"metadata": per_file_metadata} if safe_serialization else {}
    for filename, tensors in state_dict_split.filename_to_tensors.items():
        shard = {tensor: state_dict[tensor] for tensor in tensors}
        save_file_fn(shard, os.path.join(save_directory, filename), **safe_file_kwargs)
        logger.debug(f"Shard saved to {filename}")

    # Save the index (if any)
    if state_dict_split.is_sharded:
        index_path = filename_pattern.format(suffix="") + ".index.json"
        index = {
            "metadata": {**state_dict_split.metadata, **metadata},
            "weight_map": state_dict_split.tensor_to_filename,
        }
        with open(os.path.join(save_directory, index_path), "w") as f:
            json.dump(index, f, indent=2)
        logger.info(
            f"The model is bigger than the maximum size per checkpoint ({max_shard_size}). "
            f"Model weighs have been saved in {len(state_dict_split.filename_to_tensors)} checkpoint shards. "
            f"You can find where each parameters has been saved in the index located at {index_path}."
        )

    logger.info(f"Model weights successfully saved to {save_directory}!")


def split_torch_state_dict_into_shards(
    state_dict: Dict[str, "torch.Tensor"],
    *,
    filename_pattern: str = constants.SAFETENSORS_WEIGHTS_FILE_PATTERN,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
) -> StateDictSplit:
    """
    Split a model state dictionary in shards so that each shard is smaller than a given size.

    The shards are determined by iterating through the `state_dict` in the order of its keys. There is no optimization
    made to make each shard as close as possible to the maximum size passed. For example, if the limit is 10GB and we
    have tensors of sizes [6GB, 6GB, 2GB, 6GB, 2GB, 2GB] they will get sharded as [6GB], [6+2GB], [6+2+2GB] and not
    [6+2+2GB], [6+2GB], [6GB].


    <Tip>

    To save a model state dictionary to the disk, see [`save_torch_state_dict`]. This helper uses
    `split_torch_state_dict_into_shards` under the hood.

    </Tip>

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    Args:
        state_dict (`Dict[str, torch.Tensor]`):
            The state dictionary to save.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"`.
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.

    Returns:
        [`StateDictSplit`]: A `StateDictSplit` object containing the shards and the index to retrieve them.

    Example:
    ```py
    >>> import json
    >>> import os
    >>> from safetensors.torch import save_file as safe_save_file
    >>> from huggingface_hub import split_torch_state_dict_into_shards

    >>> def save_state_dict(state_dict: Dict[str, torch.Tensor], save_directory: str):
    ...     state_dict_split = split_torch_state_dict_into_shards(state_dict)
    ...     for filename, tensors in state_dict_split.filename_to_tensors.items():
    ...         shard = {tensor: state_dict[tensor] for tensor in tensors}
    ...         safe_save_file(
    ...             shard,
    ...             os.path.join(save_directory, filename),
    ...             metadata={"format": "pt"},
    ...         )
    ...     if state_dict_split.is_sharded:
    ...         index = {
    ...             "metadata": state_dict_split.metadata,
    ...             "weight_map": state_dict_split.tensor_to_filename,
    ...         }
    ...         with open(os.path.join(save_directory, "model.safetensors.index.json"), "w") as f:
    ...             f.write(json.dumps(index, indent=2))
    ```
    """
    return split_state_dict_into_shards_factory(
        state_dict,
        max_shard_size=max_shard_size,
        filename_pattern=filename_pattern,
        get_storage_size=get_torch_storage_size,
        get_storage_id=get_torch_storage_id,
    )


def get_torch_storage_id(tensor: "torch.Tensor") -> Tuple["torch.device", int, int]:
    """
    Return unique identifier to a tensor storage.

    Multiple different tensors can share the same underlying storage. For
    example, "meta" tensors all share the same storage, and thus their identifier will all be equal. This identifier is
    guaranteed to be unique and constant for this tensor's storage during its lifetime. Two tensor storages with
    non-overlapping lifetimes may have the same id.

    Taken from https://github.com/huggingface/transformers/blob/1ecf5f7c982d761b4daaa96719d162c324187c64/src/transformers/pytorch_utils.py#L278.
    """
    if tensor.device.type == "xla" and is_torch_tpu_available():
        # NOTE: xla tensors dont have storage
        # use some other unique id to distinguish.
        # this is a XLA tensor, it must be created using torch_xla's
        # device. So the following import is safe:
        import torch_xla

        unique_id = torch_xla._XLAC._xla_get_tensor_id(tensor)
    else:
        unique_id = storage_ptr(tensor)

    return tensor.device, unique_id, get_torch_storage_size(tensor)


def get_torch_storage_size(tensor: "torch.Tensor") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/08db34094e9e59e2f9218f2df133b7b4aaff5a99/bindings/python/py_src/safetensors/torch.py#L31C1-L41C59
    """
    try:
        return tensor.untyped_storage().nbytes()
    except AttributeError:
        # Fallback for torch==1.10
        try:
            return tensor.storage().size() * _get_dtype_size(tensor.dtype)
        except NotImplementedError:
            # Fallback for meta storage
            # On torch >=2.0 this is the tensor size
            return tensor.nelement() * _get_dtype_size(tensor.dtype)


@lru_cache()
def is_torch_tpu_available(check_device=True):
    """
    Checks if `torch_xla` is installed and potentially if a TPU is in the environment

    Taken from https://github.com/huggingface/transformers/blob/1ecf5f7c982d761b4daaa96719d162c324187c64/src/transformers/utils/import_utils.py#L463.
    """
    if importlib.util.find_spec("torch_xla") is not None:
        if check_device:
            # We need to check if `xla_device` can be found, will raise a RuntimeError if not
            try:
                import torch_xla.core.xla_model as xm

                _ = xm.xla_device()
                return True
            except RuntimeError:
                return False
        return True
    return False


def storage_ptr(tensor: "torch.Tensor") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L11.
    """
    try:
        return tensor.untyped_storage().data_ptr()
    except Exception:
        # Fallback for torch==1.10
        try:
            return tensor.storage().data_ptr()
        except NotImplementedError:
            # Fallback for meta storage
            return 0


def _clean_state_dict_for_safetensors(
    state_dict: Dict[str, "torch.Tensor"], metadata: Dict[str, str], force_contiguous: bool = True
):
    """Remove shared tensors from state_dict and update metadata accordingly (for reloading).

    Warning: `state_dict` and `metadata` are mutated in-place!

    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L155.
    """
    to_removes = _remove_duplicate_names(state_dict)
    for kept_name, to_remove_group in to_removes.items():
        for to_remove in to_remove_group:
            if metadata is None:
                metadata = {}

            if to_remove not in metadata:
                # Do not override user data
                metadata[to_remove] = kept_name
            del state_dict[to_remove]
    if force_contiguous:
        state_dict = {k: v.contiguous() for k, v in state_dict.items()}
    return state_dict


def _end_ptr(tensor: "torch.Tensor") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L23.
    """
    if tensor.nelement():
        stop = tensor.view(-1)[-1].data_ptr() + _get_dtype_size(tensor.dtype)
    else:
        stop = tensor.data_ptr()
    return stop


def _filter_shared_not_shared(tensors: List[Set[str]], state_dict: Dict[str, "torch.Tensor"]) -> List[Set[str]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L44
    """
    filtered_tensors = []
    for shared in tensors:
        if len(shared) < 2:
            filtered_tensors.append(shared)
            continue

        areas = []
        for name in shared:
            tensor = state_dict[name]
            areas.append((tensor.data_ptr(), _end_ptr(tensor), name))
        areas.sort()

        _, last_stop, last_name = areas[0]
        filtered_tensors.append({last_name})
        for start, stop, name in areas[1:]:
            if start >= last_stop:
                filtered_tensors.append({name})
            else:
                filtered_tensors[-1].add(name)
            last_stop = stop

    return filtered_tensors


def _find_shared_tensors(state_dict: Dict[str, "torch.Tensor"]) -> List[Set[str]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L69.
    """
    import torch

    tensors_dict = defaultdict(set)
    for k, v in state_dict.items():
        if v.device != torch.device("meta") and storage_ptr(v) != 0 and get_torch_storage_size(v) != 0:
            # Need to add device as key because of multiple GPU.
            tensors_dict[(v.device, storage_ptr(v), get_torch_storage_size(v))].add(k)
    tensors = list(sorted(tensors_dict.values()))
    tensors = _filter_shared_not_shared(tensors, state_dict)
    return tensors


def _is_complete(tensor: "torch.Tensor") -> bool:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L80
    """
    return tensor.data_ptr() == storage_ptr(tensor) and tensor.nelement() * _get_dtype_size(
        tensor.dtype
    ) == get_torch_storage_size(tensor)


def _remove_duplicate_names(
    state_dict: Dict[str, "torch.Tensor"],
    *,
    preferred_names: Optional[List[str]] = None,
    discard_names: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L80
    """
    if preferred_names is None:
        preferred_names = []
    unique_preferred_names = set(preferred_names)
    if discard_names is None:
        discard_names = []
    unique_discard_names = set(discard_names)

    shareds = _find_shared_tensors(state_dict)
    to_remove = defaultdict(list)
    for shared in shareds:
        complete_names = set([name for name in shared if _is_complete(state_dict[name])])
        if not complete_names:
            raise RuntimeError(
                "Error while trying to find names to remove to save state dict, but found no suitable name to keep"
                f" for saving amongst: {shared}. None is covering the entire storage. Refusing to save/load the model"
                " since you could be storing much more memory than needed. Please refer to"
                " https://huggingface.co/docs/safetensors/torch_shared_tensors for more information. Or open an"
                " issue."
            )

        keep_name = sorted(list(complete_names))[0]

        # Mechanism to preferentially select keys to keep
        # coming from the on-disk file to allow
        # loading models saved with a different choice
        # of keep_name
        preferred = complete_names.difference(unique_discard_names)
        if preferred:
            keep_name = sorted(list(preferred))[0]

        if unique_preferred_names:
            preferred = unique_preferred_names.intersection(complete_names)
            if preferred:
                keep_name = sorted(list(preferred))[0]
        for name in sorted(shared):
            if name != keep_name:
                to_remove[keep_name].append(name)
    return to_remove


@lru_cache()
def _get_dtype_size(dtype: "torch.dtype") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/08db34094e9e59e2f9218f2df133b7b4aaff5a99/bindings/python/py_src/safetensors/torch.py#L344
    """
    import torch

    # torch.float8 formats require 2.1; we do not support these dtypes on earlier versions
    _float8_e4m3fn = getattr(torch, "float8_e4m3fn", None)
    _float8_e5m2 = getattr(torch, "float8_e5m2", None)
    _SIZE = {
        torch.int64: 8,
        torch.float32: 4,
        torch.int32: 4,
        torch.bfloat16: 2,
        torch.float16: 2,
        torch.int16: 2,
        torch.uint8: 1,
        torch.int8: 1,
        torch.bool: 1,
        torch.float64: 8,
        _float8_e4m3fn: 1,
        _float8_e5m2: 1,
    }
    return _SIZE[dtype]
