"""
Main configuration settings for the AI Football Betting Advisor.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bettor.db")

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Betting settings
MAX_DAILY_TIPS = 5
MIN_ODDS = 1.5
MAX_ODDS = 10.0
MIN_CONFIDENCE = 0.6

# Bankroll management
INITIAL_BANKROLL = 1000
MAX_STAKE_PERCENTAGE = 5  # Maximum stake as percentage of bankroll
MIN_STAKE = 10  # Minimum stake amount

# Data collection settings
ODDS_UPDATE_INTERVAL = 300  # 5 minutes
MATCH_UPDATE_INTERVAL = 1800  # 30 minutes
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Model settings
PREDICTION_CONFIDENCE_THRESHOLD = 0.7
VALUE_BET_THRESHOLD = 0.05  # Minimum expected value for a bet
MAX_HISTORICAL_MATCHES = 50  # Number of historical matches to consider

# API endpoints (to be implemented)
ODDS_API_URL = "https://api.football-odds.com/v1"
STATS_API_URL = "https://api.football-stats.com/v1"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "logs" / "bettor.log"

# Create necessary directories
for directory in [DATA_DIR, BASE_DIR / "logs"]:
    directory.mkdir(parents=True, exist_ok=True) 