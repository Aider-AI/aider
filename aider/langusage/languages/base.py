"""
Base language handler interface for workon.py
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Set, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

class LanguageHandler(ABC):
    """Base class for language-specific handlers"""
    
    @abstractmethod
    def find_files(self, start_dir: str) -> List[str]:
        """Find all relevant files in the given directory and its subdirectories."""
        pass
    
    @abstractmethod
    def extract_exports(self, file_path: str) -> Dict[str, List[str]]:
        """Extract exported symbols from a file."""
        pass
    
    @abstractmethod
    def extract_imports(self, file_path: str) -> List[Tuple[str, str, str]]:
        """Extract imports from a file."""
        pass
    
    @abstractmethod
    def resolve_import_path(self, base_file: str, import_path: str, src_dir: str) -> Optional[str]:
        """Resolve relative import paths to absolute paths."""
        pass
    
    def build_export_map(self, src_dir: str) -> Dict[str, List[Tuple[str, str]]]:
        """Build a map of all exports in the project."""
        logger.debug(f"Building export map from directory: {src_dir}")
        export_map = {}
        file_count = 0
        
        for file_path in self.find_files(src_dir):
            file_count += 1
            if file_count % 50 == 0:
                logger.debug(f"Processed {file_count} files for exports...")
            exports = self.extract_exports(file_path)
            
            # Add all exports to the map
            for export_type, names in exports.items():
                for name in names:
                    if name not in export_map:
                        export_map[name] = []
                    export_map[name].append((file_path, export_type))
        
        logger.debug(f"Export map built with {len(export_map)} unique exports from {file_count} files")
        return export_map
    
    def analyze_file_imports(self, file_path: str, src_dir: str, detailed: bool = False) -> int:
        """Analyze imports in a specific file and match them to exports."""
        logger.debug(f"Analyzing imports in file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File '{file_path}' does not exist.")
            if detailed:
                print(f"Error: File '{file_path}' does not exist.")
            return 1
        
        if detailed:
            print(f"Analyzing imports in {file_path}...\n")
        
        # Build export map
        if detailed:
            print("Building export map...")
        export_map = self.build_export_map(src_dir)
        if detailed:
            print(f"Found {len(export_map)} unique exports.\n")
        
        # Extract imports
        logger.debug(f"Extracting imports from {file_path}")
        imports = self.extract_imports(file_path)
        
        if not imports:
            logger.debug("No imports found in the file.")
            if detailed:
                print("No imports found in the file.")
            return 0
        
        logger.debug(f"Found {len(imports)} imports in the file.")
        if detailed:
            print(f"Found {len(imports)} imports in the file.\n")
        
        # Match imports to exports
        logger.debug("Matching imports to exports...")
        matched_imports = []
        unmatched_imports = []
        
        for imported_name, import_path, import_type in imports:
            if imported_name in export_map:
                for export_file, export_type in export_map[imported_name]:
                    matched_imports.append((imported_name, import_path, export_file, export_type))
            else:
                # Try to resolve the import path
                resolved_path = self.resolve_import_path(file_path, import_path, src_dir)
                if resolved_path:
                    exports = self.extract_exports(resolved_path)
                    found = False
                    for export_type, names in exports.items():
                        if imported_name in names or (import_type == 'default' and export_type == 'default'):
                            matched_imports.append((imported_name, import_path, resolved_path, export_type))
                            found = True
                            break
                    
                    # If still not found, check for barrel exports (index files re-exporting)
                    if not found and self._is_index_file(resolved_path):
                        # Check if this is a barrel file that re-exports from other files
                        index_imports = self.extract_imports(resolved_path)
                        for idx_name, idx_path, idx_type in index_imports:
                            idx_resolved = self.resolve_import_path(resolved_path, idx_path, src_dir)
                            if idx_resolved:
                                idx_exports = self.extract_exports(idx_resolved)
                                for idx_export_type, idx_names in idx_exports.items():
                                    if imported_name in idx_names:
                                        matched_imports.append((imported_name, import_path, idx_resolved, idx_export_type))
                                        found = True
                                        break
                                if found:
                                    break
                    
                    if not found:
                        unmatched_imports.append((imported_name, import_path))
                else:
                    unmatched_imports.append((imported_name, import_path))
        
        # Print results
        if not detailed:
            # Only print file paths when no --f flag is specified
            file_paths = set()
            for _, _, export_file, _ in matched_imports:
                file_paths.add(export_file)
            
            # Extract prefix from the input file path
            prefix = extract_prefix_from_path(file_path)
            if not prefix and '/src/' not in file_path and file_path.startswith('src/'):
                # If no prefix found but path starts with src/, use empty prefix
                prefix = ""
            elif not prefix:
                # Default prefix if not found
                prefix = "paintshop-frontend"
            
            # Add the provided file to the output
            normalized_path = normalize_path(file_path)
            output_path = normalized_path
            
            print(f"{output_path}")
            
            for export_file in sorted(file_paths):
                normalized_export = normalize_path(export_file)
                output_export = normalized_export
                print(f"{output_export}")
        else:
            if matched_imports:
                print("Matched imports:")
                # Group by import path for cleaner output
                imports_by_path = {}
                for name, import_path, export_file, export_type in matched_imports:
                    if import_path not in imports_by_path:
                        imports_by_path[import_path] = []
                    imports_by_path[import_path].append((name, export_file, export_type))
                
                for import_path, imports_list in imports_by_path.items():
                    print(f"\nFrom '{import_path}':")
                    for name, export_file, export_type in imports_list:
                        rel_export_path = normalize_path(os.path.relpath(export_file))
                        print(f"  - {name} (found in '{rel_export_path}' as {export_type})")
            
            if unmatched_imports:
                print("\nUnmatched imports:")
                # Group by import path
                unmatched_by_path = {}
                for name, import_path in unmatched_imports:
                    if import_path not in unmatched_by_path:
                        unmatched_by_path[import_path] = []
                    unmatched_by_path[import_path].append(name)
                
                for import_path, names in unmatched_by_path.items():
                    print(f"\nFrom '{import_path}':")
                    for name in names:
                        print(f"  - {name} (not found in project exports)")
        
        return 0
    
    def list_all_exports(self, src_dir: str, detailed: bool = False) -> int:
        """List all exports in the project."""
        logger.debug(f"Listing all exports in directory: {src_dir}")
        
        if not os.path.exists(src_dir):
            logger.error(f"Directory '{src_dir}' does not exist.")
            if detailed:
                print(f"Error: Directory '{src_dir}' does not exist.")
            return 1
        
        if detailed:
            print(f"Scanning files in {src_dir}...\n")
        
        for file_path in self.find_files(src_dir):
            exports = self.extract_exports(file_path)
            
            # Only process files that have exports
            if any(exports.values()):
                if not detailed:
                    # Just print the file path when no --f flag is specified
                    normalized_path = normalize_path(file_path)
                    
                    # Extract prefix from the file path
                    prefix = extract_prefix_from_path(file_path)
                    if not prefix and '/src/' not in file_path and file_path.startswith('src/'):
                        # If no prefix found but path starts with src/, use empty prefix
                        prefix = ""
                    elif not prefix:
                        # Default prefix if not found
                        prefix = "paintshop-frontend"
                    
                    # Add prefix to the path if it starts with src/
                    if normalized_path.startswith('src/'):
                        output_path = f"{prefix}/{normalized_path}"
                    else:
                        output_path = normalized_path
                        
                    print(f"{output_path}")
                else:
                    rel_path = normalize_path(os.path.relpath(file_path))
                    print(f"\n{rel_path}:")
                    
                    self._print_detailed_exports(exports)
        
        return 0
    
    def _is_index_file(self, file_path: str) -> bool:
        """Check if the file is an index file (language-specific)"""
        return False
    
    def _print_detailed_exports(self, exports: Dict[str, List[str]]) -> None:
        """Print detailed exports information (to be overridden by subclasses)"""
        pass

# Utility functions (moved from main module)
def normalize_path(file_path: str) -> str:
    """Remove current directory prefix from file path if present."""
    current_dir = os.getcwd()
    current_dir_name = os.path.basename(current_dir)
    
    # Check if the file path starts with the current directory name
    path_parts = file_path.split(os.sep)
    if path_parts and path_parts[0] == current_dir_name:
        # Remove the current directory from the path
        normalized = os.sep.join(path_parts[1:])
        logger.debug(f"Normalized path: '{file_path}' -> '{normalized}'")
        return normalized
    return file_path

def extract_prefix_from_path(file_path: str) -> Optional[str]:
    """Extract the prefix before 'src' from a file path."""
    src_pos = file_path.find('/src/')
    if src_pos != -1:
        # Return everything up to but not including '/src/'
        prefix = file_path[:src_pos]
        logger.debug(f"Extracted prefix from path: '{prefix}'")
        return prefix
    return None

def extract_src_dir(file_path: str) -> str:
    """Extract the src directory from a file path."""
    # Find the position of '/src/' in the file path
    logger.debug(f"Extracting src directory from file path: {file_path}")
    src_pos = file_path.find('/src/')
    if src_pos != -1:
        # Return everything up to and including '/src/'
        src_dir = file_path[:src_pos + 5]  # +5 to include '/src/'
        logger.debug(f"Extracted src directory: {src_dir}")
        return src_dir
    else:
        # Default to src if '/src/' not found
        default_src = 'src'
        logger.debug(f"Using default src directory: {default_src}")
        return default_src
