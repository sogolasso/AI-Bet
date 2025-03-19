"""
Odds evaluator for the AI Football Betting Advisor.
Analyzes odds from multiple bookmakers to find value bets.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from models.prediction import Prediction, ConfidenceLevel

@dataclass
class ValueBet:
    """Class representing a value bet recommendation."""
    match_id: str
    home_team: str
    away_team: str
    match_time: str
    league: str
    market: str
    selection: str
    odds: float
    bookmaker: str
    probability: float
    expected_value: float
    confidence: ConfidenceLevel
    reasoning: str

class OddsEvaluator:
    """Evaluates odds from multiple bookmakers to find value bets."""
    
    def __init__(self, min_ev_threshold: float = 0.05, min_odds: float = 1.5, max_odds: float = 10.0):
        """Initialize the odds evaluator.
        
        Args:
            min_ev_threshold: Minimum expected value threshold for value bets
            min_odds: Minimum odds to consider
            max_odds: Maximum odds to consider
        """
        self.logger = logging.getLogger(__name__)
        self.min_ev_threshold = min_ev_threshold
        self.min_odds = min_odds
        self.max_odds = max_odds
    
    def evaluate_odds(
        self, 
        match_data: Dict[str, Any], 
        odds_data: Dict[str, List[Dict[str, Any]]], 
        predictions: List[Prediction]
    ) -> List[ValueBet]:
        """Evaluate odds to find value bets.
        
        Args:
            match_data: Dictionary containing match details
            odds_data: Dictionary containing odds for various markets
            predictions: List of model predictions
            
        Returns:
            List of ValueBet objects representing recommended bets
        """
        self.logger.info(f"Evaluating odds for match {match_data['id']}")
        
        value_bets = []
        
        for prediction in predictions:
            market = prediction.market
            selection = prediction.selection
            
            if market in odds_data:
                # Find the best odds for this selection
                relevant_odds = [
                    o for o in odds_data[market] if o["selection"] == selection
                ]
                
                if not relevant_odds:
                    continue
                
                # Find best odds
                best_odds_data = max(relevant_odds, key=lambda x: x["odds"])
                best_odds = best_odds_data["odds"]
                bookmaker = best_odds_data["bookmaker"]
                
                # Skip if odds are outside our acceptable range
                if best_odds < self.min_odds or best_odds > self.max_odds:
                    continue
                
                # Calculate expected value
                ev = prediction.expected_value
                
                # Check if this is a value bet
                if ev >= self.min_ev_threshold:
                    value_bet = ValueBet(
                        match_id=match_data["id"],
                        home_team=match_data["home_team"],
                        away_team=match_data["away_team"],
                        match_time=match_data["match_time"],
                        league=match_data.get("league", "Unknown"),
                        market=market,
                        selection=selection,
                        odds=best_odds,
                        bookmaker=bookmaker,
                        probability=prediction.probability,
                        expected_value=ev,
                        confidence=prediction.confidence,
                        reasoning=prediction.reasoning
                    )
                    
                    value_bets.append(value_bet)
        
        # Sort value bets by expected value (highest first)
        value_bets.sort(key=lambda x: x.expected_value, reverse=True)
        
        return value_bets
    
    def find_arbitrage_opportunities(self, odds_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities across bookmakers.
        
        Args:
            odds_data: Dictionary containing odds for various markets
            
        Returns:
            List of dictionaries representing arbitrage opportunities
        """
        self.logger.info("Looking for arbitrage opportunities")
        
        arbitrage_opps = []
        
        # Check for arbitrage in match winner market
        if "match_winner" in odds_data:
            # Group by bookmaker
            bookmaker_odds = {}
            for odds_item in odds_data["match_winner"]:
                bookmaker = odds_item["bookmaker"]
                selection = odds_item["selection"]
                odds = odds_item["odds"]
                
                if bookmaker not in bookmaker_odds:
                    bookmaker_odds[bookmaker] = {}
                
                bookmaker_odds[bookmaker][selection] = odds
            
            # Find best odds for each outcome
            best_home_odds = max([
                odds.get("home", 0) for odds in bookmaker_odds.values()
            ], default=0)
            best_draw_odds = max([
                odds.get("draw", 0) for odds in bookmaker_odds.values()
            ], default=0)
            best_away_odds = max([
                odds.get("away", 0) for odds in bookmaker_odds.values()
            ], default=0)
            
            # Check for arbitrage opportunity
            if best_home_odds > 0 and best_draw_odds > 0 and best_away_odds > 0:
                margin = (1 / best_home_odds) + (1 / best_draw_odds) + (1 / best_away_odds)
                
                if margin < 1.0:
                    # Arbitrage opportunity found
                    arbitrage_opps.append({
                        "market": "match_winner",
                        "margin": margin,
                        "profit_percentage": ((1 / margin) - 1) * 100,
                        "best_odds": {
                            "home": best_home_odds,
                            "draw": best_draw_odds,
                            "away": best_away_odds
                        }
                    })
        
        # Check for arbitrage in over/under markets
        for market in odds_data:
            if market.startswith("over_under_"):
                # Group by selection
                selection_odds = {}
                for odds_item in odds_data[market]:
                    selection = odds_item["selection"]
                    odds = odds_item["odds"]
                    
                    if selection not in selection_odds or odds > selection_odds[selection]:
                        selection_odds[selection] = odds
                
                # Check if we have both over and under
                if "over" in selection_odds and "under" in selection_odds:
                    over_odds = selection_odds["over"]
                    under_odds = selection_odds["under"]
                    
                    margin = (1 / over_odds) + (1 / under_odds)
                    
                    if margin < 1.0:
                        # Arbitrage opportunity found
                        arbitrage_opps.append({
                            "market": market,
                            "margin": margin,
                            "profit_percentage": ((1 / margin) - 1) * 100,
                            "best_odds": {
                                "over": over_odds,
                                "under": under_odds
                            }
                        })
        
        return arbitrage_opps
    
    def check_line_movement(
        self, 
        current_odds: Dict[str, List[Dict[str, Any]]], 
        previous_odds: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Dict[str, float]]:
        """Check for significant line movements in odds.
        
        Args:
            current_odds: Current odds data
            previous_odds: Previous odds data
            
        Returns:
            Dictionary of line movements by market and selection
        """
        self.logger.info("Checking for line movements")
        
        movements = {}
        
        for market in current_odds:
            if market in previous_odds:
                market_movements = {}
                
                # Convert current odds to dictionary for easier lookup
                current_dict = {}
                for odds_item in current_odds[market]:
                    selection = odds_item["selection"]
                    odds = odds_item["odds"]
                    bookmaker = odds_item["bookmaker"]
                    key = f"{selection}_{bookmaker}"
                    current_dict[key] = odds
                
                # Convert previous odds to dictionary for easier lookup
                previous_dict = {}
                for odds_item in previous_odds[market]:
                    selection = odds_item["selection"]
                    odds = odds_item["odds"]
                    bookmaker = odds_item["bookmaker"]
                    key = f"{selection}_{bookmaker}"
                    previous_dict[key] = odds
                
                # Check for movements
                for key in current_dict:
                    if key in previous_dict:
                        current_odds_val = current_dict[key]
                        previous_odds_val = previous_dict[key]
                        
                        # Calculate percentage change
                        if previous_odds_val > 0:
                            pct_change = (current_odds_val - previous_odds_val) / previous_odds_val * 100
                            
                            # Only record significant movements (>= 5%)
                            if abs(pct_change) >= 5.0:
                                selection, bookmaker = key.split("_", 1)
                                movement_key = f"{selection}_{bookmaker}"
                                market_movements[movement_key] = pct_change
                
                if market_movements:
                    movements[market] = market_movements
        
        return movements 