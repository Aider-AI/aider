# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union
from typing_extensions import Literal, Required, TypeAlias, TypedDict

__all__ = [
    "FileBatchCreateParams",
    "ChunkingStrategy",
    "ChunkingStrategyAutoChunkingStrategyRequestParam",
    "ChunkingStrategyStaticChunkingStrategyRequestParam",
    "ChunkingStrategyStaticChunkingStrategyRequestParamStatic",
]


class FileBatchCreateParams(TypedDict, total=False):
    file_ids: Required[List[str]]
    """
    A list of [File](https://platform.openai.com/docs/api-reference/files) IDs that
    the vector store should use. Useful for tools like `file_search` that can access
    files.
    """

    chunking_strategy: ChunkingStrategy
    """The chunking strategy used to chunk the file(s).

    If not set, will use the `auto` strategy.
    """


class ChunkingStrategyAutoChunkingStrategyRequestParam(TypedDict, total=False):
    type: Required[Literal["auto"]]
    """Always `auto`."""


class ChunkingStrategyStaticChunkingStrategyRequestParamStatic(TypedDict, total=False):
    chunk_overlap_tokens: Required[int]
    """The number of tokens that overlap between chunks. The default value is `400`.

    Note that the overlap must not exceed half of `max_chunk_size_tokens`.
    """

    max_chunk_size_tokens: Required[int]
    """The maximum number of tokens in each chunk.

    The default value is `800`. The minimum value is `100` and the maximum value is
    `4096`.
    """


class ChunkingStrategyStaticChunkingStrategyRequestParam(TypedDict, total=False):
    static: Required[ChunkingStrategyStaticChunkingStrategyRequestParamStatic]

    type: Required[Literal["static"]]
    """Always `static`."""


ChunkingStrategy: TypeAlias = Union[
    ChunkingStrategyAutoChunkingStrategyRequestParam, ChunkingStrategyStaticChunkingStrategyRequestParam
]
