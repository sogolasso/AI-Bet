#!/usr/bin/env python3
"""
All-in-One Runner for AI Football Betting Advisor

This comprehensive script handles all the setup and execution steps:
1. Environment setup and dependency installation
2. Configuration of Telegram bot and user ID
3. Seamless launching of either shadow mode or production mode
"""

import os
import sys
import subprocess
import shutil
import platform
import argparse
import tempfile
import time
import json
import asyncio
import pkg_resources
from pathlib import Path
from datetime import datetime
import getpass
try:
    from dotenv import load_dotenv
except ImportError:
    # Will install later
    pass

# Constants
REQUIRED_DIRS = [
    "data",
    "data/shadow",
    "logs",
    "utils",
    "bot",
    "models"
]

REQUIRED_PACKAGES = [
    "python-telegram-bot==13.7",  # Using older version to avoid breaking changes
    "python-dotenv",
    "pandas",
    "numpy",
    "redis",
    "requests",
    "aiohttp",
    "beautifulsoup4",
    "lxml",
    "matplotlib"
]

# Terminal colors
class Colors:
    """Terminal colors for better UI."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def supported():
        """Check if colors are supported in the terminal."""
        if platform.system() == "Windows":
            return os.environ.get("WT_SESSION") or "TERM" in os.environ
        return True

def colorize(text, color):
    """Apply color to text if supported."""
    if Colors.supported():
        return f"{color}{text}{Colors.ENDC}"
    return text

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def print_header():
    """Print the program header."""
    clear_screen()
    print(colorize("=" * 80, Colors.BLUE))
    print(colorize(" " * 20 + "AI FOOTBALL BETTING ADVISOR", Colors.BOLD + Colors.GREEN))
    print(colorize(" " * 20 + "All-in-One Setup & Runner", Colors.YELLOW))
    print(colorize("=" * 80, Colors.BLUE))
    print()

def print_step(step_num, total_steps, description):
    """Print a step header."""
    print(colorize(f"[Step {step_num}/{total_steps}] {description}", Colors.BOLD + Colors.BLUE))
    print(colorize("-" * 80, Colors.BLUE))

def check_python_version():
    """Check if the Python version is compatible."""
    print(colorize("Checking Python version...", Colors.BLUE))
    major, minor, _ = platform.python_version_tuple()
    
    if int(major) < 3 or (int(major) == 3 and int(minor) < 8):
        print(colorize(f"❌ Error: Python 3.8 or later is required", Colors.RED))
        print(colorize(f"   Current version: {major}.{minor}", Colors.RED))
        print(colorize(f"   Please upgrade your Python installation", Colors.RED))
        return False
    
    print(colorize(f"✅ Python version {major}.{minor} is compatible", Colors.GREEN))
    return True

def create_directories():
    """Create required directories if they don't exist."""
    print(colorize("Creating required directories...", Colors.BLUE))
    
    for directory in REQUIRED_DIRS:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(colorize(f"  Created: {directory}/", Colors.GREEN))
        else:
            print(colorize(f"  Already exists: {directory}/", Colors.YELLOW))

def install_dependencies():
    """Install required dependencies."""
    print(colorize("Checking and installing dependencies...", Colors.BLUE))
    
    packages_to_install = []
    
    # Check which packages need to be installed
    for package in REQUIRED_PACKAGES:
        package_name = package.split("==")[0]
        try:
            pkg_resources.get_distribution(package_name)
            print(colorize(f"  ✅ {package} is already installed", Colors.GREEN))
        except pkg_resources.DistributionNotFound:
            packages_to_install.append(package)
            print(colorize(f"  ❌ {package} needs to be installed", Colors.YELLOW))
    
    # Install missing packages
    if packages_to_install:
        print(colorize("Installing missing packages...", Colors.BLUE))
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages_to_install)
            print(colorize("✅ All packages installed successfully", Colors.GREEN))
        except subprocess.CalledProcessError:
            print(colorize("❌ Failed to install some packages.", Colors.RED))
            print(colorize(f"   Try: pip install {' '.join(packages_to_install)}", Colors.YELLOW))
            return False
    else:
        print(colorize("✅ All required packages are already installed", Colors.GREEN))
    
    # Import dotenv after ensuring it's installed
    global load_dotenv
    from dotenv import load_dotenv
    
    return True

def setup_env_file():
    """Create or update .env file."""
    env_path = Path(".env")
    
    if env_path.exists():
        print(colorize(".env file already exists", Colors.YELLOW))
        update = input(colorize("   Do you want to update it? (y/n): ", Colors.YELLOW)).lower() == 'y'
        if not update:
            return True
    
    print(colorize("Setting up .env file...", Colors.BLUE))
    
    # Get Telegram bot token
    print(colorize("\nTelegram Bot Setup", Colors.BOLD))
    print(colorize("To create a new Telegram bot:", Colors.BLUE))
    print("1. Open Telegram and search for @BotFather")
    print("2. Send /newbot command to @BotFather")
    print("3. Follow the instructions to create a new bot")
    print("4. BotFather will give you a bot token (like 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi)")
    
    bot_token = input(colorize("\nEnter your Telegram bot token (or press Enter to skip for now): ", Colors.YELLOW))
    
    # Default environment file content
    env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={bot_token if bot_token else 'your_bot_token_here'}
# Replace with your actual Telegram user ID
# Run the get_telegram_id function in this script to get your ID
TELEGRAM_ADMIN_IDS=

# Application Settings
INITIAL_BANKROLL=1000
MAX_DAILY_BETS=5
MIN_CONFIDENCE=Medium
MIN_VALUE_THRESHOLD=0.05
STAKING_STRATEGY=kelly
KELLY_FRACTION=0.25
MAX_STAKE_PER_BET_PERCENT=5.0

# Data Sources
DAYS_AHEAD=3

# Logging
LOG_LEVEL=INFO
"""
    
    # Write the file
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(colorize("✅ .env file created successfully", Colors.GREEN))
        return True
    except Exception as e:
        print(colorize(f"❌ Failed to create .env file: {e}", Colors.RED))
        return False

def get_telegram_id():
    """Run a Telegram bot to get the user's Telegram ID."""
    print(colorize("\nGetting Your Telegram ID", Colors.BOLD))
    print(colorize("This will start a temporary bot to help you get your Telegram ID.", Colors.BLUE))
    print("Once you have your ID, you'll need to add it to your .env file.")

    # Load environment variables
    load_dotenv()
    
    # Check if token is available
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        print(colorize("❌ No valid Telegram bot token found in .env file.", Colors.RED))
        new_token = input(colorize("Enter your Telegram bot token to continue: ", Colors.YELLOW))
        if not new_token:
            print(colorize("❌ Cannot continue without a Telegram bot token.", Colors.RED))
            return False
        token = new_token
        
        # Update .env file with the new token
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            env_content = env_content.replace('TELEGRAM_BOT_TOKEN=your_bot_token_here', f'TELEGRAM_BOT_TOKEN={token}')
            
            with open(env_path, 'w') as f:
                f.write(env_content)
    
    try:
        # Create a temporary script to get the Telegram ID
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write('''
import os
import sys
import logging
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    
    update.message.reply_html(
        f"Hi {user.mention_html()}!\\n\\n"
        f"Your Telegram user ID is: <b>{user_id}</b>\\n\\n"
        f"Please add this ID to your .env file:\\n"
        f"TELEGRAM_ADMIN_IDS={user_id}"
    )
    
    logger.info(f"User {user.full_name} (ID: {user_id}) started the bot")
    print(f"\\nUser ID found: {user_id}\\n")
    print(f"Add this to your .env file as: TELEGRAM_ADMIN_IDS={user_id}")

def get_id(update: Update, context: CallbackContext) -> None:
    """Echo the user ID of the user who sent a message."""
    user_id = update.effective_user.id
    update.message.reply_html(
        f"Your Telegram user ID is: <b>{user_id}</b>\\n\\n"
        f"Add this to your .env file as:\\n"
        f"TELEGRAM_ADMIN_IDS={user_id}"
    )
    print(f"\\nUser ID found: {user_id}\\n")
    print(f"Add this to your .env file as: TELEGRAM_ADMIN_IDS={user_id}")

def main() -> None:
    """Start the bot."""
    # Get telegram token from command line argument
    token = sys.argv[1]
    
    # Create the Updater and pass it your bot's token
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))

    # Register message handler for getting user ID
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, get_id
    ))

    # Start the Bot
    updater.start_polling()

    print("Bot started. Send a message to your bot to get your Telegram user ID.")
    print("When done, press Ctrl+C to stop the bot.")

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
''')
            temp_script = f.name
        
        print(colorize("\nStarting Telegram ID helper bot...", Colors.BLUE))
        print(colorize("1. Open Telegram and find your bot", Colors.YELLOW))
        print(colorize("2. Send any message to your bot", Colors.YELLOW))
        print(colorize("3. The bot will reply with your Telegram user ID", Colors.YELLOW))
        print(colorize("4. Press Ctrl+C when done to continue", Colors.YELLOW))
        
        print(colorize("\nWaiting for messages to your bot...", Colors.BLUE))
        subprocess.run([sys.executable, temp_script, token], check=True)
        
    except KeyboardInterrupt:
        print(colorize("\nBot stopped. Did you get your user ID?", Colors.YELLOW))
    except Exception as e:
        print(colorize(f"\n❌ Error running Telegram bot: {e}", Colors.RED))
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_script)
        except:
            pass
    
    # Ask for the ID to update .env
    user_id = input(colorize("\nEnter your Telegram user ID to update .env file: ", Colors.YELLOW))
    if user_id:
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            # Replace the admin IDs line
            if 'TELEGRAM_ADMIN_IDS=' in env_content:
                env_content = env_content.replace('TELEGRAM_ADMIN_IDS=', f'TELEGRAM_ADMIN_IDS={user_id}')
                
                with open(env_path, 'w') as f:
                    f.write(env_content)
                
                print(colorize(f"✅ Updated .env file with your Telegram ID: {user_id}", Colors.GREEN))
            else:
                print(colorize("❌ Could not find TELEGRAM_ADMIN_IDS in .env file", Colors.RED))
        else:
            print(colorize("❌ .env file not found", Colors.RED))
    
    return True

async def run_shadow_mode(duration=14, bankroll=100, quick_mode=False):
    """Run the system in shadow mode."""
    print(colorize("\nStarting Telegram Shadow Mode", Colors.BOLD))
    print(colorize(f"Duration: {duration} days", Colors.BLUE))
    print(colorize(f"Bankroll: ${bankroll}", Colors.BLUE))
    if quick_mode:
        print(colorize("Quick mode: Enabled (faster simulation)", Colors.BLUE))
        os.environ["SHADOW_QUICK_MODE"] = "1"
    
    try:
        # Import here to avoid circular imports
        from telegram_shadow_mode import TelegramShadowMode
        
        # Create and run shadow mode
        shadow_mode = TelegramShadowMode(
            duration_days=duration,
            bankroll=bankroll,
            data_dir="data/shadow"
        )
        
        print(colorize("\nInitializing shadow mode simulation...", Colors.BLUE))
        print(colorize("This will run for the specified duration, simulating daily betting.", Colors.YELLOW))
        print(colorize("Check your Telegram for updates during the simulation.", Colors.YELLOW))
        print(colorize("Press Ctrl+C to stop the simulation at any time.\n", Colors.YELLOW))
        
        await shadow_mode.run()
        
        print(colorize("\n✅ Shadow mode completed successfully", Colors.GREEN))
        print(colorize("Results have been saved to data/shadow/ directory.", Colors.BLUE))
        
    except KeyboardInterrupt:
        print(colorize("\n⚠️ Shadow mode interrupted by user", Colors.YELLOW))
    except ImportError as e:
        print(colorize(f"\n❌ Error importing required modules: {e}", Colors.RED))
        print(colorize("Make sure you've run the setup function first.", Colors.YELLOW))
    except Exception as e:
        print(colorize(f"\n❌ Error in shadow mode: {e}", Colors.RED))
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def run_production_mode():
    """Run the system in production mode."""
    print(colorize("\nStarting Production Mode", Colors.BOLD))
    
    try:
        # Import the production mode components
        try:
            from betting.betting_advisor import BettingAdvisor
            from bot.new_telegram_bot import BettingAdvisorBot
            from dotenv import load_dotenv
            from production_mode import ProductionMode
        except ImportError as e:
            print(colorize(f"❌ Could not import required modules for production mode: {e}", Colors.RED))
            print(colorize("The production mode components might not be fully implemented yet.", Colors.YELLOW))
            return False
            
        # Force reload environment variables
        try:
            load_dotenv(override=True)
            print(colorize("Environment variables reloaded from .env file", Colors.BLUE))
        except Exception as e:
            print(colorize(f"Error loading .env file: {e}", Colors.RED))
        
        # Check token before starting production mode
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not telegram_token or telegram_token == 'your_bot_token_here':
            print(colorize("❌ No valid Telegram bot token found in environment variables.", Colors.RED))
            
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
                                print(colorize(f"Found token in .env file: {telegram_token[:5]}...", Colors.BLUE))
                                break
                        else:
                            print(colorize("❌ No valid Telegram bot token found in .env file.", Colors.RED))
                            return False
                else:
                    print(colorize("❌ .env file not found.", Colors.RED))
                    return False
            except Exception as e:
                print(colorize(f"❌ Error reading .env file directly: {e}", Colors.RED))
                return False
                
            if not telegram_token or telegram_token == 'your_bot_token_here':
                print(colorize("❌ Please set a valid TELEGRAM_BOT_TOKEN in your .env file.", Colors.RED))
                return False
        else:
            print(colorize(f"Found token in environment: {telegram_token[:5]}...", Colors.BLUE))
        
        # Check for admin IDs
        admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS')
        if not admin_ids:
            print(colorize("⚠️ Warning: TELEGRAM_ADMIN_IDS environment variable is not set.", Colors.YELLOW))
            print(colorize("   Production mode updates will not be sent to any users.", Colors.YELLOW))
            print(colorize("   Run the get_telegram_id.py script to get your Telegram user ID.", Colors.YELLOW))
        else:
            try:
                # Parse admin IDs - handle various formats
                admin_ids = admin_ids.strip('[]')
                admin_id_list = [id.strip() for id in admin_ids.split(',')]
                valid_ids = [int(id) for id in admin_id_list if id.strip().isdigit()]
                
                if valid_ids:
                    print(colorize(f"Found valid admin IDs: {valid_ids}", Colors.BLUE))
                else:
                    print(colorize("⚠️ Warning: TELEGRAM_ADMIN_IDS environment variable does not contain valid IDs.", Colors.YELLOW))
            except Exception as e:
                print(colorize(f"⚠️ Warning: Error parsing admin IDs: {e}", Colors.YELLOW))
        
        # Create and run production mode
        print(colorize("Initializing production mode...", Colors.BLUE))
        production_mode = ProductionMode()
        
        print(colorize("Starting production mode...", Colors.BLUE))
        print(colorize("Press Ctrl+C at any time to stop.", Colors.YELLOW))
        await production_mode.run()
            
    except KeyboardInterrupt:
        print(colorize("\n⚠️ Production mode interrupted by user", Colors.YELLOW))
    except Exception as e:
        print(colorize(f"\n❌ Error in production mode: {e}", Colors.RED))
        import traceback
        traceback.print_exc()
        return False
    
    return True

def setup():
    """Run the complete setup process."""
    total_steps = 4
    
    print_header()
    print_step(1, total_steps, "Checking Environment")
    if not check_python_version():
        return False
    
    create_directories()
    
    print_step(2, total_steps, "Installing Dependencies")
    if not install_dependencies():
        return False
    
    print_step(3, total_steps, "Setting Up Configuration")
    if not setup_env_file():
        return False
    
    print_step(4, total_steps, "Configuring Telegram")
    if not get_telegram_id():
        print(colorize("⚠️ Telegram ID setup was skipped or failed.", Colors.YELLOW))
        print(colorize("You can run the get_telegram_id function later.", Colors.YELLOW))
    
    print(colorize("\n✅ Setup completed successfully!", Colors.GREEN))
    print(colorize("You can now run the system in shadow mode or production mode.", Colors.BLUE))
    
    return True

def show_menu():
    """Show the main menu."""
    while True:
        print_header()
        print(colorize("Main Menu", Colors.BOLD))
        print(colorize("1. ", Colors.YELLOW) + "Setup Environment (install dependencies, configure Telegram)")
        print(colorize("2. ", Colors.YELLOW) + "Get Telegram User ID")
        print(colorize("3. ", Colors.YELLOW) + "Run Shadow Mode (for testing without real money)")
        print(colorize("4. ", Colors.YELLOW) + "Run Production Mode (real betting advisor)")
        print(colorize("5. ", Colors.YELLOW) + "Exit")
        
        choice = input(colorize("\nSelect an option (1-5): ", Colors.GREEN))
        
        if choice == '1':
            setup()
            input(colorize("\nPress Enter to return to the menu...", Colors.YELLOW))
        elif choice == '2':
            get_telegram_id()
            input(colorize("\nPress Enter to return to the menu...", Colors.YELLOW))
        elif choice == '3':
            # Shadow mode options
            print_header()
            print(colorize("Shadow Mode Settings", Colors.BOLD))
            
            try:
                duration = int(input(colorize("Duration in days (default: 14): ", Colors.YELLOW)) or 14)
                bankroll = float(input(colorize("Initial bankroll (default: 100): ", Colors.YELLOW)) or 100)
                quick = input(colorize("Enable quick mode? (y/n, default: y): ", Colors.YELLOW)).lower() != 'n'
                
                asyncio.run(run_shadow_mode(duration, bankroll, quick))
            except ValueError:
                print(colorize("❌ Invalid input. Using default values.", Colors.RED))
                asyncio.run(run_shadow_mode())
            
            input(colorize("\nPress Enter to return to the menu...", Colors.YELLOW))
        elif choice == '4':
            asyncio.run(run_production_mode())
            input(colorize("\nPress Enter to return to the menu...", Colors.YELLOW))
        elif choice == '5':
            print(colorize("\nExiting AI Football Betting Advisor. Goodbye!", Colors.GREEN))
            return
        else:
            print(colorize("\n❌ Invalid choice. Please try again.", Colors.RED))
            time.sleep(1)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="All-in-One Runner for AI Football Betting Advisor"
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Run the setup process"
    )
    parser.add_argument(
        "--get-id", action="store_true",
        help="Get your Telegram user ID"
    )
    parser.add_argument(
        "--shadow", action="store_true",
        help="Run in shadow mode (testing without real money)"
    )
    parser.add_argument(
        "--production", action="store_true",
        help="Run in production mode (real betting advisor)"
    )
    parser.add_argument(
        "--duration", "-d", type=int, default=14,
        help="Duration in days for shadow mode (default: 14)"
    )
    parser.add_argument(
        "--bankroll", "-b", type=float, default=100,
        help="Initial bankroll for shadow mode (default: 100)"
    )
    parser.add_argument(
        "--quick", "-q", action="store_true",
        help="Enable quick mode for faster shadow mode simulation"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.setup:
        return setup()
    elif args.get_id:
        return get_telegram_id()
    elif args.shadow:
        return asyncio.run(run_shadow_mode(args.duration, args.bankroll, args.quick))
    elif args.production:
        return asyncio.run(run_production_mode())
    else:
        # No specific command, show the menu
        return show_menu()

if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        print(colorize("\nOperation cancelled by user. Exiting...", Colors.YELLOW))
        sys.exit(0) 