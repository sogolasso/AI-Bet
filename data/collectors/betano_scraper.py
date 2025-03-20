import logging
import time
import random
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class BetanoScraper:
    """Selenium-based browser scraper for Betano.pt."""
    
    def __init__(self, days_ahead: int = 2, headless: bool = False):
        """Initialize the Betano scraper.
        
        Args:
            days_ahead: Number of days ahead to scrape
            headless: Whether to run in headless mode (default False for Betano)
        """
        self.days_ahead = days_ahead
        self.headless = headless
        self.base_url = 'https://www.betano.pt'
        
        # Football-specific URLs
        self.urls = [
            # Today's football matches
            f'{self.base_url}/sport/futebol/jogos-de-hoje/',
            # Tomorrow's football matches
            f'{self.base_url}/sport/futebol/jogos-de-amanha/'
        ]
        
        # Add more days if needed
        if days_ahead > 2:
            self.urls.append(f'{self.base_url}/sport/futebol/jogos-2-dias/')
        
        # User agents for randomization - focus on modern browsers with Portuguese locale
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
        
        # Screen sizes for randomization - focus on common desktop resolutions
        self.screen_sizes = [
            (1920, 1080),
            (1366, 768),
            (1440, 900),
            (1536, 864)
        ]
        
        # Debug mode - saves HTML and screenshots
        self.debug = True
        self.debug_dir = "debug"
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up the Chrome WebDriver with anti-detection features.
        
        Returns:
            Configured Chrome WebDriver instance
        """
        # Set up Chrome options
        chrome_options = Options()
        
        # Headless mode setup - with additional arguments for better rendering
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # These window size settings are crucial for headless mode
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
        else:
            # Choose a random screen size for non-headless mode
            width, height = random.choice(self.screen_sizes)
            chrome_options.add_argument(f"--window-size={width},{height}")
        
        # Choose a random user agent
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f"user-agent={user_agent}")
        
        # Set Portuguese language to help with localization
        chrome_options.add_argument("--lang=pt-PT")
        
        # Disable automation flag
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Disable notifications
        chrome_options.add_argument("--disable-notifications")
        
        # Enable JavaScript
        chrome_options.add_argument("--enable-javascript")
        
        # Add additional performance options
        chrome_options.add_argument("--disable-extensions")
        
        # Create a custom profile with pre-accepted cookies
        prefs = {
            "profile.default_content_setting_values.cookies": 1,
            "profile.cookie_controls_mode": 0,
            "profile.block_third_party_cookies": False,
            "profile.managed_default_content_settings.images": 1,
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Set up ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Modify navigator properties to avoid detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-PT', 'pt', 'en-US', 'en']
                });
                
                // Add better fingerprinting evasion
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                Object.defineProperty(navigator, 'productSub', {
                    get: () => '20100101'
                });
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
            """
        })
        
        # Set location to Portugal to avoid geo-blocking
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": 38.736946,  # Lisbon, Portugal
            "longitude": -9.142685,
            "accuracy": 100
        })
        
        return driver

    def _accept_cookies(self, driver: webdriver.Chrome) -> bool:
        """Accept cookies and close any popup dialogs.
        
        Args:
            driver: Chrome WebDriver instance
            
        Returns:
            True if cookies were accepted successfully
        """
        try:
            # First save screenshot for analysis
            if self.debug:
                driver.save_screenshot(f"{self.debug_dir}/before_cookie_accept.png")
            
            # Multiple approaches to find and click cookie consent buttons
            
            # Approach 1: Common cookie button selectors with WebDriverWait
            cookie_selectors = [
                "button.cookie-consent-btn",
                "button.btn-accept",
                "button[aria-label*='cookie']",
                "button.agree-button",
                "button.consent-btn",
                "button.accept-cookies",
                "button#onetrust-accept-btn-handler",
                "button.CybotCookiebotDialogBodyButton",
                "button[data-test-id='cookie-accept-all']"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_consent = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cookie_consent.click()
                    logger.info(f"Cookies accepted successfully with selector: {selector}")
                    time.sleep(1)
                    return True
                except:
                    continue
            
            # Approach 2: Look for buttons with specific text content
            cookie_texts = ["Accept", "Accept All", "I Accept", "Accept Cookies", "Allow", "Allow All", "Aceitar", "Concordar"]
            
            for text in cookie_texts:
                try:
                    # Find all buttons and check their text
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        if text.lower() in button.text.lower() and button.is_displayed():
                            button.click()
                            logger.info(f"Cookies accepted by clicking button with text: {text}")
                            time.sleep(1)
                            return True
                except:
                    continue
            
            # Approach 3: JavaScript click on likely elements
            js_selectors = [
                "document.querySelector('button.cookie-consent-btn')",
                "document.querySelector('button.btn-accept')",
                "document.querySelector('button[aria-label*=\"cookie\"]')",
                "document.querySelector('div.cookie-banner button')",
                "document.querySelector('.cookies button')",
                "document.querySelector('.gdpr button')"
            ]
            
            for js_selector in js_selectors:
                try:
                    driver.execute_script(f"if({js_selector}) {{ {js_selector}.click(); }}")
                    logger.info(f"Attempted JavaScript click on cookie button with: {js_selector}")
                    time.sleep(1)
                except:
                    continue
            
            # If we got here, we didn't find a specific cookie button, but that's ok
            # The site might not have a cookie banner or it might be automatically handled
            logger.info("No specific cookie consent button found or automatically handled")
            return True
            
        except Exception as e:
            logger.error(f"Error in cookie acceptance process: {e}")
            # Return true anyway to continue the process
            return True
    
    def _close_popups(self, driver: webdriver.Chrome) -> None:
        """Close any popup dialogs like registration prompts.
        
        Args:
            driver: Chrome WebDriver instance
        """
        try:
            # Look for common close buttons in popups
            close_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button.close-btn, button.popup-close, button[aria-label='Close'], div.bt-modal__close"
            )
            
            for button in close_buttons:
                if button.is_displayed():
                    logger.info("Found popup to close")
                    try:
                        button.click()
                        logger.info("Popup closed successfully")
                        time.sleep(1)  # Wait for animation
                    except ElementClickInterceptedException:
                        # Try with JavaScript if normal click doesn't work
                        driver.execute_script("arguments[0].click();", button)
                        logger.info("Popup closed using JavaScript")
                        time.sleep(1)
        
            # Check for specific close X button in the registration dialog
            close_x = driver.find_elements(By.CSS_SELECTOR, "button.registration-form__close, div.modal-close")
            for x_button in close_x:
                if x_button.is_displayed():
                    try:
                        x_button.click()
                        logger.info("Registration dialog closed")
                        time.sleep(1)
                    except Exception:
                        driver.execute_script("arguments[0].click();", x_button)
                        
        except Exception as e:
            logger.warning(f"Error closing popups: {e}")
    
    def _scroll_page(self, driver: webdriver.Chrome) -> None:
        """Scroll the page like a human to load dynamic content.
        
        Args:
            driver: Chrome WebDriver instance
        """
        try:
            # Get initial page height
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            # Scroll in chunks with random pauses
            viewport_height = driver.execute_script("return window.innerHeight")
            scroll_positions = list(range(0, last_height, int(viewport_height * 0.7)))
            
            # Limit number of scroll positions to avoid excessive scrolling
            if len(scroll_positions) > 5:
                scroll_positions = scroll_positions[:5]
            
            for pos in scroll_positions:
                # Scroll to position
                driver.execute_script(f"window.scrollTo(0, {pos});")
                
                # Random pause like a human
                time.sleep(random.uniform(0.5, 1.5))
                
                # Occasionally move mouse to simulate human behavior - only in non-headless mode
                # In headless mode, this can cause "move target out of bounds" errors
                if random.random() > 0.7 and not self.headless:
                    try:
                        # Get window dimensions
                        window_width = driver.execute_script("return window.innerWidth")
                        window_height = driver.execute_script("return window.innerHeight")
                        
                        # Calculate safe mouse movement - stay within viewport
                        safe_x = random.randint(int(window_width * 0.1), int(window_width * 0.9))
                        safe_y = random.randint(int(window_height * 0.1), int(window_height * 0.9))
                        
                        ActionChains(driver).move_by_offset(safe_x, safe_y).perform()
                    except Exception as e:
                        logger.warning(f"Mouse movement failed, ignoring: {e}")
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            logger.warning(f"Error during page scrolling: {e}")
            # Continue execution even if scrolling fails
            
    def _extract_match_data(self, driver: webdriver.Chrome) -> List[Dict[str, Any]]:
        """Extract football match data from the Betano page.
        
        Args:
            driver: Chrome WebDriver instance
            
        Returns:
            List of dictionaries containing match information
        """
        matches = []
        match_counter = 0
        
        try:
            # Save the page source for debugging first
            if self.debug:
                with open(f"{self.debug_dir}/betano_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                driver.save_screenshot(f"{self.debug_dir}/betano_page.png")
            
            # Wait for the events containers to load - use multiple selectors
            selectors = [
                "div.events-list", 
                "div.events-list__grid",
                "div.events-list__grid__event", 
                "a.event-selection"
            ]
            
            # Try each selector until one works
            for selector in selectors:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found elements with selector: {selector}")
                    break
                except:
                    continue
            
            # Try different approaches to find competition blocks
            competition_blocks = []
            
            # First attempt - standard competition groups
            competition_blocks = driver.find_elements(By.CSS_SELECTOR, "div.events-list__group")
            if not competition_blocks:
                # Second attempt - alternative layout
                competition_blocks = driver.find_elements(By.CSS_SELECTOR, "div.events-list-group")
            if not competition_blocks:
                # Third attempt - look for event sections
                competition_blocks = driver.find_elements(By.CSS_SELECTOR, "section.events-block")
            if not competition_blocks:
                # Last resort - treat the whole page as one block
                competition_blocks = [driver.find_element(By.TAG_NAME, "body")]
            
            logger.info(f"Found {len(competition_blocks)} competition blocks")
            
            for comp_idx, competition_block in enumerate(competition_blocks):
                try:
                    # Extract competition name
                    competition_name = "Unknown League"
                    competition_selectors = [
                        "div.events-list__title",
                        "h2.title",
                        "div.title",
                        "div.competition-name"
                    ]
                    
                    for selector in competition_selectors:
                        try:
                            competition_elem = competition_block.find_element(By.CSS_SELECTOR, selector)
                            competition_name = competition_elem.text.strip()
                            if competition_name:
                                break
                        except:
                            continue
                    
                    logger.info(f"Processing competition: {competition_name}")
                    
                    # Extract match events - try multiple selectors
                    match_elements = []
                    match_selectors = [
                        "div.events-list__grid__event", 
                        "div.event-list-component", 
                        "div.event", 
                        "div.events-list__grid a",
                        "a.event"
                    ]
                    
                    for selector in match_selectors:
                        try:
                            elements = competition_block.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                match_elements = elements
                                logger.info(f"Found {len(match_elements)} match elements using selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not match_elements:
                        logger.warning(f"No match elements found in competition {competition_name}")
                        continue
                    
                    logger.info(f"Processing {len(match_elements)} match elements in {competition_name}")
                    
                    for match_idx, match_element in enumerate(match_elements):
                        try:
                            # Extract match date and time
                            date_element = None
                            date_selectors = [
                                "div.event-time", 
                                "span.event-time", 
                                "div.events-list__grid__info__date", 
                                "div.events-list__grid__info",
                                "span.starting-time"
                            ]
                            
                            for selector in date_selectors:
                                try:
                                    date_element = match_element.find_element(By.CSS_SELECTOR, selector)
                                    if date_element:
                                        break
                                except:
                                    continue
                            
                            if not date_element:
                                logger.warning(f"Could not find date element for match {match_idx+1}")
                                continue
                            
                            date_time_text = date_element.text.strip()
                            
                            # Parse date and time - format varies
                            match_datetime = self._parse_date_time(date_time_text)
                            if not match_datetime:
                                logger.warning(f"Could not parse date time from: {date_time_text}")
                                continue
                            
                            # Skip if match is too far in the future
                            if match_datetime > datetime.now() + timedelta(days=self.days_ahead):
                                continue
                            
                            # Extract teams
                            home_team = None
                            away_team = None
                            
                            # Try approach 1: team containers
                            team_containers = []
                            team_selectors = [
                                "div.event-participants span.event-participant", 
                                "span.participant-container",
                                "div.event-participant",
                                "span.teams-name"
                            ]
                            
                            for selector in team_selectors:
                                try:
                                    containers = match_element.find_elements(By.CSS_SELECTOR, selector)
                                    if len(containers) >= 2:
                                        team_containers = containers
                                        break
                                except:
                                    continue
                            
                            if len(team_containers) >= 2:
                                home_team = team_containers[0].text.strip()
                                away_team = team_containers[1].text.strip()
                            else:
                                # Try approach 2: find teams text and split
                                teams_text = None
                                teams_selectors = [
                                    "div.event-teams",
                                    "div.participants",
                                    "div.event-description"
                                ]
                                
                                for selector in teams_selectors:
                                    try:
                                        teams_element = match_element.find_element(By.CSS_SELECTOR, selector)
                                        if teams_element:
                                            teams_text = teams_element.text
                                            break
                                    except:
                                        continue
                                
                                if teams_text:
                                    separator = " - "
                                    if separator in teams_text:
                                        teams = teams_text.split(separator)
                                        if len(teams) >= 2:
                                            home_team = teams[0].strip()
                                            away_team = teams[1].strip()
                            
                            if not home_team or not away_team:
                                logger.warning(f"Could not extract teams for match {match_idx+1} in {competition_name}")
                                continue
                            
                            # Extract odds
                            odds_elements = []
                            odds_selectors = [
                                "div.selection", 
                                "div.odd-item", 
                                "span.odd", 
                                "span.selections-item", 
                                "div.event-pick", 
                                "a.event-selection span.selection-price"
                            ]
                            
                            for selector in odds_selectors:
                                try:
                                    elements = match_element.find_elements(By.CSS_SELECTOR, selector)
                                    if len(elements) >= 3:
                                        odds_elements = elements
                                        break
                                except:
                                    continue
                            
                            home_win_odds = 0
                            draw_odds = 0
                            away_win_odds = 0
                            
                            # Main odds (1X2)
                            if len(odds_elements) >= 3:
                                try:
                                    home_win_odds = float(odds_elements[0].text.strip().replace(',', '.'))
                                    draw_odds = float(odds_elements[1].text.strip().replace(',', '.'))
                                    away_win_odds = float(odds_elements[2].text.strip().replace(',', '.'))
                                except (ValueError, IndexError):
                                    logger.warning(f"Error extracting main odds for {home_team} vs {away_team}")
                            
                            # Create match info dictionary
                            match_info = {
                                "id": f"betano_{match_counter}",
                                "home_team": home_team,
                                "away_team": away_team,
                                "league": competition_name,
                                "date": match_datetime.strftime("%Y-%m-%d"),
                                "match_time": match_datetime.isoformat(),
                                "source": "betano_direct",
                                "url": driver.current_url,
                                "sport": "Football",
                                "odds": {
                                    "home_win": home_win_odds,
                                    "draw": draw_odds,
                                    "away_win": away_win_odds,
                                    "bookmaker": "Betano"
                                }
                            }
                            
                            matches.append(match_info)
                            match_counter += 1
                            logger.info(f"Extracted match: {home_team} vs {away_team}")
                            
                        except Exception as e:
                            logger.warning(f"Error processing match {match_idx+1} in {competition_name}: {e}")
                            continue
                
                except Exception as e:
                    logger.warning(f"Error processing competition block {comp_idx+1}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {match_counter} matches")
            
            # Save extracted matches to JSON for debugging
            if self.debug:
                with open(f"{self.debug_dir}/betano_matches.json", "w", encoding="utf-8") as f:
                    json.dump(matches, f, indent=2, ensure_ascii=False)
            
            return matches
            
        except Exception as e:
            logger.error(f"Error extracting match data: {e}")
            return []
    
    def _parse_date_time(self, date_time_text: str) -> datetime:
        """Parse date and time from Betano's format.
        
        Args:
            date_time_text: Date and time text from Betano
            
        Returns:
            Datetime object or None if parsing fails
        """
        try:
            # Format could be "25/12 20:30", "Hoje, 20:45", "Amanhã, 20:45"
            now = datetime.now()
            
            # Case: "Hoje, 20:45" (Today, 20:45)
            if "hoje" in date_time_text.lower():
                time_part = re.search(r"(\d{1,2}):(\d{2})", date_time_text)
                if time_part:
                    hour, minute = map(int, time_part.groups())
                    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Case: "Amanhã, 20:45" (Tomorrow, 20:45)
            elif "amanhã" in date_time_text.lower() or "amanha" in date_time_text.lower():
                time_part = re.search(r"(\d{1,2}):(\d{2})", date_time_text)
                if time_part:
                    hour, minute = map(int, time_part.groups())
                    tomorrow = now + timedelta(days=1)
                    return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Case: "25/12 20:30"
            date_match = re.search(r"(\d{1,2})/(\d{1,2})", date_time_text)
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_time_text)
            
            if date_match and time_match:
                day, month = map(int, date_match.groups())
                hour, minute = map(int, time_match.groups())
                
                # Assume current year, but handle December-January transition
                year = now.year
                if month < now.month:
                    year += 1
                
                return datetime(year, month, day, hour, minute, 0)
            
            # Couldn't parse, return None
            logger.warning(f"Could not parse date time: {date_time_text}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date time '{date_time_text}': {e}")
            return None

    def scrape_matches(self) -> List[Dict[str, Any]]:
        """Scrape football matches from Betano.
        
        Returns:
            List of dictionaries containing match information
        """
        all_matches = []
        driver = None
        
        try:
            # Set up WebDriver
            driver = self._setup_driver()
            logger.info("WebDriver initialized")
            
            for url_idx, url in enumerate(self.urls):
                logger.info(f"Processing URL {url_idx+1}/{len(self.urls)}: {url}")
                try:
                    # Navigate to URL
                    driver.get(url)
                    logger.info(f"Navigated to {url}")
                    
                    # Accept cookies and close popups
                    if url_idx == 0:  # Only need to do this once
                        self._accept_cookies(driver)
                        self._close_popups(driver)
                    
                    # Wait for page to load
                    time.sleep(3)
                    
                    # Scroll page to load dynamic content
                    self._scroll_page(driver)
                    
                    # Close any popups that might have appeared after scrolling
                    self._close_popups(driver)
                    
                    # Extract match data
                    url_matches = self._extract_match_data(driver)
                    logger.info(f"Extracted {len(url_matches)} matches from {url}")
                    
                    # Add matches to all_matches if they're not already there
                    existing_match_keys = {f"{m['home_team']}|{m['away_team']}|{m['date']}" for m in all_matches}
                    
                    for match in url_matches:
                        match_key = f"{match['home_team']}|{match['away_team']}|{match['date']}"
                        if match_key not in existing_match_keys:
                            all_matches.append(match)
                    
                    logger.info(f"Total unique matches so far: {len(all_matches)}")
                    
                    # Random pause between URLs
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(all_matches)} unique matches from Betano")
            
            return all_matches
            
        except Exception as e:
            logger.error(f"Error scraping Betano: {e}")
            logger.exception("Exception details:")
            return []
        finally:
            if driver:
                driver.quit()
                logger.info("WebDriver closed")

def scrape_betano_matches(days_ahead: int = 2, headless: bool = False) -> List[Dict[str, Any]]:
    """Convenience function to scrape matches from Betano.
    
    Args:
        days_ahead: Number of days ahead to scrape
        headless: Whether to run in headless mode
        
    Returns:
        List of dictionaries containing match information
    """
    scraper = BetanoScraper(days_ahead=days_ahead, headless=headless)
    return scraper.scrape_matches()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the scraper
    matches = scrape_betano_matches(headless=False)
    print(f"Scraped {len(matches)} matches from Betano")
    
    # Save to a JSON file for analysis
    with open("betano_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    # Print the first 3 matches
    for i, match in enumerate(matches[:3]):
        print(f"\nMatch {i+1}:")
        print(f"  {match['home_team']} vs {match['away_team']}")
        print(f"  Date: {match['date']} at {match['match_time'].split('T')[1][:5] if 'T' in match['match_time'] else '00:00'}")
        print(f"  League: {match['league']}")
        print(f"  Betano Odds: Home {match['odds']['home_win']} | Draw {match['odds']['draw']} | Away {match['odds']['away_win']}") 