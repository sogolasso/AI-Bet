"""
Stress tests for the AI Football Betting Advisor system.
"""
import pytest
import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from data.collectors.match_collector import MatchCollector
from data.storage.database import Database
from data.storage.models import (
    Match, Odds, Bet, Bankroll, BettingMarket,
    MatchStatus, BetResult, BetType
)
from bot.telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@pytest.fixture(scope="session")
def match_collector():
    """Create a MatchCollector instance for testing."""
    return MatchCollector()

@pytest.fixture(scope="session")
def telegram_bot():
    """Create a TelegramBot instance for testing."""
    return TelegramBot(test_mode=True)

def get_system_metrics():
    """Get current system metrics."""
    process = psutil.Process()
    return {
        'cpu_percent': process.cpu_percent(),
        'memory_percent': process.memory_percent(),
        'threads': process.num_threads(),
        'open_files': len(process.open_files())
    }

@pytest.mark.asyncio
async def test_high_volume_scraping(match_collector):
    """Test system stability under high-volume web scraping."""
    logger.info("Starting high-volume scraping test")
    start_metrics = get_system_metrics()
    
    # Simulate scraping 1000 matches
    tasks = []
    for _ in range(1000):
        tasks.append(match_collector._fetch_flashscore_matches(days_ahead=7))
        tasks.append(match_collector._fetch_sofascore_matches(days_ahead=7))
    
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    end_metrics = get_system_metrics()
    
    # Log performance metrics
    logger.info(f"High-volume scraping completed in {end_time - start_time:.2f} seconds")
    logger.info(f"CPU usage: {end_metrics['cpu_percent']}%")
    logger.info(f"Memory usage: {end_metrics['memory_percent']}%")
    
    # Assert system stability
    assert end_metrics['cpu_percent'] < 90  # CPU should not be maxed out
    assert end_metrics['memory_percent'] < 80  # Memory usage should be reasonable
    assert end_metrics['threads'] < 100  # Thread count should be controlled

@pytest.mark.asyncio
async def test_database_stress(database):
    """Test database performance under high load."""
    logger.info("Starting database stress test")
    start_metrics = get_system_metrics()
    
    # Create test data
    matches = []
    odds_list = []
    bets = []
    
    # Generate 1000 matches with odds and bets
    for i in range(1000):
        match = Match(
            home_team=f"Team {i}",
            away_team=f"Team {i+1}",
            league="Premier League",
            match_date=datetime.now() + timedelta(days=i),
            status=MatchStatus.NOT_STARTED,
            source="flashscore"
        )
        matches.append(match)
        
        odds = Odds(
            match_id=match.id,
            market=BettingMarket.MATCH_WINNER,
            home_odds=2.50,
            away_odds=2.80,
            draw_odds=3.40,
            source="flashscore"
        )
        odds_list.append(odds)
        
        bet = Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=2.50,
            result=BetResult.WON
        )
        bets.append(bet)
    
    # Perform rapid database operations
    start_time = time.time()
    
    # Store matches
    for match in matches:
        await database.store_match(match)
    
    # Store odds
    for odds in odds_list:
        await database.store_odds(odds)
    
    # Store bets
    for bet in bets:
        await database.store_bet(bet)
    
    # Perform concurrent queries
    query_tasks = []
    for match in matches:
        query_tasks.append(database.get_match_odds(match.id))
        query_tasks.append(database.get_bet_history(match_id=match.id))
    
    await asyncio.gather(*query_tasks)
    
    end_time = time.time()
    end_metrics = get_system_metrics()
    
    # Log performance metrics
    logger.info(f"Database stress test completed in {end_time - start_time:.2f} seconds")
    logger.info(f"CPU usage: {end_metrics['cpu_percent']}%")
    logger.info(f"Memory usage: {end_metrics['memory_percent']}%")
    
    # Assert database stability
    assert end_metrics['cpu_percent'] < 90
    assert end_metrics['memory_percent'] < 80
    assert end_time - start_time < 30  # Should complete within 30 seconds

@pytest.mark.asyncio
async def test_telegram_bot_stress(telegram_bot):
    """Test Telegram bot under high user load."""
    logger.info("Starting Telegram bot stress test")
    start_metrics = get_system_metrics()
    
    # Simulate multiple users sending commands
    mock_updates = []
    mock_contexts = []
    
    for i in range(100):  # Simulate 100 users
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.chat = Mock(spec=Chat)
        update.message.chat.id = i
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = i
        mock_updates.append(update)
        
        context = Mock(spec=CallbackContext)
        context.bot = AsyncMock()
        mock_contexts.append(context)
    
    # Send commands concurrently
    start_time = time.time()
    
    command_tasks = []
    for update, context in zip(mock_updates, mock_contexts):
        # Simulate different commands
        update.message.text = "/start"
        command_tasks.append(telegram_bot.start_command(update, context))
        
        update.message.text = "/help"
        command_tasks.append(telegram_bot.help_command(update, context))
        
        update.message.text = "/stats"
        command_tasks.append(telegram_bot.stats_command(update, context))
    
    await asyncio.gather(*command_tasks)
    
    end_time = time.time()
    end_metrics = get_system_metrics()
    
    # Log performance metrics
    logger.info(f"Telegram bot stress test completed in {end_time - start_time:.2f} seconds")
    logger.info(f"CPU usage: {end_metrics['cpu_percent']}%")
    logger.info(f"Memory usage: {end_metrics['memory_percent']}%")
    
    # Assert bot stability
    assert end_metrics['cpu_percent'] < 90
    assert end_metrics['memory_percent'] < 80
    assert end_time - start_time < 10  # Should complete within 10 seconds

@pytest.mark.asyncio
async def test_end_to_end_betting_workflow(database, match_collector, telegram_bot):
    """Test complete betting workflow under load."""
    logger.info("Starting end-to-end betting workflow test")
    start_metrics = get_system_metrics()
    
    # 1. Fetch matches and odds
    start_time = time.time()
    matches = await match_collector.fetch_upcoming_matches(days_ahead=7)
    odds_list = []
    
    for match in matches:
        odds = await match_collector.fetch_match_odds(match)
        odds_list.extend(odds)
    
    # 2. Store data
    for match in matches:
        await database.store_match(match)
    
    for odds in odds_list:
        await database.store_odds(odds)
    
    # 3. Simulate bet placement
    bets = []
    for match, odds in zip(matches, odds_list):
        bet = Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=odds.home_odds,
            result=BetResult.WON
        )
        bets.append(bet)
        await database.store_bet(bet)
        await database.update_bankroll(bet)
    
    # 4. Generate reports
    report_tasks = []
    for _ in range(10):  # Generate multiple reports concurrently
        report_tasks.append(telegram_bot._generate_performance_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        ))
    
    await asyncio.gather(*report_tasks)
    
    end_time = time.time()
    end_metrics = get_system_metrics()
    
    # Log performance metrics
    logger.info(f"End-to-end workflow completed in {end_time - start_time:.2f} seconds")
    logger.info(f"CPU usage: {end_metrics['cpu_percent']}%")
    logger.info(f"Memory usage: {end_metrics['memory_percent']}%")
    
    # Assert workflow stability
    assert end_metrics['cpu_percent'] < 90
    assert end_metrics['memory_percent'] < 80
    assert end_time - start_time < 60  # Should complete within 60 seconds 