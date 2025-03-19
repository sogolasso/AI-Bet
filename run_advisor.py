#!/usr/bin/env python3
"""
Main runner script for the AI Football Betting Advisor.

This script launches the entire betting advisor system, including:
1. Running the daily betting process
2. Starting the Telegram bot
3. Setting up scheduled tasks
"""

import asyncio
import argparse
import logging
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from betting.betting_advisor import BettingAdvisor
from bot.new_telegram_bot import BettingAdvisorBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/advisor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_daily_process(advisor):
    """Run the daily betting process."""
    logger.info("Running daily betting process")
    result = await advisor.run_daily_process()
    
    if result.get("status") == "completed":
        logger.info(f"Daily process completed. Found {result.get('bets_recommended', 0)} recommendations.")
    else:
        logger.error(f"Daily process failed: {result.get('error', 'Unknown error')}")
    
    return result

async def check_results(advisor):
    """Check and update results of pending bets."""
    logger.info("Checking results of pending bets")
    result = await advisor.check_results()
    
    if result.get("status") == "completed":
        if "message" in result:
            logger.info(result["message"])
        else:
            logger.info(f"Checked {result.get('checked_count', 0)} bets. "
                        f"Won: {result.get('won_count', 0)}, "
                        f"Lost: {result.get('lost_count', 0)}, "
                        f"Void: {result.get('void_count', 0)}")
    
    return result

async def generate_report(advisor, days=30):
    """Generate a performance report."""
    logger.info(f"Generating performance report for last {days} days")
    performance = await advisor.generate_performance_report(days=days)
    logger.info(f"Report generated with ROI: {performance.get('roi', 0):.2f}%")
    return performance

async def main():
    """Main entry point for the application."""
    # Load environment variables
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="AI Football Betting Advisor")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--daily", action="store_true", help="Run daily process and exit")
    parser.add_argument("--check-results", action="store_true", help="Check bet results and exit")
    parser.add_argument("--report", type=int, nargs="?", const=30, help="Generate performance report (days)")
    parser.add_argument("--no-bot", action="store_true", help="Don't start the Telegram bot")
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    
    # From config file if provided
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Override with environment variables
    config.update({
        "initial_bankroll": float(os.environ.get("INITIAL_BANKROLL", config.get("initial_bankroll", 1000))),
        "max_daily_bets": int(os.environ.get("MAX_DAILY_BETS", config.get("max_daily_bets", 5))),
        "min_confidence": os.environ.get("MIN_CONFIDENCE", config.get("min_confidence", "Medium")),
        "min_value_threshold": float(os.environ.get("MIN_VALUE_THRESHOLD", config.get("min_value_threshold", 0.05))),
        "staking_strategy": os.environ.get("STAKING_STRATEGY", config.get("staking_strategy", "kelly")),
        "days_ahead": int(os.environ.get("DAYS_AHEAD", config.get("days_ahead", 1))),
    })
    
    # Create data directories if they don't exist
    Path("data").mkdir(exist_ok=True)
    Path("data/cache").mkdir(exist_ok=True)
    Path("data/bets").mkdir(exist_ok=True)
    Path("data/results").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize betting advisor
    advisor = BettingAdvisor(config=config)
    
    # Run specific commands if requested
    if args.daily:
        await run_daily_process(advisor)
        return
    
    if args.check_results:
        await check_results(advisor)
        return
    
    if args.report is not None:
        await generate_report(advisor, days=args.report)
        return
    
    # Otherwise, run the full application
    
    # Start by checking results of any pending bets
    await check_results(advisor)
    
    # Run the daily process if it hasn't been run today
    today = datetime.now().strftime("%Y%m%d")
    report_file = Path(f"data/results/daily_report_{today}.json")
    
    if not report_file.exists():
        await run_daily_process(advisor)
    
    # Start the Telegram bot if not disabled
    if not args.no_bot:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("No Telegram bot token provided. Please set TELEGRAM_BOT_TOKEN environment variable.")
            return
        
        bot = BettingAdvisorBot(token=token, config=config)
        await bot.initialize()
        
        try:
            logger.info("Starting Telegram bot")
            await bot.start()
            
            # Keep the application running
            while True:
                await asyncio.sleep(60)
                
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
        finally:
            if bot:
                await bot.stop()
    else:
        logger.info("Telegram bot disabled. Exiting.")

if __name__ == "__main__":
    asyncio.run(main()) 