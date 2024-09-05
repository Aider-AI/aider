# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Contain helper class to retrieve/store token from/to local cache."""

import warnings
from pathlib import Path
from typing import Optional

from .. import constants
from ._token import get_token


class HfFolder:
    path_token = Path(constants.HF_TOKEN_PATH)
    # Private attribute. Will be removed in v0.15
    _old_path_token = Path(constants._OLD_HF_TOKEN_PATH)

    # TODO: deprecate when adapted in transformers/datasets/gradio
    # @_deprecate_method(version="1.0", message="Use `huggingface_hub.login` instead.")
    @classmethod
    def save_token(cls, token: str) -> None:
        """
        Save token, creating folder as needed.

        Token is saved in the huggingface home folder. You can configure it by setting
        the `HF_HOME` environment variable.

        Args:
            token (`str`):
                The token to save to the [`HfFolder`]
        """
        cls.path_token.parent.mkdir(parents=True, exist_ok=True)
        cls.path_token.write_text(token)

    # TODO: deprecate when adapted in transformers/datasets/gradio
    # @_deprecate_method(version="1.0", message="Use `huggingface_hub.get_token` instead.")
    @classmethod
    def get_token(cls) -> Optional[str]:
        """
        Get token or None if not existent.

        This method is deprecated in favor of [`huggingface_hub.get_token`] but is kept for backward compatibility.
        Its behavior is the same as [`huggingface_hub.get_token`].

        Returns:
            `str` or `None`: The token, `None` if it doesn't exist.
        """
        # 0. Check if token exist in old path but not new location
        try:
            cls._copy_to_new_path_and_warn()
        except Exception:  # if not possible (e.g. PermissionError), do not raise
            pass

        return get_token()

    # TODO: deprecate when adapted in transformers/datasets/gradio
    # @_deprecate_method(version="1.0", message="Use `huggingface_hub.logout` instead.")
    @classmethod
    def delete_token(cls) -> None:
        """
        Deletes the token from storage. Does not fail if token does not exist.
        """
        try:
            cls.path_token.unlink()
        except FileNotFoundError:
            pass

        try:
            cls._old_path_token.unlink()
        except FileNotFoundError:
            pass

    @classmethod
    def _copy_to_new_path_and_warn(cls):
        if cls._old_path_token.exists() and not cls.path_token.exists():
            cls.save_token(cls._old_path_token.read_text())
            warnings.warn(
                f"A token has been found in `{cls._old_path_token}`. This is the old"
                " path where tokens were stored. The new location is"
                f" `{cls.path_token}` which is configurable using `HF_HOME` environment"
                " variable. Your token has been copied to this new location. You can"
                " now safely delete the old token file manually or use"
                " `huggingface-cli logout`."
            )
