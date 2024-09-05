# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseInferenceType


@dataclass
class ZeroShotObjectDetectionInputData(BaseInferenceType):
    """The input image data, with candidate labels"""

    candidate_labels: List[str]
    """The candidate labels for this image"""
    image: Any
    """The image data to generate bounding boxes from"""


@dataclass
class ZeroShotObjectDetectionInput(BaseInferenceType):
    """Inputs for Zero Shot Object Detection inference"""

    inputs: ZeroShotObjectDetectionInputData
    """The input image data, with candidate labels"""
    parameters: Optional[Dict[str, Any]] = None
    """Additional inference parameters"""


@dataclass
class ZeroShotObjectDetectionBoundingBox(BaseInferenceType):
    """The predicted bounding box. Coordinates are relative to the top left corner of the input
    image.
    """

    xmax: int
    xmin: int
    ymax: int
    ymin: int


@dataclass
class ZeroShotObjectDetectionOutputElement(BaseInferenceType):
    """Outputs of inference for the Zero Shot Object Detection task"""

    box: ZeroShotObjectDetectionBoundingBox
    """The predicted bounding box. Coordinates are relative to the top left corner of the input
    image.
    """
    label: str
    """A candidate label"""
    score: float
    """The associated score / probability"""
