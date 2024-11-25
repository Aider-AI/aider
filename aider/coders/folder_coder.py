import re
from importlib.abc import Traversable
from importlib.resources import files
from typing import Type

from pylibtypes import create_named_subclass, load_class_attrs_from_folder, FolderBasedAttrsError
from .base_prompts import CoderPrompts
from .base_coder import Coder


class FolderCoder(Coder):
    """A coder that loads prompts from a folder"""

    def __init__(self, *args, prompt_folder_path: Traversable, **kwargs):
        super().__init__(*args, **{k: v for k, v in kwargs.items() if k not in ["edit_format"]})
        self.gpt_prompts = self._create_coder_prompts_subclass(prompt_folder_path, self.edit_format)

    @staticmethod
    def _create_coder_prompts_subclass(prompt_folder_path: Traversable, coder_name: str) -> Type[CoderPrompts]:
        """Creates a folder-based subclass of CoderPrompts"""
        coder_prompts_subclass: Type[CoderPrompts] = create_named_subclass(CoderPrompts, coder_name)
        coder_path: Traversable = prompt_folder_path / coder_name
        load_class_attrs_from_folder(coder_path, coder_prompts_subclass, FolderCoder.parse_cedarml_pairs)
        return coder_prompts_subclass

    @staticmethod
    def parse_cedarml_pairs(content: str) -> list[dict[str, str]]:
        messages = []
        user_pattern = r'<cedarml:role.user>(.*?)</cedarml:role.user>'
        assistant_pattern = r'<cedarml:role.assistant>(.*?)</cedarml:role.assistant>'

        users = re.findall(user_pattern, content, re.DOTALL)
        assistants = re.findall(assistant_pattern, content, re.DOTALL)

        if len(users) != len(assistants):
            raise ValueError(
                f"Mismatched number of user {len(users)} and assistant {len(assistants)} messages"
            )

        for user, assistant in zip(users, assistants):
            messages.append({"role": "user", "content": user.strip()})
            messages.append({"role": "assistant", "content": assistant.strip()})

        return messages

class AiderFolderCoder(FolderCoder):
    """A FolderCoder that loads Aider's built-in Coders"""
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            prompt_folder_path = files('aider.resources.folder-coders'),
            **kwargs
        )
