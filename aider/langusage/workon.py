#!/usr/bin/env python3
"""
Script to analyze imports and exports in different programming languages.

Usage:
  - To list all exports: python workon.py
  - To analyze imports in a file: python workon.py path/to/file.[ts|kt|java]
  - To print detailed information: add --f flag (e.g., python workon.py path/to/file.ts --f)
"""

import os
import sys
import logging
from pathlib import Path

# Import utility functions from base module
from aider.langusage.languages.base import normalize_path, extract_prefix_from_path, extract_src_dir
from aider.langusage.languages.handler_factory import get_handler_for_file, get_default_handler

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_file_imports(handler, file_path, src_dir, output_func=print, detailed=False):
    """Analyze imports in a specific file and match them to exports."""
    logger.debug(f"Analyzing imports in file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File '{file_path}' does not exist.")
        if detailed:
            output_func(f"Error: File '{file_path}' does not exist.")
        return 1
    
    if detailed:
        output_func(f"Analyzing imports in {file_path}...\n")
    
    # Build export map
    if detailed:
        output_func("Building export map...")
    export_map = handler.build_export_map(src_dir)
    if detailed:
        output_func(f"Found {len(export_map)} unique exports.\n")
    
    # Extract imports
    logger.debug(f"Extracting imports from {file_path}")
    imports = handler.extract_imports(file_path)
    
    if not imports:
        logger.debug("No imports found in the file.")
        if detailed:
            output_func("No imports found in the file.")
        return 0
    
    logger.debug(f"Found {len(imports)} imports in the file.")
    if detailed:
        output_func(f"Found {len(imports)} imports in the file.\n")
    
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
            resolved_path = handler.resolve_import_path(file_path, import_path, src_dir)
            if resolved_path:
                exports = handler.extract_exports(resolved_path)
                found = False
                for export_type, names in exports.items():
                    if imported_name in names or (import_type == 'default' and export_type == 'default'):
                        matched_imports.append((imported_name, import_path, resolved_path, export_type))
                        found = True
                        break
                
                # If still not found, check for barrel exports (index files re-exporting)
                if not found and handler._is_index_file(resolved_path):
                    # Check if this is a barrel file that re-exports from other files
                    index_imports = handler.extract_imports(resolved_path)
                    for idx_name, idx_path, idx_type in index_imports:
                        idx_resolved = handler.resolve_import_path(resolved_path, idx_path, src_dir)
                        if idx_resolved:
                            idx_exports = handler.extract_exports(idx_resolved)
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
        
        output_func(f"{output_path}")
        
        for export_file in sorted(file_paths):
            normalized_export = normalize_path(export_file)
            output_path = normalized_export
            output_func(f"{output_path}")
    else:
        if matched_imports:
            output_func("Matched imports:")
            # Group by import path for cleaner output
            imports_by_path = {}
            for name, import_path, export_file, export_type in matched_imports:
                if import_path not in imports_by_path:
                    imports_by_path[import_path] = []
                imports_by_path[import_path].append((name, export_file, export_type))
            
            for import_path, imports_list in imports_by_path.items():
                output_func(f"\nFrom '{import_path}':")
                for name, export_file, export_type in imports_list:
                    rel_export_path = normalize_path(os.path.relpath(export_file))
                    output_func(f"  - {name} (found in '{rel_export_path}' as {export_type})")
        
        if unmatched_imports:
            output_func("\nUnmatched imports:")
            # Group by import path
            unmatched_by_path = {}
            for name, import_path in unmatched_imports:
                if import_path not in unmatched_by_path:
                    unmatched_by_path[import_path] = []
                unmatched_by_path[import_path].append(name)
            
            for import_path, names in unmatched_by_path.items():
                output_func(f"\nFrom '{import_path}':")
                for name in names:
                    output_func(f"  - {name} (not found in project exports)")
    
    return 0

def list_all_exports(handler, src_dir, output_func=print, detailed=False):
    """List all exports in the project."""
    logger.debug(f"Listing all exports in directory: {src_dir}")
    
    if not os.path.exists(src_dir):
        logger.error(f"Directory '{src_dir}' does not exist.")
        if detailed:
            output_func(f"Error: Directory '{src_dir}' does not exist.")
        return 1
    
    if detailed:
        output_func(f"Scanning files in {src_dir}...\n")
    
    for file_path in handler.find_files(src_dir):
        exports = handler.extract_exports(file_path)
        
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
                    
                output_func(f"{output_path}")
            else:
                rel_path = normalize_path(os.path.relpath(file_path))
                output_func(f"\n{rel_path}:")
                
                handler._print_detailed_exports(exports)
    
    return 0

def workon(pattern, source_dir=None):
    """
    Search for files matching the pattern and return a list of matching files.
    """
    import glob
    import os

    # If source_dir is provided, change to that directory
    original_dir = None
    if source_dir:
        original_dir = os.getcwd()
        os.chdir(source_dir)

    # Expand the pattern to match files
    matches = glob.glob(pattern, recursive=True)

    # Filter out directories
    files = [match for match in matches if os.path.isfile(match)]

    # If we changed directory, change back and update file paths
    if original_dir:
        # Convert to absolute paths before changing back
        files = [os.path.abspath(f) for f in files]
        os.chdir(original_dir)

    return files


def main():
    """Main function to traverse files and analyze imports/exports."""
    # Default src directory (will be overridden if file_path is provided)
    src_dir = os.path.join('src')
    
    # Check if --f flag is present
    detailed = "--f" in sys.argv
    if detailed:
        # Remove the flag from arguments
        sys.argv.remove("--f")
        # Set logging to DEBUG level for more detailed output
        logger.setLevel(logging.DEBUG)
    
    logger.debug(f"Starting code analysis tool")
    
    if len(sys.argv) == 1:
        # No arguments, list all exports using default handler (TypeScript)
        logger.debug("No file specified, listing all exports")
        handler = get_default_handler()
        return list_all_exports(handler, src_dir, detailed=detailed)
    elif len(sys.argv) == 2:
        # File path provided, analyze imports
        file_path = normalize_path(sys.argv[1])
        logger.debug(f"Analyzing file: {file_path}")
        
        # Get the appropriate handler for the file type
        handler = get_handler_for_file(file_path)
        if not handler:
            logger.error(f"Unsupported file type: {file_path}")
            if detailed:
                print(f"Error: Unsupported file type: {file_path}")
                print("Supported file types: .ts, .vue, .kt, .kts, .java")
            return 1
        
        # Extract src directory from file path
        src_dir = extract_src_dir(file_path)
        if detailed:
            print(f"Using source directory: {src_dir}")
        return analyze_file_imports(handler, file_path, src_dir, detailed=detailed)
    else:
        if detailed:
            print("Usage:")
            print("  - To list all exports: python workon.py")
            print("  - To analyze imports in a file: python workon.py path/to/file.[ts|kt|java]")
            print("  - To print detailed information: add --f flag (e.g., python workon.py path/to/file.ts --f)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
