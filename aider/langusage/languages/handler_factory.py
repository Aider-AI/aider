"""
Factory for creating language handlers
"""

import os
import logging
from typing import Optional

from aider.langusage.languages.base import LanguageHandler
from languages.typescript import TypeScriptHandler
from languages.kotlin import KotlinHandler
from languages.java import JavaHandler

# Configure logging
logger = logging.getLogger(__name__)

def get_handler_for_file(file_path: str) -> Optional[LanguageHandler]:
    """
    Get the appropriate language handler for a given file path
    based on its extension.
    """
    if not file_path:
        return None
        
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext in ['.ts', '.vue']:
        logger.debug(f"Using TypeScript handler for {file_path}")
        return TypeScriptHandler()
    elif file_ext in ['.kt', '.kts']:
        logger.debug(f"Using Kotlin handler for {file_path}")
        return KotlinHandler()
    elif file_ext == '.java':
        logger.debug(f"Using Java handler for {file_path}")
        return JavaHandler()
    else:
        logger.warning(f"No handler found for file extension: {file_ext}")
        return None

def get_default_handler() -> LanguageHandler:
    """Get the default language handler (TypeScript)"""
    return TypeScriptHandler()
