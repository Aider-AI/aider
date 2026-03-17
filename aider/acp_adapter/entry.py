"""
Copied and adapted from ~/.hermes/hermes-agent/acp_adapter/entry.py
Copyright (c) 2025 Nous Research (MIT License)

Changes made:
- Added launch_acp helper.
- Configures generic logging into /tmp/aider_acp.log and silences rich or third-party output to protect JSON-RPC on stdio.

Merge Note: If updating from Hermes, follow logging level strategies.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

import acp
from .server import AiderACPAgent


def setup_logging() -> None:
    """Redirect standard logs to a file to protect stdio for JSON-RPC."""
    log_file = "/tmp/aider_acp.log"
    level = logging.INFO
    
    # Clear any root handlers that write to stdout/stderr
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    logging.basicConfig(
        filename=log_file,
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
    )
    
    # Silence verbose libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Aider ACP logging initialized into %s", log_file)


def launch_acp(args: argparse.Namespace) -> None:
    """Launch the Aider ACP server adapter over stdio channels."""
    # Force colors off to keep any unexpected prints generic
    os.environ["NO_COLOR"] = "1"
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting AiderACPAgent on stdio")
    
    try:
        agent = AiderACPAgent()
        import asyncio
        asyncio.run(acp.run_agent(agent))
    except Exception:
        logger.exception("Failed to run AiderACPAgent")
        sys.exit(1)
