#!/usr/bin/env python3
"""
Production Mode for AI Football Betting Advisor

This module contains the production mode implementation for the AI Football Betting Advisor.
It includes Telegram integration for sending betting tips and results.
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/production_mode.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("production_mode")

class ProductionMode:
    """Runs the betting advisor in production mode with Telegram integration."""
    
    def __init__(self, config_path=None, data_dir="data/production"):
        """Initialize the production mode.
        
        Args:
            config_path: Path to configuration file
            data_dir: Directory to store production data
        """
        self.config_path = config_path
        self.data_dir = data_dir
        self.telegram_bot = None
        self.config = self._load_config()
        
        # Create data directory if it doesn't exist
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
    def _load_config(self):
        """Load configuration from file if provided."""
        config = {}
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        return config
    
    async def setup(self):
        """Set up the production mode environment."""
        logger.info("Setting up production mode environment...")
        
        # Make sure the data/collectors directory exists
        Path("data/collectors").mkdir(parents=True, exist_ok=True)
        
        # Force reload environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            logger.info("Environment variables reloaded from .env file")
        except Exception as e:
            logger.error(f"Error loading .env file: {e}")
        
        # Initialize Telegram bot
        from bot.new_telegram_bot import BettingAdvisorBot
        
        # Get token from environment or try direct file read if that fails
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            logger.error("Telegram bot token not found in environment variables")
            
            # Try to read directly from .env file as a fallback
            try:
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
                if os.path.exists(env_path):
                    with open(env_path, 'r') as f:
                        for line in f:
                            if line.strip().startswith('TELEGRAM_BOT_TOKEN='):
                                telegram_token = line.strip().split('=', 1)[1].strip()
                                if telegram_token.startswith('"') and telegram_token.endswith('"'):
                                    telegram_token = telegram_token[1:-1]
                                logger.info(f"Found token in .env file: {telegram_token[:5]}...")
                                break
            except Exception as e:
                logger.error(f"Error reading .env file directly: {e}")
            
            if not telegram_token:
                raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        else:
            logger.info(f"Found token in environment: {telegram_token[:5]}...")
        
        # Parse admin IDs from environment
        admin_ids_str = os.environ.get('TELEGRAM_ADMIN_IDS', '')
        admin_ids = []
        try:
            # Remove brackets if present
            admin_ids_str = admin_ids_str.strip('[]')
            
            # Split by comma and strip whitespace
            admin_id_strings = [id.strip() for id in admin_ids_str.split(',')]
            
            # Convert to integers
            admin_ids = [int(id) for id in admin_id_strings if id.strip().isdigit()]
            
            # Update the global constant in the bot module
            sys.modules['bot.new_telegram_bot'].ADMIN_USER_IDS = admin_ids
            
            logger.info(f"Admin IDs set: {admin_ids}")
        except Exception as e:
            logger.error(f"Error parsing admin IDs: {e}")
        
        # Create a bot instance that works with both async and non-async methods
        self.telegram_bot = BettingAdvisorBot(token=telegram_token)
        await self.telegram_bot.initialize()
        
        # Start the bot to ensure it's polling for updates
        try:
            await self.telegram_bot.start()
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
        
        # Add our own sync wrapper method for sending messages
        def sync_send_message(chat_id, text, parse_mode=None):
            try:
                if hasattr(self.telegram_bot.updater.bot, "send_message"):
                    # Try using the bot's send_message method directly
                    msg = self.telegram_bot.updater.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode
                    )
                    return msg
            except Exception as e:
                logger.error(f"Error in sync_send_message: {e}")
                return None
        
        # Attach the sync method to our bot
        self.telegram_bot.sync_send_message = sync_send_message
        
        logger.info("Production mode setup complete with Telegram integration")
        
        # Send initialization message
        await self._send_telegram_update("<b>🚀 AI Football Betting Advisor</b>\n\nProduction mode initialized and ready to provide betting tips.")
    
    async def _send_telegram_update(self, message):
        """Send a Telegram update to admin users."""
        try:
            # Get admin IDs from environment
            admin_ids_str = os.environ.get('TELEGRAM_ADMIN_IDS', '')
            
            # Log admin IDs for debugging
            logger.info(f"Admin IDs from environment: {admin_ids_str}")
            
            # Parse admin IDs - handle various formats (comma-separated, with/without brackets)
            if admin_ids_str:
                # Remove brackets if present
                admin_ids_str = admin_ids_str.strip('[]')
                
                # Split by comma and strip whitespace
                admin_ids = [id.strip() for id in admin_ids_str.split(',')]
                
                # Convert to integers
                admin_ids = [int(id) for id in admin_ids if id.strip().isdigit()]
                
                if not admin_ids:
                    logger.error("No valid admin IDs found after parsing")
                else:
                    logger.info(f"Parsed admin IDs: {admin_ids}")
            else:
                logger.error("No admin IDs found in environment variables")
                admin_ids = []
            
            for admin_id in admin_ids:
                try:
                    # Use our sync wrapper to avoid async/sync mismatches
                    if hasattr(self.telegram_bot, "sync_send_message"):
                        # Use the synchronous wrapper we added
                        self.telegram_bot.sync_send_message(
                            chat_id=admin_id,
                            text=message,
                            parse_mode="HTML"
                        )
                        logger.info(f"Message sent to admin {admin_id}")
                    else:
                        logger.error("No sync_send_message method available")
                except Exception as e:
                    logger.error(f"Failed to send message to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error in _send_telegram_update: {e}")
            logger.exception(e)
    
    async def run(self):
        """Run the production mode."""
        logger.info("Starting production mode")
        
        # Setup environment and initialize the Telegram bot
        await self.setup()
        
        try:
            # Initial status message
            await self._send_telegram_update(
                f"<b>🚀 AI Football Betting Advisor - Production Mode</b>\n\n"
                f"The system is now running in production mode.\n"
                f"You will receive daily betting tips and results.\n\n"
                f"<b>Current time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"<b>Initial bankroll:</b> {self.config.get('initial_bankroll', 100.0):.2f}"
            )
            
            while True:
                # Current date
                current_date = datetime.now()
                logger.info(f"Running production mode for {current_date.strftime('%Y-%m-%d')}")
                
                # Check current time - send daily tips around noon
                current_hour = current_date.hour
                
                # Generate tips at noon
                if current_hour == 12:
                    logger.info("Generating daily betting tips")
                    # In a real implementation, this would call the betting advisor
                    # For now, we'll just send a placeholder message
                    tips_message = (
                        f"<b>📊 BETTING TIPS FOR {current_date.strftime('%Y-%m-%d')}</b>\n\n"
                        f"The betting advisor is analyzing today's matches.\n"
                        f"Tips will be sent when the analysis is complete.\n\n"
                        f"<i>This is a placeholder - in the real system, actual tips would be provided here.</i>"
                    )
                    await self._send_telegram_update(tips_message)
                
                # Check results in the evening
                elif current_hour == 22:
                    logger.info("Checking results of today's bets")
                    # In a real implementation, this would check actual results
                    # For now, we'll just send a placeholder message
                    results_message = (
                        f"<b>📈 BETTING RESULTS FOR {current_date.strftime('%Y-%m-%d')}</b>\n\n"
                        f"The system is checking the results of today's bets.\n"
                        f"A performance update will be sent when all results are in.\n\n"
                        f"<i>This is a placeholder - in the real system, actual results would be provided here.</i>"
                    )
                    await self._send_telegram_update(results_message)
                
                # Send a heartbeat message every 6 hours to show the system is running
                elif current_hour % 6 == 0 and current_date.minute < 5:
                    heartbeat_message = (
                        f"<b>⏱️ AI Football Betting Advisor</b>\n\n"
                        f"The system is running normally in production mode.\n"
                        f"Current time: {current_date.strftime('%H:%M:%S')}\n"
                        f"Next tips will be generated at 12:00."
                    )
                    await self._send_telegram_update(heartbeat_message)
                
                # Wait for 5 minutes before checking time again
                await asyncio.sleep(300)  # 5 minutes = 300 seconds
                
        except KeyboardInterrupt:
            logger.info("Production mode interrupted by user")
            await self._send_telegram_update("<b>⚠️ Production mode has been stopped by the user.</b>")
        except Exception as e:
            logger.error(f"Error in production mode: {e}")
            logger.exception(e)
            await self._send_telegram_update(f"<b>❌ ERROR:</b> Production mode encountered an error: {str(e)}")
        finally:
            # Clean up and close the Telegram bot
            if self.telegram_bot:
                logger.info("Stopping Telegram bot")
                await self._send_telegram_update("<b>🛑 Production mode is shutting down.</b>")
                await self.telegram_bot.stop()
            
            logger.info("Production mode stopped")

async def main():
    """Main entry point for production mode."""
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run AI Football Betting Advisor in production mode")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    args = parser.parse_args()
    
    # Create and run production mode
    try:
        production = ProductionMode(config_path=args.config)
        await production.run()
    except Exception as e:
        logger.error(f"Error in production mode: {e}")
        logger.exception(e)
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main()) 