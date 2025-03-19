import logging
import json
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class MatchCollector:
    """Collects match data from various sources."""
    
    def __init__(self, days_ahead: int = 1, redis_host: str = 'localhost', redis_port: int = 6379):
        """Initialize the match collector.
        
        Args:
            days_ahead: Number of days ahead to look for matches
            redis_host: Redis host for caching
            redis_port: Redis port for caching
        """
        self.days_ahead = days_ahead
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.sources = self._initialize_sources()
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_sources(self) -> List[Dict[str, Any]]:
        """Initialize data sources."""
        return [
            {
                "name": "api_football",
                "type": "api",
                "url": "https://api-football-v1.p.rapidapi.com/v3",
                "priority": 1
            }
        ]
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get the list of configured data sources."""
        return self.sources
    
    async def get_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Get upcoming matches for the configured days ahead."""
        logger.info(f"Fetching upcoming matches for next {self.days_ahead} days")
        
        # Generate mock data for demonstration
        mock_matches = self._generate_mock_upcoming_matches()
        return mock_matches
    
    async def process_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process matches for prediction."""
        logger.info(f"Processing {len(matches)} matches")
        
        processed_matches = []
        for match in matches:
            # Enhance match data for prediction
            processed_match = await self._enhance_match_data(match)
            processed_matches.append(processed_match)
        
        return processed_matches
    
    async def _enhance_match_data(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance match data with additional statistics."""
        # Add mock data
        enhanced_match = match.copy()
        enhanced_match["home_form"] = ["W", "D", "W", "L", "W"]
        enhanced_match["away_form"] = ["L", "W", "D", "D", "W"]
        enhanced_match["h2h"] = []
        enhanced_match["home_stats"] = {"goals_scored": 15, "goals_conceded": 10}
        enhanced_match["away_stats"] = {"goals_scored": 12, "goals_conceded": 14}
        
        return enhanced_match
    
    def _generate_mock_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Generate mock upcoming matches for testing."""
        teams = [
            ("Liverpool", "Premier League"),
            ("Manchester City", "Premier League"),
            ("Arsenal", "Premier League"),
            ("Chelsea", "Premier League")
        ]
        
        matches = []
        now = datetime.now()
        
        # Debug print to show the current date/time
        logger.info(f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Start from today (day=0) instead of tomorrow (day=1)
        for day in range(0, self.days_ahead):
            match_date = now + timedelta(days=day)
            # Debug print to show what date we're generating matches for
            logger.info(f"Generating matches for: {match_date.strftime('%Y-%m-%d')}")
            
            # Generate 2 matches per day
            for i in range(2):
                home_idx = (i * 2) % len(teams)
                away_idx = (i * 2 + 1) % len(teams)
                
                home_team, league = teams[home_idx]
                away_team, _ = teams[away_idx]
                
                # Generate match time - ensure it's future time if it's today
                hour = 15 + (i % 4)
                minute = 0
                
                # If it's today and the hour is in the past, move to a future time
                if day == 0 and hour < now.hour:
                    hour = now.hour + 1
                    minute = 30  # Set to 30 minutes from now if in the current hour
                
                match_time = match_date.replace(hour=hour, minute=minute, second=0)
                
                match = {
                    "id": f"match_{day}_{i+1}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "match_time": match_time.isoformat(),
                    # Add date field for easier filtering
                    "date": match_date.strftime("%Y-%m-%d"),
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
                
                # Debug print for each match
                logger.info(f"Added match: {home_team} vs {away_team} on {match_date.strftime('%Y-%m-%d')} at {hour}:{minute:02d}")
                
                matches.append(match)
        
        return matches
