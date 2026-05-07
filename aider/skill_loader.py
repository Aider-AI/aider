"""
skill_loader.py — Loads Claude Code skills from ~/.claude/skills/ for the aider GUI.

Scans each subdirectory for a SKILL.md with YAML frontmatter and returns a list of
skill dicts: {name, description, path}. Results are cached for the lifetime of the
process (one scan per session).
"""

import os
import re

_SKILLS_DIR = os.path.expanduser("~/.claude/skills")
_SKILLS_CACHE = None


def _parse_frontmatter(text):
    """
    Extract YAML frontmatter from a SKILL.md string.
    Returns a dict with at least 'name' and 'description' keys, or an empty dict.
    Only parses what we need (name, description, triggers) — no external YAML dep required.
    """
    if not text.startswith("---"):
        return {}

    end = text.find("\n---", 3)
    if end == -1:
        return {}

    block = text[3:end].strip()
    result = {}

    # Parse name
    name_match = re.search(r'^name:\s*["\']?(.*?)["\']?\s*$', block, re.MULTILINE)
    if name_match:
        result["name"] = name_match.group(1).strip()

    # Parse description (may be quoted with single or double quotes, or unquoted multiline)
    desc_match = re.search(r'^description:\s*["\']?(.*?)["\']?\s*$', block, re.MULTILINE)
    if desc_match:
        result["description"] = desc_match.group(1).strip()

    # Parse triggers (YAML list)
    triggers_block = re.search(r'^triggers:\s*\n((?:\s+-\s+.*\n?)+)', block, re.MULTILINE)
    if triggers_block:
        raw_lines = triggers_block.group(1).splitlines()
        triggers = []
        for line in raw_lines:
            m = re.match(r'\s+-\s+["\']?(.*?)["\']?\s*$', line)
            if m:
                triggers.append(m.group(1).strip())
        result["triggers"] = triggers

    return result


def load_skills():
    """
    Scan ~/.claude/skills/ and return a sorted list of skill dicts:
      {name: str, description: str, path: str (absolute path to SKILL.md)}

    Result is cached — call this as many times as you like, disk is only hit once.
    """
    global _SKILLS_CACHE
    if _SKILLS_CACHE is not None:
        return _SKILLS_CACHE

    skills = []

    if not os.path.isdir(_SKILLS_DIR):
        _SKILLS_CACHE = skills
        return skills

    for entry in os.scandir(_SKILLS_DIR):
        if not entry.is_dir():
            continue
        skill_md_path = os.path.join(entry.path, "SKILL.md")
        if not os.path.isfile(skill_md_path):
            continue

        try:
            with open(skill_md_path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read(4096)  # frontmatter is always in the first few KB
        except OSError:
            continue

        meta = _parse_frontmatter(content)
        skill_name = meta.get("name") or entry.name
        skill_desc = meta.get("description") or ""

        skills.append(
            {
                "name": skill_name,
                "description": skill_desc,
                "path": skill_md_path,
            }
        )

    # Sort alphabetically by name
    skills.sort(key=lambda s: s["name"].lower())

    _SKILLS_CACHE = skills
    return skills


def get_skill_by_name(skill_name):
    """
    Look up a single skill by its name (case-insensitive). Returns the skill dict or None.
    """
    target = skill_name.lstrip("/").lower()
    for skill in load_skills():
        if skill["name"].lower() == target:
            return skill
    return None


def get_skill_prompt(skill_name):
    """
    Return the injection prompt for a single skill invocation.
    If the skill is not found, return a best-effort prompt using the skill name alone.
    """
    skill = get_skill_by_name(skill_name)
    clean_name = skill_name.lstrip("/")

    if skill:
        path = skill["path"]
        return (
            f"The user has invoked the /{clean_name} command. "
            f"Load the skill file at {path} into your working memory and execute its "
            f"contents as your directions. Read the file now and follow it."
        )
    else:
        return (
            f"The user has invoked the /{clean_name} command. "
            f"Execute the /{clean_name} skill as your directions."
        )


def get_multi_skill_prompt(skill_names):
    """
    Return a sequenced injection prompt for multiple skills.
    skill_names: list of str, each may have a leading "/" or not.
    """
    if not skill_names:
        return ""
    if len(skill_names) == 1:
        return get_skill_prompt(skill_names[0])

    lines = [
        "The user has invoked multiple skills in sequence. "
        "Execute them one at a time in order:",
        "",
    ]
    for i, sname in enumerate(skill_names, start=1):
        skill = get_skill_by_name(sname)
        clean = sname.lstrip("/")
        if skill:
            lines.append(f"Task {i}: /{clean} — Load {skill['path']} and execute its directions.")
        else:
            lines.append(f"Task {i}: /{clean} — Execute the /{clean} skill as your directions.")

    lines.append("")
    lines.append("Start with Task 1. When complete, proceed to the next task. Do not skip any task.")
    return "\n".join(lines)


def build_skill_option_labels(skills=None):
    """
    Return a list of display strings for use in a multiselect widget.
    Format: "/name — description (truncated)"
    """
    if skills is None:
        skills = load_skills()
    labels = []
    for s in skills:
        desc = s["description"]
        if len(desc) > 80:
            desc = desc[:77] + "..."
        if desc:
            labels.append(f"/{s['name']} — {desc}")
        else:
            labels.append(f"/{s['name']}")
    return labels


def skill_name_from_label(label):
    """
    Parse the skill name back out of a display label produced by build_skill_option_labels().
    Returns the plain name without the leading "/".
    """
    # Label format: "/name — ..." or "/name"
    name_part = label.split(" — ")[0].lstrip("/").strip()
    return name_part
