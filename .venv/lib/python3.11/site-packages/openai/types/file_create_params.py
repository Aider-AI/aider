# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Required, TypedDict

from .._types import FileTypes
from .file_purpose import FilePurpose

__all__ = ["FileCreateParams"]


class FileCreateParams(TypedDict, total=False):
    file: Required[FileTypes]
    """The File object (not file name) to be uploaded."""

    purpose: Required[FilePurpose]
    """The intended purpose of the uploaded file.

    Use "assistants" for
    [Assistants](https://platform.openai.com/docs/api-reference/assistants) and
    [Message](https://platform.openai.com/docs/api-reference/messages) files,
    "vision" for Assistants image file inputs, "batch" for
    [Batch API](https://platform.openai.com/docs/guides/batch), and "fine-tune" for
    [Fine-tuning](https://platform.openai.com/docs/api-reference/fine-tuning).
    """
