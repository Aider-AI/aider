# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, Literal, Optional

from .base import BaseInferenceType


ImageSegmentationSubtask = Literal["instance", "panoptic", "semantic"]


@dataclass
class ImageSegmentationParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Image Segmentation
    """

    mask_threshold: Optional[float] = None
    """Threshold to use when turning the predicted masks into binary values."""
    overlap_mask_area_threshold: Optional[float] = None
    """Mask overlap threshold to eliminate small, disconnected segments."""
    subtask: Optional["ImageSegmentationSubtask"] = None
    """Segmentation task to be performed, depending on model capabilities."""
    threshold: Optional[float] = None
    """Probability threshold to filter out predicted masks."""


@dataclass
class ImageSegmentationInput(BaseInferenceType):
    """Inputs for Image Segmentation inference"""

    inputs: Any
    """The input image data"""
    parameters: Optional[ImageSegmentationParameters] = None
    """Additional inference parameters"""


@dataclass
class ImageSegmentationOutputElement(BaseInferenceType):
    """Outputs of inference for the Image Segmentation task
    A predicted mask / segment
    """

    label: str
    """The label of the predicted segment"""
    mask: Any
    """The corresponding mask as a black-and-white image"""
    score: Optional[float] = None
    """The score or confidence degreee the model has"""
