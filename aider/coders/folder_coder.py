from importlib.abc import Traversable
from importlib.resources import files
from typing import Type

from .base_prompts import CoderPrompts
from .base_coder import Coder


def create_named_subclass(base_class: Type, name: str) -> Type:
    """Create a named subclass dynamically"""
    return type(name, (base_class,), {})


def load_class_attrs_from_folder(folder_path: Traversable, target_class: Type) -> None:
    """Load class attributes from text files in a folder.
    
    For each .txt file in the folder, its content will be set as a class attribute on
    the target_class. The attribute name is derived by removing the .txt extension
    from the filename.
    """
    if not hasattr(folder_path, 'iterdir'):
        # If folder_path doesn't exist or is not a directory, return silently
        return
    
    try:
        for item in folder_path.iterdir():
            if item.is_file() and item.name.endswith('.txt'):
                # Get attribute name by removing .txt extension
                attr_name = item.name[:-4]
                # Read file content
                content = item.read_text(encoding='utf-8')
                # Set as class attribute
                setattr(target_class, attr_name, content)
    except (OSError, IOError):
        # If we can't read the folder, return silently
        pass


class FolderCoder(Coder):
    """A coder that loads prompts from a folder"""

    def __init__(self, *args, prompt_folder_path: Traversable, edit_format: str = None, **kwargs):
        # If edit_format was passed in kwargs, use it. Otherwise use class attribute
        if edit_format is None:
            edit_format = getattr(self, 'edit_format', None)
        
        # Create the prompts subclass before calling super().__init__
        self.gpt_prompts = self._create_coder_prompts_subclass(prompt_folder_path, edit_format)
        
        # Now call parent init without edit_format (since it's not a parameter of Coder.__init__)
        super().__init__(*args, **kwargs)

    @staticmethod
    def _create_coder_prompts_subclass(prompt_folder_path: Traversable, coder_name: str) -> Type[CoderPrompts]:
        """Creates a folder-based subclass of CoderPrompts"""
        coder_prompts_subclass: Type[CoderPrompts] = create_named_subclass(CoderPrompts, coder_name)
        coder_path: Traversable = prompt_folder_path / coder_name
        load_class_attrs_from_folder(coder_path, coder_prompts_subclass)
        return coder_prompts_subclass


class AiderFolderCoder(FolderCoder):
    """A FolderCoder that loads Aider's built-in Coders"""
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            prompt_folder_path = files('aider.resources.folder-coders'),
            **kwargs
        )
