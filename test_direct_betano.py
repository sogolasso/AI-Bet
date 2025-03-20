import asyncio
import logging
import time
import json
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

async def test_direct_betano_scraper():
    """Test the direct Betano scraper implementation."""
    try:
        logger.info("Testing direct Betano scraper...")
        
        # Load the scraper
        from data.collectors.betano_scraper import scrape_betano_matches
        
        # Start timer
        start_time = time.time()
        
        # Run the scraper - with headless=True to avoid browser window
        matches = scrape_betano_matches(days_ahead=2, headless=True)
        
        # End timer
        elapsed_time = time.time() - start_time
        
        # Check results
        if matches:
            logger.info(f"Successfully scraped {len(matches)} matches from Betano.pt in {elapsed_time:.2f} seconds")
            
            # Save the matches to a file
            output_file = Path("betano_direct_test_results.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved match data to {output_file.absolute()}")
            
            # Display sample of first 3 matches
            if len(matches) > 0:
                logger.info("\nSample of matches:")
                for i, match in enumerate(matches[:3]):
                    logger.info(f"\nMatch {i+1}:")
                    logger.info(f"  {match['home_team']} vs {match['away_team']}")
                    logger.info(f"  League: {match['league']}")
                    logger.info(f"  Date: {match['date']} at {match['match_time'].split('T')[1][:5] if 'T' in match['match_time'] else '00:00'}")
                    odds = match.get('odds', {})
                    logger.info(f"  Odds: Home {odds.get('home_win', 'N/A')} | Draw {odds.get('draw', 'N/A')} | Away {odds.get('away_win', 'N/A')}")
                    logger.info(f"  Source: {match.get('source', 'unknown')}")
            
            return True
        else:
            logger.error("No matches scraped from Betano.pt")
            return False
            
    except Exception as e:
        logger.error(f"Error testing direct Betano scraper: {e}")
        logger.exception("Exception details:")
        return False

async def test_match_collector():
    """Test the match collector using the new direct Betano scraper."""
    try:
        logger.info("Testing match collector with direct Betano scraper...")
        
        # Import match collector
        from data.collectors.match_collector import MatchCollector
        
        # Initialize collector - DEVELOPMENT_MODE must be true
        import os
        os.environ["DEVELOPMENT_MODE"] = "true"
        
        collector = MatchCollector(days_ahead=2)
        
        # Start timer
        start_time = time.time()
        
        # Get upcoming matches
        matches = await collector.get_upcoming_matches()
        
        # End timer
        elapsed_time = time.time() - start_time
        
        # Check results
        if matches:
            logger.info(f"MatchCollector successfully retrieved {len(matches)} matches in {elapsed_time:.2f} seconds")
            
            # Save the matches to a file
            output_file = Path("match_collector_test_results.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved match data to {output_file.absolute()}")
            
            # Count sources
            sources = {}
            for match in matches:
                source = match.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            # Display source breakdown
            logger.info("\nMatch sources:")
            for source, count in sources.items():
                logger.info(f"  {source}: {count} matches")
            
            # Display sample of first 3 matches
            if len(matches) > 0:
                logger.info("\nSample of matches:")
                for i, match in enumerate(matches[:3]):
                    logger.info(f"\nMatch {i+1}:")
                    logger.info(f"  {match['home_team']} vs {match['away_team']}")
                    logger.info(f"  League: {match.get('league', 'Unknown')}")
                    logger.info(f"  Date: {match.get('date', 'Unknown')} at {match['match_time'].split('T')[1][:5] if 'T' in match.get('match_time', '') else '00:00'}")
                    odds = match.get('odds', {})
                    logger.info(f"  Odds: Home {odds.get('home_win', 'N/A')} | Draw {odds.get('draw', 'N/A')} | Away {odds.get('away_win', 'N/A')}")
                    logger.info(f"  Source: {match.get('source', 'unknown')}")
            
            return True
        else:
            logger.error("Match collector returned no matches")
            return False
            
    except Exception as e:
        logger.error(f"Error testing match collector: {e}")
        logger.exception("Exception details:")
        return False

async def main():
    """Main function to run the tests."""
    logger.info("Starting Betano direct scraper tests...")
    
    # Test the direct scraper
    direct_result = await test_direct_betano_scraper()
    
    # Test the match collector
    collector_result = await test_match_collector()
    
    if direct_result and collector_result:
        logger.info("\n✓ All tests passed successfully!")
    elif direct_result:
        logger.info("\n✓ Direct scraper test passed, but match collector test failed")
    elif collector_result:
        logger.info("\n✓ Match collector test passed, but direct scraper test failed")
    else:
        logger.info("\n✗ Both tests failed")
    
    logger.info("Tests completed")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 