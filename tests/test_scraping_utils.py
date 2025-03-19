"""
Unit tests for ScrapingUtils class.
"""
import pytest
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from data.collectors.scraping_utils import (
    ScrapingUtils, OddsData, BettingMarket, RateLimiter
)

@pytest.fixture
def scraping_utils():
    """Create a ScrapingUtils instance for testing."""
    return ScrapingUtils()

@pytest.fixture
def sample_flashscore_html():
    """Create sample Flashscore HTML for testing."""
    return """
    <div class="match-row">
        <div class="match-header">
            <div class="team-name">Manchester United</div>
            <div class="team-name">Liverpool</div>
        </div>
        <div class="match-time">TODAY 20:00</div>
        <div class="odds-container">
            <div class="odds-value">2.50</div>
            <div class="odds-value">3.40</div>
            <div class="odds-value">2.80</div>
            <div class="asian-handicap-odds">
                <div class="odds-value">1.95</div>
                <div class="odds-value">1.85</div>
                <span>+0.5</span>
            </div>
            <div class="btts-odds">
                <div class="odds-value">1.90</div>
                <div class="odds-value">1.90</div>
            </div>
            <div class="corners-odds">
                <div class="odds-value">1.85</div>
                <div class="odds-value">1.95</div>
                <span>10.5</span>
            </div>
            <div class="half-odds">
                <div class="odds-value">2.20</div>
                <div class="odds-value">3.30</div>
                <div class="odds-value">3.00</div>
                <span>1st Half</span>
            </div>
            <div class="dnb-odds">
                <div class="odds-value">1.95</div>
                <div class="odds-value">1.85</div>
            </div>
        </div>
        <div class="match-status">Not Started</div>
    </div>
    """

@pytest.fixture
def sample_sofascore_html():
    """Create sample Sofascore HTML for testing."""
    return """
    <div class="match-row">
        <div class="match-header">
            <div class="team-name">Arsenal</div>
            <div class="team-name">Chelsea</div>
        </div>
        <div class="match-time">TOMORROW 15:30</div>
        <div class="odds-container">
            <div class="odds-value">1.95</div>
            <div class="odds-value">3.50</div>
            <div class="odds-value">3.80</div>
            <div class="asian-handicap-odds">
                <div class="odds-value">1.90</div>
                <div class="odds-value">1.90</div>
                <span>-0.5</span>
            </div>
            <div class="btts-odds">
                <div class="odds-value">1.85</div>
                <div class="odds-value">1.95</div>
            </div>
            <div class="corners-odds">
                <div class="odds-value">1.90</div>
                <div class="odds-value">1.90</div>
                <span>9.5</span>
            </div>
            <div class="half-odds">
                <div class="odds-value">2.00</div>
                <div class="odds-value">3.40</div>
                <div class="odds-value">3.20</div>
                <span>2nd Half</span>
            </div>
            <div class="dnb-odds">
                <div class="odds-value">1.90</div>
                <div class="odds-value">1.90</div>
            </div>
        </div>
        <div class="match-status">Not Started</div>
    </div>
    """

def test_rate_limiter():
    """Test RateLimiter functionality."""
    limiter = RateLimiter(calls_per_minute=2)
    
    # First two calls should be immediate
    assert limiter.calls == []
    
    # Third call should wait
    now = datetime.now()
    limiter.calls = [now - timedelta(seconds=30)]
    assert len(limiter.calls) == 1

def test_parse_match_time():
    """Test match time parsing."""
    utils = ScrapingUtils()
    
    # Test TODAY format
    today_time = utils._parse_match_time("TODAY 20:00")
    now = datetime.now()
    assert today_time.hour == 20
    assert today_time.minute == 0
    assert today_time.date() == now.date()
    
    # Test TOMORROW format
    tomorrow_time = utils._parse_match_time("TOMORROW 15:30")
    tomorrow = datetime.now() + timedelta(days=1)
    assert tomorrow_time.hour == 15
    assert tomorrow_time.minute == 30
    assert tomorrow_time.date() == tomorrow.date()
    
    # Test full datetime format
    full_time = utils._parse_match_time("2024-03-20 19:45")
    assert full_time.year == 2024
    assert full_time.month == 3
    assert full_time.day == 20
    assert full_time.hour == 19
    assert full_time.minute == 45

def test_parse_flashscore_match(scraping_utils, sample_flashscore_html):
    """Test Flashscore match parsing."""
    match_data = scraping_utils.parse_flashscore_match(sample_flashscore_html)
    
    # Test basic match data
    assert match_data['home_team'] == "Manchester United"
    assert match_data['away_team'] == "Liverpool"
    assert match_data['status'] == "Not Started"
    
    # Test odds data
    odds_list = match_data['odds']
    assert len(odds_list) > 0
    
    # Test match winner odds
    match_winner = next(o for o in odds_list if o.market == BettingMarket.MATCH_WINNER)
    assert match_winner.home_odds == 2.50
    assert match_winner.away_odds == 2.80
    assert match_winner.draw_odds == 3.40
    
    # Test Asian Handicap odds
    ah_odds = next(o for o in odds_list if o.market == BettingMarket.ASIAN_HANDICAP)
    assert ah_odds.handicap == 0.5
    assert ah_odds.home_odds == 1.95
    assert ah_odds.away_odds == 1.85
    
    # Test BTTS odds
    btts_odds = next(o for o in odds_list if o.market == BettingMarket.BTTS)
    assert btts_odds.home_odds == 1.90
    assert btts_odds.away_odds == 1.90

def test_parse_sofascore_match(scraping_utils, sample_sofascore_html):
    """Test Sofascore match parsing."""
    match_data = scraping_utils.parse_sofascore_match(sample_sofascore_html)
    
    # Test basic match data
    assert match_data['home_team'] == "Arsenal"
    assert match_data['away_team'] == "Chelsea"
    assert match_data['status'] == "Not Started"
    
    # Test odds data
    odds_list = match_data['odds']
    assert len(odds_list) > 0
    
    # Test match winner odds
    match_winner = next(o for o in odds_list if o.market == BettingMarket.MATCH_WINNER)
    assert match_winner.home_odds == 1.95
    assert match_winner.away_odds == 3.80
    assert match_winner.draw_odds == 3.50
    
    # Test Asian Handicap odds
    ah_odds = next(o for o in odds_list if o.market == BettingMarket.ASIAN_HANDICAP)
    assert ah_odds.handicap == -0.5
    assert ah_odds.home_odds == 1.90
    assert ah_odds.away_odds == 1.90

def test_validate_odds(scraping_utils):
    """Test odds validation."""
    # Test valid odds
    valid_odds = [
        OddsData(
            market=BettingMarket.MATCH_WINNER,
            home_odds=2.50,
            away_odds=2.80,
            draw_odds=3.40
        ),
        OddsData(
            market=BettingMarket.ASIAN_HANDICAP,
            home_odds=1.95,
            away_odds=1.85,
            handicap=0.5
        ),
        OddsData(
            market=BettingMarket.TOTAL_CORNERS,
            home_odds=1.85,
            away_odds=1.95,
            total=10.5
        )
    ]
    
    validated = scraping_utils.validate_odds(valid_odds)
    assert len(validated) == 3
    
    # Test invalid odds
    invalid_odds = [
        OddsData(
            market=BettingMarket.MATCH_WINNER,
            home_odds=0.95,  # Too low
            away_odds=2.80,
            draw_odds=3.40
        ),
        OddsData(
            market=BettingMarket.ASIAN_HANDICAP,
            home_odds=1.95,
            away_odds=1.85,
            handicap=6.0  # Too high
        ),
        OddsData(
            market=BettingMarket.TOTAL_CORNERS,
            home_odds=1.85,
            away_odds=1.95,
            total=25.0  # Too high
        )
    ]
    
    validated = scraping_utils.validate_odds(invalid_odds)
    assert len(validated) == 0

def test_standardize_team_name(scraping_utils):
    """Test team name standardization."""
    # Test with mapping
    assert scraping_utils.standardize_team_name("Man Utd") == "Manchester United"
    assert scraping_utils.standardize_team_name("Ars") == "Arsenal"
    
    # Test without mapping
    assert scraping_utils.standardize_team_name("New Team") == "New Team"
    
    # Test case insensitivity
    assert scraping_utils.standardize_team_name("MAN UTD") == "Manchester United" 