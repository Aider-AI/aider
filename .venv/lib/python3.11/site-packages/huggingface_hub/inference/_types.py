# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, TypedDict


# Legacy types
# Types are now generated from the JSON schema spec in @huggingface/tasks.
# See ./src/huggingface_hub/inference/_generated/types


class ConversationalOutputConversation(TypedDict):
    """Dictionary containing the "conversation" part of a [`~InferenceClient.conversational`] task.

    Args:
        generated_responses (`List[str]`):
            A list of the responses from the model.
        past_user_inputs (`List[str]`):
            A list of the inputs from the user. Must be the same length as `generated_responses`.
    """

    generated_responses: List[str]
    past_user_inputs: List[str]


class ConversationalOutput(TypedDict):
    """Dictionary containing the output of a  [`~InferenceClient.conversational`] task.

    Args:
        generated_text (`str`):
            The last response from the model.
        conversation (`ConversationalOutputConversation`):
            The past conversation.
        warnings (`List[str]`):
            A list of warnings associated with the process.
    """

    conversation: ConversationalOutputConversation
    generated_text: str
    warnings: List[str]
