#!/usr/bin/env python3
"""
Script to run the AI Football Betting Advisor in shadow mode.

Shadow mode allows tracking betting performance without placing real bets.
"""

import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import json
import sys
import os

from shadow_mode import ShadowModeRunner

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/shadow_mode.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Run shadow mode."""
    load_dotenv()
    
    # Ensure necessary directories exist
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("data/shadow").mkdir(exist_ok=True, parents=True)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run AI Football Betting Advisor in shadow mode")
    parser.add_argument("--duration", type=int, default=30, help="Duration in days for shadow mode")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Initial bankroll amount")
    parser.add_argument("--telegram", action="store_true", help="Send updates to Telegram")
    parser.add_argument("--config", help="Path to configuration file")
    args = parser.parse_args()
    
    # Load config file if provided
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            sys.exit(1)
    
    # Create shadow mode runner with correct parameters
    shadow_runner = ShadowModeRunner(
        duration_days=args.duration,
        bankroll=args.bankroll,
        notify_telegram=args.telegram,
        data_dir="data/shadow"
    )
    
    # Run shadow mode
    logger.info(f"Starting shadow mode for {args.duration} days with {args.bankroll} initial bankroll")
    try:
        await shadow_runner.run()
        logger.info("Shadow mode completed successfully")
    except Exception as e:
        logger.error(f"Error in shadow mode: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 