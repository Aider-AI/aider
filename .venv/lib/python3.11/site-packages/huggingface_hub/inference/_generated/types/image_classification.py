# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, Literal, Optional

from .base import BaseInferenceType


ClassificationOutputTransform = Literal["sigmoid", "softmax", "none"]


@dataclass
class ImageClassificationParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Image Classification
    """

    function_to_apply: Optional["ClassificationOutputTransform"] = None
    top_k: Optional[int] = None
    """When specified, limits the output to the top K most probable classes."""


@dataclass
class ImageClassificationInput(BaseInferenceType):
    """Inputs for Image Classification inference"""

    inputs: Any
    """The input image data"""
    parameters: Optional[ImageClassificationParameters] = None
    """Additional inference parameters"""


@dataclass
class ImageClassificationOutputElement(BaseInferenceType):
    """Outputs of inference for the Image Classification task"""

    label: str
    """The predicted class label."""
    score: float
    """The corresponding probability."""
