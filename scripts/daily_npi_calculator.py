# Daily NPI Calculator - Works with rolling scraper data
# Loads accumulated games and calculates current NPI rankings

import json
import os
import pandas as pd
from datetime import datetime
import sys

# Add the myapp directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'myapp'))

try:
    from models.official_soccer_npi import OfficialSoccerNPI
except ImportError:
    print("❌ Could not import OfficialSoccerNPI")
    print("   Make sure myapp/models/official_soccer_npi.py exists")
    exit(1)

class DailyNPICalculator:
    def __init__(self, data_dir="data"):
        """
        Initialize the daily NPI calculator
        
        Args:
            data_dir (str): Directory containing scraped game data
        """
        self.data_dir = data_dir
        self.games_file = os.path.join(data_dir, "all_season_games.json")
        self.rankings_file = os.path.join(data_dir, "current_npi_rankings.json")
        self.rankings_csv = os.path.join(data_dir, "current_npi_rankings.csv")
        self.summary_file = os.path.join(data_dir, "npi_summary.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)

    def load_games(self):
        """Load all accumulated games from the rolling scraper"""
        if not os.path.exists(self.games_file):
            print(f"❌ No games file found at {self.games_file}")
            print("   Run the daily scraper first: python daily_rolling_scraper.py")
            return []
        
        try:
            with open(self.games_file, 'r') as f:
                games = json.load(f)
            print(f"📂 Loaded {len(games)} games from accumulated data")
            return games
        except Exception as e:
            print(f"❌ Error loading games: {e}")
            return []

    def filter_games_by_date_range(self, games, start_date="2024-08-30", end_date="2024-11-10"):
        """
        Filter games to only include those in the specified date range
        
        Args:
            games (list): List of all games
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            list: Filtered games within date range
        """
        filtered_games = []
        
        for game in games:
            game_date = game.get('game_date', '')
            if start_date <= game_date <= end_date:
                filtered_games.append(game)
        
        print(f"📅 Filtered to {len(filtered_games)} games between {start_date} and {end_date}")
        return filtered_games

    def convert_to_npi_format(self, games):
        """
        Convert scraped games to NPI calculator format
        
        Args:
            games (list): Scraped games from rolling scraper
            
        Returns:
            list: Games in NPI calculator format
        """
        npi_games = []
        
        for game in games:
            try:
                home_team = game.get('home_team', '').strip()
                away_team = game.get('away_team', '').strip()
                home_score = int(game.get('home_team_score', 0))
                away_score = int(game.get('away_team_score', 0))
                
                # Skip invalid games
                if not home_team or not away_team or home_team == away_team:
                    continue
                
                npi_game = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'date': game.get('game_date', ''),
                    'status': game.get('status', 'FINAL')
                }
                
                npi_games.append(npi_game)
                
            except (ValueError, TypeError) as e:
                print(f"⚠️  Skipping malformed game: {game.get('home_team', 'Unknown')} vs {game.get('away_team', 'Unknown')}")
                continue
        
        print(f"✅ Converted {len(npi_games)} valid games for NPI calculation")
        return npi_games

    def calculate_current_rankings(self, games):
        """
        Calculate current NPI rankings from all accumulated games
        
        Args:
            games (list): Games in NPI format
            
        Returns:
            list: Current NPI rankings
        """
        if not games:
            print("❌ No games available for NPI calculation")
            return []
        
        print("🧮 Calculating NPI rankings from accumulated data...")
        
        # Create NPI calculator
        npi_calculator = OfficialSoccerNPI()
        
        # Add all games
        for game in games:
            npi_calculator.add_game(
                home_team=game['home_team'],
                away_team=game['away_team'],
                home_score=game['home_score'],
                away_score=game['away_score']
            )
        
        # Calculate rankings
        rankings = npi_calculator.calculate_npi()
        
        if rankings:
            print(f"🏆 Calculated rankings for {len(rankings)} teams")
        else:
            print("❌ No rankings calculated")
        
        return rankings

    def save_rankings(self, rankings):
        """Save current rankings to files"""
        if not rankings:
            print("❌ No rankings to save")
            return
        
        # Save detailed JSON
        with open(self.rankings_file, 'w') as f:
            json.dump(rankings, f, indent=2)
        
        # Save CSV for easy viewing
        df = pd.DataFrame(rankings)
        df.to_csv(self.rankings_csv, index=False)
        
        print(f"💾 Saved rankings to {self.rankings_file} and {self.rankings_csv}")

    def create_summary(self, rankings, total_games):
        """Create a summary of current NPI standings"""
        if not rankings:
            return {}
        
        # Calculate summary statistics
        tournament_eligible = [team for team in rankings if team.get('tournament_eligible', False)]
        top_10 = rankings[:10]
        
        summary = {
            'last_updated': datetime.now().isoformat(),
            'total_teams': len(rankings),
            'total_games': total_games,
            'tournament_eligible_teams': len(tournament_eligible),
            'top_10': top_10,
            'season_progress': {
                'games_with_8plus_wins': len([t for t in rankings if t.get('wins', 0) >= 8]),
                'games_with_10plus_wins': len([t for t in rankings if t.get('wins', 0) >= 10]),
                'average_games_played': sum(t.get('total_games', 0) for t in rankings) / len(rankings) if rankings else 0
            }
        }
        
        # Save summary
        with open(self.summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary

    def run_daily_calculation(self):
        """
        Main function for daily NPI calculation (perfect for GitHub Actions)
        
        Returns:
            dict: Summary of the calculation run
        """
        print(f"🧮 DAILY NPI RANKING CALCULATION")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Load all accumulated games
        all_games = self.load_games()
        
        if not all_games:
            return {'error': 'No games found'}
        
        # Filter to season date range
        season_games = self.filter_games_by_date_range(all_games)
        
        if not season_games:
            return {'error': 'No games in season date range'}
        
        # Convert to NPI format
        npi_games = self.convert_to_npi_format(season_games)
        
        if not npi_games:
            return {'error': 'No valid games after conversion'}
        
        # Calculate current rankings
        rankings = self.calculate_current_rankings(npi_games)
        
        if not rankings:
            return {'error': 'NPI calculation failed'}
        
        # Save rankings
        self.save_rankings(rankings)
        
        # Create summary
        summary = self.create_summary(rankings, len(npi_games))
        
        # Print current top 10
        print(f"\n🏆 CURRENT TOP 10 NPI RANKINGS:")
        print("=" * 60)
        for i, team in enumerate(rankings[:10], 1):
            npi_score = team.get('npi', 0)
            wins = team.get('wins', 0)
            losses = team.get('losses', 0)
            ties = team.get('ties', 0)
            eligible = "✓" if team.get('tournament_eligible', False) else "✗"
            
            print(f"{i:2d}. {team['team']:<30} {npi_score:6.3f} ({wins}-{losses}-{ties}) {eligible}")
        
        # Summary stats
        print(f"\n📊 SUMMARY:")
        print(f"   Total teams ranked: {len(rankings)}")
        print(f"   Tournament eligible (8+ wins): {summary.get('tournament_eligible_teams', 0)}")
        print(f"   Games used in calculation: {len(npi_games)}")
        print(f"   Average games per team: {summary['season_progress']['average_games_played']:.1f}")
        
        result = {
            'success': True,
            'teams_ranked': len(rankings),
            'games_processed': len(npi_games),
            'tournament_eligible': summary.get('tournament_eligible_teams', 0),
            'last_updated': summary['last_updated']
        }
        
        print(f"\n✅ NPI CALCULATION COMPLETE")
        return result


def main():
    """Main function for command line usage"""
    print("🧮 Daily NPI Calculator")
    
    # Create calculator
    calculator = DailyNPICalculator()
    
    # Run daily calculation
    result = calculator.run_daily_calculation()
    
    if result.get('error'):
        print(f"❌ Calculation failed: {result['error']}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
