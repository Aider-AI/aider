import os
import tree_sitter

def parse_file_for_errors(file_path):
    """
    Parses the given file using tree-sitter and prints out the line number of every syntax/parse error.
    """
    # Load the language
    Language = tree_sitter.Language
    PARSER = tree_sitter.Parser()
    LANGUAGE = Language(os.path.join('build', 'my-languages.so'), 'python')
    PARSER.set_language(LANGUAGE)

    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Parse the content
    tree = PARSER.parse(bytes(content, "utf8"))

    # Traverse the tree to find errors
    def traverse_tree(node):
        if node.type == 'ERROR':
            print(f"Syntax error at line: {node.start_point[0] + 1}")
        for child in node.children:
            traverse_tree(child)

    traverse_tree(tree.root_node)
