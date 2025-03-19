#!/usr/bin/env python3
"""
Tests for the Telegram Bot component of AI Football Betting Advisor.

This tests the bot's ability to format messages, handle commands,
and verify API connectivity.
"""

import os
import sys
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the TelegramBot class
from bot.telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def sample_bet_recommendations():
    """Create sample betting recommendations for testing."""
    return [
        {
            "match": {
                "id": "sample_match_1",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "Premier League",
                "match_time": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
            },
            "prediction": {
                "market": "match_winner",
                "selection": "home",
                "probability": 0.58,
                "confidence": "medium"
            },
            "odds": {
                "value": 2.2,
                "bookmaker": "bet365",
                "ev": 0.276  # Expected value: (probability * odds - 1)
            },
            "stake": {
                "amount": 25.0,
                "percentage": 2.5,
                "method": "kelly"
            }
        },
        {
            "match": {
                "id": "sample_match_2",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "league": "La Liga",
                "match_time": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
            },
            "prediction": {
                "market": "btts",
                "selection": "yes",
                "probability": 0.72,
                "confidence": "high"
            },
            "odds": {
                "value": 1.95,
                "bookmaker": "William Hill",
                "ev": 0.404  # Expected value: (probability * odds - 1)
            },
            "stake": {
                "amount": 40.0,
                "percentage": 4.0,
                "method": "kelly"
            }
        },
        {
            "match": {
                "id": "sample_match_3",
                "home_team": "Juventus",
                "away_team": "AC Milan",
                "league": "Serie A",
                "match_time": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
            },
            "prediction": {
                "market": "over_under_2_5",
                "selection": "over",
                "probability": 0.66,
                "confidence": "medium"
            },
            "odds": {
                "value": 1.85,
                "bookmaker": "Betfair",
                "ev": 0.221  # Expected value: (probability * odds - 1)
            },
            "stake": {
                "amount": 30.0,
                "percentage": 3.0,
                "method": "kelly"
            }
        }
    ]

@pytest.fixture
def sample_performance_data():
    """Create sample performance data for testing."""
    return {
        "overall": {
            "bets": 120,
            "wins": 54,
            "losses": 66,
            "profit_loss": 186.5,
            "roi": 15.54,
            "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        },
        "by_market": {
            "match_winner": {"bets": 60, "wins": 27, "profit_loss": 98.2, "roi": 16.37},
            "btts": {"bets": 30, "wins": 14, "profit_loss": 52.3, "roi": 17.43},
            "over_under_2_5": {"bets": 30, "wins": 13, "profit_loss": 36.0, "roi": 12.00}
        },
        "by_league": {
            "Premier League": {"bets": 30, "wins": 14, "profit_loss": 56.8, "roi": 18.93},
            "La Liga": {"bets": 25, "wins": 11, "profit_loss": 42.5, "roi": 17.00},
            "Serie A": {"bets": 25, "wins": 12, "profit_loss": 44.2, "roi": 17.68},
            "Bundesliga": {"bets": 20, "wins": 9, "profit_loss": 28.0, "roi": 14.00},
            "Ligue 1": {"bets": 20, "wins": 8, "profit_loss": 15.0, "roi": 7.50}
        },
        "by_confidence": {
            "high": {"bets": 40, "wins": 22, "profit_loss": 92.5, "roi": 23.13},
            "medium": {"bets": 50, "wins": 21, "profit_loss": 74.0, "roi": 14.80},
            "low": {"bets": 30, "wins": 11, "profit_loss": 20.0, "roi": 6.67}
        },
        "recent_bets": [
            {"match": "Liverpool vs Man Utd", "market": "match_winner", "selection": "home", "odds": 1.8, "stake": 30.0, "result": "win", "profit": 24.0, "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")},
            {"match": "Bayern vs Dortmund", "market": "over_under_2_5", "selection": "over", "odds": 1.7, "stake": 25.0, "result": "win", "profit": 17.5, "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")},
            {"match": "PSG vs Lyon", "market": "btts", "selection": "yes", "odds": 1.9, "stake": 30.0, "result": "loss", "profit": -30.0, "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")},
            {"match": "Inter vs Roma", "market": "match_winner", "selection": "home", "odds": 2.1, "stake": 20.0, "result": "win", "profit": 22.0, "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")},
            {"match": "Arsenal vs Spurs", "market": "btts", "selection": "yes", "odds": 1.75, "stake": 25.0, "result": "loss", "profit": -25.0, "date": datetime.now().strftime("%Y-%m-%d")}
        ]
    }

@pytest.mark.asyncio
async def test_bot_initialization():
    """Test that the bot initializes correctly with valid token."""
    with patch('telegram.Bot') as mock_bot_class:
        # Mock the Bot class
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        # Test initialization
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Verify bot was created with the token
        mock_bot_class.assert_called_once_with(token="test_token")
        
        # Check initialization status
        assert bot.initialized is True
        assert bot.chat_id == "test_chat_id"

@pytest.mark.asyncio
async def test_send_message():
    """Test sending a message through the bot."""
    with patch('telegram.Bot') as mock_bot_class:
        # Mock the Bot instance
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        # Create Telegram bot instance
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Test sending a message
        await bot.send_message("Test message")
        
        # Verify the message was sent
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        assert kwargs["chat_id"] == "test_chat_id"
        assert kwargs["text"] == "Test message"

@pytest.mark.asyncio
async def test_format_daily_tips(sample_bet_recommendations):
    """Test that daily tips are formatted correctly."""
    with patch('telegram.Bot'):
        # Create Telegram bot instance
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Format daily tips message
        message = bot.format_daily_tips(sample_bet_recommendations)
        
        # Verify message structure
        assert "🚨 DAILY BETTING TIPS 🚨" in message
        assert "Arsenal vs Chelsea" in message
        assert "Barcelona vs Real Madrid" in message
        assert "Juventus vs AC Milan" in message
        assert "Confidence: HIGH" in message  # Check confidence levels
        assert "Confidence: MEDIUM" in message
        assert "Expected Value: 40.4%" in message  # Check EV formatting
        assert "Stake: 40.0" in message  # Check stake
        assert "Odds: 1.95" in message  # Check odds

@pytest.mark.asyncio
async def test_format_performance_report(sample_performance_data):
    """Test that performance report is formatted correctly."""
    with patch('telegram.Bot'):
        # Create Telegram bot instance
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Format performance report message
        message = bot.format_performance_report(sample_performance_data)
        
        # Verify message structure
        assert "📊 PERFORMANCE REPORT 📊" in message
        assert "Total Bets: 120" in message
        assert "Win Rate: 45.0%" in message
        assert "ROI: 15.54%" in message
        assert "Profit/Loss: +186.50" in message
        
        # Check market breakdown
        assert "By Market:" in message
        assert "Match Winner: +98.20" in message
        
        # Check league breakdown
        assert "By League:" in message
        assert "Premier League: +56.80" in message
        
        # Check confidence level breakdown
        assert "By Confidence:" in message
        assert "HIGH (23.13%)" in message

@pytest.mark.asyncio
async def test_format_value_alert(sample_bet_recommendations):
    """Test that high-value bet alerts are formatted correctly."""
    with patch('telegram.Bot'):
        # Create Telegram bot instance
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Format high-value alert (using first recommendation)
        high_value_bet = sample_bet_recommendations[1]  # Using the BTTS bet with high confidence
        message = bot.format_value_alert(high_value_bet)
        
        # Verify message structure
        assert "🔥 HIGH VALUE BET ALERT 🔥" in message
        assert "Barcelona vs Real Madrid" in message
        assert "Market: Both Teams To Score" in message
        assert "Selection: Yes" in message
        assert "Confidence: HIGH" in message
        assert "Expected Value: 40.4%" in message
        assert "Recommended Stake: 40.0" in message
        assert "Odds: 1.95" in message
        assert "Bookmaker: William Hill" in message

@pytest.mark.asyncio
async def test_handle_commands():
    """Test the bot's command handling."""
    with patch('telegram.Bot'):
        # Create Telegram bot instance
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Mock get_performance_data method
        bot.get_performance_data = MagicMock(return_value=sample_performance_data())
        
        # Mock get_daily_tips method
        bot.get_daily_tips = MagicMock(return_value=sample_bet_recommendations())
        
        # Test command handling
        with patch.object(bot, 'send_message') as mock_send:
            # Test help command
            await bot.handle_command("/help")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "Available commands:" in args[0]
            mock_send.reset_mock()
            
            # Test tips command
            await bot.handle_command("/tips")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "DAILY BETTING TIPS" in args[0]
            mock_send.reset_mock()
            
            # Test performance command
            await bot.handle_command("/performance")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "PERFORMANCE REPORT" in args[0]
            mock_send.reset_mock()
            
            # Test start command
            await bot.handle_command("/start")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "Welcome to AI Football Betting Advisor" in args[0]
            mock_send.reset_mock()
            
            # Test unknown command
            await bot.handle_command("/unknown")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "Unknown command" in args[0]

@pytest.mark.asyncio
async def test_test_connection():
    """Test the connection test function."""
    with patch('telegram.Bot') as mock_bot_class:
        # Mock the Bot instance
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        # Set up the mock response
        mock_bot.get_me.return_value = {"id": 123456, "first_name": "TestBot", "username": "test_bot"}
        
        # Create Telegram bot instance
        bot = TelegramBot(token="test_token", chat_id="test_chat_id")
        
        # Test the connection
        result = await bot.test_connection()
        
        # Verify the connection was tested
        mock_bot.get_me.assert_called_once()
        assert result is True

@pytest.mark.asyncio
async def test_dry_run_mode():
    """Test that dry run mode doesn't actually send messages."""
    with patch('telegram.Bot') as mock_bot_class:
        # Mock the Bot instance
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        # Create Telegram bot instance in dry run mode
        bot = TelegramBot(token="test_token", chat_id="test_chat_id", dry_run=True)
        
        # Test sending a message in dry run mode
        await bot.send_message("Test message")
        
        # Verify the message was NOT sent
        mock_bot.send_message.assert_not_called()

if __name__ == "__main__":
    asyncio.run(pytest.main(["-xvs", __file__])) 