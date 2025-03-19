#!/usr/bin/env python3
"""
Performance tests for the AI Football Betting Advisor.
Tests system efficiency under various loads, focusing on:
- Scraping performance from different sources
- Caching efficiency
- Database query performance
- System handling of large data volumes
"""

import os
import sys
import pytest
import asyncio
import time
import redis
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import components to test
from data.match_collector import MatchCollector
from data.scraping_utils import ScrapingUtils, OddsData
from models.prediction import PredictionModel
from betting.odds_evaluator import OddsEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def redis_client():
    """Create a Redis client for testing caching."""
    try:
        client = redis.Redis(host='localhost', port=6379, db=0)
        # Test connection
        client.ping()
        yield client
        # Clear test data
        client.flushdb()
    except redis.exceptions.ConnectionError:
        # If Redis is not available, use a mock
        class MockRedis:
            def __init__(self):
                self.data = {}
            
            def set(self, key, value, ex=None):
                self.data[key] = value
                return True
            
            def get(self, key):
                return self.data.get(key)
            
            def exists(self, key):
                return key in self.data
            
            def delete(self, key):
                if key in self.data:
                    del self.data[key]
                return True
            
            def flushdb(self):
                self.data = {}
        
        logger.warning("Redis not available. Using in-memory mock.")
        yield MockRedis()

@pytest.fixture(scope="session")
def match_collector():
    """Create a MatchCollector instance for testing."""
    return MatchCollector()

@pytest.fixture(scope="session")
def scraping_utils():
    """Create a ScrapingUtils instance for testing."""
    return ScrapingUtils()

@pytest.fixture(scope="session")
def prediction_model():
    """Create a PredictionModel instance for testing."""
    return PredictionModel()

@pytest.fixture(scope="session")
def odds_evaluator():
    """Create an OddsEvaluator instance for testing."""
    return OddsEvaluator(min_ev_threshold=0.05, min_odds=1.5, max_odds=10.0)

@pytest.fixture
def sample_match_data():
    """Create sample match data for testing."""
    tomorrow = datetime.now() + timedelta(days=1)
    
    return {
        "id": "match_test_1",
        "home_team": "Liverpool",
        "away_team": "Manchester City",
        "league": "Premier League",
        "match_time": tomorrow.strftime("%Y-%m-%d %H:%M"),
        "status": "upcoming",
        "venue": "Anfield",
        "home_form": ["W", "W", "D", "L", "W"],
        "away_form": ["W", "W", "W", "D", "W"],
        "home_league_position": 2,
        "away_league_position": 1,
        "head_to_head": [
            {"date": "2022-10-16", "home_score": 1, "away_score": 0},
            {"date": "2022-04-10", "home_score": 2, "away_score": 2}
        ]
    }

@pytest.fixture
def sample_odds_data():
    """Create sample odds data for testing."""
    return {
        "match_winner": [
            {"selection": "home", "odds": 2.1, "bookmaker": "bet365"},
            {"selection": "draw", "odds": 3.4, "bookmaker": "bet365"},
            {"selection": "away", "odds": 3.5, "bookmaker": "bet365"}
        ],
        "over_under_2_5": [
            {"selection": "over", "odds": 1.85, "bookmaker": "bet365"},
            {"selection": "under", "odds": 2.0, "bookmaker": "bet365"}
        ],
        "btts": [
            {"selection": "yes", "odds": 1.7, "bookmaker": "bet365"},
            {"selection": "no", "odds": 2.2, "bookmaker": "bet365"}
        ]
    }

@pytest.mark.asyncio
async def test_scraping_performance(match_collector, monkeypatch):
    """Test web scraping performance."""
    logger.info("Testing scraping performance...")
    
    # Create mock responses to avoid actual network calls
    async def mock_fetch_html(*args, **kwargs):
        # Return a minimal valid HTML response
        return """
        <html>
            <body>
                <div class="match-row">
                    <div class="team home">Team A</div>
                    <div class="team away">Team B</div>
                    <div class="time">20:00</div>
                </div>
                <div class="match-row">
                    <div class="team home">Team C</div>
                    <div class="team away">Team D</div>
                    <div class="time">15:30</div>
                </div>
            </body>
        </html>
        """
    
    # Patch the fetch_html method to use our mock
    monkeypatch.setattr(match_collector, 'fetch_html', mock_fetch_html)
    
    # Test performance of getting upcoming matches
    start_time = time.time()
    await match_collector.get_upcoming_matches(days_ahead=1)
    matches_time = time.time() - start_time
    
    # Test performance of get_match_details
    start_time = time.time()
    await match_collector.get_match_details("match_1")
    details_time = time.time() - start_time
    
    # Test performance of get_match_odds
    start_time = time.time()
    await match_collector.get_match_odds("match_1")
    odds_time = time.time() - start_time
    
    # Log performance metrics
    logger.info(f"Scraping Performance Metrics:")
    logger.info(f"Get Upcoming Matches: {matches_time:.2f} seconds")
    logger.info(f"Get Match Details: {details_time:.2f} seconds")
    logger.info(f"Get Match Odds: {odds_time:.2f} seconds")
    
    # Assert reasonable performance
    assert matches_time < 2.0, f"Fetching matches took too long: {matches_time:.2f}s"
    assert details_time < 1.0, f"Fetching match details took too long: {details_time:.2f}s"
    assert odds_time < 1.0, f"Fetching match odds took too long: {odds_time:.2f}s"

@pytest.mark.asyncio
async def test_caching_performance(match_collector, redis_client, sample_match_data, monkeypatch):
    """Test caching performance."""
    logger.info("Testing caching performance...")
    
    original_get_match_odds = match_collector.get_match_odds
    
    # Create a wrapper that counts calls
    call_count = 0
    
    async def mock_get_match_odds(match_id):
        nonlocal call_count
        call_count += 1
        # Add artificial delay to simulate network call
        await asyncio.sleep(0.2)
        return {
            "match_winner": [
                {"selection": "home", "odds": 2.1, "bookmaker": "bet365"},
                {"selection": "draw", "odds": 3.4, "bookmaker": "bet365"},
                {"selection": "away", "odds": 3.5, "bookmaker": "bet365"}
            ]
        }
    
    # Patch the method
    monkeypatch.setattr(match_collector, 'get_match_odds', mock_get_match_odds)
    
    # Test first call (cache miss)
    start_time = time.time()
    await match_collector.get_match_odds("test_match_1")
    cache_miss_time = time.time() - start_time
    
    # Reset call count for consistent testing 
    call_count = 0
    
    # Second call should be a cache hit if caching is implemented
    start_time = time.time()
    await match_collector.get_match_odds("test_match_1")
    cache_hit_time = time.time() - start_time
    
    # Cache hits should be faster and not make the underlying call
    logger.info(f"Caching Performance Metrics:")
    logger.info(f"Cache Miss: {cache_miss_time:.3f} seconds")
    logger.info(f"Cache Hit: {cache_hit_time:.3f} seconds")
    if cache_hit_time < cache_miss_time:
        logger.info(f"Cache Speedup: {cache_miss_time / max(cache_hit_time, 0.001):.1f}x faster")
    
    # Wait for cache to expire (if TTL is implemented)
    logger.info("Waiting for cache to expire...")
    await asyncio.sleep(3)  # Adjust based on your cache TTL
    
    # Test after expiration (should be a cache miss again)
    start_time = time.time()
    await match_collector.get_match_odds("test_match_1")
    after_expiry_time = time.time() - start_time
    
    logger.info(f"After Cache Expiry: {after_expiry_time:.3f} seconds")
    
    # Assertions
    assert cache_hit_time < cache_miss_time, "Cache hit should be faster than cache miss"
    assert cache_hit_time < 0.1, f"Cache hit should be very fast, took {cache_hit_time:.3f}s"
    
    # Restore original method
    monkeypatch.setattr(match_collector, 'get_match_odds', original_get_match_odds)

@pytest.mark.asyncio
async def test_ml_prediction_performance(prediction_model, sample_match_data, sample_odds_data):
    """Test performance of ML prediction model."""
    logger.info("Testing ML prediction performance...")
    
    iterations = 10
    total_time = 0
    
    for i in range(iterations):
        start_time = time.time()
        predictions = await prediction_model.predict_match(sample_match_data, sample_odds_data)
        iteration_time = time.time() - start_time
        total_time += iteration_time
        
        # Ensure we got predictions
        assert predictions, f"No predictions returned for iteration {i+1}"
    
    avg_time = total_time / iterations
    logger.info(f"ML Prediction Performance Metrics:")
    logger.info(f"Average prediction time: {avg_time:.3f} seconds")
    logger.info(f"Predictions per second: {1/avg_time:.1f}")
    
    # Assert reasonable performance for ML inference
    assert avg_time < 0.5, f"ML prediction too slow: {avg_time:.3f}s per prediction"

@pytest.mark.asyncio
async def test_full_pipeline_performance(
    match_collector, prediction_model, odds_evaluator, sample_match_data, sample_odds_data
):
    """Test performance of the full prediction and evaluation pipeline."""
    logger.info("Testing full pipeline performance...")
    
    start_time = time.time()
    
    # 1. Get match data
    match_data = sample_match_data
    
    # 2. Get odds data
    odds_data = sample_odds_data
    
    # 3. Make predictions
    predictions = await prediction_model.predict_match(match_data, odds_data)
    
    # 4. Evaluate odds and find value bets
    value_bets = odds_evaluator.evaluate_odds(match_data, odds_data, predictions)
    
    total_time = time.time() - start_time
    
    logger.info(f"Full Pipeline Performance Metrics:")
    logger.info(f"Total pipeline time: {total_time:.3f} seconds")
    logger.info(f"Predictions generated: {len(predictions)}")
    logger.info(f"Value bets found: {len(value_bets)}")
    
    # Assert reasonable performance
    assert total_time < 1.0, f"Full pipeline too slow: {total_time:.3f}s"

@pytest.mark.asyncio
async def test_concurrent_processing_performance(
    match_collector, prediction_model, odds_evaluator, sample_match_data, sample_odds_data
):
    """Test performance with concurrent processing of multiple matches."""
    logger.info("Testing concurrent processing performance...")
    
    # Create multiple match scenarios
    num_matches = 20
    match_copies = []
    
    for i in range(num_matches):
        match_copy = sample_match_data.copy()
        match_copy["id"] = f"match_{i}"
        match_copy["home_team"] = f"Team {i*2 + 1}"
        match_copy["away_team"] = f"Team {i*2 + 2}"
        match_copies.append(match_copy)
    
    # Process matches sequentially
    sequential_start = time.time()
    sequential_results = []
    
    for match in match_copies:
        predictions = await prediction_model.predict_match(match, sample_odds_data)
        value_bets = odds_evaluator.evaluate_odds(match, sample_odds_data, predictions)
        sequential_results.append(value_bets)
    
    sequential_time = time.time() - sequential_start
    
    # Process matches concurrently
    concurrent_start = time.time()
    
    async def process_match(match):
        predictions = await prediction_model.predict_match(match, sample_odds_data)
        return odds_evaluator.evaluate_odds(match, sample_odds_data, predictions)
    
    tasks = [process_match(match) for match in match_copies]
    concurrent_results = await asyncio.gather(*tasks)
    
    concurrent_time = time.time() - concurrent_start
    
    logger.info(f"Concurrent Processing Performance Metrics:")
    logger.info(f"Sequential processing time: {sequential_time:.3f} seconds")
    logger.info(f"Concurrent processing time: {concurrent_time:.3f} seconds")
    logger.info(f"Speedup factor: {sequential_time / concurrent_time:.2f}x")
    
    # Assert reasonable performance
    assert concurrent_time < sequential_time, "Concurrent processing should be faster"
    assert concurrent_time < 5.0, f"Concurrent processing too slow: {concurrent_time:.3f}s"

@pytest.mark.asyncio
async def test_load_handling(
    match_collector, prediction_model, odds_evaluator, sample_match_data, sample_odds_data
):
    """Test system's ability to handle increasing load."""
    logger.info("Testing load handling...")
    
    # Test with increasingly large batches
    batch_sizes = [10, 50, 100]
    results = {}
    
    for size in batch_sizes:
        # Create batch of matches
        matches = []
        for i in range(size):
            match_copy = sample_match_data.copy()
            match_copy["id"] = f"match_batch_{size}_{i}"
            match_copy["home_team"] = f"Team {i*2 + 1}"
            match_copy["away_team"] = f"Team {i*2 + 2}"
            matches.append(match_copy)
        
        # Process batch concurrently
        start_time = time.time()
        
        async def process_match(match):
            predictions = await prediction_model.predict_match(match, sample_odds_data)
            return odds_evaluator.evaluate_odds(match, sample_odds_data, predictions)
        
        tasks = [process_match(match) for match in matches]
        batch_results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        per_match_time = total_time / size
        
        results[size] = {
            "total_time": total_time,
            "per_match_time": per_match_time
        }
        
        logger.info(f"Batch size {size}: {total_time:.3f}s total, {per_match_time:.3f}s per match")
    
    # Calculate scaling efficiency (should be sub-linear)
    scaling_factor = results[batch_sizes[-1]]["total_time"] / results[batch_sizes[0]]["total_time"]
    expected_linear = batch_sizes[-1] / batch_sizes[0]
    
    logger.info(f"Scaling factor: {scaling_factor:.2f}x (linear would be {expected_linear:.2f}x)")
    
    # Assert reasonable scaling
    assert scaling_factor < expected_linear, "System should scale sub-linearly"
    assert results[batch_sizes[-1]]["per_match_time"] < 0.1, "Per-match time should remain low under load"

@pytest.mark.asyncio
async def test_memory_usage():
    """Test memory usage under load."""
    import psutil
    import gc
    
    logger.info("Testing memory usage...")
    
    # Get current process
    process = psutil.Process(os.getpid())
    
    # Measure baseline memory usage
    gc.collect()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create large dataset
    large_data = []
    for i in range(1000):
        match_data = {
            "id": f"memory_test_match_{i}",
            "home_team": f"Home Team {i}",
            "away_team": f"Away Team {i}",
            "league": "Test League",
            "match_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "odds": {
                "match_winner": [
                    {"selection": "home", "odds": 2.0 + (i % 10) / 10, "bookmaker": "test_bookie"}
                    for _ in range(10)  # 10 bookmakers per match
                ],
                "over_under_2_5": [
                    {"selection": "over", "odds": 1.8 + (i % 10) / 10, "bookmaker": "test_bookie"}
                    for _ in range(10)
                ],
                "btts": [
                    {"selection": "yes", "odds": 1.7 + (i % 10) / 10, "bookmaker": "test_bookie"}
                    for _ in range(10)
                ]
            }
        }
        large_data.append(match_data)
    
    # Measure memory after creating large dataset
    loaded_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_used = loaded_memory - baseline_memory
    
    logger.info(f"Memory Usage Metrics:")
    logger.info(f"Baseline memory: {baseline_memory:.2f} MB")
    logger.info(f"Memory after loading data: {loaded_memory:.2f} MB")
    logger.info(f"Memory used: {memory_used:.2f} MB")
    logger.info(f"Memory per match: {memory_used / len(large_data):.3f} MB")
    
    # Free memory
    del large_data
    gc.collect()
    
    # Measure memory after cleanup
    cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    logger.info(f"Memory after cleanup: {cleanup_memory:.2f} MB")
    logger.info(f"Memory reclaimed: {loaded_memory - cleanup_memory:.2f} MB")
    
    # Assert reasonable memory usage
    memory_per_match = memory_used / 1000
    assert memory_per_match < 0.5, f"Memory usage per match too high: {memory_per_match:.3f} MB"
    
if __name__ == "__main__":
    # Run tests directly if file is executed
    asyncio.run(pytest.main(["-xvs", __file__])) 