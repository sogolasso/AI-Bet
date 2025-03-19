import logging
import json
import time
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import re

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
        
        # User agent to use in requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def _initialize_sources(self) -> List[Dict[str, Any]]:
        """Initialize data sources."""
        return [
            {
                "name": "sofascore",
                "type": "api",
                "url": "https://api.sofascore.com/api/v1/sport/football/scheduled-events",
                "priority": 1
            },
            {
                "name": "fotmob",
                "type": "api",
                "url": "https://www.fotmob.com/api/matches?date=",
                "priority": 2
            }
        ]
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get the list of configured data sources."""
        return self.sources
    
    async def get_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Get upcoming matches for the configured days ahead."""
        logger.info(f"Fetching upcoming matches for next {self.days_ahead} days")
        
        # Check cache first
        cache_file = self.cache_dir / f"upcoming_matches_{self.days_ahead}.json"
        if cache_file.exists():
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            # Make the cache last only 15 minutes to ensure fresher data during development
            if datetime.now() - cache_time < timedelta(minutes=15):  # Cache valid for 15 minutes
                logger.info("Using cached upcoming matches")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        # Try to get real match data from different sources
        matches = []
        error_occurred = False
        
        try:
            # First try Fotmob
            matches = self._fetch_fotmob_matches()
            
            # If Fotmob didn't return any matches, try Livescore
            if not matches:
                logger.info("No matches from Fotmob, trying Livescore")
                matches = self._fetch_livescore_matches()
            
            # If we still have no matches, log a warning
            if not matches:
                logger.warning("Could not fetch real match data from any source")
                error_occurred = True
        except Exception as e:
            logger.error(f"Error fetching match data: {e}")
            logger.exception("Exception details:")
            error_occurred = True
        
        # Only fall back to mock data if an error occurred or no matches were found
        if error_occurred or not matches:
            logger.warning("Falling back to mock data")
            matches = self._generate_mock_upcoming_matches()
        else:
            logger.info(f"Successfully fetched {len(matches)} real matches")
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(matches, f, indent=2)
        
        return matches
    
    def _fetch_fotmob_matches(self) -> List[Dict[str, Any]]:
        """Fetch upcoming matches from Fotmob."""
        matches = []
        now = datetime.now()
        
        # Get matches for the specified number of days
        for day_offset in range(self.days_ahead + 1):
            target_date = now + timedelta(days=day_offset)
            date_str = target_date.strftime("%Y%m%d")
            
            try:
                url = f"https://www.fotmob.com/api/matches?date={date_str}"
                logger.info(f"Fetching matches from Fotmob for date: {date_str}")
                
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Process leagues
                    for league in data.get('leagues', []):
                        league_name = league.get('name', 'Unknown League')
                        country = league.get('ccode', '')
                        
                        # Filter to major leagues for better quality data
                        major_leagues = [
                            'Premier League', 'LaLiga', 'Bundesliga', 'Serie A', 
                            'Ligue 1', 'Champions League', 'Europa League', 
                            'Conference League', 'World Cup', 'Euro'
                        ]
                        
                        if any(major in league_name for major in major_leagues) or country in ['ENG', 'ESP', 'GER', 'ITA', 'FRA']:
                            for match in league.get('matches', []):
                                match_date = target_date.strftime("%Y-%m-%d")
                                
                                # Parse time
                                match_time = None
                                if 'status' in match and 'utcTime' in match['status']:
                                    try:
                                        utc_time = int(match['status']['utcTime']) / 1000  # Convert milliseconds to seconds
                                        match_time = datetime.fromtimestamp(utc_time)
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Failed to parse match time: {e}")
                                
                                if not match_time:
                                    # Use default time if can't parse
                                    hour = 15 + (len(matches) % 4)
                                    match_time = target_date.replace(hour=hour, minute=0, second=0)
                                
                                home_team = match.get('home', {}).get('name', 'Unknown Team')
                                away_team = match.get('away', {}).get('name', 'Unknown Team')
                                
                                # Skip matches that have already started
                                if match_time < now:
                                    continue
                                
                                # Get odds if available
                                odds = {
                                    "home_win": 0,
                                    "draw": 0,
                                    "away_win": 0,
                                    "over_2_5": 0,
                                    "under_2_5": 0,
                                    "btts_yes": 0,
                                    "btts_no": 0
                                }
                                
                                try:
                                    if 'odds' in match and '1x2' in match['odds']:
                                        odds_data = match['odds']['1x2']
                                        if isinstance(odds_data, list) and len(odds_data) >= 3:
                                            odds["home_win"] = float(odds_data[0])
                                            odds["draw"] = float(odds_data[1])
                                            odds["away_win"] = float(odds_data[2])
                                except Exception as e:
                                    logger.warning(f"Error parsing odds: {e}")
                                
                                match_data = {
                                    "id": str(match.get('id', f"{day_offset}_{len(matches)}")),
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "league": f"{league_name}",
                                    "match_time": match_time.isoformat(),
                                    "date": match_date,
                                    "venue": match.get('venue', {}).get('name', f"{home_team} Stadium"),
                                    "odds": odds
                                }
                                
                                logger.info(f"Found match: {home_team} vs {away_team} on {match_date} at {match_time.strftime('%H:%M')}")
                                matches.append(match_data)
            except Exception as e:
                logger.error(f"Error fetching from Fotmob for date {date_str}: {e}")
                logger.exception("Exception details:")
        
        # Check if we actually got any matches
        if matches:
            logger.info(f"Successfully fetched {len(matches)} matches from Fotmob")
            return matches
        else:
            logger.warning("No matches found from Fotmob")
            return []
    
    def _fetch_livescore_matches(self) -> List[Dict[str, Any]]:
        """Fetch upcoming matches from Livescore."""
        matches = []
        now = datetime.now()
        
        try:
            # Try to fetch from the API first (newer approach)
            api_url = "https://api.livescore.com/v1/api/app/date/soccer/20230316/0?MD=1"
            logger.info(f"Fetching matches from Livescore API")
            
            try:
                response = requests.get(api_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    stages = data.get('Stages', [])
                    
                    for stage in stages:
                        league_name = stage.get('Cnm', '') + ' ' + stage.get('Snm', '')
                        events = stage.get('Events', [])
                        
                        for event in events:
                            home_team = event.get('T1', [{}])[0].get('Nm', 'Unknown Team')
                            away_team = event.get('T2', [{}])[0].get('Nm', 'Unknown Team')
                            
                            # Parse time
                            event_time_str = event.get('Esd', '')
                            match_time = now.replace(hour=16, minute=0, second=0)  # Default time
                            match_date = now.strftime("%Y-%m-%d")
                            
                            if event_time_str:
                                try:
                                    # Format is usually like "/Date(1679169600000)/"
                                    time_match = re.search(r'\((\d+)\)', event_time_str)
                                    if time_match:
                                        timestamp = int(time_match.group(1)) / 1000
                                        dt = datetime.fromtimestamp(timestamp)
                                        match_time = dt
                                        match_date = dt.strftime("%Y-%m-%d")
                                except Exception as e:
                                    logger.warning(f"Failed to parse event time: {e}")
                            
                            # Skip matches that have already started
                            if match_time < now:
                                continue
                                
                            match_data = {
                                "id": f"ls_api_{event.get('Eid', len(matches))}",
                                "home_team": home_team,
                                "away_team": away_team,
                                "league": league_name,
                                "match_time": match_time.isoformat(),
                                "date": match_date,
                                "venue": event.get('Stnm', f"{home_team} Stadium"),
                                "odds": {
                                    "home_win": 0,
                                    "draw": 0,
                                    "away_win": 0,
                                    "over_2_5": 0,
                                    "under_2_5": 0,
                                    "btts_yes": 0,
                                    "btts_no": 0
                                }
                            }
                            
                            logger.info(f"Found match: {home_team} vs {away_team} on {match_date} at {match_time.strftime('%H:%M')}")
                            matches.append(match_data)
            except Exception as e:
                logger.error(f"Error fetching from Livescore API: {e}")
                logger.exception("API request error details:")
            
            # If API approach failed, try web scraping as fallback
            if not matches:
                url = "https://www.livescore.com/en/football/"
                logger.info(f"Trying fallback method: scraping Livescore website")
                
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Very basic scraping - look for title patterns that usually indicate matches
                    match_titles = re.findall(r'<title>(.+?) vs (.+?) - (\d{1,2}/\d{1,2}/\d{2,4})', html_content)
                    
                    for idx, (home, away, date_str) in enumerate(match_titles):
                        # Parse date (assuming DD/MM/YYYY format)
                        try:
                            day, month, year = map(int, date_str.split('/'))
                            if year < 100:
                                year += 2000  # Convert 2-digit year to 4-digit
                            
                            match_date = datetime(year, month, day)
                            date_str = match_date.strftime("%Y-%m-%d")
                            
                            # Default time
                            match_time = match_date.replace(hour=15 + (idx % 4), minute=0, second=0)
                            
                            # Skip matches that have already started
                            if match_time < now:
                                continue
                                
                            match_data = {
                                "id": f"ls_web_{idx}",
                                "home_team": home,
                                "away_team": away,
                                "league": "Unknown League",
                                "match_time": match_time.isoformat(),
                                "date": date_str,
                                "venue": f"{home} Stadium",
                                "odds": {
                                    "home_win": 0,
                                    "draw": 0,
                                    "away_win": 0,
                                    "over_2_5": 0,
                                    "under_2_5": 0,
                                    "btts_yes": 0,
                                    "btts_no": 0
                                }
                            }
                            
                            logger.info(f"Found match: {home} vs {away} on {date_str} at {match_time.strftime('%H:%M')}")
                            matches.append(match_data)
                        except Exception as e:
                            logger.warning(f"Error parsing match date: {e}")
        except Exception as e:
            logger.error(f"Error fetching from Livescore: {e}")
            logger.exception("Exception details:")
        
        # Check if we actually got any matches
        if matches:
            logger.info(f"Successfully fetched {len(matches)} matches from Livescore")
            return matches
        else:
            logger.warning("No matches found from Livescore")
            return []
    
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
        # Add realistic data
        enhanced_match = match.copy()
        
        # Generate random but realistic form (more wins than losses for better teams)
        home_team = match['home_team'].lower()
        away_team = match['away_team'].lower()
        
        # List of top teams that should have better form
        top_teams = ['manchester city', 'liverpool', 'arsenal', 'barcelona', 'real madrid', 
                      'bayern', 'paris', 'psg', 'inter', 'juventus', 'chelsea', 'atletico',
                      'dortmund', 'milan', 'napoli', 'leipzig']
        
        # Generate more realistic form based on team strength
        home_form = self._generate_realistic_form(home_team, top_teams)
        away_form = self._generate_realistic_form(away_team, top_teams)
        
        enhanced_match["home_form"] = home_form
        enhanced_match["away_form"] = away_form
        enhanced_match["h2h"] = []
        
        # Generate realistic team stats
        home_stats = self._generate_realistic_stats(home_team, top_teams)
        away_stats = self._generate_realistic_stats(away_team, top_teams)
        
        enhanced_match["home_stats"] = home_stats
        enhanced_match["away_stats"] = away_stats
        
        return enhanced_match
    
    def _generate_realistic_form(self, team_name: str, top_teams: List[str]) -> List[str]:
        """Generate realistic form for a team based on its perceived strength."""
        import random
        
        # Check if this is a top team
        is_top_team = any(top in team_name.lower() for top in top_teams)
        
        if is_top_team:
            # Top teams win more
            weights = [0.6, 0.25, 0.15]  # W, D, L
        else:
            # Regular teams have more balanced results
            weights = [0.4, 0.3, 0.3]  # W, D, L
        
        # Generate last 5 results
        return random.choices(["W", "D", "L"], weights=weights, k=5)
    
    def _generate_realistic_stats(self, team_name: str, top_teams: List[str]) -> Dict[str, Any]:
        """Generate realistic stats for a team based on its perceived strength."""
        import random
        
        # Check if this is a top team
        is_top_team = any(top in team_name.lower() for top in top_teams)
        
        if is_top_team:
            # Top teams score more, concede less
            goals_scored = random.randint(15, 35)
            goals_conceded = random.randint(5, 20)
        else:
            # Regular teams have more balanced stats
            goals_scored = random.randint(10, 25)
            goals_conceded = random.randint(15, 30)
        
        return {
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded
        }
    
    def _generate_mock_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Generate mock upcoming matches for testing."""
        logger.warning("Using MOCK match data - for development only!")
        
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
            logger.info(f"Generating mock matches for: {match_date.strftime('%Y-%m-%d')}")
            
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
                logger.info(f"Added mock match: {home_team} vs {away_team} on {match_date.strftime('%Y-%m-%d')} at {hour}:{minute:02d}")
                
                matches.append(match)
        
        return matches
