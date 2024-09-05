# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Literal, Optional

from .base import BaseInferenceType


ClassificationOutputTransform = Literal["sigmoid", "softmax", "none"]


@dataclass
class TextClassificationParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Text Classification
    """

    function_to_apply: Optional["ClassificationOutputTransform"] = None
    top_k: Optional[int] = None
    """When specified, limits the output to the top K most probable classes."""


@dataclass
class TextClassificationInput(BaseInferenceType):
    """Inputs for Text Classification inference"""

    inputs: str
    """The text to classify"""
    parameters: Optional[TextClassificationParameters] = None
    """Additional inference parameters"""


@dataclass
class TextClassificationOutputElement(BaseInferenceType):
    """Outputs of inference for the Text Classification task"""

    label: str
    """The predicted class label."""
    score: float
    """The corresponding probability."""
