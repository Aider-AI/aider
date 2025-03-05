"""
Java language handler for workon.py
"""

import os
import re
import logging
from typing import Dict, List, Tuple, Set, Optional, Any

from aider.langusage.languages.base import LanguageHandler

# Configure logging
logger = logging.getLogger(__name__)

class JavaHandler(LanguageHandler):
    """Handler for Java files"""
    
    def find_files(self, start_dir: str) -> List[str]:
        """Find all Java files in the given directory and its subdirectories."""
        logger.debug(f"Scanning for Java files in: {start_dir}")
        file_count = 0
        java_files = []
        for root, _, files in os.walk(start_dir):
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    file_count += 1
                    if file_count % 100 == 0:
                        logger.debug(f"Found {file_count} Java files so far...")
                    java_files.append(file_path)
        logger.debug(f"Total Java files found: {file_count}")
        return java_files
    
    def extract_exports(self, file_path: str) -> Dict[str, List[str]]:
        """Extract exported classes, interfaces, etc. from a Java file."""
        try:
            logger.debug(f"Extracting exports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract package name
            package_match = re.search(r'package\s+([\w.]+);', content)
            package_name = package_match.group(1) if package_match else ""
            
            # Regular expressions to match Java declarations
            class_pattern = re.compile(r'(?:public|protected)\s+(?:final\s+)?class\s+(\w+)')
            interface_pattern = re.compile(r'(?:public|protected)\s+interface\s+(\w+)')
            enum_pattern = re.compile(r'(?:public|protected)\s+enum\s+(\w+)')
            method_pattern = re.compile(r'(?:public|protected)\s+(?:static\s+)?(?:final\s+)?(?:[\w<>[\],\s]+)\s+(\w+)\s*\([^)]*\)')
            
            classes = class_pattern.findall(content)
            interfaces = interface_pattern.findall(content)
            enums = enum_pattern.findall(content)
            methods = method_pattern.findall(content)
            
            return {
                'classes': classes,
                'interfaces': interfaces,
                'enums': enums,
                'methods': methods,
                'package': [package_name] if package_name else []
            }
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return {
                'classes': [],
                'interfaces': [],
                'enums': [],
                'methods': [],
                'package': []
            }
    
    def extract_imports(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Extract imports from a Java file."""
        try:
            logger.debug(f"Extracting imports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Match import statements
            # Pattern: import package.name.Class;
            # Pattern: import package.name.*;
            # Pattern: import static package.name.Class.method;
            import_pattern = re.compile(r'import\s+(?:static\s+)?([\w.]+);', re.MULTILINE)
            
            imports = []
            for match in import_pattern.finditer(content):
                import_path = match.group(1)
                
                # Extract the class/method name from the import path
                if '.' in import_path and not import_path.endswith('.*'):
                    imported_name = import_path.split('.')[-1]
                    imports.append((imported_name, import_path, 'direct'))
                elif import_path.endswith('.*'):
                    # Wildcard import
                    package_path = import_path[:-2]
                    imports.append(('*', package_path, 'wildcard'))
            
            return imports
        except Exception as e:
            print(f"Error extracting imports from {file_path}: {e}")
            return []
    
    def resolve_import_path(self, base_file: str, import_path: str, src_dir: str) -> Optional[str]:
        """Resolve Java import paths to actual file paths."""
        logger.debug(f"Resolving import path: '{import_path}' from file: '{base_file}'")
        
        # Convert package notation to directory structure
        # e.g., com.example.myapp.MyClass -> com/example/myapp/MyClass.java
        if import_path.endswith('.*'):
            # For wildcard imports, we're looking for a directory
            package_path = import_path[:-2].replace('.', os.sep)
            package_dir = os.path.join(src_dir, package_path)
            
            if os.path.isdir(package_dir):
                return package_dir
        else:
            # For direct imports, we're looking for a file
            # Extract the class name and package path
            if '.' in import_path:
                class_name = import_path.split('.')[-1]
                package_path = import_path[:-len(class_name)-1].replace('.', os.sep)
                
                # Look for the file in the src directory
                possible_file = os.path.join(src_dir, package_path, f"{class_name}.java")
                if os.path.exists(possible_file):
                    return possible_file
                
                # Search for files that might match the class name
                for root, _, files in os.walk(src_dir):
                    for file in files:
                        if file == f"{class_name}.java":
                            return os.path.join(root, file)
            
            # If we couldn't find it by class name, try to find any file that contains the import
            for root, _, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Check if the file contains a class/interface declaration that matches
                            # the last part of the import path
                            if '.' in import_path:
                                class_name = import_path.split('.')[-1]
                                if re.search(rf'(?:class|interface|enum)\s+{class_name}\b', content):
                                    return file_path
                        except Exception:
                            # Skip files that can't be read
                            pass
        
        logger.debug(f"Could not resolve import path: {import_path}")
        return None
    
    def _is_index_file(self, file_path: str) -> bool:
        """Check if the file is an index file (not applicable for Java)"""
        return False
    
    def _print_detailed_exports(self, exports: Dict[str, List[str]]) -> None:
        """Print detailed exports information"""
        if exports['package']:
            print(f"  Package: {exports['package'][0]}")
        
        if exports['classes']:
            print("  Classes:")
            for cls in exports['classes']:
                print(f"    - {cls}")
        
        if exports['interfaces']:
            print("  Interfaces:")
            for interface in exports['interfaces']:
                print(f"    - {interface}")
        
        if exports['enums']:
            print("  Enums:")
            for enum in exports['enums']:
                print(f"    - {enum}")
        
        if exports['methods']:
            print("  Methods:")
            for method in exports['methods']:
                print(f"    - {method}")
