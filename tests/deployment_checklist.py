#!/usr/bin/env python3
"""
Deployment Readiness Checklist for AI Football Betting Advisor

This script performs a comprehensive system validation to ensure all components
are properly configured and functioning correctly before deployment.
It covers environment variables, system dependencies, connectivity to external services,
and basic end-to-end functionality checks.
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
import importlib
from typing import Dict, List, Any, Tuple
import dotenv
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("deployment_checklist.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Update the import path
try:
    # Try the nested import structure first
    from data.collectors.match_collector import MatchCollector
except ImportError:
    # Fall back to the flat structure
    from data.match_collector import MatchCollector

class DeploymentChecker:
    """Validates system readiness for deployment."""
    
    def __init__(self):
        """Initialize deployment checker."""
        self.results = {
            "environment_variables": {"status": "pending", "details": {}},
            "dependencies": {"status": "pending", "details": {}},
            "database": {"status": "pending", "details": {}},
            "telegram_bot": {"status": "pending", "details": {}},
            "scrapers": {"status": "pending", "details": {}},
            "ml_model": {"status": "pending", "details": {}},
            "end_to_end": {"status": "pending", "details": {}}
        }
        self.critical_failures = []
        
    async def run_all_checks(self):
        """Run all deployment readiness checks."""
        logger.info("Starting deployment readiness checks...")
        
        # Check environment variables
        await self.check_environment_variables()
        
        # Check Python dependencies
        self.check_dependencies()
        
        # Check database connectivity
        await self.check_database()
        
        # Check Telegram bot configuration
        await self.check_telegram_bot()
        
        # Check scraper functionality
        await self.check_scrapers()
        
        # Check ML model readiness
        await self.check_ml_model()
        
        # Run basic end-to-end test
        await self.check_end_to_end()
        
        # Report results
        self.report_results()
    
    async def check_environment_variables(self):
        """Check if all required environment variables are set and valid."""
        logger.info("Checking environment variables...")
        
        # Load .env file if it exists
        env_file = Path('../.env')
        if env_file.exists():
            dotenv.load_dotenv(env_file)
            self.results["environment_variables"]["details"]["env_file"] = "found"
        else:
            self.results["environment_variables"]["details"]["env_file"] = "not found"
            logger.warning(".env file not found")
        
        # Define required environment variables
        required_vars = {
            "BANKROLL": {"type": "float", "min": 0.0},
            "MAX_STAKE_PERCENT": {"type": "float", "min": 0.0, "max": 100.0},
            "MIN_STAKE_PERCENT": {"type": "float", "min": 0.0, "max": 100.0},
            "DAYS_AHEAD": {"type": "int", "min": 1},
            "MIN_ODDS": {"type": "float", "min": 1.0},
            "MAX_ODDS": {"type": "float", "min": 1.0},
            "MIN_EV_THRESHOLD": {"type": "float"},
            "TELEGRAM_TOKEN": {"type": "str", "min_length": 20},
            "TELEGRAM_CHAT_ID": {"type": "str"}
        }
        
        # Check each variable
        missing = []
        invalid = []
        
        for var_name, requirements in required_vars.items():
            value = os.environ.get(var_name)
            
            if value is None:
                missing.append(var_name)
                continue
                
            # Validate value type and constraints
            try:
                if requirements["type"] == "float":
                    parsed_value = float(value)
                    if "min" in requirements and parsed_value < requirements["min"]:
                        invalid.append(f"{var_name} (below minimum: {requirements['min']})")
                    if "max" in requirements and parsed_value > requirements["max"]:
                        invalid.append(f"{var_name} (above maximum: {requirements['max']})")
                        
                elif requirements["type"] == "int":
                    parsed_value = int(value)
                    if "min" in requirements and parsed_value < requirements["min"]:
                        invalid.append(f"{var_name} (below minimum: {requirements['min']})")
                    if "max" in requirements and parsed_value > requirements["max"]:
                        invalid.append(f"{var_name} (above maximum: {requirements['max']})")
                        
                elif requirements["type"] == "str":
                    if "min_length" in requirements and len(value) < requirements["min_length"]:
                        invalid.append(f"{var_name} (too short)")
            except ValueError:
                invalid.append(f"{var_name} (invalid format)")
        
        # Update results
        if not missing and not invalid:
            self.results["environment_variables"]["status"] = "pass"
            logger.info("✅ Environment variables check passed")
        else:
            self.results["environment_variables"]["status"] = "fail"
            self.results["environment_variables"]["details"]["missing"] = missing
            self.results["environment_variables"]["details"]["invalid"] = invalid
            
            if missing:
                logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
                self.critical_failures.append("Missing required environment variables")
                
            if invalid:
                logger.error(f"❌ Invalid environment variables: {', '.join(invalid)}")
                self.critical_failures.append("Invalid environment variable values")
    
    def check_dependencies(self):
        """Check if all required Python dependencies are installed and have correct versions."""
        logger.info("Checking Python dependencies...")
        
        # Read requirements.txt
        try:
            with open('../requirements.txt', 'r') as f:
                requirements = f.readlines()
            
            # Clean up requirements
            requirements = [r.strip() for r in requirements if r.strip() and not r.startswith('#')]
            
            missing_deps = []
            version_mismatch = []
            
            for req in requirements:
                # Parse package name and version
                if "==" in req:
                    pkg_name, required_version = req.split("==")
                else:
                    pkg_name, required_version = req, None
                
                # Check if package is installed
                try:
                    pkg = importlib.import_module(pkg_name)
                    
                    # Check version if specified
                    if required_version and hasattr(pkg, "__version__"):
                        actual_version = pkg.__version__
                        if actual_version != required_version:
                            version_mismatch.append(f"{pkg_name} (required: {required_version}, found: {actual_version})")
                            
                except ImportError:
                    missing_deps.append(pkg_name)
            
            # Update results
            if not missing_deps and not version_mismatch:
                self.results["dependencies"]["status"] = "pass"
                logger.info("✅ Dependencies check passed")
            else:
                self.results["dependencies"]["status"] = "fail"
                
                if missing_deps:
                    self.results["dependencies"]["details"]["missing"] = missing_deps
                    logger.error(f"❌ Missing dependencies: {', '.join(missing_deps)}")
                    self.critical_failures.append("Missing required Python dependencies")
                    
                if version_mismatch:
                    self.results["dependencies"]["details"]["version_mismatch"] = version_mismatch
                    logger.error(f"❌ Version mismatch: {', '.join(version_mismatch)}")
                
        except FileNotFoundError:
            self.results["dependencies"]["status"] = "fail"
            self.results["dependencies"]["details"]["error"] = "requirements.txt not found"
            logger.error("❌ requirements.txt not found")
            self.critical_failures.append("requirements.txt not found")
    
    async def check_database(self):
        """Check database connectivity and permissions."""
        logger.info("Checking database connectivity...")
        
        # For Redis
        try:
            import redis
            # Try to connect to Redis
            redis_host = os.environ.get("REDIS_HOST", "localhost")
            redis_port = int(os.environ.get("REDIS_PORT", "6379"))
            
            client = redis.Redis(host=redis_host, port=redis_port, db=0)
            client.ping()  # Will raise exception if connection fails
            
            # Test basic operations
            test_key = "deployment_test_key"
            client.set(test_key, "test_value", ex=10)
            retrieved_value = client.get(test_key)
            
            if retrieved_value == b"test_value":
                self.results["database"]["status"] = "pass"
                logger.info("✅ Redis database check passed")
            else:
                self.results["database"]["status"] = "fail"
                self.results["database"]["details"]["error"] = "Value retrieval failed"
                logger.error("❌ Redis value retrieval failed")
                
            # Clean up
            client.delete(test_key)
            
        except ImportError:
            self.results["database"]["status"] = "skip"
            self.results["database"]["details"]["error"] = "Redis module not installed"
            logger.warning("⚠️ Redis module not installed - skipping database check")
            
        except redis.exceptions.ConnectionError:
            self.results["database"]["status"] = "fail"
            self.results["database"]["details"]["error"] = f"Cannot connect to Redis at {redis_host}:{redis_port}"
            logger.error(f"❌ Cannot connect to Redis at {redis_host}:{redis_port}")
            self.critical_failures.append("Cannot connect to Redis database")
        
        except Exception as e:
            self.results["database"]["status"] = "fail"
            self.results["database"]["details"]["error"] = str(e)
            logger.error(f"❌ Database check failed: {e}")
            self.critical_failures.append(f"Database check failed: {e}")
    
    async def check_telegram_bot(self):
        """Check if Telegram bot is properly configured and can send messages."""
        logger.info("Checking Telegram bot configuration...")
        
        token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if not token or not chat_id:
            self.results["telegram_bot"]["status"] = "skip"
            self.results["telegram_bot"]["details"]["error"] = "Telegram token or chat ID not configured"
            logger.warning("⚠️ Telegram token or chat ID not configured - skipping Telegram check")
            return
        
        try:
            # Try to import the telegram module
            from bot.telegram_bot import TelegramBot
            
            # Initialize bot with minimal configuration for testing
            bot = TelegramBot(token=token, chat_id=chat_id)
            
            # Test initialization
            if not bot.initialized:
                self.results["telegram_bot"]["status"] = "fail"
                self.results["telegram_bot"]["details"]["error"] = "Bot initialization failed"
                logger.error("❌ Telegram bot initialization failed")
                self.critical_failures.append("Telegram bot initialization failed")
                return
            
            # Test send message functionality in dry-run mode (avoid spamming)
            # This will validate the bot's API without actually sending messages
            await bot.test_connection()
            
            self.results["telegram_bot"]["status"] = "pass"
            logger.info("✅ Telegram bot check passed")
            
        except ImportError:
            self.results["telegram_bot"]["status"] = "fail"
            self.results["telegram_bot"]["details"]["error"] = "Telegram module not installed"
            logger.error("❌ Telegram module not installed")
            self.critical_failures.append("Telegram module not installed")
            
        except Exception as e:
            self.results["telegram_bot"]["status"] = "fail"
            self.results["telegram_bot"]["details"]["error"] = str(e)
            logger.error(f"❌ Telegram bot check failed: {e}")
            self.critical_failures.append(f"Telegram bot check failed: {e}")
    
    async def check_scrapers(self):
        """Check if scrapers can successfully fetch data."""
        logger.info("Checking scraper functionality...")
        
        try:
            # Initialize scraper
            match_collector = MatchCollector()
            
            # Test connectivity to data sources
            connectivity_results = await match_collector.test_connectivity()
            
            if connectivity_results["status"] == "success":
                self.results["scrapers"]["status"] = "pass"
                self.results["scrapers"]["details"] = connectivity_results
                logger.info("✅ Scraper check passed")
            else:
                self.results["scrapers"]["status"] = "warn"
                self.results["scrapers"]["details"] = connectivity_results
                logger.warning(f"⚠️ Some scrapers failed: {connectivity_results}")
                
        except ImportError:
            self.results["scrapers"]["status"] = "fail"
            self.results["scrapers"]["details"]["error"] = "Scraper module not installed"
            logger.error("❌ Scraper module not installed")
            self.critical_failures.append("Scraper module not installed")
            
        except Exception as e:
            self.results["scrapers"]["status"] = "fail"
            self.results["scrapers"]["details"]["error"] = str(e)
            logger.error(f"❌ Scraper check failed: {e}")
            self.critical_failures.append(f"Scraper check failed: {e}")
    
    async def check_ml_model(self):
        """Check if ML model is properly loaded and can make predictions."""
        logger.info("Checking ML model readiness...")
        
        try:
            from models.prediction import PredictionModel
            
            # Initialize model
            model = PredictionModel()
            
            # Check model readiness
            model_ready = await model.check_readiness()
            
            if model_ready:
                self.results["ml_model"]["status"] = "pass"
                logger.info("✅ ML model check passed")
            else:
                self.results["ml_model"]["status"] = "fail"
                self.results["ml_model"]["details"]["error"] = "Model not ready"
                logger.error("❌ ML model not ready")
                self.critical_failures.append("ML model not ready")
                
        except ImportError:
            self.results["ml_model"]["status"] = "fail"
            self.results["ml_model"]["details"]["error"] = "ML model module not installed"
            logger.error("❌ ML model module not installed")
            self.critical_failures.append("ML model module not installed")
            
        except Exception as e:
            self.results["ml_model"]["status"] = "fail"
            self.results["ml_model"]["details"]["error"] = str(e)
            logger.error(f"❌ ML model check failed: {e}")
            self.critical_failures.append(f"ML model check failed: {e}")
    
    async def check_end_to_end(self):
        """Run a basic end-to-end test of the entire system."""
        logger.info("Running basic end-to-end test...")
        
        try:
            # Mock imports to avoid real API calls or Telegram messages
            from unittest.mock import patch, MagicMock
            import importlib
            
            # Reset path to ensure we get the right modules
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            
            # Import the main module
            main_spec = importlib.util.find_spec('main')
            
            if main_spec is None:
                self.results["end_to_end"]["status"] = "fail"
                self.results["end_to_end"]["details"]["error"] = "main.py not found"
                logger.error("❌ main.py not found")
                self.critical_failures.append("main.py not found")
                return
                
            # Import classes from BettingAdvisor (avoid executing main.py)
            from main import BettingAdvisor
            
            # Use mocks to prevent actual network calls
            with patch('data.match_collector.MatchCollector.get_upcoming_matches') as mock_get_matches, \
                 patch('data.match_collector.MatchCollector.get_match_details') as mock_get_details, \
                 patch('data.match_collector.MatchCollector.get_match_odds') as mock_get_odds, \
                 patch('models.prediction.PredictionModel.predict_match') as mock_predict, \
                 patch('bot.telegram_bot.TelegramBot.send_message') as mock_send:
                
                # Mock return values
                mock_get_matches.return_value = [
                    {"id": "test_match_1", "home_team": "Team A", "away_team": "Team B"}
                ]
                
                mock_get_details.return_value = {
                    "id": "test_match_1",
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "league": "Test League",
                    "match_time": "2023-12-31 12:00",
                    "home_form": ["W", "W", "D"],
                    "away_form": ["L", "D", "W"],
                    "home_league_position": 4,
                    "away_league_position": 8
                }
                
                mock_get_odds.return_value = {
                    "match_winner": [
                        {"selection": "home", "odds": 2.0, "bookmaker": "test_bookie"},
                        {"selection": "draw", "odds": 3.4, "bookmaker": "test_bookie"},
                        {"selection": "away", "odds": 3.8, "bookmaker": "test_bookie"}
                    ]
                }
                
                mock_predict.return_value = [
                    {"market": "match_winner", "selection": "home", "probability": 0.55, "confidence": "medium"},
                    {"market": "match_winner", "selection": "draw", "probability": 0.25, "confidence": "low"},
                    {"market": "match_winner", "selection": "away", "probability": 0.20, "confidence": "low"}
                ]
                
                mock_send.return_value = True
                
                # Create the advisor with test settings
                advisor = BettingAdvisor(
                    bankroll=1000.0,
                    days_ahead=1,
                    dry_run=True  # Important for testing
                )
                
                # Run the main process
                await advisor.run()
                
                # Check if all the expected calls were made
                called_components = []
                
                if mock_get_matches.called:
                    called_components.append("match_collector.get_upcoming_matches")
                
                if mock_get_details.called:
                    called_components.append("match_collector.get_match_details")
                
                if mock_get_odds.called:
                    called_components.append("match_collector.get_match_odds")
                    
                if mock_predict.called:
                    called_components.append("prediction_model.predict_match")
                    
                if mock_send.called:
                    called_components.append("telegram_bot.send_message")
                
                expected_components = [
                    "match_collector.get_upcoming_matches",
                    "match_collector.get_match_details",
                    "match_collector.get_match_odds",
                    "prediction_model.predict_match",
                    "telegram_bot.send_message"
                ]
                
                missing_components = [c for c in expected_components if c not in called_components]
                
                if not missing_components:
                    self.results["end_to_end"]["status"] = "pass"
                    logger.info("✅ End-to-end test passed")
                else:
                    self.results["end_to_end"]["status"] = "fail"
                    self.results["end_to_end"]["details"]["error"] = f"Missing component calls: {missing_components}"
                    logger.error(f"❌ End-to-end test failed. Missing component calls: {missing_components}")
                    self.critical_failures.append("End-to-end test failed")
            
        except Exception as e:
            self.results["end_to_end"]["status"] = "fail"
            self.results["end_to_end"]["details"]["error"] = str(e)
            logger.error(f"❌ End-to-end test failed with error: {e}")
            self.critical_failures.append(f"End-to-end test failed: {e}")
    
    def report_results(self):
        """Generate and display a summary report of all checks."""
        logger.info("\n" + "=" * 60)
        logger.info("DEPLOYMENT READINESS REPORT")
        logger.info("=" * 60)
        
        all_pass = True
        for component, result in self.results.items():
            status = result["status"]
            status_symbol = "✅" if status == "pass" else "⚠️" if status == "warn" else "❌"
            logger.info(f"{status_symbol} {component.replace('_', ' ').title()}: {status.upper()}")
            if status != "pass":
                all_pass = False
        
        # Summary
        logger.info("\nSummary:")
        if all_pass:
            logger.info("✅ All checks passed! The system is ready for deployment.")
        elif self.critical_failures:
            logger.info(f"❌ DEPLOYMENT BLOCKED: {len(self.critical_failures)} critical issues found:")
            for i, failure in enumerate(self.critical_failures, 1):
                logger.info(f"  {i}. {failure}")
        else:
            logger.info("⚠️ Some checks failed or were skipped, but no critical failures.")
            logger.info("   The system can be deployed with caution, but review warnings first.")
        
        # Save results to file
        with open("deployment_readiness_report.json", "w") as f:
            json.dump({
                "timestamp": datetime.datetime.now().isoformat(),
                "results": self.results,
                "critical_failures": self.critical_failures,
                "ready_for_deployment": all_pass
            }, f, indent=2)
            
        logger.info("\nDetailed report saved to deployment_readiness_report.json")
        logger.info("=" * 60)
        
        return all_pass

async def main():
    """Main entry point for the deployment checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor Deployment Checker')
    parser.add_argument('--env-file', type=str, help='Path to .env file (defaults to ../.env)')
    
    args = parser.parse_args()
    
    # Load environment file if specified
    if args.env_file:
        dotenv.load_dotenv(args.env_file)
    
    checker = DeploymentChecker()
    await checker.run_all_checks()

if __name__ == "__main__":
    import datetime
    asyncio.run(main()) 