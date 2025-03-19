import os
import random
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BetanoMelhorOddScraper:
    """Optimized scraper for MelhorOdd.pt focusing exclusively on Betano odds."""
    
    def __init__(self, days_ahead: int = 2, cache_duration: int = 3600):
        """Initialize the MelhorOdd.pt scraper specifically for Betano odds.
        
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
        
        # Screen sizes for randomization
        self.screen_sizes = [
            (1920, 1080),
            (1366, 768),
            (1440, 900),
            (1536, 864),
            (1280, 720)
        ]
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up the Chrome WebDriver with anti-detection features.
        
        Returns:
            Configured Chrome WebDriver instance
        """
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # Using new headless mode
        
        # Choose a random user agent, preferring Portuguese localized browsers
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f"user-agent={user_agent}")
        
        # Set Portuguese language to help with localization
        chrome_options.add_argument("--lang=pt-PT")
        
        # Choose a random screen size
        width, height = random.choice(self.screen_sizes)
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Performance options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Enable cookies
        chrome_options.add_argument("--enable-cookies")
        
        # Set up proxy if provided in environment variables
        proxy = os.environ.get("HTTP_PROXY")
        if proxy:
            chrome_options.add_argument(f"--proxy-server={proxy}")
            logger.info(f"Using proxy: {proxy}")
        
        # Custom preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "intl.accept_languages": "pt-PT,pt,en-US,en"
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Create and return the driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Modify navigator properties to avoid detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    
    def _simulate_human_behavior(self, driver: webdriver.Chrome):
        """Simulate human-like interactions with the page.
        
        Args:
            driver: The WebDriver instance
        """
        try:
            # Random scrolling
            total_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            
            # Scroll down in chunks with random pauses
            current_position = 0
            while current_position < total_height:
                scroll_amount = random.randint(100, 300)
                current_position += scroll_amount
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Random delay before scrolling back up
            time.sleep(random.uniform(1, 2))
            
            # Scroll back up in chunks
            while current_position > 0:
                scroll_amount = random.randint(100, 300)
                current_position -= scroll_amount
                if current_position < 0:
                    current_position = 0
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(random.uniform(0.3, 0.7))
            
            # Try to find and click "Load More" buttons if they exist
            try:
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Carregar') or contains(text(), 'Mais') or contains(text(), 'Load')]")
                if load_more_buttons:
                    for button in load_more_buttons:
                        if button.is_displayed() and button.is_enabled():
                            # Scroll to the button
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(random.uniform(0.5, 1.0))
                            # Click the button
                            button.click()
                            time.sleep(random.uniform(1.5, 3.0))
                            # Simulate human scrolling after loading more content
                            self._simulate_human_behavior(driver)
            except Exception as e:
                logger.debug(f"Error interacting with load more buttons: {e}")
                
        except Exception as e:
            logger.warning(f"Error simulating human behavior: {e}")
    
    def _extract_date_from_text(self, date_text: str) -> Optional[datetime]:
        """Extract date and time from text.
        
        Args:
            date_text: Text containing date information
            
        Returns:
            Datetime object or None if parsing failed
        """
        try:
            # Common formats on melhorodd.pt: "19/03 - 20:00" or "19-03-2023 20:00"
            patterns = [
                r'(\d{2}/\d{2})\s*[-–]\s*(\d{2}:\d{2})',  # 19/03 - 20:00
                r'(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})',   # 19-03-2023 20:00
                r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})',   # 19/03/2023 20:00
                r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})'    # 2023-03-19 20:00
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_text)
                if match:
                    date_str, time_str = match.groups()
                    
                    # Parse date based on format
                    if '/' in date_str and len(date_str) == 5:  # DD/MM format
                        day, month = map(int, date_str.split('/'))
                        year = datetime.now().year
                    elif '-' in date_str and len(date_str) == 10:  # DD-MM-YYYY format
                        day, month, year = map(int, date_str.split('-'))
                    elif '/' in date_str and len(date_str) == 10:  # DD/MM/YYYY format
                        day, month, year = map(int, date_str.split('/'))
                    elif '-' in date_str and len(date_str) == 10:  # YYYY-MM-DD format
                        year, month, day = map(int, date_str.split('-'))
                    else:
                        continue
                    
                    # Parse time
                    hour, minute = map(int, time_str.split(':'))
                    
                    # Create datetime object
                    match_datetime = datetime(
                        year=year,
                        month=month,
                        day=day,
                        hour=hour,
                        minute=minute
                    )
                    
                    # If the date is in the past, it might be for next year
                    if match_datetime < datetime.now() - timedelta(hours=3):
                        match_datetime = match_datetime.replace(year=year + 1)
                    
                    return match_datetime
            
            return None
        except Exception as e:
            logger.warning(f"Error parsing match date: {e}")
            return None
    
    def _extract_betano_odds(self, row: Any, soup: BeautifulSoup) -> Dict[str, float]:
        """Extract Betano odds from a table row.
        
        Args:
            row: BeautifulSoup row element
            soup: BeautifulSoup object of the entire page
            
        Returns:
            Dictionary with odds values
        """
        odds = {
            "home_win": 0,
            "draw": 0,
            "away_win": 0,
            "over_2_5": 0,
            "under_2_5": 0,
            "btts_yes": 0,
            "btts_no": 0,
            "bookmaker": "Betano"
        }
        
        try:
            # Look for Betano logo or link
            betano_selectors = [
                'img[src*="betano"], a[href*="betano"]',
                'img[alt*="betano"], a[alt*="betano"]',
                'img[title*="betano"], a[title*="betano"]',
                'td:has(a[href*="betano"])'
            ]
            
            betano_elements = []
            for selector in betano_selectors:
                elements = row.select(selector)
                if elements:
                    betano_elements.extend(elements)
                    break
            
            if not betano_elements:
                # If we can't find direct Betano elements, check for Betano text
                for cell in row.find_all('td'):
                    if 'betano' in cell.get_text().lower():
                        betano_elements.append(cell)
            
            if not betano_elements:
                # If still not found, we don't have Betano odds for this match
                return odds
            
            # Extract odd values from cells near Betano elements
            for betano_element in betano_elements:
                parent_cell = betano_element.parent
                if parent_cell.name != 'td':
                    parent_cell = parent_cell.parent
                
                # Get siblings (next cells in the row which should contain odds)
                sibling_cells = parent_cell.find_next_siblings('td')
                
                # Extract 1X2 (Match Winner) odds
                if len(sibling_cells) >= 2:
                    # Home win (1)
                    home_text = sibling_cells[0].get_text(strip=True).replace(',', '.')
                    try:
                        odds["home_win"] = float(home_text)
                    except (ValueError, TypeError):
                        pass
                    
                    # Draw (X)
                    draw_text = sibling_cells[1].get_text(strip=True).replace(',', '.')
                    try:
                        odds["draw"] = float(draw_text)
                    except (ValueError, TypeError):
                        pass
                    
                    # Away win (2)
                    if len(sibling_cells) >= 3:
                        away_text = sibling_cells[2].get_text(strip=True).replace(',', '.')
                        try:
                            odds["away_win"] = float(away_text)
                        except (ValueError, TypeError):
                            pass
                
                # Try to find Over/Under odds
                over_under_row = None
                
                # Check if there's a following row with the same teams but for Over/Under market
                current_match = row.select_one('td:nth-child(5)')
                if current_match:
                    match_text = current_match.get_text(strip=True)
                    following_rows = row.find_next_siblings('tr')
                    
                    for following_row in following_rows:
                        match_cell = following_row.select_one('td:nth-child(5)')
                        if match_cell and match_cell.get_text(strip=True) == match_text:
                            market_cell = following_row.select_one('td:nth-child(3)')
                            if market_cell and 'over' in market_cell.get_text().lower():
                                over_under_row = following_row
                                break
                
                if over_under_row:
                    # Extract Over/Under odds from the dedicated row
                    betano_cell_ou = None
                    for cell in over_under_row.find_all('td'):
                        if 'betano' in str(cell).lower():
                            betano_cell_ou = cell
                            break
                    
                    if betano_cell_ou:
                        ou_siblings = betano_cell_ou.find_next_siblings('td')
                        if len(ou_siblings) >= 2:
                            # Over 2.5
                            over_text = ou_siblings[0].get_text(strip=True).replace(',', '.')
                            try:
                                odds["over_2_5"] = float(over_text)
                            except (ValueError, TypeError):
                                pass
                            
                            # Under 2.5
                            under_text = ou_siblings[1].get_text(strip=True).replace(',', '.')
                            try:
                                odds["under_2_5"] = float(under_text)
                            except (ValueError, TypeError):
                                pass
            
            # If we found any valid odds, mark this as a Betano source
            if any(value > 0 for key, value in odds.items() if key != "bookmaker"):
                return odds
            else:
                return {key: 0 for key in odds.keys()}
            
        except Exception as e:
            logger.warning(f"Error extracting Betano odds: {e}")
            return odds
    
    def scrape_matches(self) -> List[Dict[str, Any]]:
        """Scrape football matches with Betano odds from MelhorOdd.pt.
        
        Returns:
            List of dictionaries containing match information with Betano odds
        """
        # Check if we have cached matches and they're still valid
        if self.cached_matches and (datetime.now() - self.cached_time).total_seconds() < self.cache_duration:
            logger.info(f"Using cached matches ({len(self.cached_matches)} matches, cached {(datetime.now() - self.cached_time).total_seconds()/60:.1f} minutes ago)")
            return self.cached_matches
        
        # Initialize driver
        driver = self._setup_driver()
        matches = []
        debug_files = []
        
        try:
            logger.info(f"Navigating to {self.base_url}")
            driver.get(self.base_url)
            
            # Wait for the page to load
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table, tr.event-row, div.event'))
                )
                logger.info("Page loaded successfully")
            except TimeoutException:
                logger.warning("Timeout waiting for page to load, proceeding anyway")
            
            # Simulate human-like scrolling to trigger JavaScript
            self._simulate_human_behavior(driver)
            
            # Save the page source to a debug file
            page_source = driver.page_source
            debug_file = "melhorodd_betano_debug.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            debug_files.append(debug_file)
            logger.info(f"Saved page source to {debug_file}")
            
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Try to specifically locate sport information
            sport_filters = soup.select('a[href*="futebol"], button:contains("Futebol"), div.filter:contains("Futebol")')
            if sport_filters:
                logger.info(f"Found {len(sport_filters)} football filter elements on the page")
                with open("football_filters.html", "w", encoding="utf-8") as f:
                    for i, filter_elem in enumerate(sport_filters):
                        f.write(f"--- Football Filter {i+1} ---\n")
                        f.write(str(filter_elem))
                        f.write("\n\n")
            
            # Log all rows with "Futebol" text
            futebol_rows = soup.find_all(lambda tag: tag.name and "futebol" in tag.get_text().lower())
            if futebol_rows:
                logger.info(f"Found {len(futebol_rows)} elements containing 'futebol' text")
                with open("futebol_elements.html", "w", encoding="utf-8") as f:
                    for i, elem in enumerate(futebol_rows):
                        f.write(f"--- Futebol Element {i+1} ---\n")
                        f.write(str(elem))
                        f.write("\n\n")
            
            # Look for table headers with "Sport" column
            all_table_headers = soup.select('tr.header th, tr.head th, thead tr th')
            sport_columns = [th for th in all_table_headers if 'sport' in th.get_text().lower() or 'esporte' in th.get_text().lower()]
            if sport_columns:
                logger.info(f"Found {len(sport_columns)} Sport column headers")
            
            # Look for tables that might contain odds
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on the page")
            
            # Identify the main table with matches and odds
            main_table = None
            football_tables = soup.select('table[id*="futebol"], table[class*="futebol"], table[id*="football"], table[class*="football"]')
            
            if football_tables:
                logger.info(f"Found {len(football_tables)} football-specific tables")
                main_table = football_tables[0]
            else:
                # If no football-specific table, use the regular approach
                for table in tables:
                    # Check if this table has match data with team names
                    if table.select('tr:has(td:contains("vs"))') or table.select('tr:has(td:contains("-"))'):
                        main_table = table
                        break
                
                if not main_table:
                    logger.warning("Could not find the main table with matches")
                    # Try to find any table that might contain matches
                    for table in tables:
                        if len(table.find_all('tr')) > 5:  # At least a few rows
                            main_table = table
                            break
            
            if main_table:
                logger.info("Found the main table with matches")
                
                # Log the table headers to help with debugging
                header_rows = main_table.find_all('tr', class_=lambda c: c and ('header' in str(c).lower() or 'head' in str(c).lower()))
                if header_rows:
                    for header_row in header_rows:
                        header_cells = header_row.find_all(['th', 'td'])
                        header_texts = [cell.get_text(strip=True) for cell in header_cells]
                        logger.info(f"Table headers: {header_texts}")
                
                # Extract rows
                rows = main_table.find_all('tr')
                logger.info(f"Found {len(rows)} rows in the main table")
                
                # Process each row
                match_count = 0
                for row in rows:
                    try:
                        # Check if this is a match row (contains date and teams)
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue
                        
                        # Check if this row is for football sport
                        is_football = False
                        sport_col_index = None
                        
                        # Try to find the Sport column by checking column headers
                        if not sport_col_index:
                            header_row = main_table.find('tr', class_=lambda c: c and 'header' in c.lower())
                            if header_row:
                                for i, th in enumerate(header_row.find_all('th')):
                                    if 'sport' in th.get_text().lower() or 'esporte' in th.get_text().lower():
                                        sport_col_index = i
                                        break
                        
                        # If we found a sport column, check if this is football
                        if sport_col_index is not None and sport_col_index < len(cells):
                            sport_text = cells[sport_col_index].get_text(strip=True).lower()
                            is_football = sport_text in ['futebol', 'football', 'soccer']
                        else:
                            # If we can't find a sport column, check the league name or other indicators
                            for cell in cells:
                                cell_text = cell.get_text(strip=True).lower()
                                if cell_text in ['futebol', 'football', 'soccer']:
                                    is_football = True
                                    break
                            
                            # Default to treating it as football if we can't determine
                            if not is_football:
                                # Look at the URL of the row if available
                                links = row.find_all('a')
                                for link in links:
                                    href = link.get('href', '')
                                    if 'futebol' in href.lower() or 'football' in href.lower() or 'soccer' in href.lower():
                                        is_football = True
                                        break
                        
                        # Skip non-football matches
                        if not is_football:
                            logger.debug(f"Skipping non-football match in row {cells}")
                            continue
                        
                        # Get date/time
                        date_cell = cells[0]
                        date_text = date_cell.get_text(strip=True)
                        match_datetime = self._extract_date_from_text(date_text)
                        
                        if not match_datetime:
                            continue
                        
                        # Skip matches that are too far in the future
                        if match_datetime > datetime.now() + timedelta(days=self.days_ahead):
                            continue
                        
                        # Extract teams
                        teams_cell = cells[4] if len(cells) > 4 else None
                        if not teams_cell:
                            continue
                        
                        teams_text = teams_cell.get_text(strip=True)
                        
                        # Check if this contains team names
                        if 'vs' not in teams_text.lower() and '-' not in teams_text and '–' not in teams_text:
                            continue
                        
                        # Extract home and away teams
                        if 'vs' in teams_text.lower():
                            home_team, away_team = teams_text.split('vs', 1)
                        elif '-' in teams_text:
                            home_team, away_team = teams_text.split('-', 1)
                        elif '–' in teams_text:
                            home_team, away_team = teams_text.split('–', 1)
                        else:
                            continue
                        
                        # Clean team names
                        home_team = home_team.strip()
                        away_team = away_team.strip()
                        
                        if not home_team or not away_team:
                            continue
                        
                        # Extract league
                        league = "Unknown League"
                        sport_type = "Football"  # We're targeting the football URL directly
                        if len(cells) > 3:
                            league_cell = cells[3]
                            league = league_cell.get_text(strip=True)
                        
                        # Extract Betano odds
                        odds = self._extract_betano_odds(row, soup)
                        
                        # Skip matches without Betano odds
                        if all(value == 0 for key, value in odds.items() if key != "bookmaker"):
                            continue
                        
                        # Create match info
                        match_info = {
                            'id': f"melhorodd_betano_{match_count}",
                            'home_team': home_team,
                            'away_team': away_team,
                            'league': league,
                            'date': match_datetime.strftime("%Y-%m-%d"),
                            'match_time': match_datetime.isoformat(),
                            'source': 'melhorodd_betano',
                            'url': self.base_url,
                            'sport': sport_type,
                            'odds': odds
                        }
                        
                        matches.append(match_info)
                        match_count += 1
                        
                    except Exception as e:
                        logger.debug(f"Error processing row: {e}")
                        continue
                
                logger.info(f"Extracted {match_count} football matches with Betano odds")
            
            # If we found matches, cache them
            if matches:
                self.cached_matches = matches
                self.cached_time = datetime.now()
                return matches
            
            # If no matches found, try to look for JavaScript data
            logger.info("No football matches found in tables, looking for JavaScript data")
            js_content_pattern = re.compile(r'"matches":\s*(\[.+?\])', re.DOTALL)
            js_match = js_content_pattern.search(page_source)
            
            if js_match:
                try:
                    logger.info("Found JavaScript match data, attempting to parse")
                    matches_json = js_match.group(1)
                    matches_data = json.loads(matches_json)
                    
                    match_count = 0
                    for match_data in matches_data:
                        try:
                            # Check if this is a match with Betano odds
                            odds_data = match_data.get('odds', {})
                            betano_odds = None
                            
                            # Look for Betano specifically in the bookmakers
                            bookmakers = match_data.get('bookmakers', [])
                            for bookmaker in bookmakers:
                                if 'betano' in bookmaker.get('name', '').lower():
                                    betano_odds = bookmaker.get('odds', {})
                                    break
                            
                            # Skip if no Betano odds
                            if not betano_odds:
                                continue
                            
                            # Extract match info
                            match_info = {
                                'id': f"melhorodd_betano_js_{match_count}",
                                'home_team': match_data.get('homeTeam', {}).get('name', 'Unknown'),
                                'away_team': match_data.get('awayTeam', {}).get('name', 'Unknown'),
                                'league': match_data.get('competition', {}).get('name', 'Unknown League'),
                                'date': match_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                                'match_time': match_data.get('startTime', datetime.now().isoformat()),
                                'source': 'melhorodd_betano_js',
                                'url': self.base_url,
                                'sport': 'Football',
                                'odds': {
                                    'home_win': float(betano_odds.get('homeWin', 0)) or 0,
                                    'draw': float(betano_odds.get('draw', 0)) or 0,
                                    'away_win': float(betano_odds.get('awayWin', 0)) or 0,
                                    'over_2_5': float(betano_odds.get('over25', 0)) or 0,
                                    'under_2_5': float(betano_odds.get('under25', 0)) or 0,
                                    'btts_yes': float(betano_odds.get('bttsYes', 0)) or 0,
                                    'btts_no': float(betano_odds.get('bttsNo', 0)) or 0,
                                    'bookmaker': 'Betano'
                                }
                            }
                            
                            matches.append(match_info)
                            match_count += 1
                            
                        except Exception as e:
                            logger.warning(f"Error parsing JS match: {e}")
                    
                    logger.info(f"Extracted {match_count} football matches from JavaScript data")
                    
                    if matches:
                        self.cached_matches = matches
                        self.cached_time = datetime.now()
                        return matches
                        
                except Exception as e:
                    logger.warning(f"Failed to parse JavaScript match data: {e}")
            
        except Exception as e:
            logger.error(f"Error scraping MelhorOdd.pt: {e}")
            logger.exception("Exception details:")
        finally:
            # Close the driver
            driver.quit()
            logger.info("Closed WebDriver")
        
        # If we got here, we couldn't find any Betano odds for football matches
        logger.warning("Could not find any Betano odds from MelhorOdd's football section")
        return []

def scrape_betano_melhorodd_matches(days_ahead: int = 2) -> List[Dict[str, Any]]:
    """Convenience function to scrape matches with Betano odds from MelhorOdd.pt.
    
    Args:
        days_ahead: Number of days ahead to scrape
        
    Returns:
        List of dictionaries containing match information with Betano odds
    """
    scraper = BetanoMelhorOddScraper(days_ahead=days_ahead)
    return scraper.scrape_matches()

if __name__ == "__main__":
    # Run the scraper
    matches = scrape_betano_melhorodd_matches()
    print(f"Scraped {len(matches)} matches with Betano odds from MelhorOdd.pt")
    
    # Save to a JSON file for analysis
    with open("betano_melhorodd_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    # Print the first 3 matches
    for i, match in enumerate(matches[:3]):
        print(f"\nMatch {i+1}:")
        print(f"  {match['home_team']} vs {match['away_team']}")
        print(f"  Date: {match['date']} at {match['match_time'].split('T')[1][:5] if 'T' in match['match_time'] else '00:00'}")
        print(f"  League: {match['league']}")
        print(f"  Betano Odds: Home {match['odds']['home_win']} | Draw {match['odds']['draw']} | Away {match['odds']['away_win']}")
        if match['odds']['over_2_5'] > 0:
            print(f"  Over/Under 2.5: Over {match['odds']['over_2_5']} | Under {match['odds']['under_2_5']}") 