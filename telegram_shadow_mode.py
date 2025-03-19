#!/usr/bin/env python3
"""
Telegram-integrated Shadow Mode for AI Football Betting Advisor

This script runs the betting advisor in shadow mode with Telegram integration,
sending updates and performance reports via the Telegram bot.
"""

import os
import sys
import json
import asyncio
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import random

# Import custom utilities
from utils.emoji_utils import sanitize_for_console, emoji_to_html
from utils.logging_config import setup_logging

# Configure logging using custom configuration
logger = setup_logging("telegram_shadow_mode", log_file="logs/telegram_shadow_mode.log")

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class TelegramShadowMode:
    """Runs the betting advisor in shadow mode with Telegram integration."""
    
    def __init__(self, 
                 duration_days: int = 14, 
                 bankroll: float = 100.0,
                 data_dir: str = 'data/shadow'):
        """Initialize the shadow mode runner with Telegram integration.
        
        Args:
            duration_days: Number of days to run in shadow mode
            bankroll: Virtual bankroll to simulate with
            data_dir: Directory to store shadow mode data
        """
        self.duration_days = duration_days
        self.bankroll = bankroll
        self.initial_bankroll = bankroll
        self.data_dir = Path(data_dir)
        self.telegram_bot = None
        
        # Check if we're in quick mode
        self.quick_mode = os.environ.get("SHADOW_QUICK_MODE") == "1"
        if self.quick_mode:
            logger.info("Running in quick mode - faster simulation with shorter delays")
        
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
        """Set up the shadow mode environment and initialize the Telegram bot."""
        logger.info("Setting up Telegram shadow mode environment...")
        
        # Force reload environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            logger.info("Environment variables reloaded from .env file")
        except Exception as e:
            logger.error(f"Error loading .env file: {e}")
        
        # Initialize Telegram bot
        from bot.new_telegram_bot import BettingAdvisorBot
        
        # Get token from environment or try direct file read if that fails
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            logger.error("Telegram bot token not found in environment variables")
            
            # Try to read directly from .env file as a fallback
            try:
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
                if os.path.exists(env_path):
                    with open(env_path, 'r') as f:
                        for line in f:
                            if line.strip().startswith('TELEGRAM_BOT_TOKEN='):
                                telegram_token = line.strip().split('=', 1)[1].strip()
                                if telegram_token.startswith('"') and telegram_token.endswith('"'):
                                    telegram_token = telegram_token[1:-1]
                                logger.info(f"Found token in .env file: {telegram_token[:5]}...")
                                break
            except Exception as e:
                logger.error(f"Error reading .env file directly: {e}")
            
            if not telegram_token:
                raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        else:
            logger.info(f"Found token in environment: {telegram_token[:5]}...")
        
        # Create a bot instance that works with both async and non-async methods
        self.telegram_bot = BettingAdvisorBot(token=telegram_token)
        await self.telegram_bot.initialize()
        
        # Add our own sync wrapper method for sending messages
        def sync_send_message(chat_id, text, parse_mode=None):
            try:
                if hasattr(self.telegram_bot.updater.bot, "send_message"):
                    # Try using the bot's send_message method directly
                    msg = self.telegram_bot.updater.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode
                    )
                    return msg
            except Exception as e:
                logger.error(f"Error in sync_send_message: {e}")
                return None
        
        # Attach the sync method to our bot
        self.telegram_bot.sync_send_message = sync_send_message
        
        # Create output files
        self._create_output_files()
        
        logger.info("Shadow mode setup complete with Telegram integration")
        
        # If we've successfully loaded existing data, send a status message
        if self._load_existing_data():
            await self._send_telegram_update("Shadow mode initialized with existing data")
    
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
    
    def _load_existing_data(self):
        """Load existing shadow mode data if available.
        
        Returns:
            bool: True if data was loaded, False otherwise
        """
        try:
            # Load bets
            if self.bets_file.exists():
                with open(self.bets_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    self.shadow_bets = list(reader)
                    
                    # Convert numeric fields
                    for bet in self.shadow_bets:
                        bet['odds'] = float(bet['odds'])
                        bet['stake'] = float(bet['stake'])
                        bet['expected_value'] = float(bet['expected_value'])
                        bet['profit_loss'] = float(bet['profit_loss'])
                        bet['bankroll_after'] = float(bet['bankroll_after'])
                
                logger.info(f"Loaded {len(self.shadow_bets)} existing shadow bets")
                
                # Update bankroll to the latest value
                if self.shadow_bets:
                    self.bankroll = self.shadow_bets[-1]['bankroll_after']
                    logger.info(f"Updated bankroll to {self.bankroll} from existing data")
            
            # Load daily results
            if self.daily_file.exists():
                with open(self.daily_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    self.daily_results = list(reader)
                    
                    # Convert numeric fields
                    for result in self.daily_results:
                        result['bets'] = int(result['bets'])
                        result['wins'] = int(result['wins'])
                        result['losses'] = int(result['losses'])
                        result['profit_loss'] = float(result['profit_loss'])
                        result['bankroll'] = float(result['bankroll'])
                        result['roi_daily'] = float(result['roi_daily'])
                        result['roi_total'] = float(result['roi_total'])
                
                logger.info(f"Loaded {len(self.daily_results)} daily performance records")
            
            return len(self.shadow_bets) > 0 or len(self.daily_results) > 0
            
        except Exception as e:
            logger.error(f"Error loading existing data: {str(e)}")
            return False
    
    async def run(self):
        """Run the shadow mode simulation for the specified duration."""
        try:
            await self.setup()
            
            # Send initial message
            await self._send_telegram_update(
                f"🏆 <b>SHADOW MODE STARTED</b> 🏆\n\n"
                f"Initial Bankroll: <b>{self.initial_bankroll:.2f}</b>\n"
                f"Duration: <b>{self.duration_days} days</b>\n"
                f"Start Date: <b>{self.start_date.strftime('%Y-%m-%d')}</b>\n"
                f"End Date: <b>{self.end_date.strftime('%Y-%m-%d')}</b>"
            )
            
            # Run simulation for each day
            current_date = self.start_date
            day_counter = 1
            
            while current_date <= self.end_date:
                logger.info(f"Day {day_counter} of {self.duration_days}")
                
                # Generate daily tips
                await self._generate_daily_tips(current_date)
                
                # Simulate results for previous day's bets
                await self._simulate_results(current_date)
                
                # Generate and send daily report
                await self._generate_daily_report(current_date)
                
                # Move to next day
                current_date += timedelta(days=1)
                day_counter += 1
                
                # Add some delay between days to avoid rate limiting
                # Use shorter delay in quick mode
                delay = 0.5 if self.quick_mode else 2
                await asyncio.sleep(delay)
            
            # Send final performance report
            await self._send_final_report()
            
        except Exception as e:
            logger.error(f"Error in shadow mode: {str(e)}", exc_info=True)
            await self._send_telegram_update(f"❌ Shadow mode error: {str(e)}")
        finally:
            # Ensure we cleanup
            if self.telegram_bot:
                await self.telegram_bot.stop()
    
    async def _generate_daily_tips(self, current_date):
        """Generate betting tips for the current day.
        
        In a real implementation, this would use the prediction model and odds evaluator.
        For demonstration, we'll generate mock tips.
        
        Args:
            current_date: The current simulation date
        """
        logger.info(f"Generating tips for {current_date.date()}")
        
        # For demonstration, generate 3-5 mock tips
        num_tips = random.randint(3, 5)
        leagues = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
        markets = ["match_winner", "over_under_2_5", "btts"]
        selections = {
            "match_winner": ["home", "away"],
            "over_under_2_5": ["over", "under"],
            "btts": ["yes", "no"]
        }
        confidence_levels = ["Low", "Medium", "High"]
        
        daily_bets = []
        total_stake = 0
        
        for i in range(num_tips):
            # Generate mock match and bet details
            match_id = f"MATCH{current_date.strftime('%Y%m%d')}{i+1}"
            home_team = f"Home Team {i+1}"
            away_team = f"Away Team {i+1}"
            league = random.choice(leagues)
            market = random.choice(markets)
            selection = random.choice(selections[market])
            odds = round(random.uniform(1.5, 4.0), 2)
            bookmaker = random.choice(["Bet365", "Betfair", "William Hill", "Unibet"])
            expected_value = round(random.uniform(0.05, 0.25), 2)
            confidence = random.choice(confidence_levels)
            
            # Calculate stake using Kelly criterion
            kelly_fraction = (odds * (0.5 + expected_value) - 1) / (odds - 1)
            kelly_fraction = max(0.01, min(0.05, kelly_fraction))  # Cap between 1% and 5%
            stake = round(self.bankroll * kelly_fraction, 2)
            total_stake += stake
            
            # Add to daily bets
            bet = {
                'date': current_date.strftime('%Y-%m-%d'),
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'market': market,
                'selection': selection,
                'odds': odds,
                'bookmaker': bookmaker,
                'stake': stake,
                'confidence': confidence,
                'expected_value': expected_value,
                'result': 'pending',
                'profit_loss': 0.0,
                'bankroll_after': self.bankroll
            }
            
            daily_bets.append(bet)
            self.shadow_bets.append(bet)
        
        # Save updated bets
        self._save_shadow_bets()
        
        # Send tips to Telegram
        if daily_bets:
            message = self._format_daily_tips(daily_bets)
            await self._send_telegram_update(message)
            logger.info(f"Sent {len(daily_bets)} tips to Telegram")
    
    async def _simulate_results(self, current_date):
        """Simulate results for pending bets.
        
        Args:
            current_date: The current simulation date
        """
        yesterday = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
        pending_bets = [bet for bet in self.shadow_bets 
                        if bet['date'] == yesterday and bet['result'] == 'pending']
        
        if not pending_bets:
            logger.info(f"No pending bets to resolve for {yesterday}")
            return
        
        logger.info(f"Simulating results for {len(pending_bets)} pending bets")
        
        # Track daily performance
        daily_profit_loss = 0
        daily_wins = 0
        daily_losses = 0
        
        # Simulate results for each pending bet
        for bet in pending_bets:
            # In a real system, we would fetch actual results
            # For simulation, we'll use expected value to influence win probability
            ev = float(bet['expected_value'])
            win_probability = 0.5 + (ev / 2)  # Better EV means higher chance of winning
            
            # Determine if bet won or lost
            if random.random() < win_probability:
                bet['result'] = 'win'
                profit = bet['stake'] * (bet['odds'] - 1)
                bet['profit_loss'] = profit
                self.bankroll += profit
                daily_profit_loss += profit
                daily_wins += 1
            else:
                bet['result'] = 'loss'
                bet['profit_loss'] = -bet['stake']
                self.bankroll -= bet['stake']
                daily_profit_loss -= bet['stake']
                daily_losses += 1
            
            bet['bankroll_after'] = self.bankroll
        
        # Save updated bets
        self._save_shadow_bets()
        
        # Record daily performance
        total_stake = sum(float(bet['stake']) for bet in pending_bets)
        daily_roi = (daily_profit_loss / total_stake * 100) if total_stake > 0 else 0
        overall_roi = ((self.bankroll - self.initial_bankroll) / self.initial_bankroll * 100) 
        
        daily_result = {
            'date': yesterday,
            'bets': len(pending_bets),
            'wins': daily_wins,
            'losses': daily_losses,
            'profit_loss': daily_profit_loss,
            'bankroll': self.bankroll,
            'roi_daily': daily_roi,
            'roi_total': overall_roi
        }
        
        self.daily_results.append(daily_result)
        
        # Save daily results
        self._save_daily_results()
        
        # Send results to Telegram
        message = self._format_daily_results(daily_result, pending_bets)
        await self._send_telegram_update(message)
    
    async def _generate_daily_report(self, current_date):
        """Generate a performance report for the current day.
        
        Args:
            current_date: The current simulation date
        """
        # Only generate reports every few days to avoid spam
        days_elapsed = (current_date - self.start_date).days
        if days_elapsed > 0 and days_elapsed % 5 == 0:
            await self._send_performance_report()
    
    async def _send_performance_report(self):
        """Send a performance report via Telegram."""
        if not self.daily_results:
            return
        
        # Calculate overall performance metrics
        total_bets = sum(result['bets'] for result in self.daily_results)
        total_wins = sum(result['wins'] for result in self.daily_results)
        total_losses = sum(result['losses'] for result in self.daily_results)
        total_profit_loss = sum(result['profit_loss'] for result in self.daily_results)
        
        win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
        roi = ((self.bankroll - self.initial_bankroll) / self.initial_bankroll * 100)
        
        # Market performance
        markets = {}
        for bet in self.shadow_bets:
            if bet['result'] != 'pending':
                market = bet['market']
                if market not in markets:
                    markets[market] = {'bets': 0, 'wins': 0, 'profit_loss': 0, 'stake': 0}
                
                markets[market]['bets'] += 1
                markets[market]['stake'] += float(bet['stake'])
                markets[market]['profit_loss'] += float(bet['profit_loss'])
                
                if bet['result'] == 'win':
                    markets[market]['wins'] += 1
        
        # Calculate ROI by market
        for market, data in markets.items():
            data['win_rate'] = (data['wins'] / data['bets'] * 100) if data['bets'] > 0 else 0
            data['roi'] = (data['profit_loss'] / data['stake'] * 100) if data['stake'] > 0 else 0
        
        # Format the report
        report = (
            f"📈 <b>SHADOW MODE PERFORMANCE REPORT</b> 📈\n\n"
            f"Duration: <b>{len(self.daily_results)} days</b>\n"
            f"Total Bets: <b>{total_bets}</b>\n"
            f"Wins/Losses: <b>{total_wins}/{total_losses}</b>\n"
            f"Win Rate: <b>{win_rate:.2f}%</b>\n"
            f"Profit/Loss: <b>{total_profit_loss:.2f}</b>\n"
            f"Current Bankroll: <b>{self.bankroll:.2f}</b>\n"
            f"ROI: <b>{roi:.2f}%</b>\n\n"
            f"<b>Performance by Market:</b>\n"
        )
        
        # Sort markets by ROI
        sorted_markets = sorted(markets.items(), key=lambda x: x[1]['roi'], reverse=True)
        
        for market, data in sorted_markets:
            report += (
                f"• {market}: {data['wins']}/{data['bets']} wins "
                f"({data['win_rate']:.1f}%), ROI: {data['roi']:.2f}%\n"
            )
        
        await self._send_telegram_update(report)
    
    async def _send_final_report(self):
        """Send a final summary report at the end of the shadow mode period."""
        # Generate and send final performance report
        await self._send_performance_report()
        
        # Additional final message
        final_message = (
            f"🏁 <b>SHADOW MODE COMPLETED</b> 🏁\n\n"
            f"Initial Bankroll: <b>{self.initial_bankroll:.2f}</b>\n"
            f"Final Bankroll: <b>{self.bankroll:.2f}</b>\n"
            f"Profit/Loss: <b>{self.bankroll - self.initial_bankroll:.2f}</b>\n"
            f"ROI: <b>{((self.bankroll - self.initial_bankroll) / self.initial_bankroll * 100):.2f}%</b>\n\n"
            f"Shadow mode has completed after {self.duration_days} days of simulation."
        )
        
        await self._send_telegram_update(final_message)
    
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
        """Save daily performance results to CSV file."""
        with open(self.daily_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'date', 'bets', 'wins', 'losses', 'profit_loss', 
                'bankroll', 'roi_daily', 'roi_total'
            ])
            
            for result in self.daily_results:
                writer.writerow([
                    result['date'], result['bets'], result['wins'], result['losses'],
                    result['profit_loss'], result['bankroll'], result['roi_daily'],
                    result['roi_total']
                ])
    
    def _format_daily_tips(self, tips):
        """Format daily tips for Telegram message.
        
        Args:
            tips: List of bet recommendations
            
        Returns:
            Formatted message string
        """
        message = f"🔮 <b>SHADOW MODE - BETTING TIPS FOR {tips[0]['date']}</b>\n\n"
        
        for i, tip in enumerate(tips, 1):
            message += (
                f"{i}. <b>{tip['home_team']} vs {tip['away_team']}</b>\n"
                f"League: {tip['league']}\n"
                f"Bet: {tip['market']} - {tip['selection']} @ {tip['odds']:.2f} ({tip['bookmaker']})\n"
                f"Stake: {tip['stake']:.2f} ({(tip['stake']/self.bankroll*100):.1f}% of bankroll)\n"
                f"Confidence: {tip['confidence']}\n"
                f"Expected Value: {tip['expected_value']:.2f}\n\n"
            )
        
        message += f"Current Bankroll: <b>{self.bankroll:.2f}</b>"
        return message
    
    def _format_daily_results(self, daily_result, resolved_bets):
        """Format daily results for Telegram message.
        
        Args:
            daily_result: Daily performance data
            resolved_bets: List of bets with results
            
        Returns:
            Formatted message string
        """
        message = f"📊 <b>SHADOW MODE - RESULTS FOR {daily_result['date']}</b>\n\n"
        
        # Summary
        win_rate = (daily_result['wins'] / daily_result['bets'] * 100) if daily_result['bets'] > 0 else 0
        
        message += (
            f"<b>Summary:</b>\n"
            f"• Bets: {daily_result['bets']}\n"
            f"• Wins/Losses: {daily_result['wins']}/{daily_result['losses']}\n"
            f"• Win Rate: {win_rate:.1f}%\n"
            f"• Profit/Loss: {daily_result['profit_loss']:.2f}\n"
            f"• Daily ROI: {daily_result['roi_daily']:.2f}%\n"
            f"• Current Bankroll: {daily_result['bankroll']:.2f}\n\n"
            f"<b>Bet Results:</b>\n\n"
        )
        
        # Individual bet results
        for bet in resolved_bets:
            result_emoji = "✅" if bet['result'] == 'win' else "❌"
            profit_loss = float(bet['profit_loss'])
            sign = "+" if profit_loss > 0 else ""
            
            message += (
                f"{result_emoji} {bet['home_team']} vs {bet['away_team']}\n"
                f"• {bet['market']} - {bet['selection']} @ {bet['odds']}\n"
                f"• Stake: {bet['stake']:.2f} | P/L: {sign}{profit_loss:.2f}\n\n"
            )
        
        return message
    
    async def _send_telegram_update(self, message):
        """Send a Telegram update to admin users."""
        try:
            # Get admin IDs from environment
            admin_ids_str = os.environ.get('TELEGRAM_ADMIN_IDS', '')
            
            # Log admin IDs for debugging
            logger.info(f"Admin IDs from environment: {admin_ids_str}")
            
            # Parse admin IDs - handle various formats (comma-separated, with/without brackets)
            if admin_ids_str:
                # Remove brackets if present
                admin_ids_str = admin_ids_str.strip('[]')
                
                # Split by comma and strip whitespace
                admin_ids = [id.strip() for id in admin_ids_str.split(',')]
                
                # Convert to integers
                admin_ids = [int(id) for id in admin_ids if id.strip().isdigit()]
                
                if not admin_ids:
                    logger.error("No valid admin IDs found after parsing")
                else:
                    logger.info(f"Parsed admin IDs: {admin_ids}")
            else:
                logger.error("No admin IDs found in environment variables")
                admin_ids = []
            
            for admin_id in admin_ids:
                try:
                    # Use our sync wrapper to avoid async/sync mismatches
                    if hasattr(self.telegram_bot, "sync_send_message"):
                        # Use the synchronous wrapper we added
                        self.telegram_bot.sync_send_message(
                            chat_id=admin_id,
                            text=message,
                            parse_mode="HTML"
                        )
                        logger.info(f"Message sent to admin {admin_id}")
                    else:
                        logger.error("No sync_send_message method available")
                except Exception as e:
                    logger.error(f"Failed to send message to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error in _send_telegram_update: {e}")
            logger.exception(e)


async def main():
    """Run the Telegram shadow mode."""
    # Load environment variables
    load_dotenv()
    
    # Ensure necessary directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("data/shadow").mkdir(exist_ok=True, parents=True)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run AI Football Betting Advisor in shadow mode with Telegram")
    parser.add_argument("--duration", type=int, default=14, help="Duration in days for shadow mode")
    parser.add_argument("--bankroll", type=float, default=1000.0, help="Initial bankroll amount")
    parser.add_argument("--config", help="Path to configuration file")
    args = parser.parse_args()
    
    # Load config file if provided
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            sys.exit(1)
    
    # Create and run shadow mode
    shadow_mode = TelegramShadowMode(
        duration_days=args.duration,
        bankroll=args.bankroll,
        data_dir="data/shadow"
    )
    
    try:
        await shadow_mode.run()
    except KeyboardInterrupt:
        logger.info("Shadow mode interrupted by user")
    except Exception as e:
        logger.error(f"Error in shadow mode: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 