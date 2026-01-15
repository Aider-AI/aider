"""Test the coders package functionality."""
import logging
from aider.coders import load_coder

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_coders():
    """Test loading a coder dynamically."""
    coder = load_coder("BaseCoder")
    if coder:
        logger.info("Successfully loaded BaseCoder")
    else:
        logger.warning("Failed to load BaseCoder")

if __name__ == "__main__":
    test_coders()