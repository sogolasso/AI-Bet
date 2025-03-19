"""
Kelly Criterion implementation for optimal bankroll management.
"""
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class KellyParameters:
    win_probability: float
    odds: float
    loss_probability: Optional[float] = None
    risk_factor: float = 0.5  # Fraction of Kelly to use (0.5 = half Kelly)

class KellyCriterion:
    """
    Implements the Kelly Criterion for optimal bankroll management.
    The Kelly Criterion determines the optimal size of a series of bets
    to maximize long-term growth of capital.
    """
    
    @staticmethod
    def calculate_kelly_fraction(params: KellyParameters) -> float:
        """
        Calculate the optimal Kelly fraction for a bet.
        
        Args:
            params: KellyParameters containing win probability, odds, and risk factor
            
        Returns:
            float: The optimal fraction of bankroll to bet (0 to 1)
        """
        if params.loss_probability is None:
            params.loss_probability = 1 - params.win_probability
            
        # Basic Kelly formula: f* = (bp - q) / b
        # where:
        # f* = optimal fraction of bankroll
        # b = odds - 1 (net odds)
        # p = probability of winning
        # q = probability of losing
        
        b = params.odds - 1
        p = params.win_probability
        q = params.loss_probability
        
        # Calculate raw Kelly fraction
        kelly_fraction = (b * p - q) / b
        
        # Apply risk factor (e.g., half Kelly)
        kelly_fraction *= params.risk_factor
        
        # Ensure the fraction is between 0 and 1
        return max(0.0, min(1.0, kelly_fraction))
    
    @staticmethod
    def calculate_expected_value(params: KellyParameters) -> float:
        """
        Calculate the expected value of a bet.
        
        Args:
            params: KellyParameters containing win probability and odds
            
        Returns:
            float: The expected value of the bet
        """
        if params.loss_probability is None:
            params.loss_probability = 1 - params.win_probability
            
        # EV = (probability of win * potential profit) - (probability of loss * stake)
        potential_profit = params.odds - 1
        ev = (params.win_probability * potential_profit) - params.loss_probability
        
        return ev
    
    @staticmethod
    def calculate_optimal_stake(
        bankroll: float,
        params: KellyParameters,
        min_stake: float = 10.0,
        max_stake_percentage: float = 0.05
    ) -> Tuple[float, float]:
        """
        Calculate the optimal stake for a bet based on Kelly Criterion.
        
        Args:
            bankroll: Current bankroll amount
            params: KellyParameters for the bet
            min_stake: Minimum allowed stake
            max_stake_percentage: Maximum stake as percentage of bankroll
            
        Returns:
            Tuple[float, float]: (optimal stake, Kelly fraction)
        """
        # Calculate Kelly fraction
        kelly_fraction = KellyCriterion.calculate_kelly_fraction(params)
        
        # Calculate optimal stake
        optimal_stake = bankroll * kelly_fraction
        
        # Apply minimum stake
        optimal_stake = max(min_stake, optimal_stake)
        
        # Apply maximum stake percentage
        max_stake = bankroll * max_stake_percentage
        optimal_stake = min(max_stake, optimal_stake)
        
        return optimal_stake, kelly_fraction
    
    @staticmethod
    def calculate_roi(
        win_probability: float,
        odds: float,
        kelly_fraction: float
    ) -> float:
        """
        Calculate the expected ROI for a bet using Kelly Criterion.
        
        Args:
            win_probability: Probability of winning the bet
            odds: Decimal odds for the bet
            kelly_fraction: Kelly fraction used for the bet
            
        Returns:
            float: Expected ROI as a percentage
        """
        # Calculate expected return
        expected_return = (win_probability * (odds - 1) * kelly_fraction) - (1 - win_probability) * kelly_fraction
        
        # Convert to percentage
        roi = expected_return * 100
        
        return roi 