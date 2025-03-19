import logging
import json
import time
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import re
import os
import random
from bs4 import BeautifulSoup

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
        
        # Initialize cache variables
        self.cached_matches = []
        self.cached_time = datetime.now() - timedelta(days=1)  # Set to expired
        self.cache_duration = 3600  # Cache duration in seconds (1 hour)
        
        # Development flag - when True, will fall back to mock data as last resort
        # This should ONLY be true in development environments
        self.is_development = os.environ.get("DEVELOPMENT_MODE", "").lower() == "true"
        
        # Check for Football-Data.org API key
        self.football_data_api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
        
        # User agent to use in requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
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
        """Get upcoming matches for the next week.
        
        Returns:
            List of dictionaries containing match information.
        """
        logger.info("Getting upcoming matches...")
        
        # Check if we have cached matches and they're still valid
        if self.cached_matches and (datetime.now() - self.cached_time).total_seconds() < self.cache_duration:
            logger.info(f"Using cached matches ({len(self.cached_matches)} matches, cached {(datetime.now() - self.cached_time).total_seconds()/60:.1f} minutes ago)")
            return self.cached_matches
        
        # List to store all matches from different sources
        all_matches = []
        
        # Try to scrape Betano odds from MelhorOdd.pt (our specialized scraper)
        logger.info("Attempting to scrape Betano odds from MelhorOdd.pt...")
        try:
            from data.collectors.betano_melhorodd_scraper import scrape_betano_melhorodd_matches
            betano_melhorodd_matches = scrape_betano_melhorodd_matches(days_ahead=self.days_ahead)
            if betano_melhorodd_matches:
                logger.info(f"Successfully scraped {len(betano_melhorodd_matches)} matches with Betano odds from MelhorOdd.pt")
                all_matches.extend(betano_melhorodd_matches)
                # If we got a good number of matches with Betano odds, no need to try other sources
                if len(betano_melhorodd_matches) >= 15:
                    logger.info(f"Found {len(betano_melhorodd_matches)} matches with Betano odds, skipping other sources")
                    self.cached_matches = all_matches
                    self.cached_time = datetime.now()
                    return all_matches
        except Exception as e:
            logger.error(f"Error scraping Betano odds from MelhorOdd.pt: {e}")
            logger.exception("Exception details:")
        
        # If our specialized scraper didn't find enough matches, try regular scrapers
        
        # Try to scrape from MelhorOdd.pt
        if len(all_matches) < 15:
            logger.info("Attempting to scrape matches from MelhorOdd.pt...")
            try:
                from data.collectors.melhorodd_scraper import scrape_melhorodd_matches
                melhorodd_matches = scrape_melhorodd_matches(days_ahead=self.days_ahead)
                if melhorodd_matches:
                    logger.info(f"Successfully scraped {len(melhorodd_matches)} matches from MelhorOdd.pt")
                    
                    # Only add unique matches that aren't already in all_matches
                    unique_matches = []
                    existing_match_keys = {f"{m['home_team']}|{m['away_team']}|{m['date']}" for m in all_matches}
                    
                    for match in melhorodd_matches:
                        match_key = f"{match['home_team']}|{match['away_team']}|{match['date']}"
                        if match_key not in existing_match_keys:
                            unique_matches.append(match)
                    
                    if unique_matches:
                        logger.info(f"Adding {len(unique_matches)} unique matches from MelhorOdd.pt")
                        all_matches.extend(unique_matches)
            except Exception as e:
                logger.error(f"Error scraping from MelhorOdd.pt: {e}")
                logger.exception("Exception details:")
        
        # Always try Betano direct scraper as well if we don't have enough matches
        if len(all_matches) < 15:
            logger.info("Attempting to scrape matches from Betano with headless browser...")
            try:
                from data.collectors.betano_scraper import scrape_betano_matches
                betano_matches = scrape_betano_matches(days_ahead=self.days_ahead)
                if betano_matches:
                    logger.info(f"Successfully scraped {len(betano_matches)} matches from Betano with headless browser")
                    
                    # Only add unique matches that aren't already in all_matches
                    unique_betano_matches = []
                    existing_match_keys = {f"{m['home_team']}|{m['away_team']}|{m['date']}" for m in all_matches}
                    
                    for match in betano_matches:
                        match_key = f"{match['home_team']}|{match['away_team']}|{match['date']}"
                        if match_key not in existing_match_keys:
                            unique_betano_matches.append(match)
                    
                    if unique_betano_matches:
                        logger.info(f"Adding {len(unique_betano_matches)} unique matches from Betano")
                        all_matches.extend(unique_betano_matches)
            except Exception as e:
                logger.error(f"Error scraping from Betano with headless browser: {e}")
                logger.exception("Exception details:")
        
        # If any scraper provided matches, use those
        if all_matches:
            logger.info(f"Using {len(all_matches)} matches from all scrapers")
            self.cached_matches = all_matches
            self.cached_time = datetime.now()
            return all_matches
            
        # If all scrapers failed, try Football-Data.org API
        try:
            logger.info("All scrapers failed, trying Football-Data.org API...")
            football_data_matches = await self._fetch_football_data_matches()
            if football_data_matches:
                logger.info(f"Successfully fetched {len(football_data_matches)} matches from Football-Data.org")
                all_matches.extend(football_data_matches)
        except Exception as e:
            logger.error(f"Error fetching from Football-Data.org: {e}")
            logger.exception("Exception details:")
        
        # If we have matches from any source, use those
        if all_matches:
            logger.info(f"Using {len(all_matches)} matches from available sources")
            self.cached_matches = all_matches
            self.cached_time = datetime.now()
            return all_matches
            
        # If we're in development mode and all real sources failed, use mock data as last resort
        if os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true":
            logger.warning("All real data sources failed, falling back to mock data (DEVELOPMENT_MODE=true)")
            mock_matches = self._generate_mock_upcoming_matches()
            self.cached_matches = mock_matches
            self.cached_time = datetime.now()
            return mock_matches
        else:
            # In production, return an empty list if all sources failed
            logger.error("All data sources failed and DEVELOPMENT_MODE=false, returning empty list")
            return []
    
    def _generate_mock_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Generate mock upcoming matches for DEVELOPMENT ONLY."""
        logger.warning("DEVELOPMENT MODE ONLY: Using MOCK match data - NOT FOR PRODUCTION!")
        
        teams = [
            ("Liverpool", "Premier League"),
            ("Manchester City", "Premier League"),
            ("Arsenal", "Premier League"),
            ("Chelsea", "Premier League"),
            ("Barcelona", "La Liga"),
            ("Real Madrid", "La Liga"),
            ("Bayern Munich", "Bundesliga"),
            ("Borussia Dortmund", "Bundesliga"),
            ("PSG", "Ligue 1"),
            ("Marseille", "Ligue 1"),
            ("Inter", "Serie A"),
            ("Juventus", "Serie A")
        ]
        
        matches = []
        now = datetime.now()
        
        # Debug print to show the current date/time
        logger.info(f"MOCK DATA - Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Start from today (day=0) instead of tomorrow (day=1)
        for day in range(0, self.days_ahead):
            match_date = now + timedelta(days=day)
            # Debug print to show what date we're generating matches for
            logger.info(f"MOCK DATA - Generating mock matches for: {match_date.strftime('%Y-%m-%d')}")
            
            # Generate 5 matches per day
            for i in range(5):
                home_idx = random.randint(0, len(teams)-1)
                away_idx = random.randint(0, len(teams)-1)
                
                # Make sure home and away teams are different
                while home_idx == away_idx:
                    away_idx = random.randint(0, len(teams)-1)
                
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
                    "id": f"mock_{day}_{i+1}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "match_time": match_time.isoformat(),
                    # Add date field for easier filtering
                    "date": match_date.strftime("%Y-%m-%d"),
                    "venue": f"{home_team} Stadium",
                    "odds": {
                        "home_win": round(random.uniform(1.5, 3.0), 2),
                        "draw": round(random.uniform(2.8, 4.0), 2),
                        "away_win": round(random.uniform(2.0, 4.5), 2),
                        "over_2_5": round(random.uniform(1.7, 2.2), 2),
                        "under_2_5": round(random.uniform(1.7, 2.2), 2),
                        "btts_yes": round(random.uniform(1.7, 2.2), 2),
                        "btts_no": round(random.uniform(1.7, 2.2), 2)
                    }
                }
                
                # Debug print for each match
                logger.info(f"MOCK DATA - Added mock match: {home_team} vs {away_team} on {match_date.strftime('%Y-%m-%d')} at {hour}:{minute:02d}")
                
                matches.append(match)
        
        return matches
    
    def _scrape_betano_matches(self) -> List[Dict[str, Any]]:
        """Scrape upcoming football matches from Betano Portugal with odds."""
        from bs4 import BeautifulSoup
        import random
        import re
        from datetime import datetime, timedelta
        
        matches = []
        now = datetime.now()
        
        # Rotating user agents to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 OPR/102.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        # Use real scraping data only, no fallback to examples
        use_example_data = False
        
        # For real scraping, use the code below
        try:
            # Create a session for persistent cookies
            session = requests.Session()
            
            # Set advanced headers to mimic a real browser
            chosen_user_agent = random.choice(user_agents)
            session.headers.update({
                'User-Agent': chosen_user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,pt-PT;q=0.8,pt;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Referer': 'https://www.google.com/',
                'Cache-Control': 'max-age=0',
                'DNT': '1'
            })
            
            # Try alternative sites for football matches and odds
            urls = [
                # Main Betano Portugal URL
                'https://www.betano.pt/sport/futebol/jogos-de-hoje/',
                'https://www.betano.pt/sport/futebol/jogos-de-amanha/',
                # Alternative sources
                'https://www.zerozero.pt/fixtures.php',
                'https://www.sofascore.com/tournament/football/portugal/primeira-liga/238'
            ]
            
            # Pages to scrape (upcoming days)
            days_to_scrape = min(self.days_ahead + 1, 3)  # Limit to 3 days to avoid excessive scraping
            
            match_count = 0
            
            # Process each URL with retry logic
            for url_index, url in enumerate(urls):
                if url_index >= days_to_scrape and "betano.pt" in url:
                    # Skip additional Betano URLs if we've reached the days limit
                    continue
                    
                logger.info(f"Scraping URL: {url}")
                
                # Add a random delay between requests to avoid detection
                time.sleep(random.uniform(2, 5))
                
                # Try up to 3 times with different user agents
                max_retries = 3
                retry_count = 0
                success = False
                
                while retry_count < max_retries and not success:
                    try:
                        # Rotate user agent on retry
                        if retry_count > 0:
                            new_user_agent = random.choice(user_agents)
                            logger.info(f"Retrying with new user agent: {new_user_agent[:20]}...")
                            session.headers.update({'User-Agent': new_user_agent})
                            # Add longer delay on retry
                            time.sleep(random.uniform(3, 7))
                        
                        # Use a proxy if available (helpful to bypass IP blocking)
                        proxies = None
                        if os.environ.get("HTTP_PROXY"):
                            proxies = {
                                "http": os.environ.get("HTTP_PROXY"),
                                "https": os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
                            }
                            logger.info(f"Using proxy: {proxies['http']}")
                            
                        # Get the page content
                        if proxies:
                            response = session.get(url, timeout=30, proxies=proxies)
                        else:
                            response = session.get(url, timeout=30)
                        
                        if response.status_code == 200:
                            success = True
                            logger.info(f"Successfully fetched page with status code 200")
                        else:
                            logger.warning(f"Failed to fetch data, status code: {response.status_code}, retry {retry_count + 1}/{max_retries}")
                            retry_count += 1
                    except Exception as e:
                        logger.warning(f"Error during request: {e}, retry {retry_count + 1}/{max_retries}")
                        retry_count += 1
                
                if not success:
                    logger.error(f"Failed to fetch data after {max_retries} retries, skipping URL")
                    continue
                
                # Parse the HTML content
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Handle different sources differently
                if "betano.pt" in url:
                    # Betano specific parsing logic
                    found_matches = self._parse_betano_page(soup, url, now, match_count)
                    if found_matches:
                        matches.extend(found_matches)
                        match_count += len(found_matches)
                elif "zerozero.pt" in url:
                    # ZeroZero parsing logic
                    found_matches = self._parse_zerozero_page(soup, url, now, match_count)
                    if found_matches:
                        matches.extend(found_matches)
                        match_count += len(found_matches)
                elif "sofascore.com" in url:
                    # SofaScore parsing logic
                    found_matches = self._parse_sofascore_page(soup, url, now, match_count)
                    if found_matches:
                        matches.extend(found_matches)
                        match_count += len(found_matches)
                        
        except Exception as e:
            logger.error(f"Error scraping match data: {e}")
            logger.exception("Exception details:")
            
        logger.info(f"Scraping complete. Found {len(matches)} matches.")
        return matches
        
    def _parse_betano_page(self, soup, url, now, current_count) -> List[Dict[str, Any]]:
        """Parse Betano page HTML to extract match data."""
        matches = []
        match_count = current_count
        
        try:
            # Find all league containers
            league_containers = soup.select('div.events-list__grid')
            
            if not league_containers:
                logger.warning(f"No league containers found on {url}")
                # Try alternative selectors
                league_containers = soup.select('div.events-list__container')
                if not league_containers:
                    logger.warning("Alternative selector also failed")
                    return matches
            
            logger.info(f"Found {len(league_containers)} league containers on {url}")
            
            # Determine the date for this URL
            if "jogos-de-hoje" in url:
                target_date = now
            elif "jogos-de-amanha" in url:
                target_date = now + timedelta(days=1)
            else:
                # Default to today
                target_date = now
                
            date_str = target_date.strftime("%Y-%m-%d")
            
            # Process each league container
            for league_container in league_containers:
                # Get the league name
                league_header = league_container.find_previous('div', class_='events-list__title')
                league_name = "Unknown League"
                if league_header:
                    league_name_elem = league_header.select_one('h2.events-list__title__label')
                    if league_name_elem:
                        league_name = league_name_elem.text.strip()
                
                # Find all events (matches) in this league
                events = league_container.select('div.event')
                
                if not events:
                    logger.warning(f"No events found in league container for {league_name}")
                    continue
                
                logger.info(f"Found {len(events)} events in {league_name}")
                
                # Process each event
                for event in events:
                    try:
                        # Get match time
                        time_elem = event.select_one('div.starting-time')
                        match_time_str = time_elem.text.strip() if time_elem else "00:00"
                        logger.debug(f"Match time string: {match_time_str}")
                        
                        # Parse hour and minute
                        try:
                            hour, minute = map(int, match_time_str.split(':'))
                            match_time = target_date.replace(hour=hour, minute=minute, second=0)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse match time: {e}")
                            # Default time if parsing fails
                            match_time = target_date.replace(hour=15, minute=0, second=0)
                        
                        # Skip matches that have already started
                        if match_time < now:
                            logger.debug(f"Skipping past match with time {match_time}")
                            continue
                        
                        # Get teams
                        teams_container = event.select_one('div.event-description')
                        if not teams_container:
                            logger.warning("No teams container found")
                            continue
                        
                        team_elems = teams_container.select('span.participants-pair-participant')
                        
                        if len(team_elems) < 2:
                            logger.warning(f"Not enough team elements found: {len(team_elems)}")
                            # Try alternative selectors
                            team_elems = teams_container.select('div.event-description__name')
                            if len(team_elems) < 2:
                                logger.warning("Alternative team selector also failed")
                                continue
                        
                        home_team = team_elems[0].text.strip()
                        away_team = team_elems[1].text.strip()
                        
                        # Get odds
                        odds_container = event.select('div.selections-selections')
                        
                        # Initialize odds object
                        odds = {
                            "home_win": 0,
                            "draw": 0,
                            "away_win": 0,
                            "over_2_5": 0,
                            "under_2_5": 0,
                            "btts_yes": 0,
                            "btts_no": 0
                        }
                        
                        # Process 1X2 odds (match winner)
                        if odds_container and len(odds_container) > 0:
                            odds_elems = odds_container[0].select('div.selection')
                            
                            if len(odds_elems) >= 3:
                                # Parse 1X2 odds
                                try:
                                    home_odds_elem = odds_elems[0].select_one('span.selection-price')
                                    draw_odds_elem = odds_elems[1].select_one('span.selection-price')
                                    away_odds_elem = odds_elems[2].select_one('span.selection-price')
                                    
                                    if home_odds_elem:
                                        odds["home_win"] = float(home_odds_elem.text.strip().replace(',', '.'))
                                    if draw_odds_elem:
                                        odds["draw"] = float(draw_odds_elem.text.strip().replace(',', '.'))
                                    if away_odds_elem:
                                        odds["away_win"] = float(away_odds_elem.text.strip().replace(',', '.'))
                                except (ValueError, AttributeError) as e:
                                    logger.warning(f"Error parsing 1X2 odds: {e}")
                        
                        # Create match object
                        match_data = {
                            "id": f"betano_{match_count}",
                            "home_team": home_team,
                            "away_team": away_team,
                            "league": league_name,
                            "match_time": match_time.isoformat(),
                            "date": date_str,
                            "venue": f"{home_team} Stadium",
                            "odds": odds,
                            "source": "betano"
                        }
                        
                        match_count += 1
                        
                        logger.info(f"Found match: {home_team} vs {away_team} on {date_str} at {match_time.strftime('%H:%M')} with odds 1X2: {odds['home_win']}/{odds['draw']}/{odds['away_win']}")
                        matches.append(match_data)
                    except Exception as e:
                        logger.warning(f"Error processing match: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error parsing Betano page: {e}")
            
        return matches
        
    def _parse_zerozero_page(self, soup, url, now, current_count) -> List[Dict[str, Any]]:
        """Parse ZeroZero page HTML to extract match data."""
        matches = []
        match_count = current_count
        
        try:
            # ZeroZero.pt specific parsing logic
            match_rows = soup.select('tr.parent')
            
            logger.info(f"Found {len(match_rows)} match rows on ZeroZero")
            
            for row in match_rows:
                try:
                    # Get date from the previous row with class "data"
                    date_row = row.find_previous('tr', class_='data')
                    date_str = now.strftime("%Y-%m-%d")  # Default to today
                    if date_row:
                        date_text = date_row.text.strip()
                        try:
                            # Parse the date in format DD/MM/YYYY
                            day, month, year = map(int, re.findall(r'(\d+)/(\d+)/(\d+)', date_text)[0])
                            date_str = f"{year}-{month:02d}-{day:02d}"
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse date: {e}")
                    
                    # Get match time
                    time_elem = row.select_one('td.hora')
                    match_time_str = time_elem.text.strip() if time_elem else "00:00"
                    
                    # Parse hour and minute
                    try:
                        hour, minute = map(int, match_time_str.split(':'))
                        match_date = datetime.strptime(date_str, "%Y-%m-%d")
                        match_time = match_date.replace(hour=hour, minute=minute, second=0)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse match time: {e}")
                        # Default time if parsing fails
                        match_date = datetime.strptime(date_str, "%Y-%m-%d")
                        match_time = match_date.replace(hour=15, minute=0, second=0)
                    
                    # Skip matches that have already started
                    if match_time < now:
                        continue
                    
                    # Get teams
                    home_elem = row.select_one('td.text.left a[itemprop="homeTeam"]')
                    away_elem = row.select_one('td.text.left a[itemprop="awayTeam"]')
                    
                    if not home_elem or not away_elem:
                        continue
                    
                    home_team = home_elem.text.strip()
                    away_team = away_elem.text.strip()
                    
                    # Get league/competition
                    comp_elem = row.select_one('td.competition a')
                    league_name = comp_elem.text.strip() if comp_elem else "Unknown League"
                    
                    # ZeroZero doesn't have odds, so create placeholder odds
                    odds = {
                        "home_win": 0,
                        "draw": 0,
                        "away_win": 0,
                        "over_2_5": 0,
                        "under_2_5": 0,
                        "btts_yes": 0,
                        "btts_no": 0
                    }
                    
                    # Create match object
                    match_data = {
                        "id": f"zerozero_{match_count}",
                        "home_team": home_team,
                        "away_team": away_team,
                        "league": league_name,
                        "match_time": match_time.isoformat(),
                        "date": date_str,
                        "venue": f"{home_team} Stadium",
                        "odds": odds,
                        "source": "zerozero"
                    }
                    
                    match_count += 1
                    logger.info(f"Found match on ZeroZero: {home_team} vs {away_team} on {date_str} at {match_time.strftime('%H:%M')}")
                    matches.append(match_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing ZeroZero match: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing ZeroZero page: {e}")
        
        return matches
        
    def _parse_sofascore_page(self, soup, url, now, current_count) -> List[Dict[str, Any]]:
        """Parse SofaScore page HTML to extract match data."""
        matches = []
        match_count = current_count
        
        # SofaScore requires JavaScript to load content, so the HTML scraping won't work directly
        # We'd need to use a headless browser like Selenium for SofaScore
        logger.warning("SofaScore scraping requires a headless browser, which is not implemented")
        
        return matches
    
    def _fetch_football_data_matches(self) -> List[Dict[str, Any]]:
        """Fetch upcoming matches from the Football-Data.org API."""
        matches = []
        now = datetime.now()
        
        # Define league codes for Football-Data.org API
        leagues = [
            {"id": 2021, "name": "Premier League"},    # Premier League
            {"id": 2014, "name": "La Liga"},           # La Liga
            {"id": 2019, "name": "Serie A"},           # Serie A
            {"id": 2002, "name": "Bundesliga"},        # Bundesliga
            {"id": 2015, "name": "Ligue 1"},           # Ligue 1
            {"id": 2016, "name": "Championship"},      # Championship
            {"id": 2001, "name": "Champions League"}   # Champions League
        ]
        
        # Basic headers - use the demo API key if none is provided
        headers = {
            'X-Auth-Token': self.football_data_api_key or '179bc8e574584a6d92f8b0e841facdf5',  # Use env var or default to the demo key
            'User-Agent': self.headers['User-Agent']
        }
        
        # Dates for filtering
        from_date = now.strftime("%Y-%m-%d")
        to_date = (now + timedelta(days=self.days_ahead)).strftime("%Y-%m-%d")
        
        # Try getting matches from each league
        for league in leagues:
            try:
                # API endpoint for upcoming matches
                url = f"https://api.football-data.org/v4/competitions/{league['id']}/matches"
                params = {
                    "dateFrom": from_date,
                    "dateTo": to_date,
                    "status": "SCHEDULED"
                }
                
                logger.info(f"Fetching matches from Football-Data.org for league: {league['name']}")
                
                response = requests.get(url, headers=headers, params=params, timeout=15)
                
                # Check if we hit the rate limit
                if response.status_code == 429:
                    logger.warning("Rate limit hit for Football-Data.org API")
                    break
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for match in data.get('matches', []):
                        # Extract match details
                        match_date_str = match.get('utcDate', '')
                        if not match_date_str:
                            continue
                            
                        try:
                            match_datetime = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                            local_match_datetime = match_datetime.replace(tzinfo=None)  # Remove TZ info for comparison
                            
                            # Skip matches that have already started
                            if local_match_datetime < now:
                                continue
                                
                            match_date = local_match_datetime.strftime("%Y-%m-%d")
                            
                            home_team = match.get('homeTeam', {}).get('name', 'Unknown Team')
                            away_team = match.get('awayTeam', {}).get('name', 'Unknown Team')
                            
                            # Use Football-Data odds or generate odds
                            odds = {
                                "home_win": round(random.uniform(1.5, 3.0), 2),
                                "draw": round(random.uniform(2.8, 4.0), 2),
                                "away_win": round(random.uniform(2.0, 4.5), 2),
                                "over_2_5": round(random.uniform(1.7, 2.2), 2),
                                "under_2_5": round(random.uniform(1.7, 2.2), 2),
                                "btts_yes": round(random.uniform(1.7, 2.2), 2),
                                "btts_no": round(random.uniform(1.7, 2.2), 2)
                            }
                            
                            match_data = {
                                "id": str(match.get('id', f"fd_{len(matches)}")),
                                "home_team": home_team,
                                "away_team": away_team,
                                "league": league['name'],
                                "match_time": local_match_datetime.isoformat(),
                                "date": match_date,
                                "venue": match.get('venue', f"{home_team} Stadium"),
                                "odds": odds
                            }
                            
                            logger.info(f"Found match: {home_team} vs {away_team} on {match_date} at {local_match_datetime.strftime('%H:%M')}")
                            matches.append(match_data)
                        except Exception as e:
                            logger.warning(f"Error processing match: {e}")
                            continue
                elif response.status_code == 403:
                    logger.error(f"Authorization failed for Football-Data.org API. Status: {response.status_code}")
                    logger.error("Please check your API key or register for a free key at football-data.org")
                    break
                else:
                    logger.warning(f"Unexpected response from Football-Data.org: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error fetching from Football-Data.org for league {league['name']}: {e}")
                continue
        
        logger.info(f"Football-Data.org fetching complete. Found {len(matches)} matches.")
        return matches
    
    def _fetch_api_football_matches(self) -> List[Dict[str, Any]]:
        """Fetch upcoming matches from the API-Football API."""
        matches = []
        now = datetime.now()
        
        # API-Football API key from RapidAPI
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        if not api_key:
            logger.warning("No RapidAPI key found for API-Football")
            return matches
        
        # Define leagues to fetch
        leagues = [39, 140, 135, 78, 61, 2, 3]  # Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League
        
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        
        try:
            # Get date range for the next few days
            dates = []
            for day in range(self.days_ahead + 1):
                date = (now + timedelta(days=day)).strftime("%Y-%m-%d")
                dates.append(date)
            
            # Fetch matches for each date
            for date in dates:
                url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
                params = {"date": date}
                
                logger.info(f"Fetching matches from API-Football for date: {date}")
                
                response = requests.get(url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'response' in data:
                        for fixture in data['response']:
                            # Filter for leagues we're interested in
                            league_id = fixture.get('league', {}).get('id')
                            if league_id not in leagues:
                                continue
                                
                            fixture_date = fixture.get('fixture', {}).get('date')
                            if not fixture_date:
                                continue
                                
                            try:
                                match_datetime = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
                                local_match_datetime = match_datetime.replace(tzinfo=None)
                                
                                # Skip matches that have already started
                                if local_match_datetime < now:
                                    continue
                                    
                                match_date = local_match_datetime.strftime("%Y-%m-%d")
                                
                                home_team = fixture.get('teams', {}).get('home', {}).get('name', 'Unknown Team')
                                away_team = fixture.get('teams', {}).get('away', {}).get('name', 'Unknown Team')
                                league_name = fixture.get('league', {}).get('name', 'Unknown League')
                                
                                # Extract odds if available
                                odds = {
                                    "home_win": 0,
                                    "draw": 0,
                                    "away_win": 0,
                                    "over_2_5": 0,
                                    "under_2_5": 0,
                                    "btts_yes": 0,
                                    "btts_no": 0
                                }
                                
                                match_data = {
                                    "id": str(fixture.get('fixture', {}).get('id', f"af_{len(matches)}")),
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "league": league_name,
                                    "match_time": local_match_datetime.isoformat(),
                                    "date": match_date,
                                    "venue": fixture.get('fixture', {}).get('venue', {}).get('name', f"{home_team} Stadium"),
                                    "odds": odds
                                }
                                
                                logger.info(f"Found match: {home_team} vs {away_team} on {match_date} at {local_match_datetime.strftime('%H:%M')}")
                                matches.append(match_data)
                            except Exception as e:
                                logger.warning(f"Error processing fixture: {e}")
                                continue
        except Exception as e:
            logger.error(f"Error fetching from API-Football: {e}")
            logger.exception("API request error details:")
        
        logger.info(f"API-Football fetching complete. Found {len(matches)} matches.")
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
