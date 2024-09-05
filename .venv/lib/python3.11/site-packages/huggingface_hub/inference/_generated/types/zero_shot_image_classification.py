# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, List, Optional

from .base import BaseInferenceType


@dataclass
class ZeroShotImageClassificationInputData(BaseInferenceType):
    """The input image data, with candidate labels"""

    candidate_labels: List[str]
    """The candidate labels for this image"""
    image: Any
    """The image data to classify"""


@dataclass
class ZeroShotImageClassificationParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Zero Shot Image Classification
    """

    hypothesis_template: Optional[str] = None
    """The sentence used in conjunction with candidateLabels to attempt the text classification
    by replacing the placeholder with the candidate labels.
    """


@dataclass
class ZeroShotImageClassificationInput(BaseInferenceType):
    """Inputs for Zero Shot Image Classification inference"""

    inputs: ZeroShotImageClassificationInputData
    """The input image data, with candidate labels"""
    parameters: Optional[ZeroShotImageClassificationParameters] = None
    """Additional inference parameters"""


@dataclass
class ZeroShotImageClassificationOutputElement(BaseInferenceType):
    """Outputs of inference for the Zero Shot Image Classification task"""

    label: str
    """The predicted class label."""
    score: float
    """The corresponding probability."""
