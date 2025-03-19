#!/usr/bin/env python3
"""
AI Football Betting Advisor - Main Entry Point

This is the main entry point for the AI Football Betting Advisor system,
which orchestrates the entire betting workflow, including data collection,
odds evaluation, and bet recommendations.
"""

import os
import sys
import argparse
import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import time
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/advisor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("betting_advisor")

# These will be imported only when needed to improve startup time for status checks
# from data.match_collector import MatchCollector
# from models.prediction import PredictionModel
# from betting.odds_evaluator import OddsEvaluator
# from betting.staking import StakingStrategy
# from bot.telegram_bot import TelegramBot

class BettingAdvisor:
    """Main class orchestrating the betting workflow."""
    
    def __init__(self):
        """Initialize the betting advisor."""
        self.start_time = datetime.now()
        self.config = self._load_config()
        self.setup_components()
        
    def _load_config(self):
        """Load configuration from environment variables."""
        # Load environment variables from .env file if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("python-dotenv not installed, using existing environment variables")
        
        config = {
            # Bankroll settings
            'bankroll': float(os.getenv('BANKROLL', '1000.0')),
            'max_stake_percent': float(os.getenv('MAX_STAKE_PERCENT', '5.0')),
            'min_stake_percent': float(os.getenv('MIN_STAKE_PERCENT', '0.5')),
            
            # Betting parameters
            'days_ahead': int(os.getenv('DAYS_AHEAD', '1')),
            'min_odds': float(os.getenv('MIN_ODDS', '1.5')),
            'max_odds': float(os.getenv('MAX_ODDS', '10.0')),
            'min_ev_threshold': float(os.getenv('MIN_EV_THRESHOLD', '0.05')),
            
            # Telegram Bot settings
            'telegram_token': os.getenv('TELEGRAM_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            
            # Redis settings
            'redis_host': os.getenv('REDIS_HOST', 'localhost'),
            'redis_port': int(os.getenv('REDIS_PORT', '6379')),
            
            # Operation mode
            'dry_run': os.getenv('DRY_RUN', 'false').lower() in ('true', '1', 't'),
        }
        
        # Validate required config
        missing_configs = []
        if config['telegram_token'] == '':
            missing_configs.append('TELEGRAM_TOKEN')
        if config['telegram_chat_id'] == '':
            missing_configs.append('TELEGRAM_CHAT_ID')
        
        if missing_configs:
            logger.warning(f"Missing required configuration: {', '.join(missing_configs)}")
            if not config['dry_run']:
                logger.error("Cannot run in live mode without complete configuration. Exiting.")
                sys.exit(1)
            else:
                logger.warning("Running in dry run mode with incomplete configuration.")
        
        return config
    
    def setup_components(self):
        """Set up the components for the betting advisor."""
        # Import the components (lazy loading)
        from data.match_collector import MatchCollector
        from models.prediction import PredictionModel
        from betting.odds_evaluator import OddsEvaluator
        from betting.staking import StakingStrategy
        from bot.telegram_bot import TelegramBot
        
        # Initialize components
        self.match_collector = MatchCollector(
            days_ahead=self.config['days_ahead'],
            redis_host=self.config['redis_host'],
            redis_port=self.config['redis_port']
        )
        
        self.prediction_model = PredictionModel()
        
        self.odds_evaluator = OddsEvaluator(
            min_odds=self.config['min_odds'],
            max_odds=self.config['max_odds'],
            min_ev_threshold=self.config['min_ev_threshold']
        )
        
        self.staking_strategy = StakingStrategy(
            bankroll=self.config['bankroll'],
            max_stake_percent=self.config['max_stake_percent'],
            min_stake_percent=self.config['min_stake_percent']
        )
        
        self.telegram_bot = TelegramBot(
            token=self.config['telegram_token'],
            chat_id=self.config['telegram_chat_id'],
            dry_run=self.config['dry_run']
        )
        
        logger.info("All components initialized successfully")
    
    async def run(self):
        """Run the betting advisor workflow."""
        logger.info("Starting betting advisor workflow")
        
        try:
            # Step 1: Fetch matches
            logger.info("Fetching upcoming matches...")
            matches = await self.match_collector.get_upcoming_matches()
            logger.info(f"Found {len(matches)} upcoming matches")
            
            # Step 2: Process matches for prediction
            logger.info("Processing matches for prediction...")
            match_data = await self.match_collector.process_matches(matches)
            
            # Step 3: Generate predictions
            logger.info("Generating predictions...")
            predictions = self.prediction_model.predict(match_data)
            
            # Step 4: Evaluate odds for value
            logger.info("Evaluating odds for value...")
            value_bets = self.odds_evaluator.find_value_bets(predictions)
            logger.info(f"Found {len(value_bets)} value betting opportunities")
            
            # Step 5: Calculate stakes
            logger.info("Calculating stakes...")
            recommended_bets = self.staking_strategy.calculate_stakes(value_bets)
            
            # Step 6: Select top 5 bets to recommend
            top_bets = sorted(recommended_bets, key=lambda x: x['expected_value'], reverse=True)[:5]
            
            # Step 7: Send recommendations
            logger.info(f"Sending {len(top_bets)} bet recommendations...")
            await self.telegram_bot.send_daily_tips(top_bets)
            
            # Step 8: Store recommendations for tracking
            self._store_recommendations(top_bets)
            
            logger.info("Betting advisor workflow completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error in betting advisor workflow: {str(e)}", exc_info=True)
            await self.telegram_bot.send_message(f"❌ Error running betting advisor: {str(e)}")
            return False
    
    def _store_recommendations(self, recommendations):
        """Store bet recommendations for tracking."""
        data_dir = Path("data/recommendations")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        filename = data_dir / f"recommendations_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.config['dry_run'],
                'recommendations': recommendations
            }, f, indent=4)
        
        logger.info(f"Stored recommendations to {filename}")
    
    def check_status(self):
        """Check the status of the betting advisor components."""
        status = {
            'healthy': True,
            'components': {},
            'uptime': str(datetime.now() - self.start_time),
            'version': '1.0.0',
            'env': 'production' if not self.config['dry_run'] else 'dry_run',
            'system': platform.system(),
            'python_version': platform.python_version()
        }
        
        # Check components
        try:
            # Check match collector
            status['components']['match_collector'] = {
                'status': 'healthy',
                'source_count': len(self.match_collector.get_sources())
            }
        except Exception as e:
            status['components']['match_collector'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            status['healthy'] = False
        
        try:
            # Check prediction model
            status['components']['prediction_model'] = {
                'status': 'healthy',
                'model_version': self.prediction_model.get_version()
            }
        except Exception as e:
            status['components']['prediction_model'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            status['healthy'] = False
        
        try:
            # Check odds evaluator
            status['components']['odds_evaluator'] = {
                'status': 'healthy',
                'min_odds': self.config['min_odds'],
                'max_odds': self.config['max_odds']
            }
        except Exception as e:
            status['components']['odds_evaluator'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            status['healthy'] = False
        
        try:
            # Check staking strategy
            status['components']['staking_strategy'] = {
                'status': 'healthy',
                'bankroll': self.config['bankroll']
            }
        except Exception as e:
            status['components']['staking_strategy'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            status['healthy'] = False
        
        try:
            # Check telegram bot
            status['components']['telegram_bot'] = {
                'status': 'healthy',
                'dry_run': self.config['dry_run']
            }
        except Exception as e:
            status['components']['telegram_bot'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            status['healthy'] = False
        
        return status
    
    def generate_performance_report(self):
        """Generate a performance report."""
        logger.info("Generating performance report...")
        
        # Directory for recommendations and results
        recs_dir = Path("data/recommendations")
        results_dir = Path("data/results")
        
        if not recs_dir.exists() or not results_dir.exists():
            logger.warning("Recommendations or results directory does not exist")
            return {
                'error': 'No historical data available',
                'recommendations_dir_exists': recs_dir.exists(),
                'results_dir_exists': results_dir.exists()
            }
        
        # Get all recommendation files
        rec_files = list(recs_dir.glob("recommendations_*.json"))
        if not rec_files:
            logger.warning("No recommendation files found")
            return {
                'error': 'No recommendations found',
                'dir': str(recs_dir)
            }
        
        # Aggregate stats
        total_bets = 0
        wins = 0
        losses = 0
        total_stake = 0
        total_returns = 0
        bets_by_league = {}
        bets_by_market = {}
        bets_by_confidence = {}
        
        # Process each recommendation file
        for rec_file in rec_files:
            date_str = rec_file.stem.split('_')[1]
            result_file = results_dir / f"results_{date_str}.json"
            
            # Skip if no results file
            if not result_file.exists():
                continue
            
            # Load recommendations and results
            with open(rec_file, 'r') as f:
                recommendations = json.load(f)
            
            with open(result_file, 'r') as f:
                results = json.load(f)
            
            # Match recommendations with results
            for rec in recommendations.get('recommendations', []):
                match_id = rec.get('match_id')
                if not match_id:
                    continue
                
                market = rec.get('market', 'unknown')
                league = rec.get('league', 'unknown')
                confidence = rec.get('confidence', 'medium')
                stake = rec.get('stake', 0)
                
                # Initialize dictionaries if needed
                if league not in bets_by_league:
                    bets_by_league[league] = {'bets': 0, 'wins': 0, 'stake': 0, 'returns': 0}
                if market not in bets_by_market:
                    bets_by_market[market] = {'bets': 0, 'wins': 0, 'stake': 0, 'returns': 0}
                if confidence not in bets_by_confidence:
                    bets_by_confidence[confidence] = {'bets': 0, 'wins': 0, 'stake': 0, 'returns': 0}
                
                # Find result
                for result in results.get('results', []):
                    if result.get('match_id') == match_id and result.get('market') == market:
                        total_bets += 1
                        total_stake += stake
                        
                        bets_by_league[league]['bets'] += 1
                        bets_by_market[market]['bets'] += 1
                        bets_by_confidence[confidence]['bets'] += 1
                        
                        bets_by_league[league]['stake'] += stake
                        bets_by_market[market]['stake'] += stake
                        bets_by_confidence[confidence]['stake'] += stake
                        
                        # Check win/loss
                        if result.get('won', False):
                            wins += 1
                            returns = stake * rec.get('odds', 0)
                            total_returns += returns
                            
                            bets_by_league[league]['wins'] += 1
                            bets_by_market[market]['wins'] += 1
                            bets_by_confidence[confidence]['wins'] += 1
                            
                            bets_by_league[league]['returns'] += returns
                            bets_by_market[market]['returns'] += returns
                            bets_by_confidence[confidence]['returns'] += returns
                        else:
                            losses += 1
                        
                        break
        
        # Calculate ROI
        roi = 0
        if total_stake > 0:
            roi = ((total_returns - total_stake) / total_stake) * 100
        
        # Calculate ROI by category
        for league in bets_by_league:
            if bets_by_league[league]['stake'] > 0:
                bets_by_league[league]['roi'] = ((bets_by_league[league]['returns'] - bets_by_league[league]['stake']) / bets_by_league[league]['stake']) * 100
            else:
                bets_by_league[league]['roi'] = 0
        
        for market in bets_by_market:
            if bets_by_market[market]['stake'] > 0:
                bets_by_market[market]['roi'] = ((bets_by_market[market]['returns'] - bets_by_market[market]['stake']) / bets_by_market[market]['stake']) * 100
            else:
                bets_by_market[market]['roi'] = 0
        
        for confidence in bets_by_confidence:
            if bets_by_confidence[confidence]['stake'] > 0:
                bets_by_confidence[confidence]['roi'] = ((bets_by_confidence[confidence]['returns'] - bets_by_confidence[confidence]['stake']) / bets_by_confidence[confidence]['stake']) * 100
            else:
                bets_by_confidence[confidence]['roi'] = 0
        
        # Generate report
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_bets': total_bets,
                'wins': wins,
                'losses': losses,
                'win_rate': (wins / total_bets * 100) if total_bets > 0 else 0,
                'total_stake': total_stake,
                'total_returns': total_returns,
                'profit': total_returns - total_stake,
                'roi': roi
            },
            'by_league': bets_by_league,
            'by_market': bets_by_market,
            'by_confidence': bets_by_confidence
        }
        
        # Save report
        report_dir = Path("data/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=4)
        
        logger.info(f"Performance report generated and saved to {report_file}")
        return report
    
    async def retrain_model(self):
        """Retrain the prediction model."""
        logger.info("Retraining prediction model...")
        
        try:
            # Get historical match data
            logger.info("Fetching historical match data...")
            historical_data = await self.match_collector.get_historical_matches()
            
            # Retrain model
            logger.info(f"Retraining model with {len(historical_data)} historical matches...")
            result = self.prediction_model.retrain(historical_data)
            
            # Send notification
            await self.telegram_bot.send_message(f"✅ Model retrained successfully. New accuracy: {result['accuracy']:.2f}%")
            
            logger.info("Model retraining completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error retraining model: {str(e)}", exc_info=True)
            await self.telegram_bot.send_message(f"❌ Error retraining model: {str(e)}")
            return {"error": str(e)}

def check_advisor_status():
    """Function to check the status of the advisor for health checks."""
    advisor = BettingAdvisor()
    return advisor.check_status()

async def main_async(args):
    """Async entry point for the betting advisor."""
    advisor = BettingAdvisor()
    
    if args.status:
        # Check status of components
        status = advisor.check_status()
        print(json.dumps(status, indent=4))
        if not status['healthy']:
            return 1
        return 0
    
    elif args.report:
        # Generate performance report
        report = advisor.generate_performance_report()
        print(json.dumps(report, indent=4))
        return 0
    
    elif args.retrain:
        # Retrain the model
        result = await advisor.retrain_model()
        print(json.dumps(result, indent=4))
        return 0
    
    else:
        # Run the normal betting workflow
        success = await advisor.run()
        return 0 if success else 1

def main():
    """Main entry point for the betting advisor."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor')
    parser.add_argument('--status', action='store_true', help='Check system status')
    parser.add_argument('--report', action='store_true', help='Generate performance report')
    parser.add_argument('--retrain', action='store_true', help='Retrain the prediction model')
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Run async main
    return asyncio.run(main_async(args))

if __name__ == "__main__":
    sys.exit(main()) 