#!/usr/bin/env python3
"""
Launcher script for Telegram Shadow Mode

This script provides a simple way to launch the Telegram-integrated shadow mode
with customizable parameters.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """Check if the environment is properly set up."""
    # Load environment variables with override to ensure they're freshly loaded
    load_dotenv(override=True)
    
    # Check for Telegram bot token
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        print("   Please add it to your .env file or set it in your environment.")
        print("   Example: TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
        return False
    else:
        print(f"✅ Found Telegram bot token: {token[:5]}...")
    
    # Check for admin IDs
    admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS')
    if not admin_ids:
        print("⚠️ Warning: TELEGRAM_ADMIN_IDS environment variable is not set.")
        print("   Shadow mode updates will not be sent to any users.")
        print("   Example: TELEGRAM_ADMIN_IDS=123456789,987654321")
        print("   Run the get_telegram_id.py script to get your Telegram user ID.")
    else:
        try:
            # Parse admin IDs - handle various formats
            admin_ids = admin_ids.strip('[]')
            admin_id_list = [id.strip() for id in admin_ids.split(',')]
            valid_ids = [int(id) for id in admin_id_list if id.strip().isdigit()]
            
            if valid_ids:
                print(f"✅ Found valid admin IDs: {valid_ids}")
            else:
                print("⚠️ Warning: TELEGRAM_ADMIN_IDS environment variable does not contain valid IDs.")
        except Exception as e:
            print(f"⚠️ Warning: Error parsing admin IDs: {e}")
    
    # Check required directories
    Path("logs").mkdir(exist_ok=True)
    Path("data/shadow").mkdir(exist_ok=True, parents=True)
    
    # Check if the required modules are available
    try:
        from telegram_shadow_mode import TelegramShadowMode
        print("✅ Found telegram_shadow_mode.py module")
    except ImportError:
        print("❌ Error: telegram_shadow_mode.py not found or has errors.")
        return False
    
    # Ensure utility directories exist
    Path("utils").mkdir(exist_ok=True)
    
    return True

async def run_shadow_mode(duration, bankroll, config_file, quick_mode=False):
    """Run the shadow mode with the given parameters."""
    # Import here to avoid circular imports
    from telegram_shadow_mode import TelegramShadowMode
    
    # Set quick mode environment variable if needed
    if quick_mode:
        os.environ["SHADOW_QUICK_MODE"] = "1"
        print("🚀 Running in quick mode - simulation will run faster")
    
    # Ensure environment variables are accessible
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable is missing even after loading .env")
        return 1
    
    admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS')
    if not admin_ids:
        print("⚠️ Warning: TELEGRAM_ADMIN_IDS environment variable is missing - no notifications will be sent")
    
    try:
        # Create and run shadow mode
        shadow_mode = TelegramShadowMode(
            duration_days=duration,
            bankroll=bankroll,
            data_dir="data/shadow"
        )
        
        await shadow_mode.run()
        print(f"✅ Shadow mode completed successfully after {duration} days simulation")
        
    except KeyboardInterrupt:
        print("\n⚠️ Shadow mode interrupted by user")
    except Exception as e:
        print(f"❌ Error in shadow mode: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

def main():
    """Parse arguments and run the shadow mode."""
    parser = argparse.ArgumentParser(
        description="Run AI Football Betting Advisor in shadow mode with Telegram integration"
    )
    parser.add_argument(
        "--duration", "-d", 
        type=int, 
        default=14, 
        help="Duration in days for shadow mode (default: 14)"
    )
    parser.add_argument(
        "--bankroll", "-b", 
        type=float, 
        default=100.0, 
        help="Initial bankroll amount (default: 100.0)"
    )
    parser.add_argument(
        "--config", "-c", 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run in quick mode (faster simulation with shorter delays)"
    )
    
    args = parser.parse_args()
    
    # Check environment before running
    if not check_environment():
        return 1
    
    # Print run parameters
    print(f"🔮 Starting AI Football Betting Advisor in Telegram Shadow Mode")
    print(f"📅 Duration: {args.duration} days")
    print(f"💰 Initial bankroll: ${args.bankroll}")
    if args.quick:
        print(f"⚡ Quick mode enabled: Simulation will run faster")
    
    # Run shadow mode
    return asyncio.run(run_shadow_mode(args.duration, args.bankroll, args.config, args.quick))

if __name__ == "__main__":
    sys.exit(main()) 