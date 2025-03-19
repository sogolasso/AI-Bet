import os
import random
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MelhorOddScraper:
    """Scraper for MelhorOdd.pt which aggregates betting odds from multiple sources."""
    
    def __init__(self, days_ahead: int = 2, cache_duration: int = 3600):
        """Initialize the MelhorOdd.pt scraper.
        
        Args:
            days_ahead: Number of days ahead to scrape
            cache_duration: Duration in seconds to cache results
        """
        self.days_ahead = days_ahead
        self.cache_duration = cache_duration
        self.cached_matches = []
        self.cached_time = datetime.min
        
        # Base URL for all games
        self.base_url = "https://www.melhorodd.pt/todos-os-jogos/"
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        ]
    
    def _get_headers(self) -> Dict[str, str]:
        """Get random headers for the request.
        
        Returns:
            Dictionary with HTTP headers
        """
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.melhorodd.pt/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers',
        }
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content of a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content of the page or None if the request failed
        """
        try:
            # Add a delay to avoid hitting rate limits
            time.sleep(random.uniform(1, 3))
            
            # Make the request
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            
            # Check if the request was successful
            if response.status_code == 200:
                logger.info(f"Successfully fetched {url}")
                return response.text
            else:
                logger.error(f"Failed to fetch {url}, status code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_date_from_match(self, match_time_element: Any) -> Optional[datetime]:
        """Extract date and time from match time element.
        
        Args:
            match_time_element: BeautifulSoup element containing the match time
            
        Returns:
            Datetime object or None if parsing failed
        """
        try:
            # Check if the element exists
            if not match_time_element:
                return None
            
            # Get the text from the element
            time_text = match_time_element.get_text(strip=True)
            
            # Common formats on melhorodd.pt
            # Format: "19/03 - 20:00"
            match = re.search(r'(\d{2}/\d{2})\s*[-–]\s*(\d{2}:\d{2})', time_text)
            
            if match:
                date_str, time_str = match.groups()
                
                # Extract day and month
                day, month = map(int, date_str.split('/'))
                hour, minute = map(int, time_str.split(':'))
                
                # Current year
                current_year = datetime.now().year
                
                # Create datetime object
                match_datetime = datetime(
                    year=current_year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute
                )
                
                # If the date is in the past, it might be for next year
                if match_datetime < datetime.now() - timedelta(hours=3):
                    match_datetime = match_datetime.replace(year=current_year + 1)
                
                return match_datetime
            
            return None
        except Exception as e:
            logger.warning(f"Error parsing match date: {e}")
            return None
    
    def _parse_odds(self, odds_elements: List[Any]) -> Dict[str, float]:
        """Parse odds values from odds elements.
        
        Args:
            odds_elements: List of BeautifulSoup elements containing odds
            
        Returns:
            Dictionary mapping odds types to values
        """
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
            # Process 1X2 odds (match winner)
            if len(odds_elements) >= 3:
                # Get text and convert to float for each odd
                for i, odd_type in enumerate(['home_win', 'draw', 'away_win']):
                    if i < len(odds_elements):
                        odd_text = odds_elements[i].get_text(strip=True).replace(',', '.')
                        try:
                            odds[odd_type] = float(odd_text)
                        except (ValueError, TypeError):
                            pass
            
            # Process Over/Under odds if available
            if len(odds_elements) >= 5:
                for i, odd_type in enumerate(['over_2_5', 'under_2_5']):
                    if i + 3 < len(odds_elements):
                        odd_text = odds_elements[i + 3].get_text(strip=True).replace(',', '.')
                        try:
                            odds[odd_type] = float(odd_text)
                        except (ValueError, TypeError):
                            pass
            
            # Process BTTS odds if available
            if len(odds_elements) >= 7:
                for i, odd_type in enumerate(['btts_yes', 'btts_no']):
                    if i + 5 < len(odds_elements):
                        odd_text = odds_elements[i + 5].get_text(strip=True).replace(',', '.')
                        try:
                            odds[odd_type] = float(odd_text)
                        except (ValueError, TypeError):
                            pass
        except Exception as e:
            logger.warning(f"Error parsing odds: {e}")
        
        return odds
    
    def scrape_matches(self) -> List[Dict[str, Any]]:
        """Scrape football matches from MelhorOdd.pt.
        
        Returns:
            List of dictionaries containing match information
        """
        # Check if we have cached matches and they're still valid
        if self.cached_matches and (datetime.now() - self.cached_time).total_seconds() < self.cache_duration:
            logger.info(f"Using cached matches ({len(self.cached_matches)} matches, cached {(datetime.now() - self.cached_time).total_seconds()/60:.1f} minutes ago)")
            return self.cached_matches
        
        matches = []
        match_count = 0
        
        # Fetch the main page with all games
        html_content = self._fetch_page(self.base_url)
        
        if not html_content:
            logger.error("Failed to fetch matches from MelhorOdd.pt")
            return self._get_example_matches()
        
        try:
            # Parse the HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Save the HTML to a file for debugging
            with open('melhorodd_debug.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("Saved HTML to melhorodd_debug.html for inspection")
            
            # Find all match containers - try various potential CSS selectors
            match_containers = soup.select('div.event-box')
            
            if not match_containers:
                match_containers = soup.select('div.game')
                
            if not match_containers:
                match_containers = soup.select('tr.event-row')
                
            if not match_containers:
                match_containers = soup.select('div.match-container')
                
            if not match_containers:
                # Log all the top-level divs with classes to help debug
                top_divs = soup.select('div[class]')
                logger.info(f"Found {len(top_divs)} divs with classes. First 10 classes:")
                for i, div in enumerate(top_divs[:10]):
                    logger.info(f"Div {i+1}: class='{div.get('class')}'")
                
                # Broader search
                match_containers = soup.find_all('div', recursive=True)
                logger.warning(f"No specific match containers found, using general approach with {len(match_containers)} divs")
            
            if not match_containers:
                logger.warning("No match containers found on the page")
                return self._get_example_matches()
            
            logger.info(f"Found {len(match_containers)} potential match containers")
            
            now = datetime.now()
            max_date = now + timedelta(days=self.days_ahead)
            
            # Process each match container
            for container in match_containers:
                try:
                    # Check if this container has team names - a good indicator it's a match
                    team_elements = None
                    
                    # Try various selectors for team names
                    for selector in ['span.team-name', 'div.team-name', 'div.team', 'span.team', 'td.team']:
                        team_elements = container.select(selector)
                        if len(team_elements) >= 2:
                            break
                    
                    # If no team elements found, try to find any element with "vs" or "-" in the text
                    if not team_elements or len(team_elements) < 2:
                        for element in container.find_all(['span', 'div', 'td', 'p']):
                            if ' vs ' in element.text or ' - ' in element.text:
                                teams_text = element.text.strip()
                                # Split by vs or -
                                if ' vs ' in teams_text:
                                    teams = teams_text.split(' vs ')
                                else:
                                    teams = teams_text.split(' - ')
                                
                                if len(teams) == 2:
                                    home_team = teams[0].strip()
                                    away_team = teams[1].strip()
                                    
                                    # Extract league name - try different approaches
                                    league_element = None
                                    for selector in ['div.league-name', 'div.league', 'span.league', 'td.league']:
                                        league_element = container.select_one(selector)
                                        if league_element:
                                            break
                                    
                                    league = league_element.get_text(strip=True) if league_element else "Unknown League"
                                    
                                    # Extract match time
                                    time_element = None
                                    for selector in ['div.date-hour', 'div.date', 'div.time', 'span.date', 'span.time', 'td.date', 'td.time']:
                                        time_element = container.select_one(selector)
                                        if time_element:
                                            break
                                    
                                    match_datetime = self._extract_date_from_match(time_element)
                                    
                                    if not match_datetime:
                                        # Try to find any date-like text in the container
                                        date_pattern = r'(\d{2}[/.-]\d{2}[/.-]\d{2,4}|\d{2}[/.-]\d{2})'
                                        time_pattern = r'(\d{1,2}:\d{2})'
                                        
                                        for text_element in container.find_all(text=True):
                                            date_match = re.search(date_pattern, text_element)
                                            time_match = re.search(time_pattern, text_element)
                                            
                                            if date_match and time_match:
                                                date_str = date_match.group(1)
                                                time_str = time_match.group(1)
                                                
                                                # Try to parse the date and time
                                                try:
                                                    # Handle different date formats
                                                    if '/' in date_str:
                                                        day, month = map(int, date_str.split('/')[0:2])
                                                    elif '-' in date_str:
                                                        day, month = map(int, date_str.split('-')[0:2])
                                                    elif '.' in date_str:
                                                        day, month = map(int, date_str.split('.')[0:2])
                                                    else:
                                                        continue
                                                    
                                                    hour, minute = map(int, time_str.split(':'))
                                                    current_year = datetime.now().year
                                                    
                                                    match_datetime = datetime(
                                                        year=current_year,
                                                        month=month,
                                                        day=day,
                                                        hour=hour,
                                                        minute=minute
                                                    )
                                                    
                                                    # If the date is in the past, it might be for next year
                                                    if match_datetime < datetime.now() - timedelta(hours=3):
                                                        match_datetime = match_datetime.replace(year=current_year + 1)
                                                    
                                                    break
                                                except Exception as e:
                                                    logger.debug(f"Failed to parse date/time: {e}")
                                                    continue
                                    
                                    if not match_datetime:
                                        # Use current date and a default time if parsing fails
                                        match_datetime = now.replace(hour=15, minute=0, second=0)
                                    
                                    # Skip matches that are too far in the future
                                    if match_datetime > max_date:
                                        continue
                                    
                                    # Skip matches that have already started
                                    if match_datetime < now:
                                        continue
                                    
                                    # Format the date and time
                                    date_str = match_datetime.strftime("%Y-%m-%d")
                                    time_str = match_datetime.strftime("%H:%M")
                                    
                                    # Extract odds
                                    odds = {"home_win": 0, "draw": 0, "away_win": 0, "over_2_5": 0, "under_2_5": 0, "btts_yes": 0, "btts_no": 0}
                                    
                                    # Look for numeric values that could be odds
                                    odd_pattern = r'(\d+[.,]\d+)'
                                    odd_values = []
                                    
                                    for element in container.find_all(['span', 'div', 'td']):
                                        text = element.get_text(strip=True)
                                        matches = re.findall(odd_pattern, text)
                                        for m in matches:
                                            try:
                                                odd_values.append(float(m.replace(',', '.')))
                                            except ValueError:
                                                pass
                                    
                                    # Assign the first 3 values to 1X2 odds if they seem reasonable
                                    if len(odd_values) >= 3:
                                        # Filter odds in a reasonable range (1.1 to 20.0)
                                        filtered_odds = [o for o in odd_values if 1.1 <= o <= 20.0]
                                        
                                        if len(filtered_odds) >= 3:
                                            odds["home_win"] = filtered_odds[0]
                                            odds["draw"] = filtered_odds[1]
                                            odds["away_win"] = filtered_odds[2]
                                            
                                            if len(filtered_odds) >= 5:
                                                odds["over_2_5"] = filtered_odds[3]
                                                odds["under_2_5"] = filtered_odds[4]
                                    
                                    # Create match object
                                    match_data = {
                                        "id": f"melhorodd_{match_count}",
                                        "home_team": home_team,
                                        "away_team": away_team,
                                        "league": league,
                                        "match_time": match_datetime.isoformat(),
                                        "date": date_str,
                                        "venue": f"{home_team} Stadium",
                                        "odds": odds,
                                        "source": "melhorodd_scrape"
                                    }
                                    
                                    matches.append(match_data)
                                    match_count += 1
                                    
                                    logger.info(f"Extracted match: {home_team} vs {away_team} ({date_str} {time_str}) odds: {odds['home_win']}/{odds['draw']}/{odds['away_win']}")
                                    break
                        
                    # If we already processed this container as a match with the vs/- method
                    if matches and matches[-1]["id"] == f"melhorodd_{match_count-1}":
                        continue
                    
                    # If we found proper team elements
                    if team_elements and len(team_elements) >= 2:
                        home_team = team_elements[0].get_text(strip=True)
                        away_team = team_elements[1].get_text(strip=True)
                        
                        # Extract league name
                        league_element = None
                        for selector in ['div.league-name', 'div.league', 'span.league', 'td.league']:
                            league_element = container.select_one(selector)
                            if league_element:
                                break
                                
                        league = league_element.get_text(strip=True) if league_element else "Unknown League"
                        
                        # Extract match time
                        time_element = None
                        for selector in ['div.date-hour', 'div.date', 'div.time', 'span.date', 'span.time', 'td.date', 'td.time']:
                            time_element = container.select_one(selector)
                            if time_element:
                                break
                                
                        match_datetime = self._extract_date_from_match(time_element)
                        
                        if not match_datetime:
                            # Use current date and a default time if parsing fails
                            match_datetime = now.replace(hour=15, minute=0, second=0)
                        
                        # Skip matches that are too far in the future
                        if match_datetime > max_date:
                            continue
                        
                        # Skip matches that have already started
                        if match_datetime < now:
                            continue
                        
                        # Format the date and time
                        date_str = match_datetime.strftime("%Y-%m-%d")
                        time_str = match_datetime.strftime("%H:%M")
                        
                        # Extract odds
                        odds = {"home_win": 0, "draw": 0, "away_win": 0, "over_2_5": 0, "under_2_5": 0, "btts_yes": 0, "btts_no": 0}
                        
                        # Try to find odds elements
                        odds_elements = []
                        for selector in ['span.odd-value', 'div.odd', 'span.odd', 'td.odd']:
                            odds_elements = container.select(selector)
                            if odds_elements:
                                break
                                
                        if odds_elements:
                            odds = self._parse_odds(odds_elements)
                        else:
                            # Look for numeric values that could be odds
                            odd_pattern = r'(\d+[.,]\d+)'
                            odd_values = []
                            
                            for element in container.find_all(['span', 'div', 'td']):
                                text = element.get_text(strip=True)
                                matches = re.findall(odd_pattern, text)
                                for m in matches:
                                    try:
                                        odd_values.append(float(m.replace(',', '.')))
                                    except ValueError:
                                        pass
                            
                            # Assign the first 3 values to 1X2 odds if they seem reasonable
                            if len(odd_values) >= 3:
                                # Filter odds in a reasonable range (1.1 to 20.0)
                                filtered_odds = [o for o in odd_values if 1.1 <= o <= 20.0]
                                
                                if len(filtered_odds) >= 3:
                                    odds["home_win"] = filtered_odds[0]
                                    odds["draw"] = filtered_odds[1]
                                    odds["away_win"] = filtered_odds[2]
                                    
                                    if len(filtered_odds) >= 5:
                                        odds["over_2_5"] = filtered_odds[3]
                                        odds["under_2_5"] = filtered_odds[4]
                        
                        # Create match object
                        match_data = {
                            "id": f"melhorodd_{match_count}",
                            "home_team": home_team,
                            "away_team": away_team,
                            "league": league,
                            "match_time": match_datetime.isoformat(),
                            "date": date_str,
                            "venue": f"{home_team} Stadium",
                            "odds": odds,
                            "source": "melhorodd_scrape"
                        }
                        
                        matches.append(match_data)
                        match_count += 1
                        
                        logger.info(f"Extracted match: {home_team} vs {away_team} ({date_str} {time_str}) odds: {odds['home_win']}/{odds['draw']}/{odds['away_win']}")
                    
                except Exception as e:
                    logger.warning(f"Error processing match container: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(matches)} matches from MelhorOdd.pt")
            
            # Cache the matches if we found any
            if matches:
                self.cached_matches = matches
                self.cached_time = datetime.now()
                return matches
            else:
                logger.warning("No matches found on the page")
                return self._get_example_matches()
                
        except Exception as e:
            logger.error(f"Error scraping matches from MelhorOdd.pt: {e}")
            logger.exception("Exception details:")
            return self._get_example_matches()
    
    def _get_example_matches(self) -> List[Dict[str, Any]]:
        """Get example match data for testing or when scraping fails.
        
        Returns:
            List of dictionaries containing example match information
        """
        logger.warning("Using example match data since scraping failed")
        
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Create some example matches with realistic odds
        example_matches = [
            {
                "id": "melhorodd_0",
                "home_team": "Sporting CP",
                "away_team": "FC Porto",
                "league": "Primeira Liga",
                "match_time": now.replace(hour=20, minute=0, second=0).isoformat(),
                "date": today,
                "venue": "Estádio José Alvalade",
                "odds": {
                    "home_win": 2.15,
                    "draw": 3.25,
                    "away_win": 3.40,
                    "over_2_5": 1.95,
                    "under_2_5": 1.85,
                    "btts_yes": 1.80,
                    "btts_no": 1.90
                },
                "source": "melhorodd_example"
            },
            {
                "id": "melhorodd_1",
                "home_team": "Benfica",
                "away_team": "Braga",
                "league": "Primeira Liga",
                "match_time": now.replace(hour=21, minute=15, second=0).isoformat(),
                "date": today,
                "venue": "Estádio da Luz",
                "odds": {
                    "home_win": 1.70,
                    "draw": 3.75,
                    "away_win": 4.50,
                    "over_2_5": 1.75,
                    "under_2_5": 2.05,
                    "btts_yes": 1.75,
                    "btts_no": 1.95
                },
                "source": "melhorodd_example"
            },
            {
                "id": "melhorodd_2",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "league": "La Liga",
                "match_time": (now + timedelta(days=1)).replace(hour=20, minute=0, second=0).isoformat(),
                "date": tomorrow,
                "venue": "Camp Nou",
                "odds": {
                    "home_win": 1.90,
                    "draw": 3.60,
                    "away_win": 3.80,
                    "over_2_5": 1.65,
                    "under_2_5": 2.25,
                    "btts_yes": 1.60,
                    "btts_no": 2.30
                },
                "source": "melhorodd_example"
            },
            {
                "id": "melhorodd_3",
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "league": "Premier League",
                "match_time": (now + timedelta(days=1)).replace(hour=16, minute=30, second=0).isoformat(),
                "date": tomorrow,
                "venue": "Etihad Stadium",
                "odds": {
                    "home_win": 1.75,
                    "draw": 3.80,
                    "away_win": 4.20,
                    "over_2_5": 1.60,
                    "under_2_5": 2.35,
                    "btts_yes": 1.55,
                    "btts_no": 2.40
                },
                "source": "melhorodd_example"
            }
        ]
        
        return example_matches


def scrape_melhorodd_matches(days_ahead: int = 2) -> List[Dict[str, Any]]:
    """Convenience function to scrape matches from MelhorOdd.pt.
    
    Args:
        days_ahead: Number of days ahead to scrape
        
    Returns:
        List of dictionaries containing match information
    """
    scraper = MelhorOddScraper(days_ahead=days_ahead)
    return scraper.scrape_matches()


if __name__ == "__main__":
    # Run the scraper
    matches = scrape_melhorodd_matches()
    print(f"Scraped {len(matches)} matches from MelhorOdd.pt")
    
    # Save to a JSON file for analysis
    with open("melhorodd_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    # Print the first 3 matches
    for i, match in enumerate(matches[:3]):
        print(f"\nMatch {i+1}:")
        print(f"  {match['home_team']} vs {match['away_team']}")
        print(f"  Date: {match['date']} at {match['match_time'].split('T')[1][:5]}")
        print(f"  League: {match['league']}")
        print(f"  Odds: Home {match['odds']['home_win']} | Draw {match['odds']['draw']} | Away {match['odds']['away_win']}")
        if match['odds']['over_2_5'] > 0:
            print(f"  Over/Under 2.5: Over {match['odds']['over_2_5']} | Under {match['odds']['under_2_5']}") 