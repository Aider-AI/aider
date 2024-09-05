# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Literal, Optional

from .base import BaseInferenceType


FeatureExtractionInputTruncationDirection = Literal["Left", "Right"]


@dataclass
class FeatureExtractionInput(BaseInferenceType):
    """Feature Extraction Input.
    Auto-generated from TEI specs.
    For more details, check out
    https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-tei-import.ts.
    """

    inputs: str
    """The text to embed."""
    normalize: Optional[bool] = None
    prompt_name: Optional[str] = None
    """The name of the prompt that should be used by for encoding. If not set, no prompt
    will be applied.
    Must be a key in the `Sentence Transformers` configuration `prompts` dictionary.
    For example if ``prompt_name`` is "query" and the ``prompts`` is {"query": "query: ",
    ...},
    then the sentence "What is the capital of France?" will be encoded as
    "query: What is the capital of France?" because the prompt text will be prepended before
    any text to encode.
    """
    truncate: Optional[bool] = None
    truncation_direction: Optional["FeatureExtractionInputTruncationDirection"] = None
