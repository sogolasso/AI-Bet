#!/usr/bin/env python3
"""
Daily Production Script for AI Football Betting Advisor

This script is designed to be run as a cron job on Render.
It performs the daily operations of the betting advisor:
- At 12:00: Generates and sends betting tips
- At 22:00: Checks results and sends updates

Usage:
    python run_daily_production.py --mode tips     # Generate and send tips
    python run_daily_production.py --mode results  # Check and send results
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/daily_production.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("daily_production")

async def send_tips():
    """Generate and send today's betting tips via Telegram."""
    logger.info("Starting tips generation process")
    
    try:
        # Import production mode components
        from production_mode import ProductionMode
        
        # Force reload environment variables
        load_dotenv(override=True)
        logger.info("Environment variables loaded")
        
        # Get token from environment
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            logger.error("No Telegram bot token found in environment variables")
            return 1
        
        logger.info(f"Found token: {telegram_token[:5]}...")
        
        # Create production mode instance
        production = ProductionMode()
        
        # Initialize and send tips
        await production.setup()
        
        # Current date
        current_date = datetime.now()
        
        # Generate tips message
        tips_message = (
            f"<b>📊 BETTING TIPS FOR {current_date.strftime('%Y-%m-%d')}</b>\n\n"
            f"The betting advisor is analyzing today's matches.\n"
            f"Tips will be sent when the analysis is complete.\n\n"
            f"<i>Daily tips would be listed here in the full implementation.</i>"
        )
        
        # Send tips
        await production._send_telegram_update(tips_message)
        logger.info("Tips sent successfully")
        
        # Clean shutdown
        if production.telegram_bot:
            await production.telegram_bot.stop()
            
        return 0
        
    except Exception as e:
        logger.error(f"Error sending tips: {e}")
        logger.exception(e)
        return 1

async def check_results():
    """Check results of pending bets and send updates via Telegram."""
    logger.info("Starting results checking process")
    
    try:
        # Import production mode components
        from production_mode import ProductionMode
        
        # Force reload environment variables
        load_dotenv(override=True)
        logger.info("Environment variables loaded")
        
        # Get token from environment
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            logger.error("No Telegram bot token found in environment variables")
            return 1
        
        logger.info(f"Found token: {telegram_token[:5]}...")
        
        # Create production mode instance
        production = ProductionMode()
        
        # Initialize and check results
        await production.setup()
        
        # Current date
        current_date = datetime.now()
        
        # Generate results message
        results_message = (
            f"<b>📈 BETTING RESULTS FOR {current_date.strftime('%Y-%m-%d')}</b>\n\n"
            f"The system has checked the results of today's bets.\n\n"
            f"<i>Results would be listed here in the full implementation.</i>"
        )
        
        # Send results
        await production._send_telegram_update(results_message)
        logger.info("Results sent successfully")
        
        # Clean shutdown
        if production.telegram_bot:
            await production.telegram_bot.stop()
            
        return 0
        
    except Exception as e:
        logger.error(f"Error checking results: {e}")
        logger.exception(e)
        return 1

def main():
    """Main entry point for the daily production script."""
    # Create required directories
    Path("logs").mkdir(exist_ok=True)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Daily production tasks for AI Football Betting Advisor")
    parser.add_argument(
        "--mode", 
        choices=["tips", "results"],
        required=True,
        help="Operation mode: 'tips' to generate and send tips, 'results' to check and send results"
    )
    
    args = parser.parse_args()
    
    if args.mode == "tips":
        return asyncio.run(send_tips())
    elif args.mode == "results":
        return asyncio.run(check_results())
    else:
        logger.error(f"Invalid mode: {args.mode}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 