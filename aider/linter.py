import os
import traceback
import subprocess
import sys
import warnings
import py_compile
from pathlib import Path

from aider.dump import dump

from grep_ast import TreeContext, filename_to_lang

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_parser  # noqa: E402
import traceback


class Linter:
    def __init__(self, encoding="utf-8", root=None):
        self.encoding = encoding
        self.root = root

        fatal = "E9,F821,F823,F831,F406,F407,F701,F702,F704,F706"
        py_cmd = f"flake8 --select={fatal} --show-source"  # noqa: F841

        self.languages = dict(
            python=self.py_lint,
        )

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
        code = Path(fname).read_text(self.encoding)

        cmd = self.languages.get(lang)

        if callable(cmd):
            return cmd(fname, rel_fname, code)

        if cmd:
            return self.run_cmd(cmd, rel_fname)

        return basic_lint(rel_fname, code)

    def py_lint(self, fname, rel_fname, code):
        res = basic_lint(rel_fname, code)
        if res:
            return res

        return lint_pycompile(fname, code)

def lint_pycompile(fname, code):
    try:
        # py_compile.compile(fname, doraise=True)
        compile(code, fname, 'exec')
        return
    except ValueError as err:
        dump(dir(err))
        dump(err.text)
        res = f"{type(err).__name__}: {err}\n"
        line_numbers = list(range(err.lineno - 1, err.end_lineno))

    dump(line_numbers)

    # Print out the Traceback, but only the last call stack
    tb_lines = traceback.format_exception(type(err), err, err.__traceback__)
    last_call_stack = ''.join(tb_lines[-2:])
    res += last_call_stack

    res += '\n'
    res += tree_context(fname, code, line_numbers)
    return res

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

    return tree_context(fname, code, errors)

def tree_context(fname, code, line_nums):
    context = TreeContext(
        fname,
        code,
        color=False,
        line_number=True,
        child_context=False,
        last_line=False,
        margin=0,
        mark_lois=True,
        loi_pad=5,
        # header_max=30,
        show_top_of_file_parent_scope=False,
    )
    line_nums = set(line_nums)
    context.add_lines_of_interest(line_nums)
    context.add_context()
    s = "s" if len(line_nums) > 1 else ""
    output = f"# Fix the error{s}, see relevant line{s} below marked with █.\n\n"
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
