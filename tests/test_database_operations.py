"""
Integration tests for database operations.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from data.storage.models import (
    Match, Odds, Bet, Bankroll, BettingMarket,
    MatchStatus, BetResult, BetType
)
from data.storage.database import Database

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def database():
    """Create a test database instance."""
    db = Database(test_mode=True)
    await db.initialize()
    yield db
    await db.close()

@pytest.fixture(scope="function")
async def clean_database(database):
    """Clean the database before each test."""
    await database.execute("TRUNCATE TABLE matches CASCADE")
    await database.execute("TRUNCATE TABLE odds CASCADE")
    await database.execute("TRUNCATE TABLE bets CASCADE")
    await database.execute("TRUNCATE TABLE bankroll CASCADE")

@pytest.mark.asyncio
async def test_match_storage_and_retrieval(database, sample_matches):
    """Test storing and retrieving match data."""
    # Store matches
    for match_data in sample_matches:
        match = Match(
            home_team=match_data["home_team"],
            away_team=match_data["away_team"],
            league=match_data["league"],
            match_date=match_data["match_date"],
            status=MatchStatus.NOT_STARTED,
            source=match_data["source"]
        )
        await database.store_match(match)
    
    # Retrieve matches
    stored_matches = await database.get_matches(
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7)
    )
    
    assert len(stored_matches) == len(sample_matches)
    assert all(
        stored.home_team == sample["home_team"] and
        stored.away_team == sample["away_team"]
        for stored, sample in zip(stored_matches, sample_matches)
    )

@pytest.mark.asyncio
async def test_odds_storage_and_deduplication(database, sample_odds_data):
    """Test storing and deduplicating odds data."""
    # Create a test match
    match = Match(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        status=MatchStatus.NOT_STARTED,
        source="flashscore"
    )
    await database.store_match(match)
    
    # Store odds
    for odds_data in sample_odds_data:
        odds = Odds(
            match_id=match.id,
            market=BettingMarket(odds_data["market"]),
            home_odds=odds_data["home_odds"],
            away_odds=odds_data["away_odds"],
            draw_odds=odds_data.get("draw_odds"),
            handicap=odds_data.get("handicap"),
            total=odds_data.get("total"),
            source=odds_data["source"]
        )
        await database.store_odds(odds)
    
    # Store duplicate odds
    for odds_data in sample_odds_data:
        odds = Odds(
            match_id=match.id,
            market=BettingMarket(odds_data["market"]),
            home_odds=odds_data["home_odds"],
            away_odds=odds_data["away_odds"],
            draw_odds=odds_data.get("draw_odds"),
            handicap=odds_data.get("handicap"),
            total=odds_data.get("total"),
            source=odds_data["source"]
        )
        await database.store_odds(odds)
    
    # Retrieve odds
    stored_odds = await database.get_match_odds(match.id)
    assert len(stored_odds) == len(sample_odds_data)  # Should be deduplicated

@pytest.mark.asyncio
async def test_bet_storage_and_roi_calculation(database):
    """Test storing bets and calculating ROI."""
    # Create a test match
    match = Match(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        status=MatchStatus.NOT_STARTED,
        source="flashscore"
    )
    await database.store_match(match)
    
    # Store odds
    odds = Odds(
        match_id=match.id,
        market=BettingMarket.MATCH_WINNER,
        home_odds=2.50,
        away_odds=2.80,
        draw_odds=3.40,
        source="flashscore"
    )
    await database.store_odds(odds)
    
    # Create initial bankroll
    bankroll = Bankroll(
        amount=1000.0,
        currency="USD",
        timestamp=datetime.now()
    )
    await database.store_bankroll(bankroll)
    
    # Place bets
    bets = [
        Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=2.50,
            result=BetResult.WON
        ),
        Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="away",
            stake=100.0,
            odds=2.80,
            result=BetResult.LOST
        )
    ]
    
    for bet in bets:
        await database.store_bet(bet)
        await database.update_bankroll(bet)
    
    # Calculate ROI
    roi = await database.calculate_roi(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now() + timedelta(days=1)
    )
    
    # Expected ROI: (250 - 100) / 200 = 75%
    assert abs(roi - 0.75) < 0.01

@pytest.mark.asyncio
async def test_bankroll_tracking(database):
    """Test bankroll tracking and updates."""
    # Create initial bankroll
    initial_bankroll = Bankroll(
        amount=1000.0,
        currency="USD",
        timestamp=datetime.now()
    )
    await database.store_bankroll(initial_bankroll)
    
    # Create a test match and odds
    match = Match(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        status=MatchStatus.NOT_STARTED,
        source="flashscore"
    )
    await database.store_match(match)
    
    odds = Odds(
        match_id=match.id,
        market=BettingMarket.MATCH_WINNER,
        home_odds=2.50,
        away_odds=2.80,
        draw_odds=3.40,
        source="flashscore"
    )
    await database.store_odds(odds)
    
    # Place a winning bet
    bet = Bet(
        match_id=match.id,
        odds_id=odds.id,
        bet_type=BetType.MATCH_WINNER,
        selection="home",
        stake=100.0,
        odds=2.50,
        result=BetResult.WON
    )
    await database.store_bet(bet)
    await database.update_bankroll(bet)
    
    # Check bankroll
    current_bankroll = await database.get_current_bankroll()
    assert current_bankroll.amount == 1150.0  # 1000 + (100 * 2.50 - 100)

@pytest.mark.asyncio
async def test_bet_history_retrieval(database):
    """Test retrieving bet history with various filters."""
    # Create test data
    match = Match(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        status=MatchStatus.NOT_STARTED,
        source="flashscore"
    )
    await database.store_match(match)
    
    odds = Odds(
        match_id=match.id,
        market=BettingMarket.MATCH_WINNER,
        home_odds=2.50,
        away_odds=2.80,
        draw_odds=3.40,
        source="flashscore"
    )
    await database.store_odds(odds)
    
    # Place various bets
    bets = [
        Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=2.50,
            result=BetResult.WON
        ),
        Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="away",
            stake=100.0,
            odds=2.80,
            result=BetResult.LOST
        ),
        Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.ASIAN_HANDICAP,
            selection="home",
            stake=100.0,
            odds=1.95,
            result=BetResult.WON
        )
    ]
    
    for bet in bets:
        await database.store_bet(bet)
    
    # Test various filters
    all_bets = await database.get_bet_history()
    assert len(all_bets) == 3
    
    winning_bets = await database.get_bet_history(result=BetResult.WON)
    assert len(winning_bets) == 2
    
    match_winner_bets = await database.get_bet_history(bet_type=BetType.MATCH_WINNER)
    assert len(match_winner_bets) == 2
    
    # Test date range filter
    date_range_bets = await database.get_bet_history(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now() + timedelta(days=2)
    )
    assert len(date_range_bets) == 3 