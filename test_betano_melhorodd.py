import logging
from data.collectors.betano_melhorodd_scraper import scrape_betano_melhorodd_matches
import json
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_betano_melhorodd_scraper():
    """Test the specialized Betano odds scraper from MelhorOdd.pt."""
    print("Starting Betano-specific scraping from MelhorOdd.pt...")
    start_time = time.time()
    
    # Set days ahead to 2 to get matches for today and tomorrow
    matches = scrape_betano_melhorodd_matches(days_ahead=2)
    
    elapsed_time = time.time() - start_time
    
    # Save matches to a JSON file for analysis
    with open("betano_melhorodd_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    print(f"Scraped {len(matches)} matches with Betano odds from MelhorOdd.pt in {elapsed_time:.2f} seconds")
    print(f"Full match data saved to betano_melhorodd_matches.json")
    
    # If matches were found, display their details
    if matches:
        # Group matches by league
        leagues = {}
        for match in matches:
            league = match.get("league", "Unknown League")
            if league not in leagues:
                leagues[league] = []
            leagues[league].append(match)
        
        # Print summary by league
        print("\n=== Matches by League ===")
        for league, league_matches in leagues.items():
            print(f"\n{league} ({len(league_matches)} matches):")
            for i, match in enumerate(league_matches):
                match_time = match['match_time'].split('T')[1][:5] if 'T' in match['match_time'] else "00:00"
                home_odds = match['odds']['home_win']
                draw_odds = match['odds']['draw']
                away_odds = match['odds']['away_win']
                
                print(f"  {i+1}. {match['date']} {match_time} - {match['home_team']} vs {match['away_team']} ({home_odds}/{draw_odds}/{away_odds})")
        
        # Print details of first 3 matches
        print("\n=== Detailed Sample Matches with Betano Odds ===")
        for i, match in enumerate(matches[:min(3, len(matches))]):
            print(f"\nMatch {i+1}:")
            print(f"  {match['home_team']} vs {match['away_team']}")
            print(f"  Date: {match['date']} at {match['match_time'].split('T')[1][:5] if 'T' in match['match_time'] else '00:00'}")
            print(f"  League: {match['league']}")
            
            # Print all available odds
            print("  Betano Odds:")
            for odd_type, value in match['odds'].items():
                if odd_type != 'bookmaker' and value > 0:
                    print(f"    {odd_type}: {value}")
    else:
        print("No matches with Betano odds were found.")
    
    # Check if debug HTML files were created and inform the user
    debug_files = [f for f in os.listdir() if f.startswith("melhorodd_betano_debug") and f.endswith(".html")]
    if debug_files:
        print(f"\nDebug HTML files were created: {', '.join(debug_files)}")
        print("You can inspect these files to further refine the selectors if needed.")

if __name__ == "__main__":
    test_betano_melhorodd_scraper() 