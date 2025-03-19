"""
Tests for Telegram bot functionality.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, Message, Chat, User
from telegram.ext import CallbackContext
from bot.telegram_bot import TelegramBot
from data.storage.models import (
    Match, Odds, Bet, Bankroll, BettingMarket,
    MatchStatus, BetResult, BetType
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def telegram_bot():
    """Create a TelegramBot instance for testing."""
    return TelegramBot(test_mode=True)

@pytest.fixture
def mock_update():
    """Create a mock Telegram update."""
    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.chat = Mock(spec=Chat)
    update.message.chat.id = 123456789
    update.message.from_user = Mock(spec=User)
    update.message.from_user.id = 123456789
    return update

@pytest.fixture
def mock_context():
    """Create a mock callback context."""
    context = Mock(spec=CallbackContext)
    context.bot = AsyncMock()
    return context

@pytest.mark.asyncio
async def test_start_command(telegram_bot, mock_update, mock_context):
    """Test the /start command."""
    mock_update.message.text = "/start"
    
    await telegram_bot.start_command(mock_update, mock_context)
    
    # Verify welcome message was sent
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[0][1]
    assert "Welcome to the AI Football Betting Advisor" in message_text

@pytest.mark.asyncio
async def test_help_command(telegram_bot, mock_update, mock_context):
    """Test the /help command."""
    mock_update.message.text = "/help"
    
    await telegram_bot.help_command(mock_update, mock_context)
    
    # Verify help message was sent
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[0][1]
    assert "Available commands" in message_text

@pytest.mark.asyncio
async def test_bet_recommendation(telegram_bot, mock_update, mock_context):
    """Test bet recommendation message formatting."""
    # Create test match and odds
    match = Match(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        status=MatchStatus.NOT_STARTED,
        source="flashscore"
    )
    
    odds = Odds(
        match_id=match.id,
        market=BettingMarket.MATCH_WINNER,
        home_odds=2.50,
        away_odds=2.80,
        draw_odds=3.40,
        source="flashscore"
    )
    
    # Format bet recommendation
    message = telegram_bot._format_bet_recommendation(match, odds, "home", 2.50, "HIGH")
    
    # Verify message format
    assert "Manchester United vs Liverpool" in message
    assert "Premier League" in message
    assert "Match Winner" in message
    assert "Home Win" in message
    assert "Odds: 2.50" in message
    assert "Confidence: HIGH" in message

@pytest.mark.asyncio
async def test_roi_report(telegram_bot, mock_update, mock_context):
    """Test ROI report generation."""
    # Mock database ROI calculation
    telegram_bot.database.calculate_roi = AsyncMock(return_value=0.15)
    
    # Generate ROI report
    message = await telegram_bot._generate_roi_report(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    
    # Verify report format
    assert "ROI Report" in message
    assert "15.00%" in message
    assert "Last 30 days" in message

@pytest.mark.asyncio
async def test_bet_history(telegram_bot, mock_update, mock_context):
    """Test bet history retrieval and formatting."""
    # Mock database bet history
    telegram_bot.database.get_bet_history = AsyncMock(return_value=[
        Bet(
            match_id=1,
            odds_id=1,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=2.50,
            result=BetResult.WON
        ),
        Bet(
            match_id=2,
            odds_id=2,
            bet_type=BetType.ASIAN_HANDICAP,
            selection="home",
            stake=100.0,
            odds=1.95,
            result=BetResult.LOST
        )
    ])
    
    # Generate bet history report
    message = await telegram_bot._generate_bet_history_report(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )
    
    # Verify report format
    assert "Bet History" in message
    assert "Last 7 days" in message
    assert "Won: 1" in message
    assert "Lost: 1" in message

@pytest.mark.asyncio
async def test_error_handling(telegram_bot, mock_update, mock_context):
    """Test error handling in bot commands."""
    # Test database error
    telegram_bot.database.get_bet_history = AsyncMock(side_effect=Exception("Database error"))
    
    await telegram_bot.bet_history_command(mock_update, mock_context)
    
    # Verify error message was sent
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[0][1]
    assert "Error" in message_text
    assert "Database error" in message_text

@pytest.mark.asyncio
async def test_high_value_bet_alert(telegram_bot, mock_update, mock_context):
    """Test high-value bet alert functionality."""
    # Create test match with high-value odds
    match = Match(
        home_team="Manchester United",
        away_team="Liverpool",
        league="Premier League",
        match_date=datetime.now() + timedelta(days=1),
        status=MatchStatus.NOT_STARTED,
        source="flashscore"
    )
    
    odds = Odds(
        match_id=match.id,
        market=BettingMarket.MATCH_WINNER,
        home_odds=3.50,  # High-value odds
        away_odds=2.20,
        draw_odds=3.40,
        source="flashscore"
    )
    
    # Send high-value bet alert
    await telegram_bot._send_high_value_bet_alert(match, odds, "home", 3.50)
    
    # Verify alert was sent
    mock_context.bot.send_message.assert_called_once()
    message_text = mock_context.bot.send_message.call_args[0][1]
    assert "HIGH VALUE BET ALERT" in message_text
    assert "Odds: 3.50" in message_text

@pytest.mark.asyncio
async def test_performance_report(telegram_bot, mock_update, mock_context):
    """Test performance report generation."""
    # Mock database performance data
    telegram_bot.database.get_bet_history = AsyncMock(return_value=[
        Bet(
            match_id=1,
            odds_id=1,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=2.50,
            result=BetResult.WON
        ),
        Bet(
            match_id=2,
            odds_id=2,
            bet_type=BetType.ASIAN_HANDICAP,
            selection="home",
            stake=100.0,
            odds=1.95,
            result=BetResult.WON
        ),
        Bet(
            match_id=3,
            odds_id=3,
            bet_type=BetType.BTTS,
            selection="yes",
            stake=100.0,
            odds=1.90,
            result=BetResult.LOST
        )
    ])
    
    # Generate performance report
    message = await telegram_bot._generate_performance_report(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    
    # Verify report format
    assert "Performance Report" in message
    assert "Win Rate: 66.67%" in message
    assert "Total Bets: 3" in message
    assert "Won: 2" in message
    assert "Lost: 1" in message 