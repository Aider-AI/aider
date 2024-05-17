import os
import tree_sitter
import sys
import warnings
from pathlib import Path

from aider.dump import dump

from grep_ast import TreeContext, filename_to_lang

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_language, get_parser  # noqa: E402

def basic_lint(fname, code):

    lang = filename_to_lang(fname)

    language = get_language(lang)
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

# Traverse the tree to find errors and print context
def traverse_tree(node):
    errors = []
    if node.type == 'ERROR' or node.is_missing:
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

    for file_path in sys.argv[1:]:
        code = Path(file_path).read_text()
        errors = basic_lint(file_path, code)
        if errors:
            print(errors)

if __name__ == "__main__":
    main()
