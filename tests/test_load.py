#!/usr/bin/env python3
"""
Load Testing for AI Football Betting Advisor

This script tests the system's performance under heavy load, simulating multiple
concurrent users and high volume data processing. It helps validate:
- System stability under peak load
- Resource utilization (CPU, memory, network)
- Response times under different load profiles
- Potential bottlenecks in the processing pipeline
"""

import os
import sys
import asyncio
import time
import random
import logging
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import aiohttp
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import components to test
from data.match_collector import MatchCollector
from models.prediction import PredictionModel
from betting.odds_evaluator import OddsEvaluator
from betting.staking import StakingStrategy, StakingMethod
from bot.telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("load_test_results.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LoadTester:
    """Tests system performance under various load conditions."""
    
    def __init__(self, 
                 concurrent_users: int = 10,
                 test_duration_seconds: int = 60,
                 ramp_up_seconds: int = 10,
                 matches_per_user: int = 5):
        """Initialize the load tester.
        
        Args:
            concurrent_users: Maximum number of simulated concurrent users
            test_duration_seconds: How long to run the test
            ramp_up_seconds: Time to gradually increase load to max users
            matches_per_user: How many matches each user processes
        """
        self.concurrent_users = concurrent_users
        self.test_duration_seconds = test_duration_seconds
        self.ramp_up_seconds = ramp_up_seconds
        self.matches_per_user = matches_per_user
        
        # Components to test
        self.match_collector = MatchCollector()
        self.prediction_model = PredictionModel()
        self.odds_evaluator = OddsEvaluator(
            min_ev_threshold=0.05,
            min_odds=1.5,
            max_odds=10.0
        )
        self.staking_strategy = StakingStrategy(
            bankroll=1000.0,
            method=StakingMethod.KELLY,
            max_stake_percent=5.0
        )
        
        # Test metrics
        self.response_times = []
        self.error_count = 0
        self.requests_processed = 0
        self.start_time = None
        self.end_time = None
        
    async def generate_test_match(self, user_id: int, match_id: int) -> Dict[str, Any]:
        """Generate test match data for load testing.
        
        Args:
            user_id: Simulated user ID
            match_id: Match ID for this user
            
        Returns:
            Dictionary with match data
        """
        teams = [
            "Arsenal", "Aston Villa", "Bournemouth", "Brentford", 
            "Brighton", "Chelsea", "Crystal Palace", "Everton",
            "Fulham", "Leeds", "Leicester", "Liverpool",
            "Manchester City", "Manchester United", "Newcastle", "Nottingham Forest",
            "Southampton", "Tottenham", "West Ham", "Wolves"
        ]
        
        leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
        
        # Ensure unique but deterministic team selection
        random.seed(user_id * 100 + match_id)
        home_idx = random.randint(0, len(teams)-1)
        away_idx = (home_idx + 1 + random.randint(0, len(teams)-2)) % len(teams)
        
        match_time = datetime.now() + timedelta(days=random.randint(1, 7))
        
        match_data = {
            "id": f"match_{user_id}_{match_id}",
            "home_team": teams[home_idx],
            "away_team": teams[away_idx],
            "league": random.choice(leagues),
            "match_time": match_time.strftime("%Y-%m-%d %H:%M"),
            "status": "upcoming",
            "venue": f"{teams[home_idx]} Stadium",
            "home_form": ["W", "D", "W", "L", "W"],
            "away_form": ["L", "W", "W", "D", "L"],
            "home_league_position": random.randint(1, 20),
            "away_league_position": random.randint(1, 20),
            "head_to_head": [
                {"date": (match_time - timedelta(days=180)).strftime("%Y-%m-%d"), 
                 "home_score": random.randint(0, 4), 
                 "away_score": random.randint(0, 3)},
                {"date": (match_time - timedelta(days=360)).strftime("%Y-%m-%d"), 
                 "home_score": random.randint(0, 3), 
                 "away_score": random.randint(0, 4)}
            ]
        }
        
        # Generate realistic odds data
        odds_data = {
            "match_winner": [
                {"selection": "home", "odds": 1.8 + random.random() * 1.5, "bookmaker": "bet365"},
                {"selection": "draw", "odds": 3.0 + random.random() * 1.0, "bookmaker": "bet365"},
                {"selection": "away", "odds": 3.2 + random.random() * 1.8, "bookmaker": "bet365"}
            ],
            "over_under_2_5": [
                {"selection": "over", "odds": 1.7 + random.random() * 0.5, "bookmaker": "bet365"},
                {"selection": "under", "odds": 2.0 + random.random() * 0.5, "bookmaker": "bet365"}
            ],
            "btts": [
                {"selection": "yes", "odds": 1.8 + random.random() * 0.4, "bookmaker": "bet365"},
                {"selection": "no", "odds": 1.9 + random.random() * 0.6, "bookmaker": "bet365"}
            ]
        }
        
        # Add additional bookmakers for more realistic load
        bookmakers = ["Unibet", "888sport", "William Hill", "Ladbrokes", "Coral"]
        for market in odds_data:
            for bookmaker in bookmakers:
                for selection in odds_data[market]:
                    base_odds = selection["odds"]
                    # Create slight variations in odds between bookmakers
                    new_odds = base_odds * (0.95 + random.random() * 0.1)  # +/- 5%
                    odds_data[market].append({
                        "selection": selection["selection"],
                        "odds": round(new_odds, 2),
                        "bookmaker": bookmaker
                    })
        
        return match_data, odds_data
    
    async def simulate_user_workflow(self, user_id: int) -> Dict[str, Any]:
        """Simulate a user's betting workflow from match selection to recommendations.
        
        Args:
            user_id: Simulated user ID
            
        Returns:
            Dictionary with timing metrics
        """
        metrics = {
            "user_id": user_id,
            "matches_processed": 0,
            "processing_times": [],
            "errors": 0,
            "total_time": 0,
            "components": {
                "match_generation": 0,
                "prediction": 0,
                "odds_evaluation": 0,
                "staking": 0
            }
        }
        
        user_start_time = time.time()
        
        try:
            for i in range(self.matches_per_user):
                match_start = time.time()
                # Generate test match data
                match_data, odds_data = await self.generate_test_match(user_id, i)
                match_gen_time = time.time() - match_start
                metrics["components"]["match_generation"] += match_gen_time
                
                # Process the match through the prediction pipeline
                try:
                    # Make predictions
                    pred_start = time.time()
                    predictions = await self.prediction_model.predict_match(match_data, odds_data)
                    pred_time = time.time() - pred_start
                    metrics["components"]["prediction"] += pred_time
                    
                    # Evaluate odds
                    eval_start = time.time()
                    value_bets = self.odds_evaluator.evaluate_odds(match_data, odds_data, predictions)
                    eval_time = time.time() - eval_start
                    metrics["components"]["odds_evaluation"] += eval_time
                    
                    # Calculate stakes
                    stake_start = time.time()
                    recommendations = self.staking_strategy.calculate_stakes(value_bets)
                    stake_time = time.time() - stake_start
                    metrics["components"]["staking"] += stake_time
                    
                    # Record successful processing
                    match_time = match_gen_time + pred_time + eval_time + stake_time
                    metrics["processing_times"].append(match_time)
                    metrics["matches_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing match for user {user_id}: {str(e)}")
                    metrics["errors"] += 1
                
                # Simulate some think time between match processing (50-300ms)
                await asyncio.sleep(0.05 + random.random() * 0.25)
        
        except Exception as e:
            logger.error(f"Error in user workflow for user {user_id}: {str(e)}")
            metrics["errors"] += 1
        
        metrics["total_time"] = time.time() - user_start_time
        return metrics
    
    async def run_test(self):
        """Run the load test with the configured parameters."""
        logger.info(f"Starting load test with {self.concurrent_users} concurrent users")
        logger.info(f"Test duration: {self.test_duration_seconds}s, Ramp-up: {self.ramp_up_seconds}s")
        
        self.start_time = time.time()
        results = []
        tasks = []
        
        # Calculate how many users to add in each ramp-up step
        users_per_step = max(1, self.concurrent_users // (self.ramp_up_seconds or 1))
        
        # Ramp up users
        active_users = 0
        ramp_start = time.time()
        
        while active_users < self.concurrent_users:
            # Check if test duration has expired
            if time.time() - self.start_time >= self.test_duration_seconds:
                break
                
            # Calculate how many users to add in this step
            users_to_add = min(users_per_step, self.concurrent_users - active_users)
            
            logger.info(f"Ramping up {users_to_add} users, total now: {active_users + users_to_add}")
            
            # Add new user tasks
            for i in range(users_to_add):
                user_id = active_users + i
                task = asyncio.create_task(self.simulate_user_workflow(user_id))
                tasks.append(task)
            
            active_users += users_to_add
            
            # Wait until next ramp-up step
            time_elapsed = time.time() - ramp_start
            step_duration = self.ramp_up_seconds / (self.concurrent_users / users_per_step)
            time_to_wait = step_duration - (time_elapsed % step_duration)
            
            if time_to_wait > 0 and active_users < self.concurrent_users:
                await asyncio.sleep(time_to_wait)
        
        # Wait for all tasks to complete or test duration to expire
        while tasks and (time.time() - self.start_time < self.test_duration_seconds):
            done, pending = await asyncio.wait(
                tasks, 
                timeout=1.0,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Process completed tasks
            for task in done:
                try:
                    user_metrics = task.result()
                    results.append(user_metrics)
                    tasks.remove(task)
                except Exception as e:
                    logger.error(f"Error getting task result: {str(e)}")
                    self.error_count += 1
        
        # Cancel any remaining tasks
        for task in tasks:
            task.cancel()
        
        # Wait for cancellations to complete
        if tasks:
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        
        self.end_time = time.time()
        
        # Process and report results
        self.analyze_results(results)
    
    def analyze_results(self, results: List[Dict[str, Any]]):
        """Analyze and report test results.
        
        Args:
            results: List of metrics from each simulated user
        """
        total_duration = self.end_time - self.start_time
        total_matches_processed = sum(r["matches_processed"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        
        all_processing_times = []
        for r in results:
            all_processing_times.extend(r["processing_times"])
        
        if not all_processing_times:
            logger.error("No processing times recorded - test failed")
            return
        
        # Calculate statistics
        avg_time = sum(all_processing_times) / len(all_processing_times)
        max_time = max(all_processing_times) if all_processing_times else 0
        min_time = min(all_processing_times) if all_processing_times else 0
        p95_time = np.percentile(all_processing_times, 95) if all_processing_times else 0
        
        # Calculate throughput
        matches_per_second = total_matches_processed / total_duration
        
        # Calculate component percentages
        component_totals = {
            "match_generation": 0,
            "prediction": 0,
            "odds_evaluation": 0,
            "staking": 0
        }
        
        for r in results:
            for component, time_val in r["components"].items():
                component_totals[component] += time_val
        
        total_component_time = sum(component_totals.values())
        
        component_percentages = {}
        if total_component_time > 0:
            for component, time_val in component_totals.items():
                component_percentages[component] = (time_val / total_component_time) * 100
        
        # Print results
        logger.info("=" * 60)
        logger.info("LOAD TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Test Duration: {total_duration:.2f} seconds")
        logger.info(f"Users Simulated: {len(results)}")
        logger.info(f"Total Matches Processed: {total_matches_processed}")
        logger.info(f"Total Errors: {total_errors}")
        logger.info(f"Error Rate: {(total_errors / max(1, total_matches_processed)) * 100:.2f}%")
        logger.info(f"Throughput: {matches_per_second:.2f} matches/second")
        
        logger.info("\nProcessing Times:")
        logger.info(f"  Average: {avg_time * 1000:.2f} ms")
        logger.info(f"  Minimum: {min_time * 1000:.2f} ms")
        logger.info(f"  Maximum: {max_time * 1000:.2f} ms")
        logger.info(f"  95th Percentile: {p95_time * 1000:.2f} ms")
        
        logger.info("\nComponent Breakdown:")
        for component, percentage in component_percentages.items():
            logger.info(f"  {component}: {percentage:.1f}%")
        
        logger.info("=" * 60)
        
        # Save results to file
        results_data = {
            "summary": {
                "test_duration": total_duration,
                "users_simulated": len(results),
                "total_matches_processed": total_matches_processed,
                "total_errors": total_errors,
                "error_rate": (total_errors / max(1, total_matches_processed)) * 100,
                "throughput": matches_per_second,
            },
            "timing": {
                "average_ms": avg_time * 1000,
                "min_ms": min_time * 1000,
                "max_ms": max_time * 1000,
                "p95_ms": p95_time * 1000
            },
            "component_percentages": component_percentages,
            "raw_results": results
        }
        
        with open("load_test_results.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        # Generate histogram of processing times
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(10, 6))
            plt.hist([t * 1000 for t in all_processing_times], bins=20)
            plt.xlabel('Processing Time (ms)')
            plt.ylabel('Frequency')
            plt.title('Match Processing Time Distribution')
            plt.grid(True, alpha=0.3)
            plt.savefig('load_test_histogram.png')
            logger.info("Processing time histogram saved to load_test_histogram.png")
        except ImportError:
            logger.warning("Matplotlib not available - histogram not generated")

async def main():
    """Main entry point for the load testing script."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor Load Tester')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users to simulate')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--ramp-up', type=int, default=10, help='Ramp-up time in seconds')
    parser.add_argument('--matches', type=int, default=5, help='Matches per user to process')
    
    args = parser.parse_args()
    
    tester = LoadTester(
        concurrent_users=args.users,
        test_duration_seconds=args.duration,
        ramp_up_seconds=args.ramp_up,
        matches_per_user=args.matches
    )
    
    await tester.run_test()

if __name__ == "__main__":
    asyncio.run(main()) 