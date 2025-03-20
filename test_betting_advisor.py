import asyncio
import logging
import json
import os
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_betting_advisor():
    """Test the full flow of the betting advisor using our scrapers."""
    try:
        logger.info("Testing betting advisor with direct Betano scraper...")
        
        # Import required classes
        from betting.betting_advisor import BettingAdvisor
        from data.collectors.match_collector import MatchCollector
        
        # Set development mode
        os.environ["DEVELOPMENT_MODE"] = "true"
        
        # Initialize advisor with match collector
        match_collector = MatchCollector(days_ahead=2)
        advisor = BettingAdvisor(match_collector=match_collector)
        
        # Get daily tips
        logger.info("Getting daily betting tips...")
        tips = await advisor.get_daily_tips(num_tips=5)
        
        if tips and len(tips) > 0:
            logger.info(f"Successfully generated {len(tips)} betting tips")
            
            # Save tips to file
            output_file = Path("advisor_tips_test_results.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(tips, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved betting tips to {output_file.absolute()}")
            
            # Display tips details
            logger.info("\nGenerated Tips:")
            for i, tip in enumerate(tips):
                logger.info(f"\nTip {i+1}:")
                logger.info(f"  Match: {tip['home_team']} vs {tip['away_team']}")
                logger.info(f"  Competition: {tip.get('competition', tip.get('league', 'Unknown Competition'))}")
                logger.info(f"  Date: {tip.get('date', 'Unknown')} at {tip.get('time', '00:00')}")
                logger.info(f"  Market: {tip.get('market', 'Unknown Market')}")
                logger.info(f"  Selection: {tip.get('selection', 'Unknown Selection')}")
                logger.info(f"  Odds: {tip.get('odds', 'N/A')}")
                logger.info(f"  Confidence: {tip.get('confidence', 'Unknown')}")
                logger.info(f"  Stake: {tip.get('stake_amount', 0):.2f} units ({tip.get('stake_percentage', '0%')})")
                
                # Show reasoning if available
                if "reasoning" in tip:
                    logger.info(f"  Reasoning: {tip['reasoning']}")
            
            return True
        else:
            logger.error("No betting tips generated")
            return False
    
    except Exception as e:
        logger.error(f"Error testing betting advisor: {e}")
        logger.exception("Exception details:")
        return False

async def main():
    """Main function to run the test."""
    logger.info("Starting betting advisor test...")
    
    # Test the betting advisor
    result = await test_betting_advisor()
    
    if result:
        logger.info("\n✓ Betting advisor test passed successfully!")
    else:
        logger.info("\n✗ Betting advisor test failed")
    
    logger.info("Test completed")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 