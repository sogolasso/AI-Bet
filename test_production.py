#!/usr/bin/env python3
"""
Quick test for production mode
"""

import asyncio
import os
from dotenv import load_dotenv
from production_mode import ProductionMode

async def main():
    """Test running production mode for a short time."""
    # Load environment variables
    load_dotenv(override=True)
    print("Environment variables loaded")
    
    # Get token
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    print(f"Token found: {token[:5]}...")
    
    # Get admin IDs
    admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS')
    print(f"Admin IDs found: {admin_ids}")
    
    # Create production mode
    print("Creating production mode instance...")
    production = ProductionMode()
    
    # Run production mode for a short time
    print("Starting production mode (will run for 30 seconds)...")
    try:
        # Setup and send initial message
        await production.setup()
        await production._send_telegram_update("<b>🧪 Test Message</b>\n\nThis is a test of the production mode.")
        
        # Wait for a short time
        print("Waiting for 30 seconds...")
        await asyncio.sleep(30)
    except Exception as e:
        print(f"Error in test: {e}")
    finally:
        # Shutdown
        if production.telegram_bot:
            print("Stopping Telegram bot...")
            await production.telegram_bot.stop()
    
    print("Test completed")

if __name__ == "__main__":
    asyncio.run(main()) 