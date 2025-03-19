#!/usr/bin/env python3
"""
Telegram Bot Environment Test

This script tests the Telegram bot environment variables and connection
to help diagnose issues with the Telegram integration.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

def test_telegram_connection():
    """Test the Telegram bot connection using the configured token."""
    print("\n🔍 Testing Telegram Bot Connection\n" + "-" * 40)
    
    # Try multiple .env file locations
    env_locations = [
        '.env',
        '../.env',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    ]
    
    for env_path in env_locations:
        if os.path.exists(env_path):
            print(f"✅ Found .env file at: {env_path}")
            load_dotenv(env_path, override=True)
            break
    else:
        print("❌ No .env file found in searched locations")
    
    # Test TELEGRAM_BOT_TOKEN
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        
        # Try to read directly from .env file if exists
        if os.path.exists('.env'):
            print("🔍 Attempting to read token directly from .env file...")
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.strip().startswith('TELEGRAM_BOT_TOKEN='):
                            token = line.strip().split('=', 1)[1].strip()
                            if token.startswith('"') and token.endswith('"'):
                                token = token[1:-1]
                            print(f"✅ Found token in .env file: {token[:5]}...")
                            break
                    else:
                        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
            except Exception as e:
                print(f"❌ Error reading .env file: {e}")
    else:
        print(f"✅ TELEGRAM_BOT_TOKEN found in environment variables: {token[:5]}...")
    
    # Test TELEGRAM_ADMIN_IDS
    admin_ids_str = os.environ.get('TELEGRAM_ADMIN_IDS', '')
    if not admin_ids_str:
        print("❌ TELEGRAM_ADMIN_IDS not found in environment variables")
        
        # Try to read directly from .env file if exists
        if os.path.exists('.env'):
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.strip().startswith('TELEGRAM_ADMIN_IDS='):
                            admin_ids_str = line.strip().split('=', 1)[1].strip()
                            print(f"✅ Found admin IDs in .env file: {admin_ids_str}")
                            break
                    else:
                        print("❌ TELEGRAM_ADMIN_IDS not found in .env file")
            except Exception as e:
                print(f"❌ Error reading .env file: {e}")
    else:
        print(f"✅ TELEGRAM_ADMIN_IDS found in environment variables: {admin_ids_str}")
    
    # Parse admin IDs if available
    if admin_ids_str:
        try:
            # Remove brackets if present
            admin_ids_str = admin_ids_str.strip('[]')
            
            # Split by comma and strip whitespace
            admin_ids = [id.strip() for id in admin_ids_str.split(',')]
            
            # Convert to integers
            admin_ids = [int(id) for id in admin_ids if id.strip().isdigit()]
            
            if not admin_ids:
                print("❌ No valid admin IDs found after parsing")
            else:
                print(f"✅ Parsed admin IDs: {admin_ids}")
        except Exception as e:
            print(f"❌ Error parsing admin IDs: {e}")
    
    # Test actual Telegram connection if token is available
    if token:
        try:
            print("\n🔄 Testing connection to Telegram API...")
            
            # Import required telegram libraries
            try:
                from telegram import Bot
                from telegram.error import TelegramError
            except ImportError:
                print("❌ Telegram library not installed. Run: pip install python-telegram-bot")
                return
            
            # Create bot instance and get info (non-async version)
            bot = Bot(token=token)
            
            try:
                # Try non-async method first
                bot_info = bot.get_me()
                print(f"✅ Successfully connected to Telegram API")
                print(f"📊 Bot Information:")
                print(f"   - Username: @{bot_info.username}")
                print(f"   - ID: {bot_info.id}")
                print(f"   - Name: {bot_info.first_name}")
                
                # Test sending message to admin if admin IDs are available (non-async)
                if admin_ids:
                    print("\n🔄 Testing message sending to configured admins...")
                    for admin_id in admin_ids:
                        try:
                            bot.send_message(
                                chat_id=admin_id,
                                text=f"<b>🧪 Test message from AI Football Betting Advisor</b>\n\nIf you can see this message, your Telegram bot configuration is working correctly!",
                                parse_mode="HTML"
                            )
                            print(f"✅ Successfully sent test message to admin ID: {admin_id}")
                        except TelegramError as e:
                            print(f"❌ Failed to send message to admin ID {admin_id}: {e}")
                else:
                    print("⚠️ No admin IDs configured, skipping message sending test")
            except AttributeError:
                print("ℹ️ The installed Telegram library appears to be async-only. Try upgrading or downgrading.")
        
        except Exception as e:
            print(f"❌ Error testing Telegram connection: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Run the Telegram environment test."""
    print("🔍 AI Football Betting Advisor - Telegram Environment Test\n" + "=" * 60)
    
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"📂 Current directory: {current_dir}")
    
    # List files in current directory to help with debugging
    print("\n📄 Files in current directory:")
    try:
        for file in os.listdir(current_dir):
            if file.endswith('.py') or file == '.env':
                print(f"   - {file}")
    except Exception as e:
        print(f"❌ Error listing files: {e}")
    
    # Display python-telegram-bot version if installed
    try:
        import telegram
        print(f"\n📦 python-telegram-bot version: {telegram.__version__}")
    except ImportError:
        print("\n⚠️ python-telegram-bot not installed")
    except AttributeError:
        print("\n⚠️ python-telegram-bot is installed but version cannot be determined")
    
    # Run the test
    test_telegram_connection()
    
    print("\n" + "=" * 60)
    print("🏁 Telegram environment test completed")

if __name__ == "__main__":
    main() 