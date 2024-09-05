# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, List, Optional

from .base import BaseInferenceType


@dataclass
class TextToImageTargetSize(BaseInferenceType):
    """The size in pixel of the output image"""

    height: int
    width: int


@dataclass
class TextToImageParameters(BaseInferenceType):
    """Additional inference parameters
    Additional inference parameters for Text To Image
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
    scheduler: Optional[str] = None
    """For diffusion models. Override the scheduler with a compatible one"""
    target_size: Optional[TextToImageTargetSize] = None
    """The size in pixel of the output image"""


@dataclass
class TextToImageInput(BaseInferenceType):
    """Inputs for Text To Image inference"""

    inputs: str
    """The input text data (sometimes called "prompt\""""
    parameters: Optional[TextToImageParameters] = None
    """Additional inference parameters"""


@dataclass
class TextToImageOutput(BaseInferenceType):
    """Outputs of inference for the Text To Image task"""

    image: Any
    """The generated image"""
