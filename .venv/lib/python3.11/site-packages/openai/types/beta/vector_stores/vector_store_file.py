# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from ...._utils import PropertyInfo
from ...._models import BaseModel

__all__ = [
    "VectorStoreFile",
    "LastError",
    "ChunkingStrategy",
    "ChunkingStrategyStatic",
    "ChunkingStrategyStaticStatic",
    "ChunkingStrategyOther",
]


class LastError(BaseModel):
    code: Literal["server_error", "unsupported_file", "invalid_file"]
    """One of `server_error` or `rate_limit_exceeded`."""

    message: str
    """A human-readable description of the error."""


class ChunkingStrategyStaticStatic(BaseModel):
    chunk_overlap_tokens: int
    """The number of tokens that overlap between chunks. The default value is `400`.

    Note that the overlap must not exceed half of `max_chunk_size_tokens`.
    """

    max_chunk_size_tokens: int
    """The maximum number of tokens in each chunk.

    The default value is `800`. The minimum value is `100` and the maximum value is
    `4096`.
    """


class ChunkingStrategyStatic(BaseModel):
    static: ChunkingStrategyStaticStatic

    type: Literal["static"]
    """Always `static`."""


class ChunkingStrategyOther(BaseModel):
    type: Literal["other"]
    """Always `other`."""


ChunkingStrategy: TypeAlias = Annotated[
    Union[ChunkingStrategyStatic, ChunkingStrategyOther], PropertyInfo(discriminator="type")
]


class VectorStoreFile(BaseModel):
    id: str
    """The identifier, which can be referenced in API endpoints."""

    created_at: int
    """The Unix timestamp (in seconds) for when the vector store file was created."""

    last_error: Optional[LastError] = None
    """The last error associated with this vector store file.

    Will be `null` if there are no errors.
    """

    object: Literal["vector_store.file"]
    """The object type, which is always `vector_store.file`."""

    status: Literal["in_progress", "completed", "cancelled", "failed"]
    """
    The status of the vector store file, which can be either `in_progress`,
    `completed`, `cancelled`, or `failed`. The status `completed` indicates that the
    vector store file is ready for use.
    """

    usage_bytes: int
    """The total vector store usage in bytes.

    Note that this may be different from the original file size.
    """

    vector_store_id: str
    """
    The ID of the
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    that the [File](https://platform.openai.com/docs/api-reference/files) is
    attached to.
    """

    chunking_strategy: Optional[ChunkingStrategy] = None
    """The strategy used to chunk the file."""
