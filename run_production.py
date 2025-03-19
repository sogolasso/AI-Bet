#!/usr/bin/env python3
"""
Production Mode Launcher for AI Football Betting Advisor

This script is a simple launcher for the production mode of the AI Football Betting Advisor.
It's a convenience wrapper around the all_in_one.py script.
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

def check_environment():
    """Check if the environment is properly set up."""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        print("✅ Environment variables loaded from .env file")
    except ImportError:
        print("⚠️ Warning: python-dotenv is not installed. Environment variables may not be loaded correctly.")
        print("   Run 'pip install python-dotenv' to install it.")
    
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
        print("   Production mode updates will not be sent to any users.")
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
    Path("data").mkdir(exist_ok=True)
    
    return True

def main():
    """Launch all_in_one.py in production mode."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    all_in_one_path = os.path.join(script_dir, "all_in_one.py")
    
    # Make sure all_in_one.py exists
    if not os.path.exists(all_in_one_path):
        print("Error: all_in_one.py not found. Make sure it exists in the same directory.")
        return 1
    
    # Check environment before running
    if not check_environment():
        return 1
    
    # Make script executable on Unix systems
    if platform.system() != "Windows":
        try:
            os.chmod(all_in_one_path, 0o755)
        except:
            pass
    
    # Pass through any command-line arguments
    args = ["--production"] + sys.argv[1:]
    
    print("\n🚀 Launching production mode...\n")
    
    # Execute all_in_one.py with the production argument
    try:
        if platform.system() == "Windows":
            return subprocess.call([sys.executable, all_in_one_path] + args)
        else:
            return subprocess.call([all_in_one_path] + args)
    except Exception as e:
        print(f"Error launching production mode: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 