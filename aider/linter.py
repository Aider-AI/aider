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

    # Traverse the tree to find errors
    def traverse_tree(node):
        if node.type == 'ERROR':
            print(f"Syntax error at line: {node.start_point[0] + 1}")
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
