import math

from difflib import SequenceMatcher
from pathlib import Path

# from aider.dump import dump


def replace_most_similar_chunk(whole, part, replace):
    if part in whole:
        return whole.replace(part, replace)

    similarity_thresh = 0.8

    max_similarity = 0
    most_similar_chunk_start = -1
    most_similar_chunk_end = -1

    whole_lines = whole.splitlines()
    part_lines = part.splitlines()

    scale = 0.1
    min_len = math.floor(len(part_lines) * (1 - scale))
    max_len = math.ceil(len(part_lines) * (1 + scale))

    for length in range(min_len, max_len):
        for i in range(len(whole_lines) - length + 1):
            chunk = whole_lines[i : i + length]
            chunk = "\n".join(chunk)

            similarity = SequenceMatcher(None, chunk, part).ratio()

            if similarity > max_similarity and similarity:
                max_similarity = similarity
                most_similar_chunk_start = i
                most_similar_chunk_end = i + length

    if max_similarity < similarity_thresh:
        return

    replace_lines = replace.splitlines()
    modified_whole = (
        whole_lines[:most_similar_chunk_start]
        + replace_lines
        + whole_lines[most_similar_chunk_end:]
    )
    modified_whole = "\n".join(modified_whole)

    if whole.endswith("\n"):
        modified_whole += "\n"

    return modified_whole


def quoted_file(fname, display_fname):
    prompt = "\n"
    prompt += display_fname
    prompt += "\n```\n"
    prompt += Path(fname).read_text()
    prompt += "\n```\n"
    return prompt


def strip_quoted_wrapping(res, fname=None):
    """
    Given an input string which may have extra "wrapping" around it, remove the wrapping.
    For example:

    filename.ext
    ```
    We just want this content
    Not the filename and triple quotes
    ```
    """
    if not res:
        return res

    res = res.splitlines()

    if fname and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res[0].startswith("```") and res[-1].startswith("```"):
        res = res[1:-1]

    res = "\n".join(res)
    if res and res[-1] != "\n":
        res += "\n"

    return res


def do_replace(fname, before_text, after_text):
    before_text = strip_quoted_wrapping(before_text, fname)
    after_text = strip_quoted_wrapping(after_text, fname)
    fname = Path(fname)

    # does it want to make a new file?
    if not fname.exists() and not before_text.strip():
        fname.touch()

    content = fname.read_text()

    if not before_text.strip():
        if content:
            new_content = content + after_text
        else:
            # first populating an empty file
            new_content = after_text
    else:
        new_content = replace_most_similar_chunk(content, before_text, after_text)
        if not new_content:
            return

    fname.write_text(new_content)
    return True


def show_messages(messages, title):
    print(title.upper(), "*" * 50)

    for msg in messages:
        print()
        print("-" * 50)
        role = msg["role"].upper()
        content = msg["content"].splitlines()
        for line in content:
            print(role, line)
