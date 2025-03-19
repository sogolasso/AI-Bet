"""
Value betting calculator for identifying profitable betting opportunities.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime, timedelta

@dataclass
class TeamStats:
    """Statistics for a team's recent performance."""
    goals_scored: float
    goals_conceded: float
    form: float  # Last 5 matches form (0-1)
    home_advantage: float = 1.0  # Home advantage factor
    injury_impact: float = 1.0  # Impact of injuries (0-1)

@dataclass
class MatchContext:
    """Context information for a match."""
    home_team: str
    away_team: str
    league: str
    match_date: datetime
    home_stats: TeamStats
    away_stats: TeamStats
    head_to_head: Dict[str, float]  # Historical performance metrics

class ValueCalculator:
    """
    Calculates value betting opportunities based on statistical analysis
    and market odds.
    """
    
    def __init__(self, min_value_threshold: float = 0.05):
        """
        Initialize the value calculator.
        
        Args:
            min_value_threshold: Minimum expected value to consider a bet
        """
        self.min_value_threshold = min_value_threshold
        
    def calculate_match_probabilities(self, context: MatchContext) -> Dict[str, float]:
        """
        Calculate probabilities for different match outcomes.
        
        Args:
            context: MatchContext containing team statistics and context
            
        Returns:
            Dict[str, float]: Probabilities for home win, draw, away win
        """
        # Calculate base probabilities using Poisson distribution
        home_goals = context.home_stats.goals_scored * context.home_stats.home_advantage
        away_goals = context.away_stats.goals_scored
        
        # Adjust for form
        home_goals *= context.home_stats.form
        away_goals *= context.away_stats.form
        
        # Adjust for injuries
        home_goals *= context.home_stats.injury_impact
        away_goals *= context.away_stats.injury_impact
        
        # Calculate probabilities using Poisson distribution
        home_win_prob = self._poisson_probability(home_goals, away_goals, "home")
        draw_prob = self._poisson_probability(home_goals, away_goals, "draw")
        away_win_prob = self._poisson_probability(home_goals, away_goals, "away")
        
        # Normalize probabilities
        total = home_win_prob + draw_prob + away_win_prob
        return {
            "home_win": home_win_prob / total,
            "draw": draw_prob / total,
            "away_win": away_win_prob / total
        }
    
    def calculate_value_bets(
        self,
        context: MatchContext,
        odds: Dict[str, float]
    ) -> List[Dict[str, float]]:
        """
        Calculate value betting opportunities for a match.
        
        Args:
            context: MatchContext containing match information
            odds: Dictionary of odds for different outcomes
            
        Returns:
            List[Dict[str, float]]: List of value betting opportunities
        """
        probabilities = self.calculate_match_probabilities(context)
        value_bets = []
        
        for outcome, prob in probabilities.items():
            if outcome in odds:
                ev = self._calculate_expected_value(prob, odds[outcome])
                if ev > self.min_value_threshold:
                    value_bets.append({
                        "outcome": outcome,
                        "probability": prob,
                        "odds": odds[outcome],
                        "expected_value": ev
                    })
        
        return sorted(value_bets, key=lambda x: x["expected_value"], reverse=True)
    
    def _poisson_probability(
        self,
        home_goals: float,
        away_goals: float,
        outcome: str
    ) -> float:
        """
        Calculate probability using Poisson distribution.
        
        Args:
            home_goals: Expected home team goals
            away_goals: Expected away team goals
            outcome: Desired outcome ("home", "draw", "away")
            
        Returns:
            float: Probability of the outcome
        """
        if outcome == "home":
            return np.exp(-home_goals) * np.exp(-away_goals) * np.sum([
                (home_goals ** i) / np.math.factorial(i) * 
                (away_goals ** j) / np.math.factorial(j)
                for i in range(1, 6)
                for j in range(i)
            ])
        elif outcome == "draw":
            return np.exp(-home_goals) * np.exp(-away_goals) * np.sum([
                (home_goals ** i) / np.math.factorial(i) * 
                (away_goals ** i) / np.math.factorial(i)
                for i in range(6)
            ])
        else:  # away win
            return np.exp(-home_goals) * np.exp(-away_goals) * np.sum([
                (home_goals ** i) / np.math.factorial(i) * 
                (away_goals ** j) / np.math.factorial(j)
                for i in range(6)
                for j in range(i + 1, 6)
            ])
    
    def _calculate_expected_value(self, probability: float, odds: float) -> float:
        """
        Calculate the expected value of a bet.
        
        Args:
            probability: Probability of the outcome
            odds: Decimal odds for the outcome
            
        Returns:
            float: Expected value of the bet
        """
        return (probability * (odds - 1)) - (1 - probability)
    
    def calculate_confidence_level(self, expected_value: float) -> str:
        """
        Calculate confidence level based on expected value.
        
        Args:
            expected_value: Expected value of the bet
            
        Returns:
            str: Confidence level ("high", "medium", "low")
        """
        if expected_value > 0.15:
            return "high"
        elif expected_value > 0.08:
            return "medium"
        else:
            return "low" 