# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, Required, TypedDict

__all__ = ["EmbeddingCreateParams"]


class EmbeddingCreateParams(TypedDict, total=False):
    input: Required[Union[str, List[str], Iterable[int], Iterable[Iterable[int]]]]
    """Input text to embed, encoded as a string or array of tokens.

    To embed multiple inputs in a single request, pass an array of strings or array
    of token arrays. The input must not exceed the max input tokens for the model
    (8192 tokens for `text-embedding-ada-002`), cannot be an empty string, and any
    array must be 2048 dimensions or less.
    [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
    for counting tokens.
    """

    model: Required[Union[str, Literal["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]]]
    """ID of the model to use.

    You can use the
    [List models](https://platform.openai.com/docs/api-reference/models/list) API to
    see all of your available models, or see our
    [Model overview](https://platform.openai.com/docs/models/overview) for
    descriptions of them.
    """

    dimensions: int
    """The number of dimensions the resulting output embeddings should have.

    Only supported in `text-embedding-3` and later models.
    """

    encoding_format: Literal["float", "base64"]
    """The format to return the embeddings in.

    Can be either `float` or [`base64`](https://pypi.org/project/pybase64/).
    """

    user: str
    """
    A unique identifier representing your end-user, which can help OpenAI to monitor
    and detect abuse.
    [Learn more](https://platform.openai.com/docs/guides/safety-best-practices/end-user-ids).
    """
