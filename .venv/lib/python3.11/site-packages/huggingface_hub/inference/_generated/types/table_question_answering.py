# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseInferenceType


@dataclass
class TableQuestionAnsweringInputData(BaseInferenceType):
    """One (table, question) pair to answer"""

    question: str
    """The question to be answered about the table"""
    table: Dict[str, List[str]]
    """The table to serve as context for the questions"""


@dataclass
class TableQuestionAnsweringInput(BaseInferenceType):
    """Inputs for Table Question Answering inference"""

    inputs: TableQuestionAnsweringInputData
    """One (table, question) pair to answer"""
    parameters: Optional[Dict[str, Any]] = None
    """Additional inference parameters"""


@dataclass
class TableQuestionAnsweringOutputElement(BaseInferenceType):
    """Outputs of inference for the Table Question Answering task"""

    answer: str
    """The answer of the question given the table. If there is an aggregator, the answer will be
    preceded by `AGGREGATOR >`.
    """
    cells: List[str]
    """List of strings made up of the answer cell values."""
    coordinates: List[List[int]]
    """Coordinates of the cells of the answers."""
    aggregator: Optional[str] = None
    """If the model has an aggregator, this returns the aggregator."""
