"""
Staking strategies for the AI Football Betting Advisor.
Implements various bankroll management strategies.
"""

import logging
import math
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

from betting.odds_evaluator import ValueBet
from models.prediction import ConfidenceLevel

class StakingMethod(Enum):
    """Enum for different staking methods."""
    FLAT = "flat"
    KELLY = "kelly"
    PERCENTAGE = "percentage"
    CONFIDENCE = "confidence"
    EXPECTED_VALUE = "expected_value"

@dataclass
class BetRecommendation:
    """Class representing a bet recommendation with stake."""
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
    stake: float
    stake_percentage: float

class StakingStrategy:
    """Implements various staking strategies for bankroll management."""
    
    def __init__(
        self, 
        bankroll: float = 1000.0, 
        method: StakingMethod = StakingMethod.KELLY,
        max_stake_percent: float = 5.0,
        min_stake_percent: float = 0.5,
        kelly_fraction: float = 0.5
    ):
        """Initialize the staking strategy.
        
        Args:
            bankroll: Current bankroll in currency units
            method: Staking method to use
            max_stake_percent: Maximum stake as percentage of bankroll
            min_stake_percent: Minimum stake as percentage of bankroll
            kelly_fraction: Fraction of Kelly to use (0.5 = half Kelly)
        """
        self.logger = logging.getLogger(__name__)
        self.bankroll = bankroll
        self.method = method
        self.max_stake_percent = max_stake_percent
        self.min_stake_percent = min_stake_percent
        self.kelly_fraction = kelly_fraction
    
    def calculate_stakes(self, value_bets: List[ValueBet], max_total_exposure: float = 20.0) -> List[BetRecommendation]:
        """Calculate stakes for a list of value bets based on the selected staking method.
        
        Args:
            value_bets: List of ValueBet objects
            max_total_exposure: Maximum total exposure as percentage of bankroll
            
        Returns:
            List of BetRecommendation objects with calculated stakes
        """
        self.logger.info(f"Calculating stakes using {self.method.value} method")
        
        # Sort value bets by expected value
        sorted_bets = sorted(value_bets, key=lambda x: x.expected_value, reverse=True)
        
        # Calculate initial stakes
        bet_recommendations = []
        total_stake_percentage = 0.0
        
        for bet in sorted_bets:
            # Calculate stake based on selected method
            if self.method == StakingMethod.FLAT:
                stake_percentage = self._flat_stake()
            elif self.method == StakingMethod.KELLY:
                stake_percentage = self._kelly_stake(bet.probability, bet.odds)
            elif self.method == StakingMethod.PERCENTAGE:
                stake_percentage = self._percentage_stake(bet.expected_value)
            elif self.method == StakingMethod.CONFIDENCE:
                stake_percentage = self._confidence_stake(bet.confidence)
            elif self.method == StakingMethod.EXPECTED_VALUE:
                stake_percentage = self._ev_stake(bet.expected_value)
            else:
                # Default to flat stake
                stake_percentage = self._flat_stake()
            
            # Ensure stake is within limits
            stake_percentage = min(self.max_stake_percent, max(self.min_stake_percent, stake_percentage))
            
            # Check if adding this bet would exceed max exposure
            if total_stake_percentage + stake_percentage > max_total_exposure:
                # If we already have some bets, we can continue with reduced stake
                if bet_recommendations:
                    # Reduce stake to fit within max exposure
                    stake_percentage = max_total_exposure - total_stake_percentage
                    
                    # If adjusted stake is below minimum, skip this bet
                    if stake_percentage < self.min_stake_percent:
                        continue
            
            # Calculate actual stake amount
            stake = self.bankroll * (stake_percentage / 100.0)
            
            # Add to total exposure
            total_stake_percentage += stake_percentage
            
            # Create bet recommendation
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
            
            # Stop if we've reached max exposure
            if total_stake_percentage >= max_total_exposure:
                break
        
        return bet_recommendations
    
    def _flat_stake(self) -> float:
        """Calculate flat stake (same percentage for all bets).
        
        Returns:
            Stake as percentage of bankroll
        """
        return 1.0  # 1% of bankroll
    
    def _kelly_stake(self, probability: float, odds: float) -> float:
        """Calculate stake using Kelly Criterion.
        
        Args:
            probability: Estimated probability of winning
            odds: Decimal odds offered
            
        Returns:
            Stake as percentage of bankroll
        """
        # Kelly formula: f* = (bp - q) / b
        # Where:
        # f* = fraction of bankroll to bet
        # b = decimal odds - 1 (i.e., the net return per unit)
        # p = probability of winning
        # q = probability of losing (1 - p)
        
        b = odds - 1
        p = probability
        q = 1 - p
        
        if p <= 0 or b <= 0:
            return 0.0
        
        kelly = (b * p - q) / b
        
        # Apply Kelly fraction to be more conservative
        fractional_kelly = kelly * self.kelly_fraction
        
        # Convert to percentage
        return max(0.0, fractional_kelly * 100.0)
    
    def _percentage_stake(self, expected_value: float) -> float:
        """Calculate stake based on a percentage of expected value.
        
        Args:
            expected_value: Expected value of the bet
            
        Returns:
            Stake as percentage of bankroll
        """
        # Higher EV means higher stake
        if expected_value <= 0:
            return 0.0
        
        # Scale based on EV (example: 10% EV = 2% stake)
        return min(self.max_stake_percent, expected_value * 20.0)
    
    def _confidence_stake(self, confidence: ConfidenceLevel) -> float:
        """Calculate stake based on confidence level.
        
        Args:
            confidence: Confidence level of the prediction
            
        Returns:
            Stake as percentage of bankroll
        """
        if confidence == ConfidenceLevel.HIGH:
            return 2.0
        elif confidence == ConfidenceLevel.MEDIUM:
            return 1.5
        else:  # LOW
            return 1.0
    
    def _ev_stake(self, expected_value: float) -> float:
        """Calculate stake based directly on expected value.
        
        Args:
            expected_value: Expected value of the bet
            
        Returns:
            Stake as percentage of bankroll
        """
        # Simple linear scaling: EV of 0.10 (10%) -> stake 1%
        return min(self.max_stake_percent, expected_value * 10.0)
    
    def update_bankroll(self, new_bankroll: float):
        """Update the current bankroll.
        
        Args:
            new_bankroll: New bankroll value
        """
        self.logger.info(f"Updating bankroll from {self.bankroll} to {new_bankroll}")
        self.bankroll = new_bankroll
    
    def adjust_strategy(self, performance_data: Dict[str, Any]):
        """Adjust staking strategy based on performance data.
        
        Args:
            performance_data: Dictionary containing performance metrics
        """
        self.logger.info("Adjusting staking strategy based on performance data")
        
        # Example: Adjust Kelly fraction based on recent performance
        win_rate = performance_data.get("win_rate", 0.5)
        
        # If win rate is low, be more conservative
        if win_rate < 0.4:
            self.kelly_fraction = max(0.1, self.kelly_fraction - 0.1)
            self.max_stake_percent = max(1.0, self.max_stake_percent - 1.0)
            self.logger.info(f"Reducing risk: Kelly fraction={self.kelly_fraction}, max stake={self.max_stake_percent}%")
        
        # If win rate is high, be more aggressive
        elif win_rate > 0.6:
            self.kelly_fraction = min(0.75, self.kelly_fraction + 0.1)
            self.max_stake_percent = min(7.5, self.max_stake_percent + 0.5)
            self.logger.info(f"Increasing risk: Kelly fraction={self.kelly_fraction}, max stake={self.max_stake_percent}%")
        
        # Example: Adjust staking method based on ROI
        roi = performance_data.get("roi", 0.0)
        
        # If ROI is negative, switch to more conservative method
        if roi < -10.0:
            self.method = StakingMethod.FLAT
            self.logger.info(f"Switching to {self.method.value} staking due to negative ROI")
        
        # If ROI is good, use more optimal methods
        elif roi > 15.0:
            self.method = StakingMethod.KELLY
            self.logger.info(f"Switching to {self.method.value} staking due to positive ROI") 