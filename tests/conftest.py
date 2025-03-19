"""
Pytest configuration file with common fixtures and settings.
"""
import pytest
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def test_data_dir():
    """Create and return a temporary directory for test data."""
    test_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    os.makedirs(test_dir, exist_ok=True)
    return test_dir

@pytest.fixture(scope="session")
def sample_team_mapping() -> Dict[str, str]:
    """Create a sample team name mapping for testing."""
    return {
        "man utd": "Manchester United",
        "ars": "Arsenal",
        "liv": "Liverpool",
        "che": "Chelsea",
        "mci": "Manchester City",
        "tot": "Tottenham Hotspur"
    }

@pytest.fixture(scope="session")
def sample_matches() -> List[Dict]:
    """Create sample match data for testing."""
    return [
        {
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "league": "Premier League",
            "match_date": datetime.now() + timedelta(days=1),
            "odds": [
                {
                    "market": "match_winner",
                    "home_odds": 2.50,
                    "away_odds": 2.80,
                    "draw_odds": 3.40
                },
                {
                    "market": "asian_handicap",
                    "home_odds": 1.95,
                    "away_odds": 1.85,
                    "handicap": 0.5
                }
            ],
            "status": "Not Started",
            "source": "flashscore"
        },
        {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "Premier League",
            "match_date": datetime.now() + timedelta(days=2),
            "odds": [
                {
                    "market": "match_winner",
                    "home_odds": 1.95,
                    "away_odds": 3.80,
                    "draw_odds": 3.50
                },
                {
                    "market": "btts",
                    "home_odds": 1.85,
                    "away_odds": 1.95
                }
            ],
            "status": "Not Started",
            "source": "sofascore"
        }
    ]

@pytest.fixture(scope="session")
def sample_odds_data() -> List[Dict]:
    """Create sample odds data for testing."""
    return [
        {
            "market": "match_winner",
            "home_odds": 2.50,
            "away_odds": 2.80,
            "draw_odds": 3.40,
            "source": "flashscore"
        },
        {
            "market": "asian_handicap",
            "home_odds": 1.95,
            "away_odds": 1.85,
            "handicap": 0.5,
            "source": "oddsportal"
        },
        {
            "market": "btts",
            "home_odds": 1.90,
            "away_odds": 1.90,
            "source": "oddschecker"
        }
    ]

@pytest.fixture(scope="session")
def mock_html_responses():
    """Create mock HTML responses for testing."""
    return {
        "flashscore": """
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
            </div>
            <div class="match-status">Not Started</div>
        </div>
        """,
        "sofascore": """
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
            </div>
            <div class="match-status">Not Started</div>
        </div>
        """
    }

def pytest_configure(config):
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as an async test"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    ) 