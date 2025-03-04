"""
Factory for creating language handlers
"""

import os
import logging
from typing import Optional

from aider.langusage.languages.base import LanguageHandler
from aider.langusage.languages.typescript import TypeScriptHandler
from aider.langusage.languages.kotlin import KotlinHandler
from aider.langusage.languages.java import JavaHandler
from aider.langusage.languages.python import PythonHandler

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
    elif file_ext == '.py':
        logger.debug(f"Using Python handler for {file_path}")
        return PythonHandler()
    else:
        logger.warning(f"No handler found for file extension: {file_ext}")
        return None

def get_default_handler() -> LanguageHandler:
    """Get the default language handler (TypeScript)"""
    return TypeScriptHandler()
