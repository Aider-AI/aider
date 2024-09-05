# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Optional
from typing_extensions import Literal, Required, TypedDict

__all__ = ["BatchCreateParams"]


class BatchCreateParams(TypedDict, total=False):
    completion_window: Required[Literal["24h"]]
    """The time frame within which the batch should be processed.

    Currently only `24h` is supported.
    """

    endpoint: Required[Literal["/v1/chat/completions", "/v1/embeddings", "/v1/completions"]]
    """The endpoint to be used for all requests in the batch.

    Currently `/v1/chat/completions`, `/v1/embeddings`, and `/v1/completions` are
    supported. Note that `/v1/embeddings` batches are also restricted to a maximum
    of 50,000 embedding inputs across all requests in the batch.
    """

    input_file_id: Required[str]
    """The ID of an uploaded file that contains requests for the new batch.

    See [upload file](https://platform.openai.com/docs/api-reference/files/create)
    for how to upload a file.

    Your input file must be formatted as a
    [JSONL file](https://platform.openai.com/docs/api-reference/batch/request-input),
    and must be uploaded with the purpose `batch`. The file can contain up to 50,000
    requests, and can be up to 100 MB in size.
    """

    metadata: Optional[Dict[str, str]]
    """Optional custom metadata for the batch."""
