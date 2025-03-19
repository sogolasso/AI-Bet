from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os

# Load bot token from environment variable or hardcode it (not recommended for security reasons)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7660309704:AAFBlMY6_WSpsovSde109hSwUcLuMnT4i30")

# Initialize the bot application
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Start Command
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome to the AI Football Betting Advisor!")

# Help Command
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Available commands:\n/start - Start the bot\n/help - Get help")

# Handle regular messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("I can only respond to commands. Type /help for options.")

# Add command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run the bot
if __name__ == "__main__":
    print("Starting Telegram Bot...")
    app.run_polling()
