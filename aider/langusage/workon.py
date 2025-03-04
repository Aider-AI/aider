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
from languages.base import normalize_path, extract_prefix_from_path, extract_src_dir
from languages.handler_factory import get_handler_for_file, get_default_handler

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

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
        return handler.list_all_exports(src_dir, detailed)
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
        return handler.analyze_file_imports(file_path, src_dir, detailed)
    else:
        if detailed:
            print("Usage:")
            print("  - To list all exports: python workon.py")
            print("  - To analyze imports in a file: python workon.py path/to/file.[ts|kt|java]")
            print("  - To print detailed information: add --f flag (e.g., python workon.py path/to/file.ts --f)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
