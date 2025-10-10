import os
import sys
import logging

# Optional: setup logging for diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Handle direct execution vs package import
if __name__ == "__main__" and __package__ is None:
    # Add parent directory to sys.path to resolve relative imports
    current_dir = os.path.dirname(__file__)
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    sys.path.insert(0, parent_dir)
    logger.info(f"Running as script. Added to sys.path: {parent_dir}")

    # Import main from aider.main
    from aider.main import main
else:
    # Import main using relative import for package context
    from .main import main

# Execute main if run directly
if __name__ == "__main__":
    logger.info("Starting aider...")
    main()
