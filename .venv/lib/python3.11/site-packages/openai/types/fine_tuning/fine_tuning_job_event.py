# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing_extensions import Literal

from ..._models import BaseModel

__all__ = ["FineTuningJobEvent"]


class FineTuningJobEvent(BaseModel):
    id: str

    created_at: int

    level: Literal["info", "warn", "error"]

    message: str

    object: Literal["fine_tuning.job.event"]
