"""
Tests for machine learning components of the AI Football Betting Advisor.
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from data.storage.models import (
    Match, Odds, Bet, BettingMarket,
    MatchStatus, BetResult, BetType
)
from data.storage.database import Database
from ml.models.bet_predictor import BetPredictor
from ml.models.roi_optimizer import ROIOptimizer
from ml.models.kelly_criterion import KellyCriterion

@pytest.fixture(scope="session")
async def database():
    """Create a test database instance."""
    db = Database(test_mode=True)
    await db.initialize()
    yield db
    await db.close()

@pytest.fixture
def bet_predictor():
    """Create a BetPredictor instance for testing."""
    return BetPredictor()

@pytest.fixture
def roi_optimizer():
    """Create an ROIOptimizer instance for testing."""
    return ROIOptimizer()

@pytest.fixture
def kelly_criterion():
    """Create a KellyCriterion instance for testing."""
    return KellyCriterion()

@pytest.fixture
async def sample_betting_data(database):
    """Create sample betting data for testing."""
    # Create matches
    matches = []
    for i in range(100):
        match = Match(
            home_team=f"Team {i}",
            away_team=f"Team {i+1}",
            league="Premier League",
            match_date=datetime.now() - timedelta(days=i),
            status=MatchStatus.COMPLETED,
            source="flashscore"
        )
        matches.append(match)
        await database.store_match(match)
    
    # Create odds
    odds_list = []
    for match in matches:
        odds = Odds(
            match_id=match.id,
            market=BettingMarket.MATCH_WINNER,
            home_odds=2.50,
            away_odds=2.80,
            draw_odds=3.40,
            source="flashscore"
        )
        odds_list.append(odds)
        await database.store_odds(odds)
    
    # Create bets with varying results
    bets = []
    for match, odds in zip(matches, odds_list):
        # Create a mix of winning and losing bets
        result = BetResult.WON if np.random.random() > 0.5 else BetResult.LOST
        bet = Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=odds.home_odds,
            result=result
        )
        bets.append(bet)
        await database.store_bet(bet)
    
    return matches, odds_list, bets

@pytest.mark.asyncio
async def test_bet_prediction_accuracy(bet_predictor, sample_betting_data):
    """Test bet prediction accuracy."""
    matches, odds_list, bets = sample_betting_data
    
    # Train the model
    await bet_predictor.train(matches, odds_list, bets)
    
    # Test predictions
    test_matches = matches[:10]
    test_odds = odds_list[:10]
    
    predictions = await bet_predictor.predict(test_matches, test_odds)
    
    # Verify prediction format
    assert len(predictions) == len(test_matches)
    for pred in predictions:
        assert 'match_id' in pred
        assert 'selection' in pred
        assert 'confidence' in pred
        assert 'expected_value' in pred
        assert 0 <= pred['confidence'] <= 1
        assert pred['selection'] in ['home', 'away', 'draw']

@pytest.mark.asyncio
async def test_roi_optimization(roi_optimizer, sample_betting_data):
    """Test ROI optimization."""
    matches, odds_list, bets = sample_betting_data
    
    # Train the optimizer
    await roi_optimizer.train(matches, odds_list, bets)
    
    # Test optimization
    test_matches = matches[:10]
    test_odds = odds_list[:10]
    
    optimized_bets = await roi_optimizer.optimize(test_matches, test_odds)
    
    # Verify optimization results
    assert len(optimized_bets) == len(test_matches)
    for bet in optimized_bets:
        assert 'match_id' in bet
        assert 'selection' in bet
        assert 'stake' in bet
        assert 'expected_roi' in bet
        assert bet['stake'] > 0
        assert bet['expected_roi'] > 0

@pytest.mark.asyncio
async def test_kelly_criterion(kelly_criterion, sample_betting_data):
    """Test Kelly Criterion calculations."""
    matches, odds_list, bets = sample_betting_data
    
    # Test Kelly Criterion calculations
    test_cases = [
        {'odds': 2.0, 'probability': 0.6, 'expected_fraction': 0.2},
        {'odds': 3.0, 'probability': 0.4, 'expected_fraction': 0.1},
        {'odds': 1.5, 'probability': 0.8, 'expected_fraction': 0.4}
    ]
    
    for case in test_cases:
        fraction = kelly_criterion.calculate(
            odds=case['odds'],
            probability=case['probability']
        )
        assert abs(fraction - case['expected_fraction']) < 0.1

@pytest.mark.asyncio
async def test_ml_model_adaptation(bet_predictor, sample_betting_data):
    """Test ML model adaptation to new betting patterns."""
    matches, odds_list, bets = sample_betting_data
    
    # Initial training
    await bet_predictor.train(matches, odds_list, bets)
    initial_predictions = await bet_predictor.predict(matches[:5], odds_list[:5])
    
    # Create new betting patterns
    new_matches = []
    new_odds = []
    new_bets = []
    
    for i in range(50):
        match = Match(
            home_team=f"New Team {i}",
            away_team=f"New Team {i+1}",
            league="Premier League",
            match_date=datetime.now() - timedelta(days=i),
            status=MatchStatus.COMPLETED,
            source="flashscore"
        )
        new_matches.append(match)
        await database.store_match(match)
        
        odds = Odds(
            match_id=match.id,
            market=BettingMarket.MATCH_WINNER,
            home_odds=3.50,  # Different odds pattern
            away_odds=2.20,
            draw_odds=3.80,
            source="flashscore"
        )
        new_odds.append(odds)
        await database.store_odds(odds)
        
        bet = Bet(
            match_id=match.id,
            odds_id=odds.id,
            bet_type=BetType.MATCH_WINNER,
            selection="home",
            stake=100.0,
            odds=odds.home_odds,
            result=BetResult.WON if np.random.random() > 0.5 else BetResult.LOST
        )
        new_bets.append(bet)
        await database.store_bet(bet)
    
    # Adapt to new patterns
    await bet_predictor.adapt(new_matches, new_odds, new_bets)
    
    # Test adapted predictions
    adapted_predictions = await bet_predictor.predict(new_matches[:5], new_odds[:5])
    
    # Verify adaptation
    assert len(adapted_predictions) == len(new_matches[:5])
    for pred in adapted_predictions:
        assert 'match_id' in pred
        assert 'selection' in pred
        assert 'confidence' in pred
        assert 'expected_value' in pred

@pytest.mark.asyncio
async def test_ml_performance_tracking(bet_predictor, roi_optimizer, sample_betting_data):
    """Test ML model performance tracking."""
    matches, odds_list, bets = sample_betting_data
    
    # Train models
    await bet_predictor.train(matches, odds_list, bets)
    await roi_optimizer.train(matches, odds_list, bets)
    
    # Track performance metrics
    bet_predictor_metrics = await bet_predictor.get_performance_metrics()
    roi_optimizer_metrics = await roi_optimizer.get_performance_metrics()
    
    # Verify metrics
    assert 'accuracy' in bet_predictor_metrics
    assert 'roi' in bet_predictor_metrics
    assert 'confidence_threshold' in bet_predictor_metrics
    
    assert 'average_roi' in roi_optimizer_metrics
    assert 'stake_efficiency' in roi_optimizer_metrics
    assert 'risk_adjustment' in roi_optimizer_metrics
    
    # Verify reasonable values
    assert 0 <= bet_predictor_metrics['accuracy'] <= 1
    assert bet_predictor_metrics['roi'] > 0
    assert 0 <= roi_optimizer_metrics['stake_efficiency'] <= 1 