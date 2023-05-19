import os
import json
import sys
import subprocess

from aider.dump import dump


def print_tags_info(filename):
    tags = sorted(get_tags(filename))
    if not tags:
        return

    last = [None] * len(tags[0])
    tab = " "
    for tag in tags:
        tag = list(tag)
        common_prefix = [tag_i for tag_i, last_i in zip(tag, last) if tag_i == last_i]
        num_common = len(common_prefix)
        indent = tab * num_common
        rest = tag[num_common:]
        for item in rest:
            print(indent + item)
            indent += tab
        last = tag


def split_path(path):
    path = os.path.relpath(path, os.getcwd())
    path_components = path.split(os.sep)
    res = [pc + os.sep for pc in path_components[:-1]]
    res.append(path_components[-1])
    return res


def get_tags(filename):
    yield split_path(filename)

    cmd = ["ctags", "--fields=+S", "--output-format=json", filename]
    output = subprocess.check_output(cmd).decode("utf-8")
    output = output.splitlines()

    for line in output:
        tag = json.loads(line)
        path = tag.get("path")
        scope = tag.get("scope")
        kind = tag.get("kind")
        name = tag.get("name")
        signature = tag.get("signature")

        last = name
        if signature:
            last += " " + signature

        res = split_path(path)
        if scope:
            res.append(scope)
        res += [kind, last]

        yield res


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        print_tags_info(filename)
