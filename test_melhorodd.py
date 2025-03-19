import logging
from data.collectors.melhorodd_scraper import scrape_melhorodd_matches
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_melhorodd_scraper():
    """Test the MelhorOdd.pt scraper."""
    print("Starting MelhorOdd.pt scraping...")
    
    # Set days ahead to 2 to get matches for today and tomorrow
    matches = scrape_melhorodd_matches(days_ahead=2)
    
    # Save matches to a JSON file for analysis
    with open("melhorodd_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    print(f"Scraped {len(matches)} matches from MelhorOdd.pt")
    print(f"Full match data saved to melhorodd_matches.json")
    
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
        print("\n=== Detailed Sample Matches ===")
        for i, match in enumerate(matches[:3]):
            print(f"\nMatch {i+1}:")
            print(f"  {match['home_team']} vs {match['away_team']}")
            print(f"  Date: {match['date']} at {match['match_time'].split('T')[1][:5] if 'T' in match['match_time'] else '00:00'}")
            print(f"  League: {match['league']}")
            
            # Print all available odds
            print("  Odds:")
            for odd_type, value in match['odds'].items():
                if value > 0:
                    print(f"    {odd_type}: {value}")
    else:
        print("No matches were found or only example data was returned.")
        
    # Analyze source of matches to see if using example data or real scraped data
    sources = set(match['source'] for match in matches)
    if 'melhorodd_example' in sources:
        print("\nWarning: Using example data for some or all matches")
    else:
        print("\nSuccess: All matches were scraped from MelhorOdd.pt")

if __name__ == "__main__":
    test_melhorodd_scraper() 