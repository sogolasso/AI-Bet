#!/usr/bin/env python3
"""
AI Football Betting Advisor - Setup Script

This script helps initialize the project environment by:
1. Creating required directories
2. Checking dependencies
3. Creating sample configuration if needed
4. Guiding the user through Telegram bot setup
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import pkg_resources
import platform

# Required directories
REQUIRED_DIRS = [
    "data",
    "data/shadow",
    "logs",
    "utils",
    "bot",
    "models"
]

# Required dependencies
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

def print_header():
    """Print a fancy header."""
    print("\n" + "=" * 60)
    print(" " * 15 + "AI FOOTBALL BETTING ADVISOR SETUP")
    print("=" * 60)

def check_python_version():
    """Check if the Python version is compatible."""
    print("\n📊 Checking Python version...")
    major, minor, _ = platform.python_version_tuple()
    
    if int(major) < 3 or (int(major) == 3 and int(minor) < 8):
        print("❌ Error: Python 3.8 or later is required")
        print(f"   Current version: {major}.{minor}")
        print("   Please upgrade your Python installation")
        return False
    
    print(f"✅ Python version {major}.{minor} is compatible")
    return True

def create_directories():
    """Create required directories if they don't exist."""
    print("\n📁 Creating required directories...")
    
    for directory in REQUIRED_DIRS:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {directory}/")
        else:
            print(f"  Already exists: {directory}/")

def check_dependencies():
    """Check and install required dependencies."""
    print("\n📦 Checking dependencies...")
    
    packages_to_install = []
    
    # Check which packages need to be installed
    for package in REQUIRED_PACKAGES:
        package_name = package.split("==")[0]
        try:
            pkg_resources.get_distribution(package_name)
            print(f"  ✅ {package} is already installed")
        except pkg_resources.DistributionNotFound:
            packages_to_install.append(package)
            print(f"  ❌ {package} needs to be installed")
    
    # Install missing packages
    if packages_to_install:
        print("\n⏳ Installing missing packages...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages_to_install)
            print("✅ All packages installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install some packages. Please try installing them manually.")
            print(f"   pip install {' '.join(packages_to_install)}")
            return False
    else:
        print("✅ All required packages are already installed")
    
    return True

def setup_env_file():
    """Create .env file if it doesn't exist or requires updates."""
    env_path = Path(".env")
    
    if env_path.exists():
        print("\n📝 .env file already exists")
        update = input("   Do you want to update it? (y/n): ").lower() == 'y'
        if not update:
            return True
    
    print("\n📝 Setting up .env file...")
    
    # Default environment file content
    env_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
# Replace with your actual Telegram user ID
# Run the get_telegram_id.py script to get your Telegram user ID
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
        print("✅ .env file created successfully")
        
        # Guide for Telegram bot setup
        print("\n🤖 To set up your Telegram bot:")
        print("  1. Talk to @BotFather on Telegram to create a new bot")
        print("  2. Copy the token and update TELEGRAM_BOT_TOKEN in your .env file")
        print("  3. Run the get_telegram_id.py script to get your Telegram user ID")
        print("  4. Add your user ID to TELEGRAM_ADMIN_IDS in your .env file")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def test_telegram_setup():
    """Test if the Telegram setup is working."""
    print("\n🧪 Testing Telegram setup...")
    
    # Check if get_telegram_id.py exists
    if not Path("get_telegram_id.py").exists():
        print("❌ get_telegram_id.py not found")
        return False
    
    print("To get your Telegram user ID:")
    print("  1. Run the following command:")
    print("     python get_telegram_id.py")
    print("  2. Message your bot and it will reply with your user ID")
    print("  3. Add your user ID to TELEGRAM_ADMIN_IDS in your .env file")
    
    run_test = input("\nDo you want to run get_telegram_id.py now? (y/n): ").lower() == 'y'
    if run_test:
        try:
            subprocess.Popen([sys.executable, "get_telegram_id.py"])
            print("✅ get_telegram_id.py is running")
            print("   Message your bot now and it will reply with your user ID")
        except Exception as e:
            print(f"❌ Failed to run get_telegram_id.py: {e}")
            return False
    
    return True

def main():
    """Main setup function."""
    print_header()
    
    if not check_python_version():
        return 1
    
    create_directories()
    
    if not check_dependencies():
        return 1
    
    if not setup_env_file():
        return 1
    
    if not test_telegram_setup():
        return 1
    
    print("\n" + "=" * 60)
    print(" " * 15 + "SETUP COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\n🚀 Your AI Football Betting Advisor is ready to use!")
    print("\nTo run in shadow mode with Telegram integration:")
    
    if platform.system() == "Windows":
        print("  - Windows: run_telegram_shadow.bat")
    else:
        print("  - Linux/macOS: ./run_telegram_shadow.sh")
    
    print("Or with Python:")
    print("  python run_telegram_shadow.py -d 14 -b 1000 -q")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 