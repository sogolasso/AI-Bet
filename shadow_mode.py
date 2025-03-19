#!/usr/bin/env python3
"""
Shadow Mode Runner for AI Football Betting Advisor

This script runs the betting advisor in shadow mode, where it makes predictions and
tracks performance but doesn't actually place bets. This is useful for validating 
the system's performance before committing real money.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
import dotenv
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shadow_mode.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Make sure we can import from our project
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Update the import path
try:
    # Try the nested import structure first
    from data.collectors.match_collector import MatchCollector
except ImportError:
    # Fall back to the flat structure
    from data.match_collector import MatchCollector

class ShadowModeRunner:
    """Runs the betting advisor in shadow mode and tracks performance."""
    
    def __init__(self, 
                 duration_days: int = 14, 
                 bankroll: float = 1000.0,
                 notify_telegram: bool = True,
                 data_dir: str = 'data/shadow'):
        """Initialize the shadow mode runner.
        
        Args:
            duration_days: Number of days to run in shadow mode
            bankroll: Virtual bankroll to simulate with
            notify_telegram: Whether to send Telegram notifications
            data_dir: Directory to store shadow mode data
        """
        self.duration_days = duration_days
        self.bankroll = bankroll
        self.initial_bankroll = bankroll
        self.notify_telegram = notify_telegram
        self.data_dir = Path(data_dir)
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Track shadow bets and performance
        self.shadow_bets = []
        self.daily_results = []
        self.start_date = datetime.now()
        self.end_date = self.start_date + timedelta(days=duration_days)
        
        logger.info(f"Shadow mode initialized with {bankroll} bankroll")
        logger.info(f"Running from {self.start_date.date()} to {self.end_date.date()}")
    
    async def setup(self):
        """Set up the shadow mode environment.
        
        Imports and initializes the necessary components.
        """
        logger.info("Setting up shadow mode environment...")
        
        # Import components (done here to ensure environment variables are set first)
        from models.prediction import PredictionModel
        from betting.odds_evaluator import OddsEvaluator
        from betting.staking import StakingStrategy, StakingMethod
        from bot.telegram_bot import TelegramBot
        
        # Initialize components
        self.match_collector = MatchCollector()
        self.prediction_model = PredictionModel()
        self.odds_evaluator = OddsEvaluator(
            min_ev_threshold=float(os.environ.get('MIN_EV_THRESHOLD', 0.05)),
            min_odds=float(os.environ.get('MIN_ODDS', 1.5)),
            max_odds=float(os.environ.get('MAX_ODDS', 10.0))
        )
        
        staking_method_str = os.environ.get('STAKING_METHOD', 'kelly').upper()
        staking_method = getattr(StakingMethod, staking_method_str, StakingMethod.KELLY)
        
        self.staking_strategy = StakingStrategy(
            bankroll=self.bankroll,
            method=staking_method,
            max_stake_percent=float(os.environ.get('MAX_STAKE_PERCENT', 5.0)),
            min_stake_percent=float(os.environ.get('MIN_STAKE_PERCENT', 0.5))
        )
        
        # Initialize Telegram bot if notifications are enabled
        if self.notify_telegram:
            token = os.environ.get('TELEGRAM_TOKEN')
            chat_id = os.environ.get('TELEGRAM_CHAT_ID')
            
            if token and chat_id:
                self.telegram_bot = TelegramBot(
                    token=token,
                    chat_id=chat_id,
                    # Use shadow prefix in messages
                    message_prefix="[SHADOW MODE] "
                )
                logger.info("Telegram notifications enabled for shadow mode")
            else:
                logger.warning("Telegram credentials not found, notifications disabled")
                self.notify_telegram = False
        
        # Create output files
        self._create_output_files()
        
        logger.info("Shadow mode setup complete")
    
    def _create_output_files(self):
        """Create output files for tracking shadow mode performance."""
        # Bets CSV file
        self.bets_file = self.data_dir / 'shadow_bets.csv'
        if not self.bets_file.exists():
            with open(self.bets_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'date', 'match_id', 'home_team', 'away_team', 'league', 'market', 
                    'selection', 'odds', 'bookmaker', 'stake', 'confidence', 
                    'expected_value', 'result', 'profit_loss', 'bankroll_after'
                ])
        
        # Daily performance file
        self.daily_file = self.data_dir / 'shadow_daily.csv'
        if not self.daily_file.exists():
            with open(self.daily_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'date', 'bets', 'wins', 'losses', 'profit_loss', 
                    'bankroll', 'roi_daily', 'roi_total'
                ])
    
    async def run_daily(self):
        """Run the shadow mode for a single day."""
        today = datetime.now().date()
        logger.info(f"Running shadow mode for {today}")
        
        # Get upcoming matches
        matches = await self.match_collector.get_upcoming_matches(
            days_ahead=int(os.environ.get('DAYS_AHEAD', 1))
        )
        
        if not matches:
            logger.warning("No matches found for today")
            return
        
        logger.info(f"Found {len(matches)} matches to analyze")
        
        # Process each match
        recommendations = []
        
        for match in matches:
            try:
                # Get match details
                match_details = await self.match_collector.get_match_details(match['id'])
                
                # Get odds
                odds_data = await self.match_collector.get_match_odds(match['id'])
                
                if not odds_data:
                    continue
                
                # Make predictions
                predictions = await self.prediction_model.predict_match(match_details, odds_data)
                
                # Find value bets
                value_bets = self.odds_evaluator.evaluate_odds(
                    match_details, odds_data, predictions
                )
                
                # Calculate stakes
                if value_bets:
                    bet_recommendations = self.staking_strategy.calculate_stakes(value_bets)
                    recommendations.extend(bet_recommendations)
                
            except Exception as e:
                logger.error(f"Error processing match {match['id']}: {str(e)}")
        
        # Sort recommendations by expected value
        recommendations.sort(key=lambda x: x['odds']['ev'], reverse=True)
        
        # Limit to top 5 recommendations
        top_recommendations = recommendations[:5]
        
        if top_recommendations:
            logger.info(f"Generated {len(top_recommendations)} bet recommendations")
            
            # Save recommendations as today's shadow bets
            for rec in top_recommendations:
                self.shadow_bets.append({
                    'date': today.strftime('%Y-%m-%d'),
                    'match_id': rec['match']['id'],
                    'home_team': rec['match']['home_team'],
                    'away_team': rec['match']['away_team'],
                    'league': rec['match']['league'],
                    'market': rec['prediction']['market'],
                    'selection': rec['prediction']['selection'],
                    'odds': rec['odds']['value'],
                    'bookmaker': rec['odds']['bookmaker'],
                    'stake': rec['stake']['amount'],
                    'confidence': rec['prediction']['confidence'],
                    'expected_value': rec['odds']['ev'],
                    'result': 'pending',
                    'profit_loss': 0.0,
                    'bankroll_after': self.bankroll
                })
            
            # Save to CSV
            self._save_shadow_bets()
            
            # Send Telegram notification if enabled
            if self.notify_telegram:
                try:
                    message = self.telegram_bot.format_daily_tips(top_recommendations)
                    await self.telegram_bot.send_message(message)
                    logger.info("Sent shadow mode tips to Telegram")
                except Exception as e:
                    logger.error(f"Error sending Telegram notification: {str(e)}")
        else:
            logger.info("No value bets found for today")
    
    async def simulate_results(self):
        """Simulate or fetch results for pending shadow bets.
        
        In a real system, this would fetch actual match results. 
        For this demo, we'll simulate results with a given win rate.
        """
        logger.info("Checking for results of pending shadow bets...")
        
        # Get bets that are still pending
        pending_bets = [bet for bet in self.shadow_bets if bet['result'] == 'pending']
        
        if not pending_bets:
            logger.info("No pending bets to check")
            return
        
        daily_stats = {
            'date': datetime.now().date().strftime('%Y-%m-%d'),
            'bets': 0,
            'wins': 0,
            'losses': 0,
            'profit_loss': 0.0,
            'bankroll': self.bankroll,
            'roi_daily': 0.0,
            'roi_total': 0.0
        }
        
        # In a real system, we would fetch actual results
        # For this demo, we'll simulate with realistic win rates based on odds
        for bet in pending_bets:
            # Check if the match date has passed
            match_date = datetime.strptime(bet['date'], '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if match_date >= today:
                # Match hasn't happened yet
                continue
            
            # Simulate result based on odds
            # Lower odds (favorites) have a higher chance of winning
            odds = bet['odds']
            implied_prob = 1 / odds
            
            # Adjust for overround (bookmaker margin)
            adjusted_prob = implied_prob * 0.9  # 10% overround assumption
            
            # Add some randomness but respect the adjusted probability
            import random
            result = 'win' if random.random() < adjusted_prob else 'loss'
            
            # Update bet info
            bet['result'] = result
            
            if result == 'win':
                profit = bet['stake'] * (odds - 1)
                bet['profit_loss'] = profit
                self.bankroll += profit
                daily_stats['wins'] += 1
            else:
                bet['profit_loss'] = -bet['stake']
                self.bankroll -= bet['stake']
                daily_stats['losses'] += 1
            
            bet['bankroll_after'] = self.bankroll
            daily_stats['bets'] += 1
            daily_stats['profit_loss'] += bet['profit_loss']
        
        # Update daily stats
        if daily_stats['bets'] > 0:
            daily_stats['bankroll'] = self.bankroll
            daily_stakes = sum([bet['stake'] for bet in pending_bets 
                               if datetime.strptime(bet['date'], '%Y-%m-%d').date() < today])
            
            if daily_stakes > 0:
                daily_stats['roi_daily'] = (daily_stats['profit_loss'] / daily_stakes) * 100
            
            total_roi = ((self.bankroll - self.initial_bankroll) / self.initial_bankroll) * 100
            daily_stats['roi_total'] = total_roi
            
            self.daily_results.append(daily_stats)
            self._save_daily_results()
        
        # Save updated bets
        self._save_shadow_bets()
        
        logger.info(f"Processed results for {daily_stats['bets']} bets")
        logger.info(f"Current bankroll: {self.bankroll:.2f}")
        
        # Send performance report if we have results
        if daily_stats['bets'] > 0 and self.notify_telegram:
            try:
                # Create a simple performance report
                message = f"🔎 SHADOW MODE RESULTS UPDATE 🔎\n\n"
                message += f"Date: {daily_stats['date']}\n"
                message += f"Bets settled: {daily_stats['bets']}\n"
                message += f"Wins: {daily_stats['wins']}\n"
                message += f"Losses: {daily_stats['losses']}\n"
                message += f"Profit/Loss: {daily_stats['profit_loss']:.2f}\n"
                message += f"Daily ROI: {daily_stats['roi_daily']:.2f}%\n"
                message += f"Total Bankroll: {daily_stats['bankroll']:.2f}\n"
                message += f"Overall ROI: {daily_stats['roi_total']:.2f}%\n"
                
                await self.telegram_bot.send_message(message)
                logger.info("Sent shadow mode results to Telegram")
            except Exception as e:
                logger.error(f"Error sending Telegram notification: {str(e)}")
    
    def _save_shadow_bets(self):
        """Save shadow bets to CSV file."""
        with open(self.bets_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'date', 'match_id', 'home_team', 'away_team', 'league', 'market', 
                'selection', 'odds', 'bookmaker', 'stake', 'confidence', 
                'expected_value', 'result', 'profit_loss', 'bankroll_after'
            ])
            
            for bet in self.shadow_bets:
                writer.writerow([
                    bet['date'], bet['match_id'], bet['home_team'], bet['away_team'],
                    bet['league'], bet['market'], bet['selection'], bet['odds'],
                    bet['bookmaker'], bet['stake'], bet['confidence'],
                    bet['expected_value'], bet['result'], bet['profit_loss'],
                    bet['bankroll_after']
                ])
    
    def _save_daily_results(self):
        """Save daily results to CSV file."""
        with open(self.daily_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'date', 'bets', 'wins', 'losses', 'profit_loss', 
                'bankroll', 'roi_daily', 'roi_total'
            ])
            
            for day in self.daily_results:
                writer.writerow([
                    day['date'], day['bets'], day['wins'], day['losses'],
                    day['profit_loss'], day['bankroll'], day['roi_daily'],
                    day['roi_total']
                ])
    
    async def generate_report(self):
        """Generate a comprehensive performance report."""
        logger.info("Generating shadow mode performance report...")
        
        # Create a report directory
        report_dir = self.data_dir / 'reports'
        report_dir.mkdir(exist_ok=True)
        
        # Calculate overall statistics
        total_bets = len([bet for bet in self.shadow_bets if bet['result'] != 'pending'])
        winning_bets = len([bet for bet in self.shadow_bets if bet['result'] == 'win'])
        losing_bets = len([bet for bet in self.shadow_bets if bet['result'] == 'loss'])
        pending_bets = len([bet for bet in self.shadow_bets if bet['result'] == 'pending'])
        
        profit_loss = sum([bet['profit_loss'] for bet in self.shadow_bets])
        win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0
        roi = ((self.bankroll - self.initial_bankroll) / self.initial_bankroll * 100) if total_bets > 0 else 0
        
        # Break down by market type
        market_stats = {}
        for bet in self.shadow_bets:
            if bet['result'] == 'pending':
                continue
                
            market = bet['market']
            if market not in market_stats:
                market_stats[market] = {
                    'bets': 0, 'wins': 0, 'losses': 0, 'profit_loss': 0, 'roi': 0
                }
                
            market_stats[market]['bets'] += 1
            
            if bet['result'] == 'win':
                market_stats[market]['wins'] += 1
            else:
                market_stats[market]['losses'] += 1
                
            market_stats[market]['profit_loss'] += bet['profit_loss']
        
        # Calculate ROI for each market
        for market in market_stats:
            total_stake = sum([bet['stake'] for bet in self.shadow_bets 
                              if bet['market'] == market and bet['result'] != 'pending'])
            if total_stake > 0:
                market_stats[market]['roi'] = (market_stats[market]['profit_loss'] / total_stake * 100)
        
        # Break down by league
        league_stats = {}
        for bet in self.shadow_bets:
            if bet['result'] == 'pending':
                continue
                
            league = bet['league']
            if league not in league_stats:
                league_stats[league] = {
                    'bets': 0, 'wins': 0, 'losses': 0, 'profit_loss': 0, 'roi': 0
                }
                
            league_stats[league]['bets'] += 1
            
            if bet['result'] == 'win':
                league_stats[league]['wins'] += 1
            else:
                league_stats[league]['losses'] += 1
                
            league_stats[league]['profit_loss'] += bet['profit_loss']
        
        # Calculate ROI for each league
        for league in league_stats:
            total_stake = sum([bet['stake'] for bet in self.shadow_bets 
                              if bet['league'] == league and bet['result'] != 'pending'])
            if total_stake > 0:
                league_stats[league]['roi'] = (league_stats[league]['profit_loss'] / total_stake * 100)
        
        # Break down by confidence level
        confidence_stats = {}
        for bet in self.shadow_bets:
            if bet['result'] == 'pending':
                continue
                
            confidence = bet['confidence']
            if confidence not in confidence_stats:
                confidence_stats[confidence] = {
                    'bets': 0, 'wins': 0, 'losses': 0, 'profit_loss': 0, 'roi': 0
                }
                
            confidence_stats[confidence]['bets'] += 1
            
            if bet['result'] == 'win':
                confidence_stats[confidence]['wins'] += 1
            else:
                confidence_stats[confidence]['losses'] += 1
                
            confidence_stats[confidence]['profit_loss'] += bet['profit_loss']
        
        # Calculate ROI for each confidence level
        for confidence in confidence_stats:
            total_stake = sum([bet['stake'] for bet in self.shadow_bets 
                              if bet['confidence'] == confidence and bet['result'] != 'pending'])
            if total_stake > 0:
                confidence_stats[confidence]['roi'] = (confidence_stats[confidence]['profit_loss'] / total_stake * 100)
        
        # Create the report
        report = {
            'generated_at': datetime.now().isoformat(),
            'duration': (datetime.now() - self.start_date).days,
            'overall': {
                'initial_bankroll': self.initial_bankroll,
                'current_bankroll': self.bankroll,
                'total_bets': total_bets,
                'winning_bets': winning_bets,
                'losing_bets': losing_bets,
                'pending_bets': pending_bets,
                'profit_loss': profit_loss,
                'win_rate': win_rate,
                'roi': roi
            },
            'by_market': market_stats,
            'by_league': league_stats,
            'by_confidence': confidence_stats,
            'daily_results': self.daily_results,
            'recent_bets': [bet for bet in self.shadow_bets if bet['result'] != 'pending'][-10:]
        }
        
        # Save report as JSON
        report_file = report_dir / f'shadow_report_{datetime.now().strftime("%Y%m%d")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Shadow mode report saved to {report_file}")
        
        # Send summary to Telegram if enabled
        if self.notify_telegram:
            try:
                message = f"📊 SHADOW MODE PERFORMANCE REPORT 📊\n\n"
                message += f"Duration: {report['duration']} days\n"
                message += f"Total Bets: {total_bets}\n"
                message += f"Win Rate: {win_rate:.2f}%\n"
                message += f"Profit/Loss: {profit_loss:.2f}\n"
                message += f"ROI: {roi:.2f}%\n"
                message += f"Starting Bankroll: {self.initial_bankroll:.2f}\n"
                message += f"Current Bankroll: {self.bankroll:.2f}\n\n"
                
                message += "Top Performing Markets:\n"
                sorted_markets = sorted(
                    [(k, v) for k, v in market_stats.items() if v['bets'] >= 5],
                    key=lambda x: x[1]['roi'],
                    reverse=True
                )
                for market, stats in sorted_markets[:3]:
                    message += f"- {market}: {stats['roi']:.2f}% ROI ({stats['wins']}/{stats['bets']})\n"
                
                message += "\nTop Performing Leagues:\n"
                sorted_leagues = sorted(
                    [(k, v) for k, v in league_stats.items() if v['bets'] >= 3],
                    key=lambda x: x[1]['roi'],
                    reverse=True
                )
                for league, stats in sorted_leagues[:3]:
                    message += f"- {league}: {stats['roi']:.2f}% ROI ({stats['wins']}/{stats['bets']})\n"
                
                message += f"\nFull report saved to {report_file}"
                
                await self.telegram_bot.send_message(message)
                logger.info("Sent shadow mode report to Telegram")
            except Exception as e:
                logger.error(f"Error sending Telegram notification: {str(e)}")
        
        return report
    
    async def load_existing_data(self):
        """Load existing shadow mode data if available."""
        logger.info("Checking for existing shadow mode data...")
        
        # Load bets
        if self.bets_file.exists():
            with open(self.bets_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert numeric values
                    row['odds'] = float(row['odds'])
                    row['stake'] = float(row['stake'])
                    row['expected_value'] = float(row['expected_value'])
                    row['profit_loss'] = float(row['profit_loss'])
                    row['bankroll_after'] = float(row['bankroll_after'])
                    
                    self.shadow_bets.append(row)
            
            logger.info(f"Loaded {len(self.shadow_bets)} existing shadow bets")
            
            # Update bankroll to the latest value
            if self.shadow_bets:
                self.bankroll = self.shadow_bets[-1]['bankroll_after']
                logger.info(f"Updated bankroll to {self.bankroll} from existing data")
        
        # Load daily results
        if self.daily_file.exists():
            with open(self.daily_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert numeric values
                    row['bets'] = int(row['bets'])
                    row['wins'] = int(row['wins'])
                    row['losses'] = int(row['losses'])
                    row['profit_loss'] = float(row['profit_loss'])
                    row['bankroll'] = float(row['bankroll'])
                    row['roi_daily'] = float(row['roi_daily'])
                    row['roi_total'] = float(row['roi_total'])
                    
                    self.daily_results.append(row)
            
            logger.info(f"Loaded {len(self.daily_results)} days of existing results")
    
    async def run(self):
        """Run the shadow mode for the specified duration."""
        await self.setup()
        await self.load_existing_data()
        
        while datetime.now().date() <= self.end_date.date():
            # Run daily process
            await self.run_daily()
            
            # Check results for previous days
            await self.simulate_results()
            
            # Generate weekly report every 7 days
            days_running = (datetime.now() - self.start_date).days
            if days_running > 0 and days_running % 7 == 0:
                await self.generate_report()
            
            # Wait until tomorrow
            logger.info("Shadow mode daily run complete, waiting for next day")
            
            # For testing, we can use a shorter interval
            if os.environ.get('SHADOW_FAST_MODE') == 'true':
                await asyncio.sleep(60)  # Wait 1 minute in fast mode
            else:
                # Calculate time until tomorrow
                now = datetime.now()
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=8, minute=0, second=0, microsecond=0
                )
                seconds_until_tomorrow = (tomorrow - now).total_seconds()
                await asyncio.sleep(seconds_until_tomorrow)
        
        # Generate final report
        logger.info("Shadow mode duration complete, generating final report")
        final_report = await self.generate_report()
        
        return final_report

async def main():
    """Main entry point for shadow mode."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor - Shadow Mode')
    parser.add_argument('--days', type=int, default=14, help='Number of days to run in shadow mode')
    parser.add_argument('--bankroll', type=float, default=1000.0, help='Virtual bankroll amount')
    parser.add_argument('--no-telegram', action='store_true', help='Disable Telegram notifications')
    parser.add_argument('--data-dir', type=str, default='data/shadow', help='Directory to store shadow mode data')
    parser.add_argument('--env-file', type=str, default='.env', help='Path to .env file')
    parser.add_argument('--fast-mode', action='store_true', help='Run in fast mode for testing (1 minute intervals)')
    
    args = parser.parse_args()
    
    # Load environment variables
    if os.path.exists(args.env_file):
        dotenv.load_dotenv(args.env_file)
        logger.info(f"Loaded environment from {args.env_file}")
    
    # Set fast mode if requested
    if args.fast_mode:
        os.environ['SHADOW_FAST_MODE'] = 'true'
    
    # Create and run shadow mode
    shadow_runner = ShadowModeRunner(
        duration_days=args.days,
        bankroll=args.bankroll,
        notify_telegram=not args.no_telegram,
        data_dir=args.data_dir
    )
    
    try:
        await shadow_runner.run()
    except KeyboardInterrupt:
        logger.info("Shadow mode interrupted by user")
        # Generate report on exit
        await shadow_runner.generate_report()
    except Exception as e:
        logger.error(f"Shadow mode error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 