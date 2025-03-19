#!/usr/bin/env python
"""
Production Mode Launcher for AI Football Betting Advisor

This script is a simple launcher for the production mode of the AI Football Betting Advisor.
It's a convenience wrapper around the all_in_one.py script.
"""

import sys
import os
import time
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import logging
import shutil

# Configure logging
logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """Ensure all required directories exist."""
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("data/production").mkdir(exist_ok=True)

def main():
    """Main entry point for the production mode launcher."""
    # Load environment variables
    load_dotenv(override=True)
    print("✅ Environment variables loaded from .env file")
    
    # Check for Telegram token
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ No Telegram bot token found. Please set TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)
    print(f"✅ Found Telegram bot token: {token[:5]}...")
    
    # Check for admin IDs
    admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS')
    if not admin_ids:
        print("❌ No Telegram admin IDs found. Please set TELEGRAM_ADMIN_IDS in .env")
        sys.exit(1)
    
    try:
        admin_id_list = [int(x.strip()) for x in admin_ids.split(',')]
        print(f"✅ Found valid admin IDs: {admin_id_list}")
    except ValueError:
        print("❌ Invalid admin IDs format. Please use comma-separated numbers")
        sys.exit(1)
    
    # Create required directories
    ensure_directories_exist()
    
    print("🚀 Launching production mode...")
    
    # Check if all_in_one.py exists
    if not os.path.exists("all_in_one.py"):
        print("❌ all_in_one.py not found in current directory")
        sys.exit(1)
    
    try:
        # Import and run the production mode
        from production_mode import ProductionMode
        
        async def run_production():
            # Ensure data directories exist
            os.makedirs('data/collectors', exist_ok=True)
            
            # Copy match_collector.py to data/collectors if it doesn't exist there
            src_match_collector = Path('data/match_collector.py')
            dst_match_collector = Path('data/collectors/match_collector.py')
            if src_match_collector.exists() and not dst_match_collector.exists():
                shutil.copy2(src_match_collector, dst_match_collector)
                logger.info(f"Copied match_collector.py to {dst_match_collector}")
            
            # Copy scraping_utils.py to data/collectors if it doesn't exist there
            src_utils = Path('data/scraping_utils.py')
            dst_utils = Path('data/collectors/scraping_utils.py')
            if src_utils.exists() and not dst_utils.exists():
                shutil.copy2(src_utils, dst_utils)
                logger.info(f"Copied scraping_utils.py to {dst_utils}")
            
            production = ProductionMode()
            await production.run()
            
        asyncio.run(run_production())
    except KeyboardInterrupt:
        print("\n⏹️ Production mode stopped by user")
    except Exception as e:
        print(f"❌ Error in production mode: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 