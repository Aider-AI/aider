# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import Literal, TypeAlias

from .chat_completion_named_tool_choice_param import ChatCompletionNamedToolChoiceParam

__all__ = ["ChatCompletionToolChoiceOptionParam"]

ChatCompletionToolChoiceOptionParam: TypeAlias = Union[
    Literal["none", "auto", "required"], ChatCompletionNamedToolChoiceParam
]
