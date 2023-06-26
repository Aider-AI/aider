from pathlib import Path

from .dump import dump  # noqa: F401


def quoted_file(fname, display_fname, fence_ticks="```", number=False):
    prompt = "\n"
    prompt += display_fname
    prompt += f"\n{fence_ticks}\n"
    file_content = Path(fname).read_text()
    lines = file_content.splitlines()
    for i, line in enumerate(lines, start=1):
        if number:
            prompt += f"{i:4d} "
        prompt += line + "\n"

    prompt += f"{fence_ticks}\n"
    return prompt


def show_messages(messages, title=None):
    if title:
        print(title.upper(), "*" * 50)

    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"].splitlines()
        for line in content:
            print(role, line)
