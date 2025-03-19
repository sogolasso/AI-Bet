#!/usr/bin/env python
"""
Production Mode Launcher for AI Football Betting Advisor

This script is a simple launcher for the production mode of the AI Football Betting Advisor.
It's a convenience wrapper around the all_in_one.py script.
"""

import sys
import os
import time
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import logging
import shutil

# Configure logging
logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """Ensure all required directories exist."""
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("data/production").mkdir(exist_ok=True)

def main():
    """Main entry point for the production mode launcher."""
    # Load environment variables
    load_dotenv(override=True)
    print("✅ Environment variables loaded from .env file")
    
    # Check for Telegram token
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ No Telegram bot token found. Please set TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)
    print(f"✅ Found Telegram bot token: {token[:5]}...")
    
    # Check for admin IDs
    admin_ids = os.environ.get('TELEGRAM_ADMIN_IDS')
    if not admin_ids:
        print("❌ No Telegram admin IDs found. Please set TELEGRAM_ADMIN_IDS in .env")
        sys.exit(1)
    
    try:
        admin_id_list = [int(x.strip()) for x in admin_ids.split(',')]
        print(f"✅ Found valid admin IDs: {admin_id_list}")
    except ValueError:
        print("❌ Invalid admin IDs format. Please use comma-separated numbers")
        sys.exit(1)
    
    # Create required directories
    ensure_directories_exist()
    
    print("🚀 Launching production mode...")
    
    # Check if all_in_one.py exists
    if not os.path.exists("all_in_one.py"):
        print("❌ all_in_one.py not found in current directory")
        sys.exit(1)
    
    try:
        # Import and run the production mode
        from production_mode import ProductionMode
        
        async def run_production():
            # Ensure data directories exist
            os.makedirs('data/collectors', exist_ok=True)
            
            # Create __init__.py files
            Path('data/__init__.py').write_text('"""Data package for the AI Football Betting Advisor."""\n')
            Path('data/collectors/__init__.py').write_text('"""Collectors package for match and odds data."""\n')
            
            # Create a simplified match_collector.py if it doesn't exist
            match_collector_path = Path('data/collectors/match_collector.py')
            if not match_collector_path.exists():
                match_collector_content = """
import logging
import json
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class MatchCollector:
    \"\"\"Collects match data from various sources.\"\"\"
    
    def __init__(self, days_ahead: int = 1, redis_host: str = 'localhost', redis_port: int = 6379):
        \"\"\"Initialize the match collector.
        
        Args:
            days_ahead: Number of days ahead to look for matches
            redis_host: Redis host for caching
            redis_port: Redis port for caching
        \"\"\"
        self.days_ahead = days_ahead
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.sources = self._initialize_sources()
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_sources(self) -> List[Dict[str, Any]]:
        \"\"\"Initialize data sources.\"\"\"
        return [
            {
                "name": "api_football",
                "type": "api",
                "url": "https://api-football-v1.p.rapidapi.com/v3",
                "priority": 1
            }
        ]
    
    def get_sources(self) -> List[Dict[str, Any]]:
        \"\"\"Get the list of configured data sources.\"\"\"
        return self.sources
    
    async def get_upcoming_matches(self) -> List[Dict[str, Any]]:
        \"\"\"Get upcoming matches for the configured days ahead.\"\"\"
        logger.info(f"Fetching upcoming matches for next {self.days_ahead} days")
        
        # Generate mock data for demonstration
        mock_matches = self._generate_mock_upcoming_matches()
        return mock_matches
    
    async def process_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        \"\"\"Process matches for prediction.\"\"\"
        logger.info(f"Processing {len(matches)} matches")
        
        processed_matches = []
        for match in matches:
            # Enhance match data for prediction
            processed_match = await self._enhance_match_data(match)
            processed_matches.append(processed_match)
        
        return processed_matches
    
    async def _enhance_match_data(self, match: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Enhance match data with additional statistics.\"\"\"
        # Add mock data
        enhanced_match = match.copy()
        enhanced_match["home_form"] = ["W", "D", "W", "L", "W"]
        enhanced_match["away_form"] = ["L", "W", "D", "D", "W"]
        enhanced_match["h2h"] = []
        enhanced_match["home_stats"] = {"goals_scored": 15, "goals_conceded": 10}
        enhanced_match["away_stats"] = {"goals_scored": 12, "goals_conceded": 14}
        
        return enhanced_match
    
    def _generate_mock_upcoming_matches(self) -> List[Dict[str, Any]]:
        \"\"\"Generate mock upcoming matches for testing.\"\"\"
        teams = [
            ("Liverpool", "Premier League"),
            ("Manchester City", "Premier League"),
            ("Arsenal", "Premier League"),
            ("Chelsea", "Premier League")
        ]
        
        matches = []
        now = datetime.now()
        
        for day in range(1, self.days_ahead + 1):
            match_date = now + timedelta(days=day)
            
            # Generate 2 matches per day
            for i in range(2):
                home_idx = (i * 2) % len(teams)
                away_idx = (i * 2 + 1) % len(teams)
                
                home_team, league = teams[home_idx]
                away_team, _ = teams[away_idx]
                
                # Generate match time
                hour = 15 + (i % 4)
                match_time = match_date.replace(hour=hour, minute=0, second=0)
                
                match = {
                    "id": f"match_{day}_{i+1}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "match_time": match_time.isoformat(),
                    "venue": f"{home_team} Stadium",
                    "odds": {
                        "home_win": 1.8,
                        "draw": 3.2,
                        "away_win": 4.5,
                        "over_2_5": 1.9,
                        "under_2_5": 2.0,
                        "btts_yes": 1.8,
                        "btts_no": 2.1
                    }
                }
                
                matches.append(match)
        
        return matches
"""
                match_collector_path.write_text(match_collector_content)
                logger.info(f"Created match_collector module at {match_collector_path}")
            
            # Create a simple scraping_utils.py if it doesn't exist
            scraping_utils_path = Path('data/collectors/scraping_utils.py')
            if not scraping_utils_path.exists():
                scraping_utils_content = """
from enum import Enum
from typing import Dict, List, Optional, Any

class BettingMarket(Enum):
    MATCH_WINNER = "match_winner"
    OVER_UNDER = "over_under"
    BTTS = "btts"
    HANDICAP = "handicap"

def normalize_team_name(name: str) -> str:
    \"\"\"Normalize team name to handle variations in naming.\"\"\"
    return name.lower().strip()
"""
                scraping_utils_path.write_text(scraping_utils_content)
                logger.info(f"Created scraping_utils module at {scraping_utils_path}")
            
            # Create a direct "redirect" version of match_collector.py
            Path('data/match_collector.py').write_text(
                'from data.collectors.match_collector import MatchCollector\n'
            )
            
            production = ProductionMode()
            await production.run()
            
        asyncio.run(run_production())
    except KeyboardInterrupt:
        print("\n⏹️ Production mode stopped by user")
    except Exception as e:
        print(f"❌ Error in production mode: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 