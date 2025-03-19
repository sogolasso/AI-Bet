#!/usr/bin/env python3
"""
ML Model Backtesting for AI Football Betting Advisor

This script performs backtesting of the prediction model against historical match data
to validate accuracy, ROI, and performance across different leagues and bet types.
"""

import os
import sys
import asyncio
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import components to test
from models.prediction import PredictionModel, Prediction, ConfidenceLevel
from betting.odds_evaluator import OddsEvaluator
from betting.staking import StakingStrategy, StakingMethod, BetRecommendation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelBacktesting:
    """Performs backtesting of the prediction model against historical data."""
    
    def __init__(self, historical_data_path: str = "data/historical"):
        """Initialize the backtesting process.
        
        Args:
            historical_data_path: Path to historical match and odds data
        """
        self.historical_data_path = historical_data_path
        self.prediction_model = PredictionModel()
        self.odds_evaluator = OddsEvaluator(
            min_ev_threshold=0.03,  # Lower threshold for backtesting to get more bets
            min_odds=1.3,
            max_odds=15.0
        )
        self.staking_strategy = StakingStrategy(
            bankroll=1000.0,
            method=StakingMethod.KELLY,
            max_stake_percent=3.0,  # More conservative for backtesting
            kelly_fraction=0.3      # Fractional Kelly for safety
        )
        
        # Metrics tracking
        self.metrics = {
            "total_matches": 0,
            "total_bets": 0,
            "winning_bets": 0,
            "losing_bets": 0,
            "total_stake": 0.0,
            "total_return": 0.0,
            "roi": 0.0,
            "leagues": {},
            "markets": {},
            "confidence_levels": {
                "HIGH": {"bets": 0, "wins": 0, "roi": 0.0},
                "MEDIUM": {"bets": 0, "wins": 0, "roi": 0.0},
                "LOW": {"bets": 0, "wins": 0, "roi": 0.0}
            },
            "monthly_performance": {}
        }
        
        # Bankroll tracking for equity curve
        self.initial_bankroll = 1000.0
        self.current_bankroll = self.initial_bankroll
        self.bankroll_history = [(datetime.now(), self.initial_bankroll)]
        
        # Load historical data
        self._load_historical_data()
    
    def _load_historical_data(self):
        """Load historical match and odds data from files."""
        logger.info(f"Loading historical data from {self.historical_data_path}")
        
        # Mock historical data for testing
        # In a real implementation, this would load actual historical data
        self.historical_matches = self._generate_mock_historical_data()
        
        logger.info(f"Loaded {len(self.historical_matches)} historical matches")
    
    def _generate_mock_historical_data(self) -> List[Dict[str, Any]]:
        """Generate mock historical data for testing.
        
        In a real implementation, this would load actual historical data from files.
        
        Returns:
            List of historical match data with results
        """
        historical_matches = []
        
        # Generate matches for the past 10 weeks
        for week in range(10, 0, -1):
            match_date = datetime.now() - timedelta(days=week*7)
            
            # Generate Premier League matches
            for i in range(5):  # 5 matches per week
                home_team = f"Team {i*2 + 1}"
                away_team = f"Team {i*2 + 2}"
                
                # Generate realistic scores with home advantage
                if np.random.random() < 0.45:  # Home win
                    home_score = np.random.randint(1, 4)
                    away_score = np.random.randint(0, home_score)
                elif np.random.random() < 0.7:  # Draw
                    home_score = np.random.randint(0, 3)
                    away_score = home_score
                else:  # Away win
                    away_score = np.random.randint(1, 4)
                    home_score = np.random.randint(0, away_score)
                
                # Create match data with results
                match = {
                    "id": f"match_{week}_{i}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": "Premier League",
                    "match_time": match_date.strftime("%Y-%m-%d %H:%M"),
                    "status": "completed",
                    "venue": f"{home_team} Stadium",
                    "home_form": ["W", "D", "W", "L", "W"],
                    "away_form": ["L", "W", "W", "D", "L"],
                    "home_league_position": i*2 + 1,
                    "away_league_position": i*2 + 2,
                    "head_to_head": [
                        {"date": (match_date - timedelta(days=180)).strftime("%Y-%m-%d"), "home_score": 2, "away_score": 1},
                        {"date": (match_date - timedelta(days=360)).strftime("%Y-%m-%d"), "home_score": 1, "away_score": 1}
                    ],
                    "result": {
                        "home_score": home_score,
                        "away_score": away_score,
                        "match_winner": "home" if home_score > away_score else "draw" if home_score == away_score else "away",
                        "over_under_2_5": "over" if home_score + away_score > 2.5 else "under",
                        "btts": "yes" if home_score > 0 and away_score > 0 else "no"
                    },
                    "odds": {
                        "match_winner": [
                            {"selection": "home", "odds": 2.0 + np.random.random(), "bookmaker": "bet365"},
                            {"selection": "draw", "odds": 3.0 + np.random.random(), "bookmaker": "bet365"},
                            {"selection": "away", "odds": 3.0 + np.random.random(), "bookmaker": "bet365"}
                        ],
                        "over_under_2_5": [
                            {"selection": "over", "odds": 1.8 + np.random.random() * 0.5, "bookmaker": "bet365"},
                            {"selection": "under", "odds": 1.8 + np.random.random() * 0.5, "bookmaker": "bet365"}
                        ],
                        "btts": [
                            {"selection": "yes", "odds": 1.7 + np.random.random() * 0.5, "bookmaker": "bet365"},
                            {"selection": "no", "odds": 1.9 + np.random.random() * 0.6, "bookmaker": "bet365"}
                        ]
                    }
                }
                
                historical_matches.append(match)
            
            # Generate some La Liga matches
            for i in range(3):  # 3 matches per week
                home_team = f"Spanish Team {i*2 + 1}"
                away_team = f"Spanish Team {i*2 + 2}"
                
                # Generate realistic scores
                if np.random.random() < 0.45:
                    home_score = np.random.randint(1, 4)
                    away_score = np.random.randint(0, home_score)
                elif np.random.random() < 0.7:
                    home_score = np.random.randint(0, 3)
                    away_score = home_score
                else:
                    away_score = np.random.randint(1, 4)
                    home_score = np.random.randint(0, away_score)
                
                match = {
                    "id": f"match_laliga_{week}_{i}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": "La Liga",
                    "match_time": match_date.strftime("%Y-%m-%d %H:%M"),
                    "status": "completed",
                    "venue": f"{home_team} Stadium",
                    "home_form": ["W", "W", "L", "W", "D"],
                    "away_form": ["D", "W", "W", "L", "W"],
                    "home_league_position": i*2 + 1,
                    "away_league_position": i*2 + 2,
                    "head_to_head": [
                        {"date": (match_date - timedelta(days=180)).strftime("%Y-%m-%d"), "home_score": 2, "away_score": 0},
                        {"date": (match_date - timedelta(days=360)).strftime("%Y-%m-%d"), "home_score": 1, "away_score": 2}
                    ],
                    "result": {
                        "home_score": home_score,
                        "away_score": away_score,
                        "match_winner": "home" if home_score > away_score else "draw" if home_score == away_score else "away",
                        "over_under_2_5": "over" if home_score + away_score > 2.5 else "under",
                        "btts": "yes" if home_score > 0 and away_score > 0 else "no"
                    },
                    "odds": {
                        "match_winner": [
                            {"selection": "home", "odds": 1.8 + np.random.random(), "bookmaker": "bet365"},
                            {"selection": "draw", "odds": 3.2 + np.random.random(), "bookmaker": "bet365"},
                            {"selection": "away", "odds": 3.5 + np.random.random(), "bookmaker": "bet365"}
                        ],
                        "over_under_2_5": [
                            {"selection": "over", "odds": 1.7 + np.random.random() * 0.5, "bookmaker": "bet365"},
                            {"selection": "under", "odds": 2.0 + np.random.random() * 0.5, "bookmaker": "bet365"}
                        ],
                        "btts": [
                            {"selection": "yes", "odds": 1.6 + np.random.random() * 0.5, "bookmaker": "bet365"},
                            {"selection": "no", "odds": 2.1 + np.random.random() * 0.6, "bookmaker": "bet365"}
                        ]
                    }
                }
                
                historical_matches.append(match)
        
        return historical_matches
    
    async def run_backtesting(self):
        """Run backtesting process on historical data."""
        logger.info("Starting model backtesting process")
        
        # Process each historical match
        for match_idx, match in enumerate(self.historical_matches):
            try:
                logger.info(f"Processing match {match_idx+1}/{len(self.historical_matches)}: "
                           f"{match['home_team']} vs {match['away_team']} ({match['league']})")
                
                # Extract match data (without result to avoid leakage)
                match_data = {k: v for k, v in match.items() if k != 'result'}
                
                # Convert odds format to match the expected input format
                odds_data = match.get('odds', {})
                
                # Update total matches count
                self.metrics["total_matches"] += 1
                
                # Update league metrics
                league = match.get('league', 'Unknown')
                if league not in self.metrics["leagues"]:
                    self.metrics["leagues"][league] = {
                        "matches": 0,
                        "bets": 0,
                        "wins": 0,
                        "stake": 0.0,
                        "return": 0.0,
                        "roi": 0.0
                    }
                self.metrics["leagues"][league]["matches"] += 1
                
                # Make predictions for the match
                predictions = await self.prediction_model.predict_match(match_data, odds_data)
                
                if not predictions:
                    logger.info(f"No predictions for match {match['id']}")
                    continue
                
                # Find value bets
                value_bets = self.odds_evaluator.evaluate_odds(match_data, odds_data, predictions)
                
                if not value_bets:
                    logger.info(f"No value bets for match {match['id']}")
                    continue
                
                # Calculate stakes
                recommendations = self.staking_strategy.calculate_stakes(value_bets)
                
                if not recommendations:
                    logger.info(f"No bet recommendations for match {match['id']}")
                    continue
                
                # Evaluate results of recommended bets
                for bet in recommendations:
                    self._evaluate_bet_result(bet, match)
                
                # Update monthly performance
                match_month = datetime.strptime(match['match_time'], "%Y-%m-%d %H:%M").strftime("%Y-%m")
                if match_month not in self.metrics["monthly_performance"]:
                    self.metrics["monthly_performance"][match_month] = {
                        "bets": 0,
                        "wins": 0,
                        "stake": 0.0,
                        "return": 0.0,
                        "roi": 0.0
                    }
                
            except Exception as e:
                logger.error(f"Error processing match {match.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Calculate overall ROI
        if self.metrics["total_stake"] > 0:
            self.metrics["roi"] = (self.metrics["total_return"] - self.metrics["total_stake"]) / self.metrics["total_stake"]
        
        # Calculate ROI for each league
        for league in self.metrics["leagues"]:
            league_data = self.metrics["leagues"][league]
            if league_data["stake"] > 0:
                league_data["roi"] = (league_data["return"] - league_data["stake"]) / league_data["stake"]
        
        # Calculate ROI for each market
        for market in self.metrics["markets"]:
            market_data = self.metrics["markets"][market]
            if market_data["stake"] > 0:
                market_data["roi"] = (market_data["return"] - market_data["stake"]) / market_data["stake"]
        
        # Calculate ROI for each confidence level
        for conf in self.metrics["confidence_levels"]:
            conf_data = self.metrics["confidence_levels"][conf]
            if conf_data["bets"] > 0:
                conf_data["win_rate"] = conf_data["wins"] / conf_data["bets"]
            if conf_data["stake"] > 0:
                conf_data["roi"] = (conf_data["return"] - conf_data["stake"]) / conf_data["stake"]
        
        # Calculate ROI for each month
        for month in self.metrics["monthly_performance"]:
            month_data = self.metrics["monthly_performance"][month]
            if month_data["stake"] > 0:
                month_data["roi"] = (month_data["return"] - month_data["stake"]) / month_data["stake"]
        
        logger.info("Backtesting completed")
        
        return self.metrics
    
    def _evaluate_bet_result(self, bet: BetRecommendation, match: Dict[str, Any]):
        """Evaluate the result of a bet against the actual match outcome.
        
        Args:
            bet: The betting recommendation
            match: The historical match with results
        """
        result = match.get('result', {})
        if not result:
            logger.warning(f"No result found for match {match.get('id', 'unknown')}")
            return
        
        # Update total bets count
        self.metrics["total_bets"] += 1
        
        # Update bet count for league
        league = match.get('league', 'Unknown')
        self.metrics["leagues"][league]["bets"] += 1
        
        # Update market metrics
        market = bet.market
        if market not in self.metrics["markets"]:
            self.metrics["markets"][market] = {
                "bets": 0,
                "wins": 0,
                "stake": 0.0,
                "return": 0.0,
                "roi": 0.0
            }
        self.metrics["markets"][market]["bets"] += 1
        
        # Update confidence level metrics
        confidence = bet.confidence.name  # Use the enum name (HIGH, MEDIUM, LOW)
        self.metrics["confidence_levels"][confidence]["bets"] += 1
        
        # Update monthly bet count
        match_month = datetime.strptime(match['match_time'], "%Y-%m-%d %H:%M").strftime("%Y-%m")
        self.metrics["monthly_performance"][match_month]["bets"] += 1
        
        # Track stake
        stake = bet.stake
        self.metrics["total_stake"] += stake
        self.metrics["leagues"][league]["stake"] += stake
        self.metrics["markets"][market]["stake"] += stake
        self.metrics["confidence_levels"][confidence]["stake"] += stake
        self.metrics["monthly_performance"][match_month]["stake"] += stake
        
        # Check if bet won
        bet_won = False
        actual_result = result.get(market, None)
        
        if actual_result is not None and actual_result == bet.selection:
            bet_won = True
        
        # Update metrics based on bet result
        if bet_won:
            returns = stake * bet.odds
            self.metrics["winning_bets"] += 1
            self.metrics["total_return"] += returns
            self.metrics["leagues"][league]["wins"] += 1
            self.metrics["leagues"][league]["return"] += returns
            self.metrics["markets"][market]["wins"] += 1
            self.metrics["markets"][market]["return"] += returns
            self.metrics["confidence_levels"][confidence]["wins"] += 1
            self.metrics["confidence_levels"][confidence]["return"] += returns
            self.metrics["monthly_performance"][match_month]["wins"] += 1
            self.metrics["monthly_performance"][match_month]["return"] += returns
            
            # Update bankroll
            self.current_bankroll += (returns - stake)
        else:
            self.metrics["losing_bets"] += 1
            self.current_bankroll -= stake
        
        # Record bankroll history
        match_date = datetime.strptime(match['match_time'], "%Y-%m-%d %H:%M")
        self.bankroll_history.append((match_date, self.current_bankroll))
        
        logger.info(f"Bet on {bet.home_team} vs {bet.away_team}, {bet.market}: {bet.selection} @ {bet.odds} - {'WON' if bet_won else 'LOST'}")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report from backtesting results.
        
        Returns:
            Dictionary with performance metrics and analysis
        """
        if self.metrics["total_bets"] == 0:
            return {"error": "No bets placed during backtesting"}
        
        win_rate = self.metrics["winning_bets"] / self.metrics["total_bets"] if self.metrics["total_bets"] > 0 else 0
        
        report = {
            "summary": {
                "total_matches": self.metrics["total_matches"],
                "total_bets": self.metrics["total_bets"],
                "winning_bets": self.metrics["winning_bets"],
                "losing_bets": self.metrics["losing_bets"],
                "win_rate": win_rate,
                "total_stake": self.metrics["total_stake"],
                "total_return": self.metrics["total_return"],
                "profit": self.metrics["total_return"] - self.metrics["total_stake"],
                "roi": self.metrics["roi"]
            },
            "by_league": {
                league: {
                    "matches": data["matches"],
                    "bets": data["bets"],
                    "win_rate": data["wins"] / data["bets"] if data["bets"] > 0 else 0,
                    "roi": data["roi"]
                }
                for league, data in self.metrics["leagues"].items()
            },
            "by_market": {
                market: {
                    "bets": data["bets"],
                    "win_rate": data["wins"] / data["bets"] if data["bets"] > 0 else 0,
                    "roi": data["roi"]
                }
                for market, data in self.metrics["markets"].items()
            },
            "by_confidence": {
                conf: {
                    "bets": data["bets"],
                    "win_rate": data["wins"] / data["bets"] if data["bets"] > 0 else 0,
                    "roi": data["roi"]
                }
                for conf, data in self.metrics["confidence_levels"].items()
            },
            "monthly_performance": {
                month: {
                    "bets": data["bets"],
                    "win_rate": data["wins"] / data["bets"] if data["bets"] > 0 else 0,
                    "roi": data["roi"]
                }
                for month, data in self.metrics["monthly_performance"].items()
            },
            "recommendations": self._generate_improvement_recommendations()
        }
        
        return report
    
    def _generate_improvement_recommendations(self) -> List[str]:
        """Generate recommendations for model improvement based on backtesting results.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check overall performance
        if self.metrics["roi"] < 0:
            recommendations.append("Overall ROI is negative. Consider adjusting model parameters or improving prediction accuracy.")
        
        # Check league performance
        underperforming_leagues = []
        for league, data in self.metrics["leagues"].items():
            if data["bets"] >= 10 and data["roi"] < -0.1:
                underperforming_leagues.append(league)
        
        if underperforming_leagues:
            recommendations.append(f"Poor performance in {', '.join(underperforming_leagues)}. Consider excluding these leagues or improving the model for them.")
        
        # Check market performance
        underperforming_markets = []
        for market, data in self.metrics["markets"].items():
            if data["bets"] >= 10 and data["roi"] < -0.1:
                underperforming_markets.append(market)
        
        if underperforming_markets:
            recommendations.append(f"Poor performance in {', '.join(underperforming_markets)} markets. Consider excluding these markets or improving predictions.")
        
        # Check confidence levels
        for conf, data in self.metrics["confidence_levels"].items():
            if data["bets"] >= 10:
                if conf == "HIGH" and data["win_rate"] < 0.5:
                    recommendations.append("High confidence predictions have a win rate below 50%. Review confidence scoring algorithm.")
                elif conf == "MEDIUM" and data["win_rate"] < 0.4:
                    recommendations.append("Medium confidence predictions have a low win rate. Adjust confidence thresholds.")
        
        # If no specific issues found
        if not recommendations:
            if self.metrics["roi"] > 0.1:
                recommendations.append("Model is performing well. Consider increasing stake sizes or adding more betting markets.")
            else:
                recommendations.append("No specific issues identified, but ROI could be improved. Consider exploring additional features or model architectures.")
        
        return recommendations
    
    def save_results(self, output_dir: str = "results"):
        """Save backtesting results to files.
        
        Args:
            output_dir: Directory to save results
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save performance report
        report = self.generate_performance_report()
        with open(os.path.join(output_dir, "backtesting_report.json"), "w") as f:
            json.dump(report, f, indent=4)
        
        # Save bankroll history for equity curve
        bankroll_df = pd.DataFrame(self.bankroll_history, columns=["date", "bankroll"])
        bankroll_df.to_csv(os.path.join(output_dir, "bankroll_history.csv"), index=False)
        
        logger.info(f"Backtesting results saved to {output_dir}")


async def main():
    """Main entry point for the backtesting script."""
    # Create data directory if it doesn't exist
    os.makedirs("data/historical", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    logger.info("Starting ML model backtesting")
    
    # Initialize backtesting
    backtesting = ModelBacktesting()
    
    # Run backtesting
    await backtesting.run_backtesting()
    
    # Generate and save results
    backtesting.save_results()
    
    # Print summary
    report = backtesting.generate_performance_report()
    summary = report["summary"]
    
    print("\n" + "="*50)
    print("BACKTESTING RESULTS SUMMARY")
    print("="*50)
    print(f"Total Matches Analyzed: {summary['total_matches']}")
    print(f"Total Bets Placed: {summary['total_bets']}")
    print(f"Win Rate: {summary['win_rate']:.2%}")
    print(f"ROI: {summary['roi']:.2%}")
    print(f"Starting Bankroll: ${backtesting.initial_bankroll:.2f}")
    print(f"Final Bankroll: ${backtesting.current_bankroll:.2f}")
    print(f"Profit/Loss: ${backtesting.current_bankroll - backtesting.initial_bankroll:.2f}")
    print("\nTop Performing Markets:")
    
    # Print top 3 markets by ROI with at least 5 bets
    markets = [(m, d["roi"]) for m, d in report["by_market"].items() if d["bets"] >= 5]
    markets.sort(key=lambda x: x[1], reverse=True)
    for i, (market, roi) in enumerate(markets[:3], 1):
        print(f"{i}. {market}: {roi:.2%} ROI")
    
    print("\nModel Improvement Recommendations:")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"{i}. {rec}")
    print("="*50)
    
    logger.info("Backtesting completed")


if __name__ == "__main__":
    asyncio.run(main()) 