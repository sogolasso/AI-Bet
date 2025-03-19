"""
Betting Advisor for the AI Football Betting Advisor.

This module serves as the main orchestrator for the betting process,
connecting data collection, prediction, odds evaluation, and bet selection.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random

# Update the import path
try:
    # Try the nested import structure first
    from data.collectors.match_collector import MatchCollector
except ImportError:
    # Fall back to the flat structure
    from data.match_collector import MatchCollector

from data.odds_collector import OddsCollector
from models.prediction import PredictionModel
from betting.bet_processor import BetProcessor

logger = logging.getLogger(__name__)

class BettingAdvisor:
    """Main betting advisor class that orchestrates the entire betting process."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the betting advisor.
        
        Args:
            config: Configuration dictionary for the advisor
        """
        self.config = config or {}
        
        # Default values
        self.days_ahead = self.config.get("days_ahead", 1)
        self.initial_bankroll = self.config.get("initial_bankroll", 1000.0)
        self.current_bankroll = self.config.get("current_bankroll", self.initial_bankroll)
        self.max_daily_bets = self.config.get("max_daily_bets", 5)
        self.min_confidence = self.config.get("min_confidence", "Medium")
        self.min_value_threshold = self.config.get("min_value_threshold", 0.05)
        self.data_dir = Path(self.config.get("data_dir", "data"))
        
        # Setup directories
        self.results_dir = self.data_dir / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.match_collector = MatchCollector(days_ahead=self.days_ahead)
        self.odds_collector = OddsCollector()
        self.prediction_model = PredictionModel()
        self.bet_processor = BetProcessor(
            config=self.config,
            max_daily_bets=self.max_daily_bets,
            min_confidence=self.min_confidence,
            min_value_threshold=self.min_value_threshold
        )
        
        # Load state
        self._load_state()
    
    def _load_state(self) -> None:
        """Load advisor state from file."""
        state_file = self.data_dir / "advisor_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.current_bankroll = state.get("current_bankroll", self.initial_bankroll)
                    # Load other state variables as needed
                    logger.info(f"Loaded advisor state with bankroll: {self.current_bankroll}")
            except Exception as e:
                logger.error(f"Error loading advisor state: {e}")
    
    def _save_state(self) -> None:
        """Save advisor state to file."""
        state_file = self.data_dir / "advisor_state.json"
        try:
            state = {
                "current_bankroll": self.current_bankroll,
                "last_updated": datetime.now().isoformat(),
                # Store other state variables as needed
            }
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"Saved advisor state with bankroll: {self.current_bankroll}")
        except Exception as e:
            logger.error(f"Error saving advisor state: {e}")
    
    async def update_bankroll(self, new_amount: Optional[float] = None, 
                            adjustment: Optional[float] = None) -> float:
        """Update the current bankroll.
        
        Args:
            new_amount: Set the bankroll to this exact amount if provided
            adjustment: Adjust the bankroll by this amount (positive or negative)
            
        Returns:
            Updated bankroll amount
        """
        if new_amount is not None:
            self.current_bankroll = max(0, new_amount)
        elif adjustment is not None:
            self.current_bankroll = max(0, self.current_bankroll + adjustment)
        
        self._save_state()
        return self.current_bankroll
    
    async def run_daily_process(self) -> Dict[str, Any]:
        """Run the daily betting process.
        
        Returns:
            Dictionary with results of the daily process
        """
        logger.info("Starting daily betting process")
        start_time = datetime.now()
        
        try:
            # Step 1: Fetch upcoming matches
            matches = await self.match_collector.get_upcoming_matches()
            logger.info(f"Fetched {len(matches)} upcoming matches")
            
            if not matches:
                return {"status": "completed", "error": "No upcoming matches found"}
            
            # Step 2: Process matches for prediction
            processed_matches = await self.match_collector.process_matches(matches)
            logger.info(f"Processed {len(processed_matches)} matches")
            
            # Step 3: Make predictions
            matches_with_predictions = self.prediction_model.predict(processed_matches)
            logger.info(f"Generated predictions for {len(matches_with_predictions)} matches")
            
            # Step 4: Calculate value bets
            matches_with_value = await self.odds_collector.calculate_value_bets(matches_with_predictions)
            logger.info(f"Found value bets for {len(matches_with_value)} matches")
            
            # Step 5: Select bets based on criteria and staking strategy
            recommended_bets = await self.bet_processor.process_matches(
                matches_with_value, self.current_bankroll
            )
            logger.info(f"Selected {len(recommended_bets)} bets to recommend")
            
            # Step 6: Save recommended bets
            self.bet_processor.add_bets(recommended_bets)
            
            # Step 7: Generate and save daily report
            report = self._generate_daily_report(recommended_bets)
            self._save_daily_report(report)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "status": "completed",
                "matches_processed": len(processed_matches),
                "value_matches_found": len(matches_with_value),
                "bets_recommended": len(recommended_bets),
                "process_duration_seconds": duration,
                "report": report
            }
            
            logger.info(f"Daily betting process completed in {duration:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error in daily betting process: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _generate_daily_report(self, recommended_bets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a daily report from recommended bets.
        
        Args:
            recommended_bets: List of recommended bets
            
        Returns:
            Dictionary with report data
        """
        total_stake = sum(bet.get("stake", 0) for bet in recommended_bets)
        potential_profit = sum(bet.get("potential_profit", 0) for bet in recommended_bets)
        
        # Group bets by market
        markets = {}
        for bet in recommended_bets:
            market = bet.get("market", "unknown")
            if market not in markets:
                markets[market] = []
            markets[market].append(bet)
        
        # Group bets by league
        leagues = {}
        for bet in recommended_bets:
            league = bet.get("league", "unknown")
            if league not in leagues:
                leagues[league] = []
            leagues[league].append(bet)
        
        # Get performance data
        performance = self.bet_processor.get_bet_performance(days=30)
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "bets_count": len(recommended_bets),
            "total_stake": total_stake,
            "potential_profit": potential_profit,
            "current_bankroll": self.current_bankroll,
            "markets": {k: len(v) for k, v in markets.items()},
            "leagues": {k: len(v) for k, v in leagues.items()},
            "bets": recommended_bets,
            "performance": performance
        }
    
    def _save_daily_report(self, report: Dict[str, Any]) -> None:
        """Save daily report to file.
        
        Args:
            report: Report data to save
        """
        date_str = datetime.now().strftime("%Y%m%d")
        report_file = self.results_dir / f"daily_report_{date_str}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved daily report to {report_file}")
    
    async def check_results(self) -> Dict[str, Any]:
        """Check results of previous bets and update records.
        
        Returns:
            Dictionary with result checking summary
        """
        logger.info("Checking results of pending bets")
        
        # Get pending bets
        pending_bets = self.bet_processor.get_pending_bets()
        
        if not pending_bets:
            return {"status": "completed", "message": "No pending bets to check"}
        
        # In a real implementation, this would fetch actual results
        # For demonstration, we'll simulate results
        
        checked_count = 0
        won_count = 0
        lost_count = 0
        void_count = 0
        profit = 0.0
        
        # Process bets that are due for settlement (match time has passed)
        now = datetime.now()
        due_bets = []
        
        for bet in pending_bets:
            match_time_str = bet.get("match_time", "")
            if not match_time_str:
                continue
                
            try:
                match_time = datetime.fromisoformat(match_time_str)
                # Add 2 hours to match time for full-time plus potential extra time
                settlement_time = match_time + timedelta(hours=2)
                
                if now >= settlement_time:
                    due_bets.append(bet)
            except (ValueError, TypeError):
                logger.warning(f"Invalid match time format for bet {bet.get('id')}")
        
        # Simulate results for bets due for settlement
        for bet in due_bets:
            # In a real implementation, fetch actual results
            # For demonstration, simulate random outcomes
            
            outcome = random.choice(["won", "lost", "lost", "void"])  # Slightly favor losing outcomes
            
            bet_id = bet.get("id", "")
            stake = bet.get("stake", 0)
            odds = bet.get("odds", 1)
            
            if outcome == "won":
                actual_profit = stake * (odds - 1)
                self.bet_processor.update_bet_status(bet_id, "won", actual_profit)
                await self.update_bankroll(adjustment=actual_profit)
                won_count += 1
                profit += actual_profit
            elif outcome == "lost":
                self.bet_processor.update_bet_status(bet_id, "lost")
                await self.update_bankroll(adjustment=-stake)
                lost_count += 1
                profit -= stake
            else:  # void
                self.bet_processor.update_bet_status(bet_id, "void")
                void_count += 1
            
            checked_count += 1
        
        return {
            "status": "completed",
            "checked_count": checked_count,
            "won_count": won_count,
            "lost_count": lost_count,
            "void_count": void_count,
            "profit": profit,
            "current_bankroll": self.current_bankroll
        }
    
    async def generate_performance_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate a comprehensive performance report.
        
        Args:
            days: Number of days to include in the report
            
        Returns:
            Dictionary with performance data
        """
        logger.info(f"Generating performance report for the last {days} days")
        
        performance = self.bet_processor.get_bet_performance(days=days)
        
        # Add additional metrics
        performance["initial_bankroll"] = self.initial_bankroll
        performance["current_bankroll"] = self.current_bankroll
        performance["bankroll_growth"] = (self.current_bankroll / self.initial_bankroll - 1) * 100
        performance["generated_at"] = datetime.now().isoformat()
        
        # Save the report
        report_file = self.results_dir / f"performance_report_{days}days.json"
        with open(report_file, 'w') as f:
            json.dump(performance, f, indent=2)
        
        logger.info(f"Saved performance report to {report_file}")
        
        return performance
    
    async def retrain_model(self) -> Dict[str, Any]:
        """Retrain the prediction model with historical data.
        
        Returns:
            Dictionary with retraining results
        """
        logger.info("Retraining prediction model with historical data")
        
        try:
            # Get historical match data
            historical_matches = await self.match_collector.get_historical_matches()
            
            # Retrain model
            retraining_results = self.prediction_model.retrain(historical_matches)
            
            # Save results to file
            retrain_file = self.results_dir / f"retraining_{datetime.now().strftime('%Y%m%d')}.json"
            with open(retrain_file, 'w') as f:
                json.dump(retraining_results, f, indent=2)
            
            logger.info(f"Model retraining completed successfully. New version: {retraining_results.get('model_version')}")
            
            return {
                "status": "completed",
                "model_version": retraining_results.get("model_version"),
                "samples_used": retraining_results.get("trained_on_samples"),
                "metrics": retraining_results.get("metrics", {})
            }
            
        except Exception as e:
            logger.error(f"Error retraining model: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_daily_tips(self) -> List[Dict[str, Any]]:
        """Get daily tips for Telegram distribution.
        
        Returns:
            List of formatted tips ready for distribution
        """
        logger.info("Preparing daily tips for distribution")
        
        date_str = datetime.now().strftime("%Y%m%d")
        report_file = self.results_dir / f"daily_report_{date_str}.json"
        
        if not report_file.exists():
            # No report for today, try to run the process
            result = await self.run_daily_process()
            if result.get("status") != "completed" or "error" in result:
                # Process failed or no matches found
                return []
        
        # Load report
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        tips = []
        for bet in report.get("bets", []):
            tip = {
                "match": f"{bet.get('home_team')} vs {bet.get('away_team')}",
                "league": bet.get("league", ""),
                "match_time": bet.get("match_time", ""),
                "tip": f"{bet.get('market')} - {bet.get('selection').upper()}",
                "odds": bet.get("odds", 0),
                "bookmaker": bet.get("bookmaker", ""),
                "confidence": bet.get("confidence", "Medium"),
                "stake": bet.get("stake", 0)
            }
            tips.append(tip)
        
        return tips
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status.
        
        Returns:
            Dictionary with system status information
        """
        return {
            "current_bankroll": self.current_bankroll,
            "initial_bankroll": self.initial_bankroll,
            "model_version": self.prediction_model.get_version(),
            "pending_bets_count": len(self.bet_processor.get_pending_bets()),
            "last_updated": datetime.now().isoformat()
        } 