"""
TypeScript language handler for workon.py
"""

import os
import re
import logging
from typing import Dict, List, Tuple, Set, Optional, Any

from languages.base import LanguageHandler

# Configure logging
logger = logging.getLogger(__name__)

class TypeScriptHandler(LanguageHandler):
    """Handler for TypeScript and Vue files"""
    
    def find_files(self, start_dir: str) -> List[str]:
        """Find all TypeScript and Vue files in the given directory and its subdirectories."""
        logger.debug(f"Scanning for TypeScript/Vue files in: {start_dir}")
        file_count = 0
        for root, _, files in os.walk(start_dir):
            for file in files:
                if file.endswith('.ts') or file.endswith('.vue'):
                    file_path = os.path.join(root, file)
                    file_count += 1
                    if file_count % 100 == 0:
                        logger.debug(f"Found {file_count} TypeScript/Vue files so far...")
                    yield file_path
        logger.debug(f"Total TypeScript/Vue files found: {file_count}")
    
    def extract_exports(self, file_path: str) -> Dict[str, List[str]]:
        """Extract exported interfaces and classes from a TypeScript or Vue file."""
        try:
            logger.debug(f"Extracting exports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regular expressions to match exported interfaces and classes
            interface_pattern = re.compile(r'export\s+interface\s+(\w+)')
            class_pattern = re.compile(r'export\s+(?:abstract\s+)?class\s+(\w+)')
            type_pattern = re.compile(r'export\s+type\s+(\w+)')
            enum_pattern = re.compile(r'export\s+enum\s+(\w+)')
            const_pattern = re.compile(r'export\s+const\s+(\w+)')
            default_export_pattern = re.compile(r'export\s+default\s+(?:class|function|const)?\s*(\w+)')
            
            interfaces = interface_pattern.findall(content)
            classes = class_pattern.findall(content)
            types = type_pattern.findall(content)
            enums = enum_pattern.findall(content)
            consts = const_pattern.findall(content)
            default_exports = default_export_pattern.findall(content)
            
            return {
                'interfaces': interfaces,
                'classes': classes,
                'types': types,
                'enums': enums,
                'consts': consts,
                'default': default_exports
            }
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return {
                'interfaces': [],
                'classes': [],
                'types': [],
                'enums': [],
                'consts': [],
                'default': []
            }
    
    def extract_imports(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Extract imports from a TypeScript or Vue file."""
        try:
            logger.debug(f"Extracting imports from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Match import statements with different patterns
            # Pattern 1: import { X, Y } from 'path'
            # Pattern 2: import X from 'path'
            # Pattern 3: import * as X from 'path'
            import_pattern = re.compile(r'import\s+(?:{([^}]*)}\s+from\s+|([^;{]*)\s+from\s+|\*\s+as\s+(\w+)\s+from\s+)[\'"]([^\'"]+)[\'"]', re.MULTILINE)
            
            imports = []
            for match in import_pattern.finditer(content):
                named_imports = match.group(1)
                default_import = match.group(2)
                namespace_import = match.group(3)
                import_path = match.group(4)
                
                if named_imports:
                    # Handle named imports like: import { Component1, Component2 } from './path'
                    # Split by commas but handle complex cases with nested braces
                    items = []
                    current_item = ""
                    brace_level = 0
                    
                    for char in named_imports:
                        if char == '{':
                            brace_level += 1
                            current_item += char
                        elif char == '}':
                            brace_level -= 1
                            current_item += char
                        elif char == ',' and brace_level == 0:
                            items.append(current_item.strip())
                            current_item = ""
                        else:
                            current_item += char
                    
                    if current_item.strip():
                        items.append(current_item.strip())
                    
                    for item in items:
                        # Handle 'as' aliases
                        if ' as ' in item:
                            original, alias = item.split(' as ')
                            imports.append((original.strip(), import_path, 'named'))
                        else:
                            imports.append((item.strip(), import_path, 'named'))
                
                if default_import and default_import.strip():
                    # Handle default imports like: import DefaultComponent from './path'
                    imports.append((default_import.strip(), import_path, 'default'))
                
                if namespace_import:
                    # Handle namespace imports like: import * as Utils from './path'
                    imports.append((namespace_import, import_path, 'namespace'))
            
            return imports
        except Exception as e:
            print(f"Error extracting imports from {file_path}: {e}")
            return []
    
    def resolve_import_path(self, base_file: str, import_path: str, src_dir: str) -> Optional[str]:
        """Resolve relative import paths to absolute paths."""
        logger.debug(f"Resolving import path: '{import_path}' from file: '{base_file}'")
        
        # Handle alias paths (like @/service/api)
        if import_path.startswith('@/'):
            # Replace @ with src directory
            alias_path = import_path.replace('@/', '')
            resolved_path = os.path.join(src_dir, alias_path)
            logger.debug(f"Alias path resolved to: {resolved_path}")
            
            # Check for file extensions or index files
            if os.path.exists(resolved_path + '.ts'):
                return resolved_path + '.ts'
            elif os.path.exists(resolved_path + '.vue'):
                return resolved_path + '.vue'
            elif os.path.exists(os.path.join(resolved_path, 'index.ts')):
                return os.path.join(resolved_path, 'index.ts')
            elif os.path.exists(resolved_path):
                return resolved_path
        elif import_path.startswith('.'):
            # Relative import
            base_dir = os.path.dirname(os.path.abspath(base_file))
            resolved_path = os.path.normpath(os.path.join(base_dir, import_path))
            logger.debug(f"Relative path resolved to: {resolved_path}")
            
            # Check for file extensions
            if os.path.exists(resolved_path + '.ts'):
                return resolved_path + '.ts'
            elif os.path.exists(resolved_path + '.vue'):
                return resolved_path + '.vue'
            elif os.path.exists(os.path.join(resolved_path, 'index.ts')):
                return os.path.join(resolved_path, 'index.ts')
            elif os.path.exists(resolved_path):
                return resolved_path
        else:
            # Non-relative import (from node_modules or other aliases)
            # Try to find matching files in the src directory
            logger.debug(f"Searching for non-relative import: {import_path}")
            possible_paths = []
            
            # Check if it's a direct path under src
            direct_path = os.path.join(src_dir, import_path)
            if os.path.exists(direct_path + '.ts'):
                return direct_path + '.ts'
            elif os.path.exists(direct_path + '.vue'):
                return direct_path + '.vue'
            elif os.path.exists(os.path.join(direct_path, 'index.ts')):
                return os.path.join(direct_path, 'index.ts')
            
            # Search for files that might match the import path
            for root, _, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.ts') or file.endswith('.vue'):
                        file_path = os.path.join(root, file)
                        # Check if the import path is part of the file path
                        rel_path = os.path.relpath(file_path, src_dir)
                        if import_path in rel_path or import_path.replace('/', os.sep) in rel_path:
                            possible_paths.append(file_path)
            
            # If we found exactly one match, return it
            if len(possible_paths) == 1:
                logger.debug(f"Found single match for '{import_path}': {possible_paths[0]}")
                return possible_paths[0]
            # If we found multiple matches, return the one that seems most specific
            elif len(possible_paths) > 1:
                # Sort by length of path (shorter is likely more specific)
                possible_paths.sort(key=len)
                logger.debug(f"Found multiple matches for '{import_path}', using: {possible_paths[0]}")
                return possible_paths[0]
        
        logger.debug(f"Could not resolve import path: {import_path}")
        return None
    
    def _is_index_file(self, file_path: str) -> bool:
        """Check if the file is an index file"""
        return file_path.endswith('index.ts')
    
    def _print_detailed_exports(self, exports: Dict[str, List[str]]) -> None:
        """Print detailed exports information"""
        if exports['interfaces']:
            print("  Interfaces:")
            for interface in exports['interfaces']:
                print(f"    - {interface}")
        
        if exports['classes']:
            print("  Classes:")
            for cls in exports['classes']:
                print(f"    - {cls}")
        
        if exports['types']:
            print("  Types:")
            for type_name in exports['types']:
                print(f"    - {type_name}")
        
        if exports['enums']:
            print("  Enums:")
            for enum_name in exports['enums']:
                print(f"    - {enum_name}")
        
        if exports['consts']:
            print("  Constants:")
            for const_name in exports['consts']:
                print(f"    - {const_name}")
        
        if exports['default']:
            print("  Default exports:")
            for default_export in exports['default']:
                print(f"    - {default_export}")
