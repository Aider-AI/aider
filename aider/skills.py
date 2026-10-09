"""Project-local skill catalog discovery and body loading."""

import json
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from aider.exceptions import LiteLLMExceptions


_RETRY_TIMEOUT = 60


SELECTOR_SYSTEM_PROMPT = """You select project skills for a user request.
Choose every skill that is directly useful, or choose none if no skill applies.
Reply with only a JSON array of exact skill catalog identifiers, for example
[\"code-review\"] or []. Do not include explanations or identifiers that are
not in the catalog."""


@dataclass(frozen=True)
class Skill:
    """Validated catalog metadata for one project skill."""

    identifier: str
    name: str
    description: str
    path: Path


def _read_frontmatter(stream):
    """Read YAML frontmatter without reading any of the Markdown body."""
    opening = stream.readline()
    if opening.rstrip("\r\n") != "---":
        raise ValueError("missing opening frontmatter delimiter")

    lines = []
    for line in stream:
        if line.rstrip("\r\n") == "---":
            return yaml.safe_load("".join(lines))
        lines.append(line)

    raise ValueError("missing closing frontmatter delimiter")


def _warn(io, skill_path, error):
    io.tool_warning(f"Skipping skill {skill_path}: {error}")


def discover_skills(root, io):
    """Discover valid project skills in deterministic identifier order.

    Only each ``SKILL.md`` frontmatter is read. When ``root`` is unavailable,
    discovery uses the current working directory.
    """
    project_root = Path(root) if root is not None else Path.cwd()
    skills_dir = project_root / ".agents" / "skills"

    try:
        if not skills_dir.is_dir():
            return []
        directories = sorted(
            (path for path in skills_dir.iterdir() if path.is_dir()), key=lambda path: path.name
        )
    except OSError as error:
        _warn(io, skills_dir, error)
        return []

    skills = []
    for directory in directories:
        skill_path = directory / "SKILL.md"
        try:
            with skill_path.open("r", encoding="utf-8", newline="") as stream:
                metadata = _read_frontmatter(stream)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as error:
            _warn(io, skill_path, error)
            continue

        if not isinstance(metadata, dict):
            _warn(io, skill_path, "frontmatter must be a YAML mapping")
            continue

        name = metadata.get("name")
        description = metadata.get("description")
        if not isinstance(name, str) or not name.strip():
            _warn(io, skill_path, "frontmatter requires a non-empty string 'name'")
            continue
        if not isinstance(description, str) or not description.strip():
            _warn(io, skill_path, "frontmatter requires a non-empty string 'description'")
            continue

        skills.append(Skill(directory.name, name, description, skill_path))

    return skills


def load_skill_body(skill):
    """Read the complete Markdown body for a previously discovered skill."""
    with skill.path.open("r", encoding="utf-8", newline="") as stream:
        _read_frontmatter(stream)
        body = stream.read()
        # A file with no body may still end with the newline written after
        # the closing delimiter; do not treat that terminator as body text.
        if body in ("\n", "\r\n"):
            return ""
        return body


def _text_content(content):
    """Return text from a conversation message, excluding non-text attachments."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None

    text_parts = [
        part["text"]
        for part in content
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    ]
    return "".join(text_parts) if text_parts else None


def build_selector_messages(conversation, request, catalog):
    """Build a selector prompt from text history, the request, and metadata only."""
    messages = [{"role": "system", "content": SELECTOR_SYSTEM_PROMPT}]

    for message in conversation or []:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            continue
        content = _text_content(message.get("content"))
        if content is not None:
            messages.append({"role": message["role"], "content": content})

    metadata = [
        {
            "identifier": skill.identifier,
            "name": skill.name,
            "description": skill.description,
        }
        for skill in catalog
    ]
    user_content = (
        "New user request:\n"
        f"{request}\n\n"
        "Available skill catalog (metadata only):\n"
        f"{json.dumps(metadata, ensure_ascii=False)}"
    )
    messages.append({"role": "user", "content": user_content})
    return messages


def _parse_skill_identifiers(content, catalog):
    """Validate all returned identifiers before resolving any catalog records."""
    if not isinstance(content, str):
        raise ValueError("selector response was not text")
    try:
        identifiers = json.loads(content)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("selector response was not valid JSON") from error

    if not isinstance(identifiers, list) or any(
        not isinstance(identifier, str) for identifier in identifiers
    ):
        raise ValueError("selector response must be a JSON array of strings")

    skills_by_identifier = {skill.identifier: skill for skill in catalog}
    if any(identifier not in skills_by_identifier for identifier in identifiers):
        raise ValueError("selector response included an unknown skill identifier")

    selected = []
    seen = set()
    for identifier in identifiers:
        if identifier not in seen:
            selected.append(skills_by_identifier[identifier])
            seen.add(identifier)
    return selected


def parse_skill_selection(content, catalog):
    """Parse a selector response, returning no skills for any invalid response."""
    try:
        return _parse_skill_identifiers(content, catalog)
    except ValueError:
        return []


def _selector_response_content(completion):
    choices = getattr(completion, "choices", None)
    if not choices:
        raise ValueError("selector returned no completion choices")
    message = getattr(choices[0], "message", None)
    if message is None:
        raise ValueError("selector returned no completion message")
    return getattr(message, "content", None)


def _warn_selection_failure(io, error):
    io.tool_warning(f"Skill selection failed; continuing without skills: {error}")


def _account_selector_usage(io, messages, completion, response_text):
    """Report selector usage when the active Coder supplied an accounting hook."""
    callback = getattr(io, "__dict__", {}).get("_skill_usage_callback")
    if callback:
        callback(messages, completion, response_text)


def select_skills(model, io, conversation, request, catalog):
    """Select catalog records with the configured model, failing open on errors."""
    if not catalog:
        return []

    messages = build_selector_messages(conversation, request, catalog)
    litellm_ex = None
    retry_delay = 0.125

    while True:
        try:
            _hash, completion = model.send_completion(messages, functions=None, stream=False)
        except Exception as error:
            try:
                if litellm_ex is None:
                    litellm_ex = LiteLLMExceptions()
                is_provider_error = isinstance(error, litellm_ex.exceptions_tuple())
            except Exception:
                is_provider_error = False

            if is_provider_error:
                ex_info = litellm_ex.get_ex_info(error)
                should_retry = ex_info.retry
                if should_retry:
                    retry_delay *= 2
                    if retry_delay > _RETRY_TIMEOUT:
                        should_retry = False
                if should_retry:
                    time.sleep(retry_delay)
                    continue

            _warn_selection_failure(io, error)
            return []

        try:
            content = _selector_response_content(completion)
        except Exception as error:
            _account_selector_usage(io, messages, completion, "")
            _warn_selection_failure(io, error)
            return []

        _account_selector_usage(
            io, messages, completion, content if isinstance(content, str) else ""
        )
        try:
            return _parse_skill_identifiers(content, catalog)
        except Exception as error:
            _warn_selection_failure(io, error)
            return []
