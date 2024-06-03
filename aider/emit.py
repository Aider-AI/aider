import os
import sys
from pathlib import Path


def emit(src, dest):
    try:
        template_content = read_template(src)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return
    if dest is None:
        print(template_content)
    else:
        dest_file_path = dest_path(src, dest)
        dest_dir = os.path.dirname(dest_file_path)
        if not os.path.exists(dest_dir):
            print(f"Error: The directory {dest_dir} does not exist.", file=sys.stderr)
        elif os.path.exists(dest_file_path):
            print(f"Refusing to overwrite the existing file at: {dest_file_path}", file=sys.stderr)
        else:
            write_template(template_content, dest_file_path)


def src_path(fname):
    return os.path.join(Path(__file__).parent, "emit", fname)


def dest_path(src, dest):
    return os.path.join(dest, src)


def read_template(fname):
    template_path = src_path(fname)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Error: The template file {fname} does not exist.")
    with open(template_path, "r") as file:
        return file.read()


def write_template(template_content, file_path):
    with open(file_path, "w") as file:
        file.write(template_content)
    print(f"Template written to: {file_path}")
