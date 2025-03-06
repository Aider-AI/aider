"""
Python language handler for workon.py
"""

import os
import re
import ast
import logging
from typing import Dict, List, Tuple, Set, Optional, Any

from aider.langusage.languages.base import LanguageHandler

# Configure logging
logger = logging.getLogger(__name__)

class PythonHandler(LanguageHandler):
    """Handler for Python files"""
    
    def find_files(self, start_dir: str) -> List[str]:
        """Find all Python files in the given directory and its subdirectories."""
        logger.debug(f"Scanning for Python files in: {start_dir}")
        file_count = 0
        python_files = []
        for root, _, files in os.walk(start_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    file_count += 1
                    if file_count % 100 == 0:
                        logger.debug(f"Found {file_count} Python files so far...")
                    python_files.append(file_path)
        logger.debug(f"Total Python files found: {file_count}")
        return python_files
    
    def extract_exports(self, file_path: str) -> Dict[str, List[str]]:
        """Extract exported classes, functions, etc. from a Python file."""
        try:
            logger.debug(f"Extracting exports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the Python file
            try:
                tree = ast.parse(content)
            except SyntaxError:
                logger.warning(f"Syntax error in {file_path}, skipping")
                return {
                    'classes': [],
                    'functions': [],
                    'variables': [],
                    'module': []
                }
            
            classes = []
            functions = []
            variables = []
            
            # Extract module name from file path
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Extract top-level definitions
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append(target.id)
            
            return {
                'classes': classes,
                'functions': functions,
                'variables': variables,
                'module': [module_name]
            }
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {
                'classes': [],
                'functions': [],
                'variables': [],
                'module': []
            }
    
    def extract_imports(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Extract imports from a Python file."""
        try:
            logger.debug(f"Extracting imports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the Python file
            try:
                tree = ast.parse(content)
            except SyntaxError:
                logger.warning(f"Syntax error in {file_path}, skipping")
                return []
            
            imports = []
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    # Handle: import module
                    for name in node.names:
                        imports.append((name.asname or name.name, name.name, 'direct'))
                
                elif isinstance(node, ast.ImportFrom):
                    # Handle: from module import name
                    module = node.module or ''
                    for name in node.names:
                        if name.name == '*':
                            # Handle wildcard imports: from module import *
                            imports.append(('*', module, 'wildcard'))
                        else:
                            # Handle regular imports: from module import name
                            imports.append((name.asname or name.name, f"{module}.{name.name}", 'from'))
            
            return imports
        except Exception as e:
            logger.error(f"Error extracting imports from {file_path}: {e}")
            return []
    
    def resolve_import_path(self, base_file: str, import_path: str, src_dir: str) -> Optional[str]:
        """Resolve Python import paths to actual file paths."""
        logger.debug(f"Resolving import path: '{import_path}' from file: '{base_file}'")
        
        # Convert dot notation to directory structure
        # e.g., package.module -> package/module.py
        path_parts = import_path.split('.')
        
        # Try different possible file paths
        possible_paths = []
        
        # 1. Direct module import (e.g., import package.module)
        module_path = os.path.join(src_dir, *path_parts) + '.py'
        if os.path.exists(module_path):
            return module_path
        
        # 2. Package import (e.g., import package)
        package_init = os.path.join(src_dir, *path_parts, '__init__.py')
        if os.path.exists(package_init):
            return package_init
        
        # 3. Relative import from current package
        base_dir = os.path.dirname(os.path.abspath(base_file))
        rel_module_path = os.path.join(base_dir, *path_parts) + '.py'
        if os.path.exists(rel_module_path):
            return rel_module_path
        
        # 4. Search for any module that matches the last part of the import path
        if len(path_parts) > 0:
            module_name = path_parts[-1]
            for root, _, files in os.walk(src_dir):
                for file in files:
                    if file == f"{module_name}.py":
                        return os.path.join(root, file)
        
        logger.debug(f"Could not resolve import path: {import_path}")
        return None
    
    def _is_index_file(self, file_path: str) -> bool:
        """Check if the file is an __init__.py file"""
        return os.path.basename(file_path) == '__init__.py'
    
    def _print_detailed_exports(self, exports: Dict[str, List[str]]) -> None:
        """Print detailed exports information"""
        if exports['module']:
            print(f"  Module: {exports['module'][0]}")
        
        if exports['classes']:
            print("  Classes:")
            for cls in exports['classes']:
                print(f"    - {cls}")
        
        if exports['functions']:
            print("  Functions:")
            for func in exports['functions']:
                print(f"    - {func}")
        
        if exports['variables']:
            print("  Variables:")
            for var in exports['variables']:
                print(f"    - {var}")
