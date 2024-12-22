import difflib
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

import json5
import yaml
from PIL import Image

from aider.dump import dump  # noqa: F401
from aider.llm import litellm

DEFAULT_MODEL_NAME = "gpt-4o"
ANTHROPIC_BETA_HEADER = "prompt-caching-2024-07-31,pdfs-2024-09-25"

OPENAI_MODELS = """
gpt-4
gpt-4o
gpt-4o-2024-05-13
gpt-4-turbo-preview
gpt-4-0314
gpt-4-0613
gpt-4-32k
gpt-4-32k-0314
gpt-4-32k-0613
gpt-4-turbo
gpt-4-turbo-2024-04-09
gpt-4-1106-preview
gpt-4-0125-preview
gpt-4-vision-preview
gpt-4-1106-vision-preview
gpt-4o-mini
gpt-4o-mini-2024-07-18
gpt-3.5-turbo
gpt-3.5-turbo-0301
gpt-3.5-turbo-0613
gpt-3.5-turbo-1106
gpt-3.5-turbo-0125
gpt-3.5-turbo-16k
gpt-3.5-turbo-16k-0613
"""

OPENAI_MODELS = [ln.strip() for ln in OPENAI_MODELS.splitlines() if ln.strip()]

ANTHROPIC_MODELS = """
claude-2
claude-2.1
claude-3-haiku-20240307
claude-3-5-haiku-20241022
claude-3-opus-20240229
claude-3-sonnet-20240229
claude-3-5-sonnet-20240620
claude-3-5-sonnet-20241022
"""

ANTHROPIC_MODELS = [ln.strip() for ln in ANTHROPIC_MODELS.splitlines() if ln.strip()]

# Mapping of model aliases to their canonical names
MODEL_ALIASES = {
    # Claude models
    "sonnet": "claude-3-5-sonnet-20241022",
    "haiku": "claude-3-5-haiku-20241022",
    "opus": "claude-3-opus-20240229",
    # GPT models
    "4": "gpt-4-0613",
    "4o": "gpt-4o",
    "4-turbo": "gpt-4-1106-preview",
    "35turbo": "gpt-3.5-turbo",
    "35-turbo": "gpt-3.5-turbo",
    "3": "gpt-3.5-turbo",
    # Other models
    "deepseek": "deepseek/deepseek-coder",
    "flash": "gemini/gemini-2.0-flash-exp",
}


@dataclass
class ModelSettings:
    # Model class needs to have each of these as well
    name: str
    edit_format: str = "whole"
    weak_model_name: Optional[str] = None
    use_repo_map: bool = False
    send_undo_reply: bool = False
    lazy: bool = False
    reminder: str = "user"
    examples_as_sys_msg: bool = False
    extra_params: Optional[dict] = None
    cache_control: bool = False
    caches_by_default: bool = False
    use_system_prompt: bool = True
    use_temperature: bool = True
    streaming: bool = True
    editor_model_name: Optional[str] = None
    editor_edit_format: Optional[str] = None


# https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
# https://platform.openai.com/docs/models/gpt-3-5-turbo
# https://openai.com/pricing

MODEL_SETTINGS = [
    # gpt-3.5
    ModelSettings(
        "gpt-3.5-turbo",
        "whole",
        weak_model_name="gpt-4o-mini",
        reminder="sys",
    ),
    ModelSettings(
        "gpt-3.5-turbo-0125",
        "whole",
        weak_model_name="gpt-4o-mini",
        reminder="sys",
    ),
    ModelSettings(
        "gpt-3.5-turbo-1106",
        "whole",
        weak_model_name="gpt-4o-mini",
        reminder="sys",
    ),
    ModelSettings(
        "gpt-3.5-turbo-0613",
        "whole",
        weak_model_name="gpt-4o-mini",
        reminder="sys",
    ),
    ModelSettings(
        "gpt-3.5-turbo-16k-0613",
        "whole",
        weak_model_name="gpt-4o-mini",
        reminder="sys",
    ),
    # gpt-4
    ModelSettings(
        "gpt-4-turbo-2024-04-09",
        "udiff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4-turbo",
        "udiff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "openai/gpt-4o",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
        editor_edit_format="editor-diff",
    ),
    ModelSettings(
        "openai/gpt-4o-2024-08-06",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4o-2024-08-06",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4o-2024-11-20",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "openai/gpt-4o-2024-11-20",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4o",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
        editor_edit_format="editor-diff",
    ),
    ModelSettings(
        "gpt-4o-mini",
        "whole",
        weak_model_name="gpt-4o-mini",
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "openai/gpt-4o-mini",
        "whole",
        weak_model_name="openai/gpt-4o-mini",
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4-0125-preview",
        "udiff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
        examples_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-1106-preview",
        "udiff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4-vision-preview",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4-0314",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        reminder="sys",
        examples_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-0613",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        reminder="sys",
    ),
    ModelSettings(
        "gpt-4-32k-0613",
        "diff",
        weak_model_name="gpt-4o-mini",
        use_repo_map=True,
        reminder="sys",
    ),
    # Claude
    ModelSettings(
        "claude-3-opus-20240229",
        "diff",
        weak_model_name="claude-3-5-haiku-20241022",
        use_repo_map=True,
    ),
    ModelSettings(
        "openrouter/anthropic/claude-3-opus",
        "diff",
        weak_model_name="openrouter/anthropic/claude-3-5-haiku",
        use_repo_map=True,
    ),
    ModelSettings(
        "claude-3-sonnet-20240229",
        "whole",
        weak_model_name="claude-3-5-haiku-20241022",
    ),
    ModelSettings(
        "claude-3-5-sonnet-20240620",
        "diff",
        weak_model_name="claude-3-5-haiku-20241022",
        editor_model_name="claude-3-5-sonnet-20240620",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
            "max_tokens": 8192,
        },
        cache_control=True,
        reminder="user",
    ),
    ModelSettings(
        "anthropic/claude-3-5-sonnet-20240620",
        "diff",
        weak_model_name="anthropic/claude-3-5-haiku-20241022",
        editor_model_name="anthropic/claude-3-5-sonnet-20240620",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
            "max_tokens": 8192,
        },
        cache_control=True,
        reminder="user",
    ),
    ModelSettings(
        "anthropic/claude-3-5-sonnet-20241022",
        "diff",
        weak_model_name="anthropic/claude-3-5-haiku-20241022",
        editor_model_name="anthropic/claude-3-5-sonnet-20241022",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
            "max_tokens": 8192,
        },
        cache_control=True,
        reminder="user",
    ),
    ModelSettings(
        "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "diff",
        weak_model_name="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
        editor_model_name="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
            "max_tokens": 8192,
        },
        cache_control=True,
        reminder="user",
    ),
    ModelSettings(
        "anthropic/claude-3-5-sonnet-latest",
        "diff",
        weak_model_name="anthropic/claude-3-5-haiku-20241022",
        editor_model_name="anthropic/claude-3-5-sonnet-20241022",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
            "max_tokens": 8192,
        },
        cache_control=True,
        reminder="user",
    ),
    ModelSettings(
        "claude-3-5-sonnet-20241022",
        "diff",
        weak_model_name="claude-3-5-haiku-20241022",
        editor_model_name="claude-3-5-sonnet-20241022",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
            "max_tokens": 8192,
        },
        cache_control=True,
        reminder="user",
    ),
    ModelSettings(
        "anthropic/claude-3-haiku-20240307",
        "whole",
        weak_model_name="anthropic/claude-3-haiku-20240307",
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
        },
        cache_control=True,
    ),
    ModelSettings(
        "anthropic/claude-3-5-haiku-20241022",
        "diff",
        weak_model_name="anthropic/claude-3-5-haiku-20241022",
        use_repo_map=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
        },
        cache_control=True,
    ),
    ModelSettings(
        "bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
        "diff",
        weak_model_name="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
        use_repo_map=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
        },
        cache_control=True,
    ),
    ModelSettings(
        "claude-3-5-haiku-20241022",
        "diff",
        weak_model_name="claude-3-5-haiku-20241022",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
        },
        cache_control=True,
    ),
    ModelSettings(
        "vertex_ai/claude-3-5-haiku@20241022",
        "diff",
        weak_model_name="vertex_ai/claude-3-5-haiku@20241022",
        use_repo_map=True,
        extra_params={
            "max_tokens": 4096,
        },
    ),
    ModelSettings(
        "claude-3-haiku-20240307",
        "whole",
        weak_model_name="claude-3-haiku-20240307",
        examples_as_sys_msg=True,
        extra_params={
            "extra_headers": {
                "anthropic-beta": ANTHROPIC_BETA_HEADER,
            },
        },
        cache_control=True,
    ),
    ModelSettings(
        "openrouter/anthropic/claude-3.5-sonnet",
        "diff",
        weak_model_name="openrouter/anthropic/claude-3-5-haiku",
        editor_model_name="openrouter/anthropic/claude-3.5-sonnet",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "max_tokens": 8192,
        },
        reminder="user",
        cache_control=True,
    ),
    ModelSettings(
        "openrouter/anthropic/claude-3.5-sonnet:beta",
        "diff",
        weak_model_name="openrouter/anthropic/claude-3-5-haiku:beta",
        editor_model_name="openrouter/anthropic/claude-3.5-sonnet:beta",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "max_tokens": 8192,
        },
        reminder="user",
        cache_control=True,
    ),
    # Vertex AI Claude models
    # Does not yet support 8k token
    ModelSettings(
        "vertex_ai/claude-3-5-sonnet@20240620",
        "diff",
        weak_model_name="vertex_ai/claude-3-5-haiku@20241022",
        editor_model_name="vertex_ai/claude-3-5-sonnet@20240620",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "max_tokens": 8192,
        },
        reminder="user",
    ),
    ModelSettings(
        "vertex_ai/claude-3-5-sonnet-v2@20241022",
        "diff",
        weak_model_name="vertex_ai/claude-3-5-haiku@20241022",
        editor_model_name="vertex_ai/claude-3-5-sonnet-v2@20241022",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        extra_params={
            "max_tokens": 8192,
        },
        reminder="user",
    ),
    ModelSettings(
        "vertex_ai/claude-3-opus@20240229",
        "diff",
        weak_model_name="vertex_ai/claude-3-5-haiku@20241022",
        use_repo_map=True,
    ),
    ModelSettings(
        "vertex_ai/claude-3-sonnet@20240229",
        "whole",
        weak_model_name="vertex_ai/claude-3-5-haiku@20241022",
    ),
    # Cohere
    ModelSettings(
        "command-r-plus",
        "whole",
        weak_model_name="command-r-plus",
        use_repo_map=True,
    ),
    # New Cohere models
    ModelSettings(
        "command-r-08-2024",
        "whole",
        weak_model_name="command-r-08-2024",
        use_repo_map=True,
    ),
    ModelSettings(
        "command-r-plus-08-2024",
        "whole",
        weak_model_name="command-r-plus-08-2024",
        use_repo_map=True,
    ),
    # Groq llama3
    ModelSettings(
        "groq/llama3-70b-8192",
        "diff",
        weak_model_name="groq/llama3-8b-8192",
        use_repo_map=False,
        send_undo_reply=False,
        examples_as_sys_msg=True,
    ),
    # Openrouter llama3
    ModelSettings(
        "openrouter/meta-llama/llama-3-70b-instruct",
        "diff",
        weak_model_name="openrouter/meta-llama/llama-3-70b-instruct",
        use_repo_map=False,
        send_undo_reply=False,
        examples_as_sys_msg=True,
    ),
    # Gemini
    ModelSettings(
        "gemini/gemini-1.5-pro-002",
        "diff",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-1.5-flash-002",
        "whole",
    ),
    ModelSettings(
        "gemini/gemini-1.5-pro",
        "diff-fenced",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-1.5-pro-latest",
        "diff-fenced",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-1.5-pro-exp-0827",
        "diff-fenced",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-exp-1206",
        "diff",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-exp-1114",
        "diff",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-exp-1121",
        "diff",
        use_repo_map=True,
    ),
    ModelSettings(
        "vertex_ai/gemini-pro-experimental",
        "diff-fenced",
        use_repo_map=True,
    ),
    ModelSettings(
        "gemini/gemini-1.5-flash-exp-0827",
        "whole",
        use_repo_map=False,
        send_undo_reply=False,
    ),
    ModelSettings(
        "gemini/gemini-2.0-flash-exp",
        "diff",
        use_repo_map=True,
        send_undo_reply=False,
    ),
    ModelSettings(
        "deepseek/deepseek-chat",
        "diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        reminder="sys",
        extra_params={
            "max_tokens": 8192,
        },
    ),
    ModelSettings(
        "deepseek/deepseek-coder",
        "diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        reminder="sys",
        caches_by_default=True,
        extra_params={
            "max_tokens": 8192,
        },
    ),
    ModelSettings(
        "deepseek-chat",
        "diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        reminder="sys",
        extra_params={
            "max_tokens": 8192,
        },
    ),
    ModelSettings(
        "deepseek-coder",
        "diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        reminder="sys",
        caches_by_default=True,
        extra_params={
            "max_tokens": 8192,
        },
    ),
    ModelSettings(
        "openrouter/deepseek/deepseek-coder",
        "diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        reminder="sys",
    ),
    ModelSettings(
        "openrouter/deepseek/deepseek-chat",
        "diff",
        use_repo_map=True,
        examples_as_sys_msg=True,
        reminder="sys",
    ),
    ModelSettings(
        "openrouter/openai/gpt-4o",
        "diff",
        weak_model_name="openrouter/openai/gpt-4o-mini",
        use_repo_map=True,
        lazy=True,
        reminder="sys",
        editor_edit_format="editor-diff",
    ),
    ModelSettings(
        "openai/o1-mini",
        "whole",
        weak_model_name="openai/gpt-4o-mini",
        editor_model_name="openai/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
    ),
    ModelSettings(
        "azure/o1-mini",
        "whole",
        weak_model_name="azure/gpt-4o-mini",
        editor_model_name="azure/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
    ),
    ModelSettings(
        "o1-mini",
        "whole",
        weak_model_name="gpt-4o-mini",
        editor_model_name="gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
    ),
    ModelSettings(
        "openai/o1-preview",
        "diff",
        weak_model_name="openai/gpt-4o-mini",
        editor_model_name="openai/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
    ),
    ModelSettings(
        "azure/o1-preview",
        "diff",
        weak_model_name="azure/gpt-4o-mini",
        editor_model_name="azure/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
    ),
    ModelSettings(
        "o1-preview",
        "architect",
        weak_model_name="gpt-4o-mini",
        editor_model_name="gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
    ),
    ModelSettings(
        "openrouter/openai/o1-mini",
        "whole",
        weak_model_name="openrouter/openai/gpt-4o-mini",
        editor_model_name="openrouter/openai/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
        streaming=False,
    ),
    ModelSettings(
        "openrouter/openai/o1-preview",
        "diff",
        weak_model_name="openrouter/openai/gpt-4o-mini",
        editor_model_name="openrouter/openai/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        reminder="user",
        use_system_prompt=False,
        use_temperature=False,
        streaming=False,
    ),
    ModelSettings(
        "openrouter/openai/o1",
        "diff",
        weak_model_name="openrouter/openai/gpt-4o-mini",
        editor_model_name="openrouter/openai/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        streaming=False,
        use_temperature=False,
        # extra_params=dict(extra_body=dict(reasoning_effort="high")),
    ),
    ModelSettings(
        "openai/o1",
        "diff",
        weak_model_name="openai/gpt-4o-mini",
        editor_model_name="openai/gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        streaming=False,
        use_temperature=False,
        # extra_params=dict(extra_body=dict(reasoning_effort="high")),
    ),
    ModelSettings(
        "o1",
        "diff",
        weak_model_name="gpt-4o-mini",
        editor_model_name="gpt-4o",
        editor_edit_format="editor-diff",
        use_repo_map=True,
        streaming=False,
        use_temperature=False,
        # extra_params=dict(extra_body=dict(reasoning_effort="high")),
    ),
    ModelSettings(
        "openrouter/qwen/qwen-2.5-coder-32b-instruct",
        "diff",
        weak_model_name="openrouter/qwen/qwen-2.5-coder-32b-instruct",
        editor_model_name="openrouter/qwen/qwen-2.5-coder-32b-instruct",
        editor_edit_format="editor-diff",
        use_repo_map=True,
    ),
]


class ModelInfoManager:
    MODEL_INFO_URL = (
        "https://raw.githubusercontent.com/BerriAI/litellm/main/"
        "model_prices_and_context_window.json"
    )
    CACHE_TTL = 60 * 60 * 24  # 24 hours

    def __init__(self):
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "model_prices_and_context_window.json"
        self.content = None
        self._load_cache()

    def _load_cache(self):
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if self.cache_file.exists():
                cache_age = time.time() - self.cache_file.stat().st_mtime
                if cache_age < self.CACHE_TTL:
                    self.content = json.loads(self.cache_file.read_text())
        except OSError:
            pass

    def _update_cache(self):
        try:
            import requests

            response = requests.get(self.MODEL_INFO_URL, timeout=5)
            if response.status_code == 200:
                self.content = response.json()
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=4))
                except OSError:
                    pass
        except Exception as ex:
            print(str(ex))
            try:
                # Save empty dict to cache file on failure
                self.cache_file.write_text("{}")
            except OSError:
                pass

    def get_model_from_cached_json_db(self, model):
        if not self.content:
            self._update_cache()

        if not self.content:
            return dict()

        info = self.content.get(model, dict())
        if info:
            return info

        pieces = model.split("/")
        if len(pieces) == 2:
            info = self.content.get(pieces[1])
            if info and info.get("litellm_provider") == pieces[0]:
                return info

        return dict()

    def get_model_info(self, model):
        cached_info = self.get_model_from_cached_json_db(model)

        litellm_info = None
        if litellm._lazy_module or not cached_info:
            try:
                litellm_info = litellm.get_model_info(model)
            except Exception as ex:
                if "model_prices_and_context_window.json" not in str(ex):
                    print(str(ex))

        if litellm_info:
            return litellm_info

        return cached_info


model_info_manager = ModelInfoManager()


class Model(ModelSettings):
    def __init__(self, model, weak_model=None, editor_model=None, editor_edit_format=None):
        # Map any alias to its canonical name
        model = MODEL_ALIASES.get(model, model)

        self.name = model

        self.max_chat_history_tokens = 1024
        self.weak_model = None
        self.editor_model = None

        # Find the extra settings
        self.extra_model_settings = next(
            (ms for ms in MODEL_SETTINGS if ms.name == "aider/extra_params"), None
        )

        self.info = self.get_model_info(model)

        # Are all needed keys/params available?
        res = self.validate_environment()
        self.missing_keys = res.get("missing_keys")
        self.keys_in_environment = res.get("keys_in_environment")

        max_input_tokens = self.info.get("max_input_tokens") or 0
        if max_input_tokens < 32 * 1024:
            self.max_chat_history_tokens = 1024
        else:
            self.max_chat_history_tokens = 2 * 1024

        self.configure_model_settings(model)
        if weak_model is False:
            self.weak_model_name = None
        else:
            self.get_weak_model(weak_model)

        if editor_model is False:
            self.editor_model_name = None
        else:
            self.get_editor_model(editor_model, editor_edit_format)

    def get_model_info(self, model):
        return model_info_manager.get_model_info(model)

    def _copy_fields(self, source):
        """Helper to copy fields from a ModelSettings instance to self"""
        for field in fields(ModelSettings):
            val = getattr(source, field.name)
            setattr(self, field.name, val)

    def configure_model_settings(self, model):
        # Look for exact model match
        exact_match = False
        for ms in MODEL_SETTINGS:
            # direct match, or match "provider/<model>"
            if model == ms.name:
                self._copy_fields(ms)
                exact_match = True
                break  # Continue to apply overrides

        model = model.lower()

        # If no exact match, try generic settings
        if not exact_match:
            self.apply_generic_model_settings(model)

        # Apply override settings last if they exist
        if self.extra_model_settings and self.extra_model_settings.extra_params:
            # Initialize extra_params if it doesn't exist
            if not self.extra_params:
                self.extra_params = {}

            # Deep merge the extra_params dicts
            for key, value in self.extra_model_settings.extra_params.items():
                if isinstance(value, dict) and isinstance(self.extra_params.get(key), dict):
                    # For nested dicts, merge recursively
                    self.extra_params[key] = {**self.extra_params[key], **value}
                else:
                    # For non-dict values, simply update
                    self.extra_params[key] = value

    def apply_generic_model_settings(self, model):
        if ("llama3" in model or "llama-3" in model) and "70b" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.send_undo_reply = True
            self.examples_as_sys_msg = True
            return  # <--

        if "gpt-4-turbo" in model or ("gpt-4-" in model and "-preview" in model):
            self.edit_format = "udiff"
            self.use_repo_map = True
            self.send_undo_reply = True
            return  # <--

        if "gpt-4" in model or "claude-3-opus" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.send_undo_reply = True
            return  # <--

        if "gpt-3.5" in model or "gpt-4" in model:
            self.reminder = "sys"
            return  # <--

        if "3.5-sonnet" in model or "3-5-sonnet" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.examples_as_sys_msg = True
            self.reminder = "user"
            return  # <--

        if model.startswith("o1-") or "/o1-" in model:
            self.use_system_prompt = False
            self.use_temperature = False
            return  # <--

        if (
            "qwen" in model
            and "coder" in model
            and ("2.5" in model or "2-5" in model)
            and "32b" in model
        ):
            self.edit_format = "diff"
            self.editor_edit_format = "editor-diff"
            self.use_repo_map = True
            if model.startswith("ollama/") or model.startswith("ollama_chat/"):
                self.extra_params = dict(num_ctx=8 * 1024)
            return  # <--

        # use the defaults
        if self.edit_format == "diff":
            self.use_repo_map = True
            return  # <--

    def __str__(self):
        return self.name

    def get_weak_model(self, provided_weak_model_name):
        # If weak_model_name is provided, override the model settings
        if provided_weak_model_name:
            self.weak_model_name = provided_weak_model_name

        if not self.weak_model_name:
            self.weak_model = self
            return

        if self.weak_model_name == self.name:
            self.weak_model = self
            return

        self.weak_model = Model(
            self.weak_model_name,
            weak_model=False,
        )
        return self.weak_model

    def commit_message_models(self):
        return [self.weak_model, self]

    def get_editor_model(self, provided_editor_model_name, editor_edit_format):
        # If editor_model_name is provided, override the model settings
        if provided_editor_model_name:
            self.editor_model_name = provided_editor_model_name
        if editor_edit_format:
            self.editor_edit_format = editor_edit_format

        if not self.editor_model_name or self.editor_model_name == self.name:
            self.editor_model = self
        else:
            self.editor_model = Model(
                self.editor_model_name,
                editor_model=False,
            )

        if not self.editor_edit_format:
            self.editor_edit_format = self.editor_model.edit_format

        return self.editor_model

    def tokenizer(self, text):
        return litellm.encode(model=self.name, text=text)

    def token_count(self, messages):
        if type(messages) is list:
            try:
                return litellm.token_counter(model=self.name, messages=messages)
            except Exception as err:
                print(f"Unable to count tokens: {err}")
                return 0

        if not self.tokenizer:
            return

        if type(messages) is str:
            msgs = messages
        else:
            msgs = json.dumps(messages)

        try:
            return len(self.tokenizer(msgs))
        except Exception as err:
            print(f"Unable to count tokens: {err}")
            return 0

    def token_count_for_image(self, fname):
        """
        Calculate the token cost for an image assuming high detail.
        The token cost is determined by the size of the image.
        :param fname: The filename of the image.
        :return: The token cost for the image.
        """
        width, height = self.get_image_size(fname)

        # If the image is larger than 2048 in any dimension, scale it down to fit within 2048x2048
        max_dimension = max(width, height)
        if max_dimension > 2048:
            scale_factor = 2048 / max_dimension
            width = int(width * scale_factor)
            height = int(height * scale_factor)

        # Scale the image such that the shortest side is 768 pixels long
        min_dimension = min(width, height)
        scale_factor = 768 / min_dimension
        width = int(width * scale_factor)
        height = int(height * scale_factor)

        # Calculate the number of 512x512 tiles needed to cover the image
        tiles_width = math.ceil(width / 512)
        tiles_height = math.ceil(height / 512)
        num_tiles = tiles_width * tiles_height

        # Each tile costs 170 tokens, and there's an additional fixed cost of 85 tokens
        token_cost = num_tiles * 170 + 85
        return token_cost

    def get_image_size(self, fname):
        """
        Retrieve the size of an image.
        :param fname: The filename of the image.
        :return: A tuple (width, height) representing the image size in pixels.
        """
        with Image.open(fname) as img:
            return img.size

    def fast_validate_environment(self):
        """Fast path for common models. Avoids forcing litellm import."""

        model = self.name
        if model in OPENAI_MODELS or model.startswith("openai/"):
            var = "OPENAI_API_KEY"
        elif model in ANTHROPIC_MODELS or model.startswith("anthropic/"):
            var = "ANTHROPIC_API_KEY"
        else:
            return

        if os.environ.get(var):
            return dict(keys_in_environment=[var], missing_keys=[])

    def validate_environment(self):
        res = self.fast_validate_environment()
        if res:
            return res

        # https://github.com/BerriAI/litellm/issues/3190

        model = self.name
        res = litellm.validate_environment(model)
        if res["keys_in_environment"]:
            return res
        if res["missing_keys"]:
            return res

        provider = self.info.get("litellm_provider", "").lower()
        if provider == "cohere_chat":
            return validate_variables(["COHERE_API_KEY"])
        if provider == "gemini":
            return validate_variables(["GEMINI_API_KEY"])
        if provider == "groq":
            return validate_variables(["GROQ_API_KEY"])

        return res


def register_models(model_settings_fnames):
    files_loaded = []
    for model_settings_fname in model_settings_fnames:
        if not os.path.exists(model_settings_fname):
            continue

        if not Path(model_settings_fname).read_text().strip():
            continue

        try:
            with open(model_settings_fname, "r") as model_settings_file:
                model_settings_list = yaml.safe_load(model_settings_file)

            for model_settings_dict in model_settings_list:
                model_settings = ModelSettings(**model_settings_dict)
                existing_model_settings = next(
                    (ms for ms in MODEL_SETTINGS if ms.name == model_settings.name), None
                )

                if existing_model_settings:
                    MODEL_SETTINGS.remove(existing_model_settings)
                MODEL_SETTINGS.append(model_settings)
        except Exception as e:
            raise Exception(f"Error loading model settings from {model_settings_fname}: {e}")
        files_loaded.append(model_settings_fname)

    return files_loaded


def register_litellm_models(model_fnames):
    files_loaded = []
    for model_fname in model_fnames:
        if not os.path.exists(model_fname):
            continue

        try:
            data = Path(model_fname).read_text()
            if not data.strip():
                continue
            model_def = json5.loads(data)
            if not model_def:
                continue

            # only load litellm if we have actual data
            litellm._load_litellm()
            litellm.register_model(model_def)
        except Exception as e:
            raise Exception(f"Error loading model definition from {model_fname}: {e}")

        files_loaded.append(model_fname)

    return files_loaded


def validate_variables(vars):
    missing = []
    for var in vars:
        if var not in os.environ:
            missing.append(var)
    if missing:
        return dict(keys_in_environment=False, missing_keys=missing)
    return dict(keys_in_environment=True, missing_keys=missing)


def sanity_check_models(io, main_model):
    problem_main = sanity_check_model(io, main_model)

    problem_weak = None
    if main_model.weak_model and main_model.weak_model is not main_model:
        problem_weak = sanity_check_model(io, main_model.weak_model)

    problem_editor = None
    if (
        main_model.editor_model
        and main_model.editor_model is not main_model
        and main_model.editor_model is not main_model.weak_model
    ):
        problem_editor = sanity_check_model(io, main_model.editor_model)

    return problem_main or problem_weak or problem_editor


def sanity_check_model(io, model):
    show = False

    if model.missing_keys:
        show = True
        io.tool_warning(f"Warning: {model} expects these environment variables")
        for key in model.missing_keys:
            value = os.environ.get(key, "")
            status = "Set" if value else "Not set"
            io.tool_output(f"- {key}: {status}")

        if platform.system() == "Windows":
            io.tool_output(
                "Note: You may need to restart your terminal or command prompt for `setx` to take"
                " effect."
            )

    elif not model.keys_in_environment:
        show = True
        io.tool_warning(f"Warning for {model}: Unknown which environment variables are required.")

    if not model.info:
        show = True
        io.tool_warning(
            f"Warning for {model}: Unknown context window size and costs, using sane defaults."
        )

        possible_matches = fuzzy_match_models(model.name)
        if possible_matches:
            io.tool_output("Did you mean one of these?")
            for match in possible_matches:
                io.tool_output(f"- {match}")

    return show


def fuzzy_match_models(name):
    name = name.lower()

    chat_models = set()
    for model, attrs in litellm.model_cost.items():
        model = model.lower()
        if attrs.get("mode") != "chat":
            continue
        provider = attrs.get("litellm_provider", "").lower()
        if not provider:
            continue
        provider += "/"

        if model.startswith(provider):
            fq_model = model
        else:
            fq_model = provider + model

        chat_models.add(fq_model)
        chat_models.add(model)

    chat_models = sorted(chat_models)
    # exactly matching model
    # matching_models = [
    #    (fq,m) for fq,m in chat_models
    #    if name == fq or name == m
    # ]
    # if matching_models:
    #    return matching_models

    # Check for model names containing the name
    matching_models = [m for m in chat_models if name in m]
    if matching_models:
        return sorted(set(matching_models))

    # Check for slight misspellings
    models = set(chat_models)
    matching_models = difflib.get_close_matches(name, models, n=3, cutoff=0.8)

    return sorted(set(matching_models))


def print_matching_models(io, search):
    matches = fuzzy_match_models(search)
    if matches:
        io.tool_output(f'Models which match "{search}":')
        for model in matches:
            io.tool_output(f"- {model}")
    else:
        io.tool_output(f'No models match "{search}".')


def get_model_settings_as_yaml():
    import yaml

    model_settings_list = []
    for ms in MODEL_SETTINGS:
        model_settings_dict = {
            field.name: getattr(ms, field.name) for field in fields(ModelSettings)
        }
        model_settings_list.append(model_settings_dict)

    return yaml.dump(model_settings_list, default_flow_style=False)


def main():
    if len(sys.argv) < 2:
        print("Usage: python models.py <model_name> or python models.py --yaml")
        sys.exit(1)

    if sys.argv[1] == "--yaml":
        yaml_string = get_model_settings_as_yaml()
        print(yaml_string)
    else:
        model_name = sys.argv[1]
        matching_models = fuzzy_match_models(model_name)

        if matching_models:
            print(f"Matching models for '{model_name}':")
            for model in matching_models:
                print(model)
        else:
            print(f"No matching models found for '{model_name}'.")


if __name__ == "__main__":
    main()
