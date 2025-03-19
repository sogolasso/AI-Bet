"""
Unit tests for MatchCollector class.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from data.collectors.match_collector import MatchCollector, MatchData
from data.collectors.scraping_utils import OddsData, BettingMarket

@pytest.fixture
def match_collector():
    """Create a MatchCollector instance for testing."""
    return MatchCollector()

@pytest.fixture
def sample_match_data():
    """Create sample match data for testing."""
    return MatchData(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        odds=[
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
            )
        ],
        status="Not Started",
        source="flashscore"
    )

@pytest.mark.asyncio
async def test_fetch_upcoming_matches(match_collector):
    """Test fetching upcoming matches."""
    # Mock the scraping utils methods
    match_collector.scraping_utils.fetch_page = AsyncMock(return_value="<html>")
    match_collector.scraping_utils.parse_flashscore_match = Mock(return_value={
        'home_team': 'Manchester United',
        'away_team': 'Liverpool',
        'league': 'Premier League',
        'match_date': datetime.now() + timedelta(days=1),
        'odds': [],
        'status': 'Not Started'
    })
    
    matches = await match_collector.fetch_upcoming_matches(days_ahead=7)
    assert len(matches) > 0
    assert matches[0].home_team == "Manchester United"
    assert matches[0].away_team == "Liverpool"

@pytest.mark.asyncio
async def test_fetch_match_odds(match_collector, sample_match_data):
    """Test fetching match odds."""
    # Mock the scraping utils methods
    match_collector.scraping_utils.fetch_page = AsyncMock(return_value="<html>")
    match_collector.scraping_utils.parse_oddsportal_odds = Mock(return_value=[
        OddsData(
            market=BettingMarket.MATCH_WINNER,
            home_odds=2.50,
            away_odds=2.80,
            draw_odds=3.40,
            source="oddsportal"
        )
    ])
    
    odds = await match_collector.fetch_match_odds(sample_match_data)
    assert len(odds) > 0
    assert odds[0].market == BettingMarket.MATCH_WINNER
    assert odds[0].source == "oddsportal"

@pytest.mark.asyncio
async def test_cache_odds(match_collector, sample_match_data):
    """Test odds caching functionality."""
    # First fetch - should not be in cache
    odds1 = await match_collector.fetch_match_odds(sample_match_data)
    
    # Second fetch - should be in cache
    odds2 = await match_collector.fetch_match_odds(sample_match_data)
    assert odds1 == odds2
    
    # Wait for cache to expire
    match_collector.cache_ttl = 0
    odds3 = await match_collector.fetch_match_odds(sample_match_data)
    assert odds1 != odds3  # Should be different as cache expired

def test_deduplicate_matches(match_collector):
    """Test match deduplication."""
    matches = [
        MatchData(
            home_team="Manchester United",
            away_team="Liverpool",
            league="Premier League",
            match_date=datetime.now(),
            odds=[],
            status="Not Started"
        ),
        MatchData(
            home_team="Manchester United",
            away_team="Liverpool",
            league="Premier League",
            match_date=datetime.now(),
            odds=[],
            status="Not Started"
        ),
        MatchData(
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            match_date=datetime.now(),
            odds=[],
            status="Not Started"
        )
    ]
    
    deduplicated = match_collector._deduplicate_matches(matches)
    assert len(deduplicated) == 2  # Should remove one duplicate

def test_deduplicate_odds(match_collector):
    """Test odds deduplication."""
    odds = [
        OddsData(
            market=BettingMarket.MATCH_WINNER,
            home_odds=2.50,
            away_odds=2.80,
            draw_odds=3.40
        ),
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
            market=BettingMarket.ASIAN_HANDICAP,
            home_odds=1.95,
            away_odds=1.85,
            handicap=0.5
        )
    ]
    
    deduplicated = match_collector._deduplicate_odds(odds)
    assert len(deduplicated) == 2  # Should remove duplicates

@pytest.mark.asyncio
async def test_error_handling(match_collector):
    """Test error handling in match collector."""
    # Mock network error
    match_collector.scraping_utils.fetch_page = AsyncMock(side_effect=Exception("Network error"))
    
    # Should handle error gracefully
    matches = await match_collector.fetch_upcoming_matches(days_ahead=7)
    assert len(matches) == 0
    
    # Mock parsing error
    match_collector.scraping_utils.fetch_page = AsyncMock(return_value="<html>")
    match_collector.scraping_utils.parse_flashscore_match = Mock(side_effect=Exception("Parsing error"))
    
    # Should handle error gracefully
    matches = await match_collector.fetch_upcoming_matches(days_ahead=7)
    assert len(matches) == 0 