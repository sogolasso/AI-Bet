"""
Enhanced Telegram Bot for the AI Football Betting Advisor.

This module implements the Telegram bot interface with enhanced commands
for interacting with the football betting advisor system.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import os
import json
from pathlib import Path

from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, Dispatcher, Application,
    ContextTypes, MessageHandler, filters
)

from betting.betting_advisor import BettingAdvisor
from bot.telegram_formatter import (
    format_daily_tips, format_performance_report, format_system_status,
    format_last_bets, format_help_message
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load admin user IDs from environment or config
ADMIN_USER_IDS = [int(id) for id in os.environ.get("TELEGRAM_ADMIN_IDS", "").split(",") if id]

class BettingAdvisorBot:
    """Enhanced Telegram bot for the Football Betting Advisor."""
    
    def __init__(self, token: str, config: Dict[str, Any] = None):
        """Initialize the bot with the provided Telegram token.
        
        Args:
            token: Telegram bot token
            config: Configuration dictionary
        """
        self.token = token
        self.config = config or {}
        self.updater = None
        self.dispatcher = None
        self.advisor = BettingAdvisor(config=self.config)
        
        # Set up command throttling to prevent abuse
        self.command_timestamps = {}
        self.throttle_seconds = self.config.get("throttle_seconds", 5)
        
        # Data directory
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.log_dir = Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize the bot application and set up command handlers."""
        # Create the updater
        self.updater = Updater(token=self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Add command handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CommandHandler("tips", self.tips_command))
        self.dispatcher.add_handler(CommandHandler("performance", self.performance_command))
        self.dispatcher.add_handler(CommandHandler("status", self.status_command))
        self.dispatcher.add_handler(CommandHandler("roi", self.roi_command))
        self.dispatcher.add_handler(CommandHandler("lastbets", self.last_bets_command))
        self.dispatcher.add_handler(CommandHandler("restart", self.restart_command))
        self.dispatcher.add_handler(CommandHandler("todaystips", self.tips_command))  # Alias for tips
        
        # Add error handler
        self.dispatcher.add_error_handler(self.error_handler)
        
        # Set up commands for the bot UI
        await self._setup_commands()
        
        logger.info("Bot initialization completed")
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None, 
                         reply_markup = None, disable_web_page_preview: bool = None) -> None:
        """Send a message through the Telegram bot.
        
        Args:
            chat_id: Telegram chat ID to send the message to
            text: Text of the message to send
            parse_mode: Parse mode for text formatting (Markdown, HTML)
            reply_markup: Additional interface options (keyboard, buttons)
            disable_web_page_preview: Disable link previews in the message
        """
        try:
            if self.updater and self.updater.bot:
                await self.updater.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_web_page_preview
                )
                logger.debug(f"Sent message to chat {chat_id}: {text[:30]}...")
            else:
                logger.error("Bot updater not initialized, cannot send message")
        except Exception as e:
            logger.error(f"Error sending message to chat {chat_id}: {e}")
    
    async def _setup_commands(self) -> None:
        """Set up commands for the Telegram bot UI."""
        commands = [
            BotCommand("start", "Start the bot and get welcome message"),
            BotCommand("help", "Display help message with available commands"),
            BotCommand("tips", "Get today's betting tips"),
            BotCommand("performance", "View performance report"),
            BotCommand("status", "Check system status"),
            BotCommand("roi", "View Return on Investment by market"),
            BotCommand("lastbets", "View recent bets and results"),
            BotCommand("restart", "Request system restart (admin only)")
        ]
        
        await asyncio.to_thread(self.updater.bot.set_my_commands, commands)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user ID is an admin.
        
        Args:
            user_id: Telegram user ID to check
            
        Returns:
            True if the user is an admin, False otherwise
        """
        return user_id in ADMIN_USER_IDS
    
    def is_throttled(self, user_id: int, command: str) -> bool:
        """Check if a command from a user is being throttled.
        
        Args:
            user_id: Telegram user ID
            command: Command name
            
        Returns:
            True if the command should be throttled, False otherwise
        """
        key = f"{user_id}:{command}"
        now = datetime.now().timestamp()
        
        if key in self.command_timestamps:
            last_time = self.command_timestamps[key]
            if now - last_time < self.throttle_seconds:
                return True
        
        self.command_timestamps[key] = now
        return False
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        if not self.updater:
            await self.initialize()
        
        logger.info("Starting Telegram bot")
        self.updater.start_polling()
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self.updater:
            logger.info("Stopping Telegram bot")
            self.updater.stop()
    
    # Command handlers
    
    def start_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /start command.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user = update.effective_user
        user_id = user.id
        
        if self.is_throttled(user_id, "start"):
            return
        
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
            "Welcome to the *AI Football Betting Advisor Bot*. I provide daily betting tips "
            "based on advanced AI analysis of football matches.\n\n"
            "🔍 I analyze team form, injuries, odds movements, and historical data to identify value bets "
            "across various markets.\n\n"
            "Use /help to see available commands.\n\n"
            "🚨 *Disclaimer*: Betting involves risk. Please gamble responsibly."
        )
        
        update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} started the bot")
    
    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /help command.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        if self.is_throttled(user_id, "help"):
            return
        
        help_message = format_help_message()
        
        update.message.reply_text(
            help_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} requested help")
    
    async def tips_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /tips and /todaystips commands.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        if self.is_throttled(user_id, "tips"):
            return
        
        # Send typing indicator
        context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Get daily tips
        tips = await self.advisor.get_daily_tips()
        
        # Format and send tips
        tips_message = format_daily_tips(tips)
        
        update.message.reply_text(
            tips_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} requested tips")
    
    async def performance_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /performance command.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        if self.is_throttled(user_id, "performance"):
            return
        
        # Send typing indicator
        context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Get performance report
        days = 30
        if context.args and context.args[0].isdigit():
            days = min(365, max(7, int(context.args[0])))
        
        performance = await self.advisor.generate_performance_report(days=days)
        
        # Format and send performance report
        performance_message = format_performance_report(performance)
        
        update.message.reply_text(
            performance_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} requested performance report for {days} days")
    
    def status_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /status command.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        if self.is_throttled(user_id, "status"):
            return
        
        # Get system status
        status = self.advisor.get_system_status()
        
        # Format and send status message
        status_message = format_system_status(status)
        
        update.message.reply_text(
            status_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} requested system status")
    
    async def roi_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /roi command.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        if self.is_throttled(user_id, "roi"):
            return
        
        # Send typing indicator
        context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Get performance for ROI calculation
        days = 30
        if context.args and context.args[0].isdigit():
            days = min(365, max(7, int(context.args[0])))
        
        performance = await self.advisor.generate_performance_report(days=days)
        
        # Extract ROI information
        roi = performance.get("roi", 0)
        markets = performance.get("markets", {})
        
        # Format ROI message
        roi_message = f"📊 *ROI REPORT - LAST {days} DAYS* 📊\n\n"
        roi_message += f"Overall ROI: {roi:.2f}%\n\n"
        
        if markets:
            roi_message += "*ROI by Market:*\n"
            # Sort markets by ROI
            sorted_markets = sorted(
                [(market, data) for market, data in markets.items()],
                key=lambda x: x[1].get("roi", 0),
                reverse=True
            )
            
            for market, data in sorted_markets:
                market_roi = data.get("roi", 0)
                roi_sign = "+" if market_roi >= 0 else ""
                roi_message += f"• {market}: {roi_sign}{market_roi:.2f}% ({data.get('bets', 0)} bets)\n"
        
        update.message.reply_text(
            roi_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} requested ROI for {days} days")
    
    def last_bets_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /lastbets command.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        if self.is_throttled(user_id, "lastbets"):
            return
        
        # Send typing indicator
        context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Get number of bets to show
        limit = 5
        if context.args and context.args[0].isdigit():
            limit = min(20, max(1, int(context.args[0])))
        
        # Get recent bets
        bets = self.advisor.bet_processor.bet_history
        
        # Format and send last bets message
        last_bets_message = format_last_bets(bets, limit=limit)
        
        update.message.reply_text(
            last_bets_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user_id} requested last {limit} bets")
    
    async def restart_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /restart command (admin only).
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object
        """
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not self.is_admin(user_id):
            update.message.reply_text(
                "⛔ Sorry, this command is only available to admins.",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.warning(f"Non-admin user {user_id} attempted to use restart command")
            return
        
        if self.is_throttled(user_id, "restart"):
            return
        
        update.message.reply_text(
            "🔄 *System restart initiated.* This may take a minute...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Admin {user_id} initiated system restart")
        
        # In a real implementation, this would trigger a system restart
        # For demonstration, we'll simulate a restart
        
        await asyncio.sleep(3)  # Simulate restart time
        
        update.message.reply_text(
            "✅ *System restarted successfully.*\nAll services are now running.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def error_handler(self, update: object, context: CallbackContext) -> None:
        """Handle errors in the bot.
        
        Args:
            update: Update object from Telegram
            context: CallbackContext object with error
        """
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Log detailed error to file
        error_log_file = self.log_dir / "telegram_errors.log"
        with open(error_log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: {str(context.error)}\n")
            
            if update:
                if isinstance(update, Update):
                    update_str = str(update.to_dict())
                else:
                    update_str = str(update)
                f.write(f"Update: {update_str}\n")
            f.write("---\n")
        
        # If update is available and is a message, notify the user
        if update and isinstance(update, Update) and update.effective_message:
            # Only notify about errors on regular commands, not admin commands
            if not update.effective_message.text.startswith(("/restart", "/admin")):
                update.effective_message.reply_text(
                    "Sorry, something went wrong while processing your request. "
                    "Please try again later."
                )


async def main() -> None:
    """Run the bot as a standalone script."""
    import argparse
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Football Betting Advisor Telegram Bot")
    parser.add_argument("--token", help="Telegram bot token")
    parser.add_argument("--config", help="Path to configuration file")
    args = parser.parse_args()
    
    # Get token from args or environment
    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        parser.error("No token provided. Set TELEGRAM_BOT_TOKEN env var or use --token")
    
    # Load config
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Create and start the bot
    bot = BettingAdvisorBot(token, config)
    await bot.initialize()
    
    try:
        await bot.start()
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopping...")
    finally:
        await bot.stop()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main()) 