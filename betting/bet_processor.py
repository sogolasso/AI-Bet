"""
Bet Processor for the AI Football Betting Advisor.

This module handles bet selection, staking calculation, and tracking bet outcomes.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import csv
import random

logger = logging.getLogger(__name__)

class BetProcessor:
    """Processes and selects bets, applies staking strategies, and tracks results."""
    
    def __init__(self, 
                 config: Dict[str, Any] = None,
                 max_daily_bets: int = 5,
                 min_confidence: str = "Medium",
                 min_value_threshold: float = 0.05,
                 max_bet_per_match: int = 1,
                 max_stake_per_bet_percent: float = 5.0):
        """Initialize the bet processor.
        
        Args:
            config: Configuration for the bet processor
            max_daily_bets: Maximum number of bets to recommend per day
            min_confidence: Minimum confidence level for bet selection ("Low", "Medium", "High")
            min_value_threshold: Minimum value threshold as a decimal (e.g., 0.05 = 5%)
            max_bet_per_match: Maximum number of bets to place on a single match
            max_stake_per_bet_percent: Maximum stake per bet as percentage of bankroll
        """
        self.config = config or {}
        self.max_daily_bets = max_daily_bets
        self.min_confidence = min_confidence
        self.min_value_threshold = min_value_threshold
        self.max_bet_per_match = max_bet_per_match
        self.max_stake_per_bet_percent = max_stake_per_bet_percent
        
        self.data_dir = Path("data/bets")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load staking strategy from config
        self.staking_strategy = self.config.get("staking_strategy", "kelly")
        self.kelly_fraction = self.config.get("kelly_fraction", 0.25)  # Conservative Kelly
        
        # Load any existing bet history
        self.bet_history = self._load_bet_history()
    
    def _load_bet_history(self) -> List[Dict[str, Any]]:
        """Load betting history from data files.
        
        Returns:
            List of historical bets
        """
        history_file = self.data_dir / "bet_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Error loading bet history, starting with empty history")
        
        return []
    
    def _save_bet_history(self) -> None:
        """Save the current bet history to disk."""
        history_file = self.data_dir / "bet_history.json"
        with open(history_file, 'w') as f:
            json.dump(self.bet_history, f, indent=2)
    
    async def process_matches(self, matches_with_value_bets: List[Dict[str, Any]], 
                             bankroll: float) -> List[Dict[str, Any]]:
        """Process matches and select bets for recommendation.
        
        Args:
            matches_with_value_bets: List of matches with value bets identified
            bankroll: Current bankroll amount
            
        Returns:
            List of recommended bets with staking information
        """
        logger.info(f"Processing {len(matches_with_value_bets)} matches for bet selection")
        
        all_potential_bets = []
        
        # Extract all potential bets from matches
        for match in matches_with_value_bets:
            match_id = match.get("id")
            match_time = match.get("match_time")
            home_team = match.get("home_team")
            away_team = match.get("away_team")
            league = match.get("league")
            
            if not all([match_id, match_time, home_team, away_team]):
                continue
            
            value_bets = match.get("value_bets", [])
            
            # Limit to max_bet_per_match bets per match
            match_bets = 0
            
            for value_bet in value_bets:
                # Skip if we've reached max bets for this match
                if match_bets >= self.max_bet_per_match:
                    break
                
                # Check confidence level
                confidence = value_bet.get("confidence", "Low")
                if self._confidence_level_insufficient(confidence):
                    continue
                
                # Check value threshold
                value = value_bet.get("value", 0)
                if value < self.min_value_threshold:
                    continue
                
                # Create complete bet record
                bet = {
                    "match_id": match_id,
                    "match_time": match_time,
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league,
                    "market": value_bet.get("market"),
                    "selection": value_bet.get("selection"),
                    "predicted_probability": value_bet.get("predicted_probability"),
                    "confidence": confidence,
                    "odds": value_bet.get("best_odds"),
                    "bookmaker": value_bet.get("bookmaker"),
                    "value": value,
                    "expected_value": value_bet.get("expected_value", 0),
                    "created_at": datetime.now().isoformat()
                }
                
                all_potential_bets.append(bet)
                match_bets += 1
        
        # Sort by expected value
        all_potential_bets.sort(key=lambda x: x.get("expected_value", 0), reverse=True)
        
        # Limit to max_daily_bets
        selected_bets = all_potential_bets[:self.max_daily_bets]
        
        # Calculate stakes for selected bets
        for bet in selected_bets:
            stake = self._calculate_stake(bet, bankroll)
            bet["stake"] = round(stake, 2)
            bet["potential_profit"] = round(stake * (bet.get("odds", 1) - 1), 2)
            bet["status"] = "pending"
        
        return selected_bets
    
    def _confidence_level_insufficient(self, confidence: str) -> bool:
        """Check if confidence level is insufficient.
        
        Args:
            confidence: Confidence level string
            
        Returns:
            True if confidence is below minimum, False otherwise
        """
        confidence_levels = {
            "Low": 1,
            "Medium": 2,
            "High": 3
        }
        
        bet_confidence = confidence_levels.get(confidence, 0)
        min_required = confidence_levels.get(self.min_confidence, 2)  # Default to Medium
        
        return bet_confidence < min_required
    
    def _calculate_stake(self, bet: Dict[str, Any], bankroll: float) -> float:
        """Calculate the stake for a bet based on the selected staking strategy.
        
        Args:
            bet: Bet information
            bankroll: Current bankroll amount
            
        Returns:
            Recommended stake amount
        """
        if self.staking_strategy == "flat":
            # Flat staking (fixed percentage of bankroll)
            percentage = self.config.get("flat_stake_percentage", 1.0)
            stake = bankroll * (percentage / 100)
        
        elif self.staking_strategy == "kelly":
            # Kelly criterion
            probability = bet.get("predicted_probability", 0.5)
            odds = bet.get("odds", 1.0)
            
            # Kelly formula: f = (bp - q) / b
            # where f is fraction of bankroll to bet
            # b is the decimal odds minus 1 (i.e., profit per unit stake)
            # p is the probability of winning
            # q is the probability of losing (1 - p)
            
            b = odds - 1  # Potential profit per unit stake
            p = probability
            q = 1 - p
            
            # Calculate Kelly stake
            kelly = (b * p - q) / b if b > 0 else 0
            
            # Apply Kelly fraction to be conservative
            kelly *= self.kelly_fraction
            
            # Limit to max stake percentage
            kelly = min(kelly, self.max_stake_per_bet_percent / 100)
            
            stake = bankroll * kelly
        
        elif self.staking_strategy == "percentage":
            # Percentage staking (proportional to confidence/value)
            base_percentage = self.config.get("base_stake_percentage", 1.0)
            
            # Adjust based on confidence
            confidence_factor = {
                "Low": 0.5,
                "Medium": 1.0,
                "High": 1.5
            }.get(bet.get("confidence", "Medium"), 1.0)
            
            # Adjust based on value
            value = bet.get("value", 0.05)
            value_factor = 1 + (value - 0.05) * 10  # Increase stake by 1x for each 10% of additional value
            
            # Calculate adjusted percentage (capped at max_stake_per_bet_percent)
            adjusted_percentage = min(
                base_percentage * confidence_factor * value_factor,
                self.max_stake_per_bet_percent
            )
            
            stake = bankroll * (adjusted_percentage / 100)
        
        else:
            # Default to conservative 1% stake
            stake = bankroll * 0.01
        
        # Ensure stake is not too small or too large
        min_stake = self.config.get("min_stake", 1.0)
        stake = max(min_stake, min(bankroll * (self.max_stake_per_bet_percent / 100), stake))
        
        return stake
    
    def add_bets(self, bets: List[Dict[str, Any]]) -> None:
        """Add bets to the history.
        
        Args:
            bets: List of bets to add
        """
        self.bet_history.extend(bets)
        self._save_bet_history()
        
        # Also add to daily bets file for tracking
        self._append_to_daily_bets(bets)
    
    def _append_to_daily_bets(self, bets: List[Dict[str, Any]]) -> None:
        """Append bets to daily bets file.
        
        Args:
            bets: List of bets to append
        """
        today = datetime.now().strftime("%Y%m%d")
        daily_file = self.data_dir / f"bets_{today}.csv"
        
        fieldnames = [
            "id", "match_id", "match_time", "home_team", "away_team", "league",
            "market", "selection", "odds", "bookmaker", "stake", "potential_profit",
            "confidence", "value", "status"
        ]
        
        file_exists = daily_file.exists()
        
        with open(daily_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            for bet in bets:
                # Add a unique bet ID
                bet_id = f"bet_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
                row = {
                    "id": bet_id,
                    "match_id": bet.get("match_id", ""),
                    "match_time": bet.get("match_time", ""),
                    "home_team": bet.get("home_team", ""),
                    "away_team": bet.get("away_team", ""),
                    "league": bet.get("league", ""),
                    "market": bet.get("market", ""),
                    "selection": bet.get("selection", ""),
                    "odds": bet.get("odds", 0),
                    "bookmaker": bet.get("bookmaker", ""),
                    "stake": bet.get("stake", 0),
                    "potential_profit": bet.get("potential_profit", 0),
                    "confidence": bet.get("confidence", ""),
                    "value": bet.get("value", 0),
                    "status": bet.get("status", "pending")
                }
                writer.writerow(row)
    
    def get_pending_bets(self) -> List[Dict[str, Any]]:
        """Get all pending bets that haven't been settled.
        
        Returns:
            List of pending bets
        """
        return [bet for bet in self.bet_history if bet.get("status") == "pending"]
    
    def update_bet_status(self, bet_id: str, status: str, profit: Optional[float] = None) -> bool:
        """Update the status of a bet.
        
        Args:
            bet_id: ID of the bet to update
            status: New status ('won', 'lost', 'void', 'pending')
            profit: Actual profit for the bet (for won bets)
            
        Returns:
            True if bet was found and updated, False otherwise
        """
        for bet in self.bet_history:
            if bet.get("id") == bet_id:
                bet["status"] = status
                bet["settled_at"] = datetime.now().isoformat()
                
                if profit is not None:
                    bet["actual_profit"] = profit
                
                self._save_bet_history()
                return True
        
        return False
    
    def get_bet_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics for bets in the specified period.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with performance metrics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter bets by date
        recent_bets = []
        for bet in self.bet_history:
            created_at = datetime.fromisoformat(bet.get("created_at", "2000-01-01T00:00:00"))
            if created_at >= cutoff_date:
                recent_bets.append(bet)
        
        # Calculate performance metrics
        total_bets = len(recent_bets)
        settled_bets = [b for b in recent_bets if b.get("status") in ["won", "lost", "void"]]
        won_bets = [b for b in settled_bets if b.get("status") == "won"]
        lost_bets = [b for b in settled_bets if b.get("status") == "lost"]
        
        total_stake = sum(b.get("stake", 0) for b in settled_bets if b.get("status") != "void")
        total_profit = sum(b.get("actual_profit", 0) for b in won_bets)
        total_loss = sum(b.get("stake", 0) for b in lost_bets)
        
        # ROI calculation
        roi = (total_profit - total_loss) / total_stake * 100 if total_stake > 0 else 0
        
        # Win rate
        win_rate = len(won_bets) / len(settled_bets) * 100 if settled_bets else 0
        
        # Group by markets
        markets = {}
        for bet in settled_bets:
            market = bet.get("market", "unknown")
            if market not in markets:
                markets[market] = {
                    "bets": 0,
                    "wins": 0,
                    "roi": 0,
                    "stake": 0,
                    "profit": 0
                }
            
            markets[market]["bets"] += 1
            if bet.get("status") == "won":
                markets[market]["wins"] += 1
                markets[market]["profit"] += bet.get("actual_profit", 0)
            elif bet.get("status") == "lost":
                markets[market]["profit"] -= bet.get("stake", 0)
            
            if bet.get("status") != "void":
                markets[market]["stake"] += bet.get("stake", 0)
        
        # Calculate ROI for each market
        for market in markets:
            stake = markets[market]["stake"]
            profit = markets[market]["profit"]
            markets[market]["roi"] = (profit / stake) * 100 if stake > 0 else 0
        
        # Group by leagues
        leagues = {}
        for bet in settled_bets:
            league = bet.get("league", "unknown")
            if league not in leagues:
                leagues[league] = {
                    "bets": 0,
                    "wins": 0,
                    "roi": 0,
                    "stake": 0,
                    "profit": 0
                }
            
            leagues[league]["bets"] += 1
            if bet.get("status") == "won":
                leagues[league]["wins"] += 1
                leagues[league]["profit"] += bet.get("actual_profit", 0)
            elif bet.get("status") == "lost":
                leagues[league]["profit"] -= bet.get("stake", 0)
            
            if bet.get("status") != "void":
                leagues[league]["stake"] += bet.get("stake", 0)
        
        # Calculate ROI for each league
        for league in leagues:
            stake = leagues[league]["stake"]
            profit = leagues[league]["profit"]
            leagues[league]["roi"] = (profit / stake) * 100 if stake > 0 else 0
        
        return {
            "period_days": days,
            "total_bets": total_bets,
            "settled_bets": len(settled_bets),
            "win_rate": win_rate,
            "total_stake": total_stake,
            "total_profit": total_profit - total_loss,
            "roi": roi,
            "markets": markets,
            "leagues": leagues
        } 