#!/usr/bin/env python3
"""
End-to-End System Test for AI Football Betting Advisor

This script executes a full betting workflow test, covering:
- Match data fetching & processing
- ML predictions & confidence scores
- Odds evaluation & value bet detection
- Stake recommendations using various strategies
- Telegram bot message formatting & delivery
"""

import os
import sys
import unittest
import asyncio
import datetime
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import components to test
from data.scraping_utils import ScrapingUtils, OddsData
from data.match_collector import MatchCollector
from models.prediction import PredictionModel, Prediction, ConfidenceLevel
from betting.odds_evaluator import OddsEvaluator, ValueBet
from betting.staking import StakingStrategy, StakingMethod, BetRecommendation
from bot.telegram_bot import TelegramBot

class EndToEndTest(unittest.TestCase):
    """End-to-end test for the complete betting workflow."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Initialize test configuration
        cls.config = {
            'bankroll': 1000.0,
            'max_stake_percent': 5.0,
            'min_odds': 1.5,
            'max_odds': 10.0,
            'min_ev_threshold': 0.05,
            'telegram_token': 'mock_token',
            'test_mode': True
        }
        
        # Create test instances
        cls.scraping_utils = ScrapingUtils()
        cls.match_collector = MatchCollector()
        cls.prediction_model = PredictionModel()
        cls.odds_evaluator = OddsEvaluator(
            min_ev_threshold=cls.config['min_ev_threshold'],
            min_odds=cls.config['min_odds'],
            max_odds=cls.config['max_odds']
        )
        cls.staking_strategy = StakingStrategy(
            bankroll=cls.config['bankroll'],
            method=StakingMethod.KELLY,
            max_stake_percent=cls.config['max_stake_percent']
        )
        cls.telegram_bot = TelegramBot(token=cls.config['telegram_token'], test_mode=cls.config['test_mode'])

    async def test_full_workflow(self):
        """Test the full betting workflow from data fetching to notification."""
        print("\n--- Testing full betting workflow ---")
        
        # 1. Fetch upcoming matches
        print("1. Fetching upcoming matches...")
        with patch.object(self.match_collector, 'get_upcoming_matches') as mock_fetch:
            # Mock response with sample matches
            mock_fetch.return_value = self._get_sample_matches()
            matches = await self.match_collector.get_upcoming_matches()
            
            self.assertIsNotNone(matches)
            self.assertGreater(len(matches), 0)
            print(f"✅ Successfully fetched {len(matches)} upcoming matches")
        
        # 2. Fetch match details and odds
        print("\n2. Fetching match details and odds...")
        match_id = matches[0]['id']
        
        with patch.object(self.match_collector, 'get_match_details') as mock_details:
            mock_details.return_value = self._get_sample_match_details(match_id)
            match_data = await self.match_collector.get_match_details(match_id)
            
            self.assertIsNotNone(match_data)
            self.assertEqual(match_data['id'], match_id)
            print(f"✅ Successfully fetched details for match: {match_data['home_team']} vs {match_data['away_team']}")
        
        with patch.object(self.match_collector, 'get_match_odds') as mock_odds:
            mock_odds.return_value = self._get_sample_odds_data()
            odds_data = await self.match_collector.get_match_odds(match_id)
            
            self.assertIsNotNone(odds_data)
            self.assertGreater(len(odds_data), 0)
            print(f"✅ Successfully fetched odds for {len(odds_data)} betting markets")
            
        # 3. Make predictions using ML model
        print("\n3. Making predictions with ML model...")
        with patch.object(self.prediction_model, 'predict_match') as mock_predict:
            # Mock prediction results
            mock_predict.return_value = self._get_sample_predictions(match_id)
            
            predictions = await self.prediction_model.predict_match(match_data, odds_data)
            
            self.assertIsNotNone(predictions)
            self.assertGreater(len(predictions), 0)
            print(f"✅ Generated {len(predictions)} predictions with confidence levels")
            
            # Print prediction details
            for pred in predictions:
                print(f"  - {pred.market}: {pred.selection} (Confidence: {pred.confidence.value}, Prob: {pred.probability:.2f})")
        
        # 4. Evaluate odds and find value bets
        print("\n4. Evaluating odds and finding value bets...")
        with patch.object(self.odds_evaluator, 'evaluate_odds') as mock_evaluate:
            # Mock value bets
            mock_evaluate.return_value = self._get_sample_value_bets(match_data)
            
            value_bets = self.odds_evaluator.evaluate_odds(match_data, odds_data, predictions)
            
            self.assertIsNotNone(value_bets)
            self.assertGreater(len(value_bets), 0)
            print(f"✅ Found {len(value_bets)} value bets")
            
            # Print value bet details
            for bet in value_bets:
                print(f"  - {bet.home_team} vs {bet.away_team}")
                print(f"    {bet.market}: {bet.selection} @ {bet.odds}")
                print(f"    Expected Value: {bet.expected_value:.2f}, Confidence: {bet.confidence.value}")
        
        # 5. Calculate optimal stakes
        print("\n5. Calculating optimal stakes...")
        with patch.object(self.staking_strategy, 'calculate_stakes') as mock_stakes:
            # Mock stakes
            mock_stakes.return_value = self._get_sample_bet_recommendations(value_bets)
            
            bet_recommendations = self.staking_strategy.calculate_stakes(value_bets)
            
            self.assertIsNotNone(bet_recommendations)
            self.assertGreater(len(bet_recommendations), 0)
            print(f"✅ Calculated stakes for {len(bet_recommendations)} bets")
            
            # Print stake details
            for bet in bet_recommendations:
                print(f"  - {bet.home_team} vs {bet.away_team}")
                print(f"    {bet.market}: {bet.selection} @ {bet.odds}")
                print(f"    Stake: ${bet.stake:.2f} ({bet.stake_percentage:.1f}% of bankroll)")
        
        # 6. Format and send Telegram notifications
        print("\n6. Formatting and sending Telegram notifications...")
        with patch.object(self.telegram_bot, 'send_daily_tips') as mock_send:
            # Use the first bet recommendation to test high value alert
            high_value_bet = bet_recommendations[0]
            
            await self.telegram_bot.send_daily_tips("mock_chat_id")
            await self.telegram_bot.send_high_value_alert("mock_chat_id", high_value_bet)
            
            last_message = self.telegram_bot.last_sent_message
            self.assertIsNotNone(last_message)
            print(f"✅ Successfully formatted and sent betting tips via Telegram")
        
        print("\n✅ Full end-to-end betting workflow test completed successfully!")
    
    def _get_sample_matches(self):
        """Generate sample matches for testing."""
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        return [
            {
                "id": "match_1",
                "home_team": "Liverpool",
                "away_team": "Manchester City",
                "league": "Premier League",
                "match_time": tomorrow.strftime("%Y-%m-%d %H:%M"),
                "status": "upcoming",
                "source": "flashscore"
            },
            {
                "id": "match_2",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "league": "La Liga",
                "match_time": tomorrow.strftime("%Y-%m-%d %H:%M"),
                "status": "upcoming",
                "source": "sofascore"
            }
        ]
    
    def _get_sample_match_details(self, match_id):
        """Generate sample match details for testing."""
        if match_id == "match_1":
            return {
                "id": "match_1",
                "home_team": "Liverpool",
                "away_team": "Manchester City",
                "league": "Premier League",
                "match_time": "2023-03-19 15:00",
                "status": "upcoming",
                "venue": "Anfield",
                "home_form": ["W", "W", "D", "L", "W"],
                "away_form": ["W", "W", "W", "D", "W"],
                "home_league_position": 2,
                "away_league_position": 1,
                "head_to_head": [
                    {"date": "2022-10-16", "home_score": 1, "away_score": 0},
                    {"date": "2022-04-10", "home_score": 2, "away_score": 2},
                    {"date": "2021-10-03", "home_score": 2, "away_score": 2},
                    {"date": "2021-02-07", "home_score": 1, "away_score": 4},
                    {"date": "2020-11-08", "home_score": 1, "away_score": 1}
                ]
            }
        else:
            return {
                "id": "match_2",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "league": "La Liga",
                "match_time": "2023-03-19 20:00",
                "status": "upcoming",
                "venue": "Camp Nou",
                "home_form": ["W", "W", "W", "W", "D"],
                "away_form": ["W", "D", "W", "W", "W"],
                "home_league_position": 1,
                "away_league_position": 2,
                "head_to_head": [
                    {"date": "2022-10-16", "home_score": 0, "away_score": 1},
                    {"date": "2022-03-20", "home_score": 0, "away_score": 4},
                    {"date": "2022-01-12", "home_score": 2, "away_score": 3},
                    {"date": "2021-10-24", "home_score": 1, "away_score": 2},
                    {"date": "2021-04-10", "home_score": 2, "away_score": 1}
                ]
            }
    
    def _get_sample_odds_data(self):
        """Generate sample odds data for testing."""
        return {
            "match_winner": [
                {"selection": "home", "odds": 2.1, "bookmaker": "bet365"},
                {"selection": "draw", "odds": 3.4, "bookmaker": "bet365"},
                {"selection": "away", "odds": 3.5, "bookmaker": "bet365"}
            ],
            "over_under_2_5": [
                {"selection": "over", "odds": 1.85, "bookmaker": "bet365"},
                {"selection": "under", "odds": 2.0, "bookmaker": "bet365"}
            ],
            "btts": [
                {"selection": "yes", "odds": 1.7, "bookmaker": "bet365"},
                {"selection": "no", "odds": 2.2, "bookmaker": "bet365"}
            ]
        }
    
    def _get_sample_predictions(self, match_id):
        """Generate sample predictions for testing."""
        return [
            Prediction(
                match_id=match_id,
                market="match_winner",
                selection="home",
                probability=0.52,
                confidence=ConfidenceLevel.HIGH,
                expected_value=0.092,
                reasoning="Liverpool has strong home form and is ranked higher than Manchester City. Our model gives them a 52.0% chance of winning."
            ),
            Prediction(
                match_id=match_id,
                market="over_under_2_5",
                selection="over",
                probability=0.65,
                confidence=ConfidenceLevel.MEDIUM,
                expected_value=0.1025,
                reasoning="Historical matches between Liverpool and Manchester City have been high-scoring. Our model predicts a 65.0% chance of over 2.5 goals."
            ),
            Prediction(
                match_id=match_id,
                market="btts",
                selection="yes",
                probability=0.72,
                confidence=ConfidenceLevel.HIGH,
                expected_value=0.084,
                reasoning="Both Liverpool and Manchester City have been scoring regularly. Our model predicts a 72.0% chance of both teams scoring."
            )
        ]
    
    def _get_sample_value_bets(self, match_data):
        """Generate sample value bets for testing."""
        return [
            ValueBet(
                match_id=match_data["id"],
                home_team=match_data["home_team"],
                away_team=match_data["away_team"],
                match_time=match_data["match_time"],
                league=match_data["league"],
                market="match_winner",
                selection="home",
                odds=2.1,
                bookmaker="bet365",
                probability=0.52,
                expected_value=0.092,
                confidence=ConfidenceLevel.HIGH,
                reasoning="Liverpool has strong home form and is ranked higher than Manchester City. Our model gives them a 52.0% chance of winning."
            ),
            ValueBet(
                match_id=match_data["id"],
                home_team=match_data["home_team"],
                away_team=match_data["away_team"],
                match_time=match_data["match_time"],
                league=match_data["league"],
                market="over_under_2_5",
                selection="over",
                odds=1.85,
                bookmaker="bet365",
                probability=0.65,
                expected_value=0.1025,
                confidence=ConfidenceLevel.MEDIUM,
                reasoning="Historical matches between Liverpool and Manchester City have been high-scoring. Our model predicts a 65.0% chance of over 2.5 goals."
            )
        ]
    
    def _get_sample_bet_recommendations(self, value_bets):
        """Generate sample bet recommendations for testing."""
        bet_recommendations = []
        
        for i, bet in enumerate(value_bets):
            stake_percentage = 2.0 if i == 0 else 1.5
            stake = 1000.0 * (stake_percentage / 100.0)
            
            recommendation = BetRecommendation(
                match_id=bet.match_id,
                home_team=bet.home_team,
                away_team=bet.away_team,
                match_time=bet.match_time,
                league=bet.league,
                market=bet.market,
                selection=bet.selection,
                odds=bet.odds,
                bookmaker=bet.bookmaker,
                probability=bet.probability,
                expected_value=bet.expected_value,
                confidence=bet.confidence,
                reasoning=bet.reasoning,
                stake=stake,
                stake_percentage=stake_percentage
            )
            
            bet_recommendations.append(recommendation)
            
        return bet_recommendations


def run_tests():
    """Run all end-to-end tests."""
    # Create async test suite
    loop = asyncio.get_event_loop()
    
    # Create test instance
    test = EndToEndTest()
    
    # Run the test
    loop.run_until_complete(test.test_full_workflow())
    
    # Close the loop
    loop.close()


if __name__ == "__main__":
    run_tests() 