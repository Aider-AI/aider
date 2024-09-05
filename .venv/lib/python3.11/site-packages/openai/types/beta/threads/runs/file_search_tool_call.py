# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing_extensions import Literal

from ....._models import BaseModel

__all__ = ["FileSearchToolCall"]


class FileSearchToolCall(BaseModel):
    id: str
    """The ID of the tool call object."""

    file_search: object
    """For now, this is always going to be an empty object."""

    type: Literal["file_search"]
    """The type of tool call.

    This is always going to be `file_search` for this type of tool call.
    """
