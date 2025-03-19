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
        """Generate a performance report for the specified number of days.
        
        Args:
            days: Number of days to include in the report
            
        Returns:
            Performance report dictionary
        """
        # In a real implementation, this would analyze past bets
        # For demonstration, we'll generate a mock report
        return await self._generate_mock_performance_report(days)
    
    def generate_performance_report_sync(self, days: int = 30) -> Dict[str, Any]:
        """Synchronous version of generate_performance_report for v13.x compatibility."""
        import asyncio
        try:
            # Try to use the running event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.generate_performance_report(days))
        except RuntimeError:
            # If no event loop is running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.generate_performance_report(days))
            loop.close()
            return result
    
    async def get_daily_tips(self) -> List[Dict[str, Any]]:
        """Get daily betting tips.
        
        Returns:
            List of betting tips
        """
        logger.info("Fetching real upcoming matches for betting tips")
        
        try:
            # Use the match collector to get real matches
            matches = await self.match_collector.get_upcoming_matches()
            
            if not matches:
                logger.warning("No matches found, cannot generate tips")
                return []
            
            logger.info(f"Found {len(matches)} upcoming matches")
            
            # Process matches for prediction
            processed_matches = await self.match_collector.process_matches(matches)
            
            # Make predictions
            matches_with_predictions = self.prediction_model.predict(processed_matches)
            
            # Generate tips based on the predictions
            tips = []
            import random
            
            # Get today's date for filtering
            today = datetime.now()
            today_str = today.strftime("%Y-%m-%d")
            
            # Markets to consider
            markets = [
                {"name": "Match Winner", "selections": ["Home Win", "Away Win", "Draw"]},
                {"name": "Over/Under 2.5", "selections": ["Over", "Under"]},
                {"name": "Both Teams to Score", "selections": ["Yes", "No"]},
                {"name": "Double Chance", "selections": ["Home/Draw", "Away/Draw"]},
                {"name": "Asian Handicap", "selections": ["+0.5", "-0.5"]}
            ]
            
            confidence_levels = ["High", "Medium", "Low"]
            bookmakers = ["Bet365", "William Hill", "Unibet", "1xBet", "888Sport"]
            
            # Priority to today's matches
            today_matches = [m for m in matches_with_predictions if m.get("date", "") == today_str]
            tomorrow_matches = [m for m in matches_with_predictions if m.get("date", "") != today_str]
            
            # Select up to 5 matches, prioritizing today's matches
            selected_matches = today_matches
            if len(selected_matches) < 5:
                selected_matches.extend(tomorrow_matches[:5-len(selected_matches)])
            
            selected_matches = selected_matches[:5]
            
            for match in selected_matches:
                market = random.choice(markets)
                
                # For match winner, use different logic
                if market["name"] == "Match Winner":
                    # Adjust selections based on team strength
                    home_team = match["home_team"].lower()
                    away_team = match["away_team"].lower()
                    
                    top_teams = ['manchester city', 'liverpool', 'arsenal', 'barcelona', 'real madrid', 
                                'bayern', 'paris', 'psg', 'inter', 'juventus', 'chelsea']
                    
                    is_home_top = any(team in home_team for team in top_teams)
                    is_away_top = any(team in away_team for team in top_teams)
                    
                    if is_home_top and not is_away_top:
                        selection = "Home Win"
                    elif is_away_top and not is_home_top:
                        selection = "Away Win"
                    else:
                        # Both top or both not top
                        selection = random.choice(market["selections"])
                else:
                    selection = random.choice(market["selections"])
                
                match_date = match.get("date", today_str)
                match_time = match.get("match_time", "")
                match_datetime = ""
                
                # Format the datetime
                try:
                    if "T" in match_time:
                        dt = datetime.fromisoformat(match_time)
                        match_datetime = f"{match_date} {dt.strftime('%H:%M')}"
                    else:
                        match_datetime = match_time
                except (ValueError, TypeError):
                    match_datetime = f"{match_date} Unknown time"
                
                tip = {
                    "match": f"{match['home_team']} vs {match['away_team']}",
                    "league": match["league"],
                    "match_date": match_date,
                    "match_time": match_datetime,
                    "tip": f"{market['name']} - {selection.upper()}",
                    "odds": match["odds"].get(selection.lower().replace(" ", "_").replace("/", "_"), round(random.uniform(1.5, 3.5), 2)),
                    "bookmaker": random.choice(bookmakers),
                    "confidence": random.choices(confidence_levels, weights=[0.3, 0.5, 0.2])[0],
                    "stake": random.randint(1, 5) * 2
                }
                
                # Log the tip being added
                logger.info(f"Generated tip: {tip['match']} on {tip['match_date']} - {tip['tip']}")
                
                tips.append(tip)
            
            return tips
            
        except Exception as e:
            logger.error(f"Error generating tips: {e}")
            logger.exception("Exception details:")
            return []
    
    def get_daily_tips_sync(self) -> List[Dict[str, Any]]:
        """Synchronous version of get_daily_tips for v13.x compatibility."""
        import asyncio
        try:
            # Try to use the running event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.get_daily_tips())
        except RuntimeError:
            # If no event loop is running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.get_daily_tips())
            loop.close()
            return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get the current system status.
        
        Returns:
            Dictionary with system status information
        """
        return {
            "status": "operational",
            "uptime": "1 day, 6 hours",
            "next_update": "Today at 12:00",
            "bankroll": {
                "initial": self.initial_bankroll,
                "current": self.current_bankroll,
                "growth": f"{(self.current_bankroll / self.initial_bankroll - 1) * 100:.2f}%"
            },
            "version": "1.0.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    async def _generate_mock_tips(self) -> List[Dict[str, Any]]:
        """Generate mock tips for demo purposes."""
        import random
        from datetime import datetime, timedelta
        
        # Get today's date and tomorrow's date
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        today_str = today.strftime("%Y-%m-%d")
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
        
        # Log the dates we're using
        logger.info(f"Generating tips for today ({today_str}) and tomorrow ({tomorrow_str})")
        
        # Generate 5 tips with varying markets and confidence levels
        tips = []
        
        # Updated match data with proper dates and times
        matches = [
            {
                "home": "Liverpool", 
                "away": "Manchester City", 
                "league": "Premier League", 
                "date": today_str,
                "time": f"{today_str} {19 if today.hour < 19 else (today.hour + 1)}:45"
            },
            {
                "home": "Barcelona", 
                "away": "Real Madrid", 
                "league": "La Liga", 
                "date": tomorrow_str,
                "time": f"{tomorrow_str} 20:00"
            },
            {
                "home": "Bayern Munich", 
                "away": "Borussia Dortmund", 
                "league": "Bundesliga", 
                "date": tomorrow_str,
                "time": f"{tomorrow_str} 15:30"
            },
            {
                "home": "PSG", 
                "away": "Marseille", 
                "league": "Ligue 1", 
                "date": today_str,
                "time": f"{today_str} {20 if today.hour < 20 else (today.hour + 1)}:00"
            },
            {
                "home": "Inter", 
                "away": "Juventus", 
                "league": "Serie A", 
                "date": tomorrow_str,
                "time": f"{tomorrow_str} 20:45"
            }
        ]
        
        markets = [
            {"name": "Match Winner", "selections": ["Home Win", "Away Win"]},
            {"name": "Over/Under 2.5", "selections": ["Over", "Under"]},
            {"name": "Both Teams to Score", "selections": ["Yes", "No"]},
            {"name": "Double Chance", "selections": ["Home/Draw", "Away/Draw"]},
            {"name": "Asian Handicap", "selections": ["+0.5", "-0.5"]}
        ]
        
        confidence_levels = ["High", "Medium", "Low"]
        bookmakers = ["Bet365", "William Hill", "Unibet", "1xBet", "888Sport"]
        
        for i in range(5):
            match = matches[i]
            market = random.choice(markets)
            
            tip = {
                "match": f"{match['home']} vs {match['away']}",
                "league": match["league"],
                "match_date": match["date"],
                "match_time": match["time"],
                "tip": f"{market['name']} - {random.choice(market['selections']).upper()}",
                "odds": round(random.uniform(1.5, 3.5), 2),
                "bookmaker": random.choice(bookmakers),
                "confidence": random.choices(confidence_levels, weights=[0.3, 0.5, 0.2])[0],
                "stake": random.randint(1, 5) * 2
            }
            
            # Log the tip being added
            logger.info(f"Generated tip: {tip['match']} on {tip['match_date']} - {tip['tip']}")
            
            tips.append(tip)
        
        return tips
    
    async def _generate_mock_performance_report(self, days: int) -> Dict[str, Any]:
        """Generate a mock performance report for demo purposes."""
        import random
        
        # Mock performance data
        total_bets = min(100, days * 3)
        won_bets = int(total_bets * random.uniform(0.4, 0.6))
        void_bets = int(total_bets * random.uniform(0.05, 0.15))
        lost_bets = total_bets - won_bets - void_bets
        
        # Create mock performance report
        report = {
            "period_days": days,
            "total_bets": total_bets,
            "won_bets": won_bets,
            "lost_bets": lost_bets,
            "void_bets": void_bets,
            "win_rate": won_bets / (total_bets - void_bets) * 100,
            "roi": random.uniform(-5, 25),
            "profit": random.uniform(-20, 50),
            "markets": {
                "Match Winner": {
                    "bets": int(total_bets * 0.3),
                    "won": int(total_bets * 0.3 * 0.5),
                    "roi": random.uniform(-10, 30)
                },
                "Over/Under": {
                    "bets": int(total_bets * 0.3),
                    "won": int(total_bets * 0.3 * 0.6),
                    "roi": random.uniform(-5, 25)
                },
                "Both Teams to Score": {
                    "bets": int(total_bets * 0.2),
                    "won": int(total_bets * 0.2 * 0.55),
                    "roi": random.uniform(0, 20)
                },
                "Asian Handicap": {
                    "bets": int(total_bets * 0.2),
                    "won": int(total_bets * 0.2 * 0.45),
                    "roi": random.uniform(-10, 15)
                }
            },
            "generated_at": datetime.now().isoformat(),
            "initial_bankroll": self.initial_bankroll,
            "current_bankroll": self.current_bankroll,
            "bankroll_growth": (self.current_bankroll / self.initial_bankroll - 1) * 100
        }
        
        return report 