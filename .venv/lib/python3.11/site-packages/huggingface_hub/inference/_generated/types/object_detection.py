# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, Optional

from .base import BaseInferenceType


@dataclass
class ObjectDetectionParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Object Detection
    """

    threshold: Optional[float] = None
    """The probability necessary to make a prediction."""


@dataclass
class ObjectDetectionInput(BaseInferenceType):
    """Inputs for Object Detection inference"""

    inputs: Any
    """The input image data"""
    parameters: Optional[ObjectDetectionParameters] = None
    """Additional inference parameters"""


@dataclass
class ObjectDetectionBoundingBox(BaseInferenceType):
    """The predicted bounding box. Coordinates are relative to the top left corner of the input
    image.
    """

    xmax: int
    xmin: int
    ymax: int
    ymin: int


@dataclass
class ObjectDetectionOutputElement(BaseInferenceType):
    """Outputs of inference for the Object Detection task"""

    box: ObjectDetectionBoundingBox
    """The predicted bounding box. Coordinates are relative to the top left corner of the input
    image.
    """
    label: str
    """The predicted label for the bounding box"""
    score: float
    """The associated score / probability"""
