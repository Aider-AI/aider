"""Initialize the coders package."""
import importlib
import logging
from typing import Type, Optional

# Setup logging
logger = logging.getLogger(__name__)

def load_coder(class_name: str) -> Optional[Type]:
    """
    Dynamically load a coder class by name.
    
    Args:
        class_name: Name of the coder class to load
        
    Returns:
        The coder class if found, None otherwise
    """
    try:
        module_name = f"aider.coders.{class_name.lower()}"
        module = importlib.import_module(module_name)
        coder_class = getattr(module, class_name)
        logger.info(f"Successfully loaded coder: {class_name}")
        return coder_class
    except Exception as e:
        logger.warning(f"Failed to load coder '{class_name}': {e}")
        return None

# Public API
__all__ = ["load_coder"]