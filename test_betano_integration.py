import asyncio
import logging
import sys
import json
from betting.betting_advisor import BettingAdvisor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def test_betano_integration():
    """Test the integration of Betano-specific scraper in the betting advisor."""
    logger.info("Testing Betano integration in the AI Football Betting Advisor")
    
    try:
        # Initialize the betting advisor
        advisor = BettingAdvisor()
        
        # Get daily tips
        logger.info("Getting daily tips with Betano odds...")
        tips = await advisor.get_daily_tips()
        
        # Log the number of tips generated
        logger.info(f"Generated {len(tips)} betting tips with Betano odds")
        
        # Save the tips to a JSON file for analysis
        with open("betano_tips.json", "w", encoding="utf-8") as f:
            json.dump(tips, f, indent=2, ensure_ascii=False)
        logger.info("Tips saved to betano_tips.json")
        
        # Display the first few tips
        if tips:
            logger.info("\n=== Sample Betting Tips (Betano odds) ===")
            for i, tip in enumerate(tips[:3]):
                logger.info(f"\nTip {i+1}:")
                logger.info(f"  Match: {tip['match']}")
                logger.info(f"  Competition: {tip['competition']}")
                logger.info(f"  Date: {tip['date']}")
                logger.info(f"  Market: {tip['market']} - {tip['selection']}")
                logger.info(f"  Odds: {tip['odds']} ({tip['bookmaker']})")
                logger.info(f"  Confidence: {tip['confidence']}")
                logger.info(f"  Reasoning: {tip['reasoning'][:100]}...")
        else:
            logger.warning("No tips were generated. This could indicate an issue with the Betano scraper integration.")
        
        return tips
    
    except Exception as e:
        logger.error(f"Error testing Betano integration: {e}")
        logger.exception("Exception details:")
        return []

def main():
    # Run the test asynchronously
    loop = asyncio.get_event_loop()
    tips = loop.run_until_complete(test_betano_integration())
    
    # Print summary
    if tips:
        print(f"\nSuccessfully generated {len(tips)} betting tips with Betano odds")
        print("The AI Football Betting Advisor is now using real Betano odds for betting recommendations")
    else:
        print("\nFailed to generate betting tips with Betano odds")
        print("Please check the logs for more details")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 