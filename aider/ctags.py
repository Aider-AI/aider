import os
import json
import sys
import subprocess

# Global cache for tags
TAGS_CACHE = {}

# from aider.dump import dump


def get_tags_map(filenames, root_dname=None):
    if not root_dname:
        root_dname = os.getcwd()

    tags = []
    for filename in filenames:
        if filename.endswith(".md"):
            continue
        tags += get_tags(filename, root_dname)
    if not tags:
        return

    tags = sorted(tags)

    output = ""
    last = [None] * len(tags[0])
    tab = "\t"
    for tag in tags:
        tag = list(tag)

        for i in range(len(last)):
            if last[i] != tag[i]:
                break

        num_common = i
        indent = tab * num_common
        rest = tag[num_common:]
        for item in rest:
            output += indent + item + "\n"
            indent += tab
        last = tag

    return output


def split_path(path, root_dname):
    path = os.path.relpath(path, root_dname)
    path_components = path.split(os.sep)
    res = [pc + os.sep for pc in path_components[:-1]]
    res.append(path_components[-1] + ":")
    return res


def get_tags(filename, root_dname):
    # Check if the file is in the cache and if the modification time has not changed
    file_mtime = os.path.getmtime(filename)
    cache_key = (filename, root_dname)
    if cache_key in TAGS_CACHE and TAGS_CACHE[cache_key]["mtime"] == file_mtime:
        return TAGS_CACHE[cache_key]["tags"]

    cmd = ["ctags", "--fields=+S", "--extras=-F", "--output-format=json", filename]
    output = subprocess.check_output(cmd).decode("utf-8")
    output = output.splitlines()

    tags = []
    if not output:
        tags.append(split_path(filename, root_dname))

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

        res = split_path(path, root_dname)
        if scope:
            res.append(scope)
        res += [kind, last]
        tags.append(res)

    # Update the cache
    TAGS_CACHE[cache_key] = {"mtime": file_mtime, "tags": tags}

    return tags


if __name__ == "__main__":
    res = get_tags_map(sys.argv[1:])
    print(res)
