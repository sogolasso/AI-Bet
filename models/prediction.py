"""
Prediction Model for the AI Football Betting Advisor.

This module handles match outcome predictions based on team statistics and historical data.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ConfidenceLevel(Enum):
    """Confidence levels for predictions."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

@dataclass
class Prediction:
    """Class representing a prediction for a betting market."""
    match_id: str
    market: str
    selection: str
    probability: float
    confidence: ConfidenceLevel
    expected_value: float
    reasoning: str = ""

class PredictionModel:
    """Prediction model for football match outcomes."""
    
    def __init__(self, model_version: str = "1.0.0"):
        """Initialize the prediction model.
        
        Args:
            model_version: Version of the prediction model
        """
        self.model_version = model_version
        self.is_trained = False
        self.feature_importance = {}  # Would store feature importance after training
    
    def get_version(self) -> str:
        """Get the model version.
        
        Returns:
            Model version string
        """
        return self.model_version
    
    def predict(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict outcomes for a list of matches.
        
        Args:
            matches: List of processed match data
            
        Returns:
            List of matches with predictions
        """
        logger.info(f"Predicting outcomes for {len(matches)} matches")
        
        predictions = []
        for match in matches:
            # In a real implementation, this would use a trained ML model
            # For demonstration, we'll use a simple heuristic
            prediction = self._predict_match(match)
            match_with_prediction = match.copy()
            match_with_prediction["predictions"] = prediction
            predictions.append(match_with_prediction)
        
        return predictions
    
    def to_prediction_objects(self, matches_with_predictions: List[Dict[str, Any]], odds_data: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> List[Prediction]:
        """Convert prediction dictionaries to Prediction objects.
        
        Args:
            matches_with_predictions: List of matches with predictions
            odds_data: Dictionary of odds data by match ID
            
        Returns:
            List of Prediction objects
        """
        prediction_objects = []
        
        for match in matches_with_predictions:
            match_id = match.get("id", "")
            if not match_id:
                continue
                
            predictions = match.get("predictions", {})
            if not predictions:
                continue
                
            # Get odds for this match
            match_odds = odds_data.get(match_id, {})
            
            # Process match winner predictions
            if "match_winner" in predictions:
                mw_pred = predictions["match_winner"]
                
                # Home win
                home_prob = mw_pred.get("home", 0)
                home_conf = mw_pred.get("confidence", ConfidenceLevel.MEDIUM)
                if isinstance(home_conf, str):
                    home_conf = ConfidenceLevel(home_conf)
                    
                if match_odds.get("match_winner"):
                    home_odds = [o for o in match_odds["match_winner"] if o.get("selection") == "home"]
                    if home_odds:
                        best_home_odds = max(home_odds, key=lambda x: x.get("odds", 0))
                        ev = (best_home_odds.get("odds", 1) - 1) * home_prob - (1 - home_prob)
                        
                        prediction_objects.append(Prediction(
                            match_id=match_id,
                            market="match_winner",
                            selection="home",
                            probability=home_prob,
                            confidence=home_conf,
                            expected_value=ev,
                            reasoning=f"Home team with {home_prob:.1%} win probability"
                        ))
                
                # Away win
                away_prob = mw_pred.get("away", 0)
                if match_odds.get("match_winner"):
                    away_odds = [o for o in match_odds["match_winner"] if o.get("selection") == "away"]
                    if away_odds:
                        best_away_odds = max(away_odds, key=lambda x: x.get("odds", 0))
                        ev = (best_away_odds.get("odds", 1) - 1) * away_prob - (1 - away_prob)
                        
                        prediction_objects.append(Prediction(
                            match_id=match_id,
                            market="match_winner",
                            selection="away",
                            probability=away_prob,
                            confidence=home_conf,  # Using home confidence for simplicity
                            expected_value=ev,
                            reasoning=f"Away team with {away_prob:.1%} win probability"
                        ))
            
            # Process over/under predictions
            if "over_under_2_5" in predictions:
                ou_pred = predictions["over_under_2_5"]
                
                # Over 2.5
                over_prob = ou_pred.get("over", 0)
                over_conf = ou_pred.get("confidence", ConfidenceLevel.MEDIUM)
                if isinstance(over_conf, str):
                    over_conf = ConfidenceLevel(over_conf)
                    
                if match_odds.get("over_under_2_5"):
                    over_odds = [o for o in match_odds["over_under_2_5"] if o.get("selection") == "over"]
                    if over_odds:
                        best_over_odds = max(over_odds, key=lambda x: x.get("odds", 0))
                        ev = (best_over_odds.get("odds", 1) - 1) * over_prob - (1 - over_prob)
                        
                        prediction_objects.append(Prediction(
                            match_id=match_id,
                            market="over_under_2_5",
                            selection="over",
                            probability=over_prob,
                            confidence=over_conf,
                            expected_value=ev,
                            reasoning=f"Over 2.5 goals with {over_prob:.1%} probability"
                        ))
            
            # Process BTTS predictions
            if "btts" in predictions:
                btts_pred = predictions["btts"]
                
                # BTTS Yes
                btts_yes_prob = btts_pred.get("yes", 0)
                btts_conf = btts_pred.get("confidence", ConfidenceLevel.MEDIUM)
                if isinstance(btts_conf, str):
                    btts_conf = ConfidenceLevel(btts_conf)
                    
                if match_odds.get("btts"):
                    btts_yes_odds = [o for o in match_odds["btts"] if o.get("selection") == "yes"]
                    if btts_yes_odds:
                        best_btts_yes_odds = max(btts_yes_odds, key=lambda x: x.get("odds", 0))
                        ev = (best_btts_yes_odds.get("odds", 1) - 1) * btts_yes_prob - (1 - btts_yes_prob)
                        
                        prediction_objects.append(Prediction(
                            match_id=match_id,
                            market="btts",
                            selection="yes",
                            probability=btts_yes_prob,
                            confidence=btts_conf,
                            expected_value=ev,
                            reasoning=f"Both teams to score with {btts_yes_prob:.1%} probability"
                        ))
        
        # Sort by expected value
        prediction_objects.sort(key=lambda x: x.expected_value, reverse=True)
        
        return prediction_objects
    
    def _predict_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Predict outcomes for a single match.
        
        Args:
            match: Processed match data
            
        Returns:
            Dictionary with predicted probabilities and confidence levels
        """
        # In a real implementation, this would use features extracted from the match data
        # and a trained ML model to predict probabilities
        
        # Extract some basic features
        home_form = match.get("home_form", [])
        away_form = match.get("away_form", [])
        home_stats = match.get("home_stats", {})
        away_stats = match.get("away_stats", {})
        
        # Calculate win percentages based on form
        home_win_rate = self._calculate_win_rate(home_form)
        away_win_rate = self._calculate_win_rate(away_form)
        
        # Adjust for home advantage
        home_advantage = 0.1  # 10% home advantage
        
        # Calculate base probabilities
        home_win_prob = (home_win_rate + home_advantage) * 0.5 + (1 - away_win_rate) * 0.5
        away_win_prob = away_win_rate * 0.5 + (1 - home_win_rate - home_advantage) * 0.5
        draw_prob = 1 - home_win_prob - away_win_prob
        
        # Adjust probabilities to ensure they sum to 1
        total_prob = home_win_prob + away_win_prob + draw_prob
        home_win_prob /= total_prob
        away_win_prob /= total_prob
        draw_prob /= total_prob
        
        # Calculate over/under probabilities
        home_goals_scored = home_stats.get("goals_scored", 30)
        home_goals_conceded = home_stats.get("goals_conceded", 30)
        away_goals_scored = away_stats.get("goals_scored", 30)
        away_goals_conceded = away_stats.get("goals_conceded", 30)
        
        expected_goals = (home_goals_scored / 30 + away_goals_conceded / 30) * 1.2 + (away_goals_scored / 30 + home_goals_conceded / 30) * 0.8
        over_2_5_prob = self._sigmoid(expected_goals - 2.5)
        under_2_5_prob = 1 - over_2_5_prob
        
        # Calculate BTTS probabilities
        home_clean_sheets = home_stats.get("clean_sheets", 5)
        away_clean_sheets = away_stats.get("clean_sheets", 5)
        
        home_clean_sheet_rate = home_clean_sheets / 30
        away_clean_sheet_rate = away_clean_sheets / 30
        
        btts_yes_prob = (1 - home_clean_sheet_rate) * (1 - away_clean_sheet_rate)
        btts_no_prob = 1 - btts_yes_prob
        
        # Assign confidence levels based on prediction clarity
        match_winner_confidence = self._get_confidence_level(
            max(home_win_prob, away_win_prob, draw_prob),
            thresholds=(0.4, 0.55)
        )
        
        over_under_confidence = self._get_confidence_level(
            max(over_2_5_prob, under_2_5_prob),
            thresholds=(0.55, 0.65)
        )
        
        btts_confidence = self._get_confidence_level(
            max(btts_yes_prob, btts_no_prob),
            thresholds=(0.55, 0.65)
        )
        
        # Return all predictions with probabilities and confidence levels
        return {
            "match_winner": {
                "home": home_win_prob,
                "draw": draw_prob,
                "away": away_win_prob,
                "confidence": match_winner_confidence
            },
            "over_under_2_5": {
                "over": over_2_5_prob,
                "under": under_2_5_prob,
                "confidence": over_under_confidence
            },
            "btts": {
                "yes": btts_yes_prob,
                "no": btts_no_prob,
                "confidence": btts_confidence
            }
        }
    
    def _calculate_win_rate(self, form: List[str]) -> float:
        """Calculate win rate from form data.
        
        Args:
            form: List of form results (W, D, L)
            
        Returns:
            Win rate as a float between 0 and 1
        """
        if not form:
            return 0.5  # Default to 50% if no form data
        
        wins = form.count("W")
        draws = form.count("D")
        
        return (wins + 0.5 * draws) / len(form)
    
    def _sigmoid(self, x: float) -> float:
        """Apply sigmoid function to x.
        
        Args:
            x: Input value
            
        Returns:
            Sigmoid of x (value between 0 and 1)
        """
        import math
        return 1 / (1 + math.exp(-x))
    
    def _get_confidence_level(self, prob: float, thresholds: tuple = (0.6, 0.8)) -> ConfidenceLevel:
        """Get confidence level based on probability.
        
        Args:
            prob: Probability value
            thresholds: Tuple of (medium_threshold, high_threshold)
            
        Returns:
            ConfidenceLevel enum value
        """
        medium_threshold, high_threshold = thresholds
        
        if prob >= high_threshold:
            return ConfidenceLevel.HIGH
        elif prob >= medium_threshold:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def retrain(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Retrain the model with historical match data.
        
        Args:
            historical_data: List of historical matches with results
            
        Returns:
            Dictionary with training results and metrics
        """
        logger.info(f"Retraining model with {len(historical_data)} historical matches")
        
        # In a real implementation, this would:
        # 1. Prepare the data (feature extraction, split into train/test)
        # 2. Train various models
        # 3. Evaluate and select the best model
        # 4. Save the model for future use
        
        # For demonstration, we'll simulate a training process
        import random
        import time
        
        # Simulate training time
        time.sleep(1)
        
        # Calculate mock metrics
        accuracy = random.uniform(0.65, 0.75)
        precision = random.uniform(0.60, 0.70)
        recall = random.uniform(0.60, 0.70)
        f1_score = 2 * (precision * recall) / (precision + recall)
        
        # Update model state
        self.is_trained = True
        self.model_version = f"1.1.0-{datetime.now().strftime('%Y%m%d')}"
        
        # Mock feature importance
        self.feature_importance = {
            "home_form": random.uniform(0.1, 0.2),
            "away_form": random.uniform(0.1, 0.2),
            "home_goals_scored": random.uniform(0.05, 0.15),
            "away_goals_scored": random.uniform(0.05, 0.15),
            "home_clean_sheets": random.uniform(0.05, 0.1),
            "away_clean_sheets": random.uniform(0.05, 0.1),
            "h2h_results": random.uniform(0.1, 0.2),
            "league_position_diff": random.uniform(0.05, 0.15)
        }
        
        # Return training results
        return {
            "model_version": self.model_version,
            "trained_at": datetime.now().isoformat(),
            "metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score
            },
            "feature_importance": self.feature_importance,
            "trained_on_samples": len(historical_data)
        } 