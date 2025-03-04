"""
Kotlin language handler for workon.py
"""

import os
import re
import logging
from typing import Dict, List, Tuple, Set, Optional, Any

from languages.base import LanguageHandler

# Configure logging
logger = logging.getLogger(__name__)

class KotlinHandler(LanguageHandler):
    """Handler for Kotlin files"""
    
    def find_files(self, start_dir: str) -> List[str]:
        """Find all Kotlin files in the given directory and its subdirectories."""
        logger.debug(f"Scanning for Kotlin files in: {start_dir}")
        file_count = 0
        for root, _, files in os.walk(start_dir):
            for file in files:
                if file.endswith('.kt') or file.endswith('.kts'):
                    file_path = os.path.join(root, file)
                    file_count += 1
                    if file_count % 100 == 0:
                        logger.debug(f"Found {file_count} Kotlin files so far...")
                    yield file_path
        logger.debug(f"Total Kotlin files found: {file_count}")
    
    def extract_exports(self, file_path: str) -> Dict[str, List[str]]:
        """Extract exported classes, functions, etc. from a Kotlin file."""
        try:
            logger.debug(f"Extracting exports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regular expressions to match Kotlin declarations
            class_pattern = re.compile(r'(?:public\s+)?(?:data\s+)?class\s+(\w+)')
            interface_pattern = re.compile(r'(?:public\s+)?interface\s+(\w+)')
            function_pattern = re.compile(r'(?:public\s+)?fun\s+(\w+)')
            object_pattern = re.compile(r'(?:public\s+)?object\s+(\w+)')
            enum_pattern = re.compile(r'(?:public\s+)?enum\s+class\s+(\w+)')
            
            classes = class_pattern.findall(content)
            interfaces = interface_pattern.findall(content)
            functions = function_pattern.findall(content)
            objects = object_pattern.findall(content)
            enums = enum_pattern.findall(content)
            
            return {
                'classes': classes,
                'interfaces': interfaces,
                'functions': functions,
                'objects': objects,
                'enums': enums
            }
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return {
                'classes': [],
                'interfaces': [],
                'functions': [],
                'objects': [],
                'enums': []
            }
    
    def extract_imports(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Extract imports from a Kotlin file."""
        try:
            logger.debug(f"Extracting imports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Match import statements
            # Pattern: import package.name.Class
            # Pattern: import package.name.*
            # Pattern: import package.name.Class as Alias
            import_pattern = re.compile(r'import\s+([\w.]+)(?:\s+as\s+(\w+))?', re.MULTILINE)
            
            imports = []
            for match in import_pattern.finditer(content):
                import_path = match.group(1)
                alias = match.group(2)
                
                # Extract the class/object name from the import path
                if '.' in import_path and not import_path.endswith('.*'):
                    imported_name = import_path.split('.')[-1]
                    if alias:
                        # If there's an alias, use that as the imported name
                        imports.append((alias, import_path, 'alias'))
                    else:
                        imports.append((imported_name, import_path, 'direct'))
                elif import_path.endswith('.*'):
                    # Wildcard import - we'll handle this differently
                    # Remove the .* from the end
                    package_path = import_path[:-2]
                    imports.append(('*', package_path, 'wildcard'))
            
            return imports
        except Exception as e:
            print(f"Error extracting imports from {file_path}: {e}")
            return []
    
    def resolve_import_path(self, base_file: str, import_path: str, src_dir: str) -> Optional[str]:
        """Resolve Kotlin import paths to actual file paths."""
        logger.debug(f"Resolving import path: '{import_path}' from file: '{base_file}'")
        
        # Convert package notation to directory structure
        # e.g., com.example.myapp.MyClass -> com/example/myapp/MyClass.kt
        if import_path.endswith('.*'):
            # For wildcard imports, we're looking for a directory
            package_path = import_path[:-2].replace('.', os.sep)
            package_dir = os.path.join(src_dir, package_path)
            
            if os.path.isdir(package_dir):
                return package_dir
        else:
            # For direct imports, we're looking for a file
            # First, check if it's a class from the same package
            base_dir = os.path.dirname(os.path.abspath(base_file))
            
            # Try to extract the class name from the import path
            if '.' in import_path:
                class_name = import_path.split('.')[-1]
                package_path = import_path[:-len(class_name)-1].replace('.', os.sep)
                
                # Look for the file in the src directory
                possible_file = os.path.join(src_dir, package_path, f"{class_name}.kt")
                if os.path.exists(possible_file):
                    return possible_file
                
                # Search for files that might match the class name
                for root, _, files in os.walk(src_dir):
                    for file in files:
                        if file == f"{class_name}.kt":
                            return os.path.join(root, file)
            
            # If we couldn't find it by class name, try to find any file that contains the import
            for root, _, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.kt'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check if the file contains a class/object/interface declaration that matches
                        # the last part of the import path
                        if '.' in import_path:
                            class_name = import_path.split('.')[-1]
                            if re.search(rf'(?:class|object|interface)\s+{class_name}\b', content):
                                return file_path
        
        logger.debug(f"Could not resolve import path: {import_path}")
        return None
    
    def _is_index_file(self, file_path: str) -> bool:
        """Check if the file is an index file (not applicable for Kotlin)"""
        return False
    
    def _print_detailed_exports(self, exports: Dict[str, List[str]]) -> None:
        """Print detailed exports information"""
        if exports['classes']:
            print("  Classes:")
            for cls in exports['classes']:
                print(f"    - {cls}")
        
        if exports['interfaces']:
            print("  Interfaces:")
            for interface in exports['interfaces']:
                print(f"    - {interface}")
        
        if exports['functions']:
            print("  Functions:")
            for function in exports['functions']:
                print(f"    - {function}")
        
        if exports['objects']:
            print("  Objects:")
            for obj in exports['objects']:
                print(f"    - {obj}")
        
        if exports['enums']:
            print("  Enums:")
            for enum in exports['enums']:
                print(f"    - {enum}")
