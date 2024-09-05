# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import List, Optional

from .base import BaseInferenceType


@dataclass
class ZeroShotClassificationInputData(BaseInferenceType):
    """The input text data, with candidate labels"""

    candidate_labels: List[str]
    """The set of possible class labels to classify the text into."""
    text: str
    """The text to classify"""


@dataclass
class ZeroShotClassificationParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Zero Shot Classification
    """

    hypothesis_template: Optional[str] = None
    """The sentence used in conjunction with candidateLabels to attempt the text classification
    by replacing the placeholder with the candidate labels.
    """
    multi_label: Optional[bool] = None
    """Whether multiple candidate labels can be true. If false, the scores are normalized such
    that the sum of the label likelihoods for each sequence is 1. If true, the labels are
    considered independent and probabilities are normalized for each candidate.
    """


@dataclass
class ZeroShotClassificationInput(BaseInferenceType):
    """Inputs for Zero Shot Classification inference"""

    inputs: ZeroShotClassificationInputData
    """The input text data, with candidate labels"""
    parameters: Optional[ZeroShotClassificationParameters] = None
    """Additional inference parameters"""


@dataclass
class ZeroShotClassificationOutputElement(BaseInferenceType):
    """Outputs of inference for the Zero Shot Classification task"""

    label: str
    """The predicted class label."""
    score: float
    """The corresponding probability."""
