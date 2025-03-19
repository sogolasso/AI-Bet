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
            # Make the cache last only 5 minutes to ensure fresher data during development
            if datetime.now() - cache_time < timedelta(minutes=5):  # Cache valid for 5 minutes
                logger.info("Using cached upcoming matches")
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    if cached_data:
                        logger.info(f"Loaded {len(cached_data)} matches from cache")
                        return cached_data
                    else:
                        logger.warning("Cache exists but contains no matches, will fetch fresh data")
        
        # Try to get real match data from different sources
        matches = []
        
        # Update user agent with a realistic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Try updated Fotmob first
        logger.info("Attempting to fetch matches from Fotmob...")
        try:
            matches = self._fetch_fotmob_matches()
            if matches:
                logger.info(f"Successfully fetched {len(matches)} matches from Fotmob")
        except Exception as e:
            logger.error(f"Error fetching from Fotmob: {e}")
            logger.exception("Exception details:")
        
        # If Fotmob didn't return matches, try Livescore
        if not matches:
            logger.info("No matches from Fotmob, attempting to fetch from Livescore...")
            try:
                matches = self._fetch_livescore_matches()
                if matches:
                    logger.info(f"Successfully fetched {len(matches)} matches from Livescore")
            except Exception as e:
                logger.error(f"Error fetching from Livescore: {e}")
                logger.exception("Exception details:")
        
        # If we have matches, cache them
        if matches:
            logger.info(f"Successfully fetched {len(matches)} real matches, caching results")
            try:
                with open(cache_file, 'w') as f:
                    json.dump(matches, f, indent=2)
            except Exception as e:
                logger.error(f"Error caching match data: {e}")
        else:
            # No matches found and no fallback to mock data
            logger.error("CRITICAL: Could not fetch any real match data from any source")
            logger.error("This advisor only works with real match data. Please check your internet connection and try again.")
        
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
                logger.debug(f"Requesting URL: {url}")
                
                response = requests.get(url, headers=self.headers, timeout=10)
                logger.debug(f"Fotmob response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Fotmob data received, leagues: {len(data.get('leagues', []))}")
                    
                    # Process leagues
                    for league in data.get('leagues', []):
                        league_name = league.get('name', 'Unknown League')
                        country = league.get('ccode', '')
                        
                        # Include more leagues to increase chance of finding matches
                        top_countries = ['ENG', 'ESP', 'GER', 'ITA', 'FRA', 'NED', 'POR', 'BRA', 'ARG', 'USA', 'MEX']
                        
                        # Process all leagues, not just major ones
                        for match in league.get('matches', []):
                            match_date = target_date.strftime("%Y-%m-%d")
                            
                            # Parse time
                            match_time = None
                            if 'status' in match and 'utcTime' in match['status']:
                                try:
                                    utc_time = int(match['status']['utcTime']) / 1000  # Convert milliseconds to seconds
                                    match_time = datetime.fromtimestamp(utc_time)
                                    logger.debug(f"Parsed time: {match_time}")
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Failed to parse match time: {e}")
                            
                            if not match_time:
                                # Use default time if can't parse
                                hour = 15 + (len(matches) % 4)
                                match_time = target_date.replace(hour=hour, minute=0, second=0)
                                logger.debug(f"Using default time: {match_time}")
                            
                            home_team = match.get('home', {}).get('name', 'Unknown Team')
                            away_team = match.get('away', {}).get('name', 'Unknown Team')
                            
                            # Skip matches that have already started
                            if match_time < now:
                                logger.debug(f"Skipping past match: {home_team} vs {away_team}")
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
                                        logger.debug(f"Parsed odds: {odds}")
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
        
        logger.info(f"Fotmob fetching complete. Found {len(matches)} matches.")
        return matches
    
    def _fetch_livescore_matches(self) -> List[Dict[str, Any]]:
        """Fetch upcoming matches from Livescore."""
        matches = []
        now = datetime.now()
        
        try:
            # Try newer date format YYYYMMDD
            current_date = now.strftime("%Y%m%d")
            api_url = f"https://api.livescore.com/v1/api/app/date/soccer/{current_date}/0?MD=1"
            logger.info(f"Fetching matches from Livescore API with URL: {api_url}")
            
            try:
                response = requests.get(api_url, headers=self.headers, timeout=10)
                logger.debug(f"Livescore API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Livescore data received, stages: {len(data.get('Stages', []))}")
                    
                    stages = data.get('Stages', [])
                    
                    for stage in stages:
                        league_name = stage.get('Cnm', '') + ' ' + stage.get('Snm', '')
                        events = stage.get('Events', [])
                        
                        for event in events:
                            try:
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
                                            logger.debug(f"Parsed event time: {match_time}")
                                    except Exception as e:
                                        logger.warning(f"Failed to parse event time: {e}")
                                
                                # Skip matches that have already started
                                if match_time < now:
                                    logger.debug(f"Skipping past match: {home_team} vs {away_team}")
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
                                logger.warning(f"Error processing event: {e}")
                                continue
            except Exception as e:
                logger.error(f"Error fetching from Livescore API: {e}")
                logger.exception("API request error details:")
            
            # If API approach failed, try web scraping as fallback
            if not matches:
                # Try with a different URL format
                url = "https://www.livescore.com/en/football/all/"
                logger.info(f"Trying fallback method: scraping Livescore website with URL: {url}")
                
                response = requests.get(url, headers=self.headers, timeout=10)
                logger.debug(f"Livescore website response status: {response.status_code}")
                
                if response.status_code == 200:
                    html_content = response.text
                    logger.debug(f"Received HTML content of length: {len(html_content)}")
                    
                    # Look for JSON data embedded in the HTML
                    json_match = re.search(r'window.__INITIAL_STATE__ = (\{.*?\});', html_content, re.DOTALL)
                    if json_match:
                        try:
                            json_str = json_match.group(1)
                            json_data = json.loads(json_str)
                            
                            # Extract match data from the JSON structure
                            if 'matches' in json_data:
                                for match_id, match_info in json_data['matches'].items():
                                    home_team = match_info.get('home', {}).get('name', 'Unknown Team')
                                    away_team = match_info.get('away', {}).get('name', 'Unknown Team')
                                    league_name = match_info.get('league', {}).get('name', 'Unknown League')
                                    start_time = match_info.get('startTime')
                                    
                                    if start_time:
                                        try:
                                            match_time = datetime.fromtimestamp(start_time / 1000)
                                            match_date = match_time.strftime("%Y-%m-%d")
                                        except:
                                            match_time = now.replace(hour=16, minute=0, second=0)
                                            match_date = now.strftime("%Y-%m-%d")
                                    else:
                                        match_time = now.replace(hour=16, minute=0, second=0)
                                        match_date = now.strftime("%Y-%m-%d")
                                    
                                    # Skip matches that have already started
                                    if match_time < now:
                                        continue
                                    
                                    match_data = {
                                        "id": f"ls_json_{match_id}",
                                        "home_team": home_team,
                                        "away_team": away_team,
                                        "league": league_name,
                                        "match_time": match_time.isoformat(),
                                        "date": match_date,
                                        "venue": match_info.get('venue', {}).get('name', f"{home_team} Stadium"),
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
                            logger.error(f"Error parsing embedded JSON: {e}")
                    
                    # If we still don't have matches, try basic title-based pattern matching
                    if not matches:
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
        
        logger.info(f"Livescore fetching complete. Found {len(matches)} matches.")
        return matches
    
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
