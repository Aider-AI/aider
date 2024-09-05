# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union
from typing_extensions import Required, TypedDict

from .moderation_model import ModerationModel

__all__ = ["ModerationCreateParams"]


class ModerationCreateParams(TypedDict, total=False):
    input: Required[Union[str, List[str]]]
    """The input text to classify"""

    model: Union[str, ModerationModel]
    """
    Two content moderations models are available: `text-moderation-stable` and
    `text-moderation-latest`.

    The default is `text-moderation-latest` which will be automatically upgraded
    over time. This ensures you are always using our most accurate model. If you use
    `text-moderation-stable`, we will provide advanced notice before updating the
    model. Accuracy of `text-moderation-stable` may be slightly lower than for
    `text-moderation-latest`.
    """
