import os
import shutil
import logging
import sys

# Adjust the Python path to include the parent directory of repomap_package
# This allows running example.py directly for testing, assuming repomap_package
# is in the same directory or its parent is in PYTHONPATH.
# For actual usage as a package, the package would be installed or PYTHONPATH set up.
# This is a common pattern for examples within a package structure.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from repomap_package.aider_service.repomap import RepoMap
except ModuleNotFoundError:
    # Fallback for cases where the example is run and repomap_package is the CWD
    # or directly in PYTHONPATH without the parent structure.
    from aider_service.repomap import RepoMap


def main():
    # --- Setup Basic Logging ---
    # So we can see output from RepoMap's logging calls
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # --- Create a Dummy Repository for the Example ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_repo_root = os.path.join(script_dir, "temp_repo_root_for_example")

    if os.path.exists(temp_repo_root):
        shutil.rmtree(temp_repo_root)
    os.makedirs(temp_repo_root)

    # Create sample files
    file1_content = """
class MyClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        # A simple greeting method
        return f"Hello, {self.name}!"

def top_level_function(value):
    # This function does something
    return value * 2
"""
    file1_path = os.path.join(temp_repo_root, "module_one.py")
    with open(file1_path, "w", encoding='utf-8') as f:
        f.write(file1_content)

    file2_content = """
# Another module
import module_one

class AnotherClass:
    def __init__(self):
        self.helper = module_one.MyClass("Helper")
        self.value = 100

    def process(self):
        return self.helper.greet() + f" and value is {self.value}"
"""
    file2_path = os.path.join(temp_repo_root, "module_two.py")
    with open(file2_path, "w", encoding='utf-8') as f:
        f.write(file2_content)

    # Create a subdirectory and another file
    sub_dir = os.path.join(temp_repo_root, "utils")
    os.makedirs(sub_dir)
    file3_content = """
# Utility functions
CONSTANT_VAL = "IMPORTANT_CONFIG"

def util_func():
    return CONSTANT_VAL
"""
    file3_path = os.path.join(sub_dir, "tools.py")
    with open(file3_path, "w", encoding='utf-8') as f:
        f.write(file3_content)


    logging.info(f"Dummy repository created at: {temp_repo_root}")

    # --- Instantiate RepoMap ---
    # Note: verbose=True in RepoMap would enable more detailed logging if implemented,
    # here we control overall verbosity via logging.basicConfig.
    # The 'verbose' param in RepoMap was originally for its internal print/io.tool_output.
    # We can pass verbose=True to see if it influences any logging decisions within.
    repo_map_instance = RepoMap(
        root=temp_repo_root,
        map_tokens=2048, # Example value
        verbose=True # This will make RepoMap use logging.info for some messages
    )

    # --- List of files to map ---
    # These should be absolute paths.
    files_to_map = [
        os.path.abspath(file1_path),
        os.path.abspath(file2_path),
        os.path.abspath(file3_path),
    ]

    # --- Files to exclude (e.g., already in chat context) ---
    # These should be relative paths from the repo_root for identifying them.
    chat_files_relative_for_exclusion = ["utils/tools.py"]

    # However, RepoMap methods generally expect absolute paths for processing.
    # So, we'll convert all paths to absolute for internal processing,
    # and use the relative list for exclusion logic where appropriate.

    # All unique absolute paths in the repo for this example
    all_repo_files_abs = files_to_map

    # Absolute paths of files that are in chat context
    chat_files_abs = [
        os.path.abspath(os.path.join(temp_repo_root, rel_path))
        for rel_path in chat_files_relative_for_exclusion
    ]

    logging.info("Generating repository map...")

    # --- Get the Repository Map ---
    # RepoMap.get_repo_map expects:
    # - chat_files: list of files considered in chat (these will be used for ranking context but excluded from the map output)
    # - other_files: list of other files in the repo to consider for map display and ranking context.
    # For RepoMap to correctly process files (read content, get mtime), it needs absolute paths.
    # The exclusion from the final map is handled by `to_tree_simplified` using relative paths.

    # The `other_files` parameter for `get_repo_map` should be all files *including* chat files,
    # as they all form the graph. The `chat_files` parameter is used to mark which ones
    # are "in chat" for personalization and final exclusion from the tree render.
    # This matches how aider's Coder class calls it.

    map_output = repo_map_instance.get_repo_map(
        chat_files=chat_files_abs,      # Absolute paths of files in chat
        other_files=all_repo_files_abs, # All relevant absolute file paths in the repo
        mentioned_fnames=set(),         # Optional: set of rel_fnames that were explicitly mentioned
        mentioned_idents=set()          # Optional: set of idents that were explicitly mentioned
    )

    print("\n--- Repository Map Output ---")
    print(map_output)
    print("--- End of Repository Map ---")

    # --- Clean up the Dummy Repository ---
    try:
        shutil.rmtree(temp_repo_root)
        logging.info(f"Cleaned up dummy repository: {temp_repo_root}")
    except OSError as e:
        logging.error(f"Error cleaning up dummy repository: {e}")

if __name__ == "__main__":
    main()
