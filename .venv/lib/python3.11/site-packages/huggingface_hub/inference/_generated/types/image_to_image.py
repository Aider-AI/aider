# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, List, Optional

from .base import BaseInferenceType


@dataclass
class ImageToImageTargetSize(BaseInferenceType):
    """The size in pixel of the output image"""

    height: int
    width: int


@dataclass
class ImageToImageParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Image To Image
    """

    guidance_scale: Optional[float] = None
    """For diffusion models. A higher guidance scale value encourages the model to generate
    images closely linked to the text prompt at the expense of lower image quality.
    """
    negative_prompt: Optional[List[str]] = None
    """One or several prompt to guide what NOT to include in image generation."""
    num_inference_steps: Optional[int] = None
    """For diffusion models. The number of denoising steps. More denoising steps usually lead to
    a higher quality image at the expense of slower inference.
    """
    target_size: Optional[ImageToImageTargetSize] = None
    """The size in pixel of the output image"""


@dataclass
class ImageToImageInput(BaseInferenceType):
    """Inputs for Image To Image inference"""

    inputs: Any
    """The input image data"""
    parameters: Optional[ImageToImageParameters] = None
    """Additional inference parameters"""


@dataclass
class ImageToImageOutput(BaseInferenceType):
    """Outputs of inference for the Image To Image task"""

    image: Any
    """The output image"""
