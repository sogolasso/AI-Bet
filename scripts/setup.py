#!/usr/bin/env python3
"""
Setup Script for AI Football Betting Advisor

This script performs initial setup for the project, including:
1. Creating required directories
2. Validating Python version
3. Checking for required system dependencies
4. Setting up minimal configuration files if they don't exist
"""

import os
import sys
import shutil
import platform
import argparse
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_project_root():
    """Get the project root directory."""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

def create_directory_structure():
    """Create the required directory structure for the project."""
    project_root = get_project_root()
    
    # Define required directories
    directories = [
        "data",
        "data/logs",
        "data/reports",
        "data/cache",
        "data/shadow",
        "data/shadow/reports",
        "logs",
        "bot",
        "models",
        "betting",
        "data",
        "tests",
    ]
    
    # Create each directory if it doesn't exist
    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            logger.info(f"Creating directory: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"Directory already exists: {dir_path}")
    
    logger.info("Directory structure created successfully")

def check_python_version():
    """Check if the Python version meets requirements."""
    logger.info("Checking Python version...")
    
    min_version = (3, 11, 0)
    current_version = sys.version_info
    
    if current_version >= min_version:
        logger.info(f"Python version {'.'.join(map(str, current_version[:3]))} meets requirements")
        return True
    else:
        logger.error(f"Python version {'.'.join(map(str, current_version[:3]))} is below minimum required version {'.'.join(map(str, min_version))}")
        return False

def check_system_dependencies():
    """Check if required system dependencies are installed."""
    logger.info("Checking system dependencies...")
    
    dependencies = []
    missing_dependencies = []
    
    # Add system-specific dependency checks
    if platform.system() == "Linux":
        dependencies.extend(["gcc", "g++", "libffi-dev"])
    elif platform.system() == "Darwin":  # macOS
        dependencies.extend(["gcc", "libffi"])
    elif platform.system() == "Windows":
        # On Windows we typically don't check for system dependencies
        # as they're often bundled with Python packages
        pass
    
    # Check each dependency
    for dependency in dependencies:
        try:
            subprocess.run(["which", dependency], 
                           check=True, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            logger.debug(f"Dependency found: {dependency}")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning(f"Missing dependency: {dependency}")
            missing_dependencies.append(dependency)
    
    if missing_dependencies:
        logger.error(f"Missing system dependencies: {', '.join(missing_dependencies)}")
        # Provide installation instructions
        if platform.system() == "Linux":
            logger.info("Install missing dependencies with: sudo apt-get install " + " ".join(missing_dependencies))
        elif platform.system() == "Darwin":
            logger.info("Install missing dependencies with: brew install " + " ".join(missing_dependencies))
        return False
    else:
        logger.info("All system dependencies are installed")
        return True

def create_env_file():
    """Create a .env file if it doesn't exist."""
    project_root = get_project_root()
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if env_file.exists():
        logger.info(".env file already exists")
        return
    
    if env_example.exists():
        logger.info("Creating .env file from .env.example")
        shutil.copy(env_example, env_file)
        logger.info("Created .env file. Please edit it with your configuration.")
    else:
        logger.warning(".env.example not found, creating basic .env file")
        with open(env_file, "w") as f:
            f.write("""# AI Football Betting Advisor Configuration

# Bankroll settings
BANKROLL=1000.0
MAX_STAKE_PERCENT=5.0
MIN_STAKE_PERCENT=0.5

# Betting parameters
DAYS_AHEAD=1
MIN_ODDS=1.5
MAX_ODDS=10.0
MIN_EV_THRESHOLD=0.05

# Telegram Bot settings
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Redis settings (optional)
# REDIS_HOST=localhost
# REDIS_PORT=6379

# Operation mode
DRY_RUN=true
""")
        logger.info("Created basic .env file. Please edit it with your configuration.")

def check_python_dependencies():
    """Check if Python dependencies are installed."""
    logger.info("Checking Python dependencies...")
    
    project_root = get_project_root()
    requirements_file = project_root / "requirements.txt"
    
    if not requirements_file.exists():
        logger.error("requirements.txt not found")
        return False
    
    try:
        # Try to import some critical packages
        import pandas
        import numpy
        import requests
        import dotenv
        
        logger.info("Critical Python dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"Missing Python dependency: {e}")
        logger.info("Install Python dependencies with: pip install -r requirements.txt")
        return False

def main():
    """Main entry point for setup script."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor Setup Utility')
    parser.add_argument('--skip-checks', action='store_true', help='Skip dependency checks')
    parser.add_argument('--force-env', action='store_true', help='Force creation of .env file even if it exists')
    
    args = parser.parse_args()
    
    logger.info("Starting AI Football Betting Advisor setup...")
    
    # Create directory structure
    create_directory_structure()
    
    # Check Python version and dependencies if not skipped
    if not args.skip_checks:
        python_version_ok = check_python_version()
        system_deps_ok = check_system_dependencies()
        python_deps_ok = check_python_dependencies()
        
        if not (python_version_ok and system_deps_ok and python_deps_ok):
            logger.warning("Some checks failed. Review the logs and fix the issues before proceeding.")
    
    # Create .env file if it doesn't exist or if forced
    if args.force_env:
        # Remove existing .env file if it exists
        env_file = get_project_root() / ".env"
        if env_file.exists():
            logger.info("Removing existing .env file")
            env_file.unlink()
    
    create_env_file()
    
    logger.info("Setup complete!")
    logger.info("Next steps:")
    logger.info("1. Edit the .env file with your configuration")
    logger.info("2. Run the deployment checklist: python tests/deployment_checklist.py")
    logger.info("3. Start the application: python main.py")

if __name__ == "__main__":
    main() 