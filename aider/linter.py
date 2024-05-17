import os
import tree_sitter
import sys
import warnings

# tree_sitter is throwing a FutureWarning
warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_language, get_parser  # noqa: E402

def parse_file_for_errors(file_path):

    lang = "python"

    language = get_language(lang)
    parser = get_parser(lang)

    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()

    tree = parser.parse(bytes(content, "utf8"))

    # Traverse the tree to find errors and print context
    def traverse_tree(node):
        if node.type == 'ERROR' or node.is_missing:
            error_type = 'Syntax error' if node.type == 'ERROR' else 'Missing element'
            start_line = max(0, node.start_point[0] - 3)
            end_line = node.end_point[0] + 3
            error_line = node.start_point[0] + 1

            with open(file_path, 'r') as file:
                lines = file.readlines()

            print(f"{error_type} at line: {error_line}")
            print("Context:")
            for i in range(start_line, min(end_line, len(lines))):
                line_number = i + 1
                prefix = ">> " if line_number == error_line else "   "
                print(f"{prefix}{line_number}: {lines[i].rstrip()}")
            print("\n")
        for child in node.children:
            traverse_tree(child)

    traverse_tree(tree.root_node)

def main():
    """
    Main function to parse files provided as command line arguments.
    """
    if len(sys.argv) < 2:
        print("Usage: python linter.py <file1> <file2> ...")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        print(f"Checking file: {file_path}")
        parse_file_for_errors(file_path)

if __name__ == "__main__":
    main()
