import os
import subprocess
import sys
import warnings
from pathlib import Path

from grep_ast import TreeContext, filename_to_lang

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_parser  # noqa: E402


class Linter:
    def __init__(self, encoding="utf-8", root=None):
        self.encoding = encoding
        self.root = root

        fatal = "E9,F821,F823,F831,F406,F407,F701,F702,F704,F706"
        py_cmd = f"flake8 --select={fatal} --show-source"

        self.languages = dict(python=py_cmd)

    def set_linter(self, lang, cmd):
        self.languages[lang] = cmd

    def get_rel_fname(self, fname):
        if self.root:
            return os.path.relpath(fname, self.root)
        else:
            return fname

    def run_cmd(self, cmd, rel_fname):
        cmd += " " + rel_fname
        cmd = cmd.split()
        try:
            subprocess.check_output(cmd, cwd=self.root).decode()
            return  # zero exit status
        except subprocess.CalledProcessError as err:
            return err.output.decode()  # non-zero exit status

    def lint(self, fname):
        lang = filename_to_lang(fname)
        if not lang:
            return

        rel_fname = self.get_rel_fname(fname)

        cmd = self.languages[lang]
        if cmd:
            return self.run_cmd(cmd, rel_fname)

        # fall back to tree sitter / tree context linter
        code = Path(fname).read_text(self.encoding)

        return basic_lint(rel_fname, code)


def basic_lint(fname, code):
    """
    Use tree-sitter to look for syntax errors, display them with tree context.
    """

    lang = filename_to_lang(fname)
    if not lang:
        return

    parser = get_parser(lang)
    tree = parser.parse(bytes(code, "utf-8"))

    errors = traverse_tree(tree.root_node)
    if not errors:
        return

    context = TreeContext(
        fname,
        code,
        color=False,
        line_number=False,
        child_context=False,
        last_line=False,
        margin=0,
        mark_lois=True,
        loi_pad=5,
        # header_max=30,
        show_top_of_file_parent_scope=False,
    )
    context.add_lines_of_interest(errors)
    context.add_context()
    output = "# Syntax Errors found on the lines marked with █\n"
    output += fname + ":\n"
    output += context.format()

    return output


# Traverse the tree to find errors
def traverse_tree(node):
    errors = []
    if node.type == "ERROR" or node.is_missing:
        line_no = node.start_point[0]
        errors.append(line_no)

    for child in node.children:
        errors += traverse_tree(child)

    return errors


def main():
    """
    Main function to parse files provided as command line arguments.
    """
    if len(sys.argv) < 2:
        print("Usage: python linter.py <file1> <file2> ...")
        sys.exit(1)

    linter = Linter(root=os.getcwd())
    for file_path in sys.argv[1:]:
        errors = linter.lint(file_path)
        if errors:
            print(errors)


if __name__ == "__main__":
    main()
