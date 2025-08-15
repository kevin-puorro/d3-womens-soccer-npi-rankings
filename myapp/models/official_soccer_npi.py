# Official NCAA D3 Women's Soccer NPI Calculator
# Save as: myapp/models/official_soccer_npi.py

from collections import defaultdict
import math

class OfficialSoccerNPI:
    """
    Official NCAA Power Index calculator for D3 Women's Soccer
    Uses exact parameters from NCAA official document:
    https://ncaaorg.s3.amazonaws.com/championships/sports/soccer/d3/women/2024-25D3WSO_PowerIndexReport.pdf
    """
    
    def __init__(self):
        # Official NCAA D3 Women's Soccer Parameters
        self.WIN_PERCENTAGE_WEIGHT = 0.20  # 20%
        self.STRENGTH_OF_SCHEDULE_WEIGHT = 0.80  # 80%
        self.HOME_MULTIPLIER = 1.0  # No home field advantage
        self.AWAY_MULTIPLIER = 1.0  # No away field disadvantage
        self.QUALITY_WIN_BASE = 54.00  # Teams above this NPI give QWB
        self.QUALITY_WIN_MULTIPLIER = 0.500  # Bonus amount per quality win
        self.OVERTIME_WIN_WEIGHT = 1.0  # 100% - overtime wins count as full wins
        self.OVERTIME_LOSS_WEIGHT = 0.0  # 0% - overtime losses count as full losses
        self.MINIMUM_WINS = 8.0  # Teams need 8+ wins for tournament consideration
        
        # Tie handling: ties = 1/3 win + 2/3 loss (2024 NCAA rule change)
        self.TIE_WIN_VALUE = 1.0 / 3.0
        self.TIE_LOSS_VALUE = 2.0 / 3.0
        
        # Data storage
        self.teams = defaultdict(lambda: {
            'wins': 0,
            'losses': 0,
            'ties': 0,
            'opponents': [],
            'quality_wins': [],
            'games': []
        })
        
        # Final calculated values
        self.final_npis = {}
        
    def add_game(self, home_team, away_team, home_score, away_score):
        """
        Add a game to the NPI calculation
        
        Args:
            home_team (str): Name of home team
            away_team (str): Name of away team  
            home_score (int): Home team's score
            away_score (int): Away team's score
        """
        # Determine game outcome
        if home_score > away_score:
            # Home team wins
            self.teams[home_team]['wins'] += 1
            self.teams[away_team]['losses'] += 1
            winner = home_team
            loser = away_team
        elif away_score > home_score:
            # Away team wins
            self.teams[away_team]['wins'] += 1
            self.teams[home_team]['losses'] += 1
            winner = away_team
            loser = home_team
        else:
            # Tie game
            self.teams[home_team]['ties'] += 1
            self.teams[away_team]['ties'] += 1
            winner = None
            loser = None
        
        # Record opponents for SOS calculation
        self.teams[home_team]['opponents'].append(away_team)
        self.teams[away_team]['opponents'].append(home_team)
        
        # Store game details
        game_data = {
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'winner': winner,
            'loser': loser,
            'is_tie': winner is None
        }
        
        self.teams[home_team]['games'].append(game_data)
        self.teams[away_team]['games'].append(game_data)
        
    def calculate_winning_percentage(self, team_name):
        """
        Calculate winning percentage using NCAA tie handling
        Ties = 1/3 win + 2/3 loss
        """
        team = self.teams[team_name]
        
        # Adjusted wins include full wins + partial wins from ties
        adjusted_wins = team['wins'] + (team['ties'] * self.TIE_WIN_VALUE)
        
        # Total games
        total_games = team['wins'] + team['losses'] + team['ties']
        
        if total_games == 0:
            return 0.0
            
        return adjusted_wins / total_games
    
    def calculate_strength_of_schedule(self, team_name, current_npis):
        """
        Calculate Strength of Schedule as average of opponents' NPIs
        """
        team = self.teams[team_name]
        opponents = team['opponents']
        
        if not opponents:
            return 0.0
            
        total_opponent_npi = 0.0
        valid_opponents = 0
        
        for opponent in opponents:
            if opponent in current_npis:
                total_opponent_npi += current_npis[opponent]
                valid_opponents += 1
        
        if valid_opponents == 0:
            return 0.0
            
        return total_opponent_npi / valid_opponents
    
    def calculate_quality_win_bonus(self, team_name, final_npis):
        """
        Calculate Quality Win Bonus for wins against teams with NPI >= 54.00
        QWB = (Opponent NPI - 54.00) × 0.500 for each qualifying win
        """
        team = self.teams[team_name]
        total_qwb = 0.0
        
        # Reset quality wins list
        team['quality_wins'] = []
        
        for game in team['games']:
            # Check if this team won the game
            if game['winner'] == team_name:
                # Determine opponent
                opponent = game['away_team'] if game['home_team'] == team_name else game['home_team']
                
                # Check if opponent's NPI qualifies for QWB
                if opponent in final_npis and final_npis[opponent] >= self.QUALITY_WIN_BASE:
                    qwb_amount = (final_npis[opponent] - self.QUALITY_WIN_BASE) * self.QUALITY_WIN_MULTIPLIER
                    total_qwb += qwb_amount
                    
                    # Track quality wins for reporting
                    team['quality_wins'].append({
                        'opponent': opponent,
                        'opponent_npi': final_npis[opponent],
                        'qwb_amount': qwb_amount
                    })
        
        return total_qwb
    
    def calculate_npi(self, max_iterations=50, convergence_threshold=0.001):
        """
        Calculate NPI for all teams using iterative method for SOS convergence
        
        Returns:
            list: Sorted list of team rankings with NPI scores
        """
        if not self.teams:
            return []
        
        team_names = list(self.teams.keys())
        
        # Initialize NPIs with winning percentage only
        current_npis = {}
        for team_name in team_names:
            win_pct = self.calculate_winning_percentage(team_name)
            current_npis[team_name] = win_pct * 100  # Scale to 0-100 range
        
        print(f"🔄 Starting iterative NPI calculation for {len(team_names)} teams...")
        
        # Iterative calculation for SOS convergence
        for iteration in range(max_iterations):
            previous_npis = current_npis.copy()
            
            # Calculate new NPIs using current opponent NPIs for SOS
            for team_name in team_names:
                win_pct = self.calculate_winning_percentage(team_name)
                sos = self.calculate_strength_of_schedule(team_name, current_npis)
                
                # Calculate base NPI (without QWB for now)
                base_npi = (self.WIN_PERCENTAGE_WEIGHT * win_pct * 100) + (self.STRENGTH_OF_SCHEDULE_WEIGHT * sos)
                current_npis[team_name] = base_npi
            
            # Check for convergence
            max_change = 0.0
            for team_name in team_names:
                change = abs(current_npis[team_name] - previous_npis[team_name])
                max_change = max(max_change, change)
            
            print(f"   Iteration {iteration + 1}: Max change = {max_change:.6f}")
            
            if max_change < convergence_threshold:
                print(f"✅ Converged after {iteration + 1} iterations")
                break
        else:
            print(f"⚠️  Reached maximum iterations ({max_iterations})")
        
        # Store final NPIs before adding QWB
        self.final_npis = current_npis.copy()
        
        # Add Quality Win Bonuses using final converged NPIs
        print("🏆 Adding Quality Win Bonuses...")
        final_results = []
        
        for team_name in team_names:
            team = self.teams[team_name]
            
            win_pct = self.calculate_winning_percentage(team_name)
            sos = self.calculate_strength_of_schedule(team_name, self.final_npis)
            qwb = self.calculate_quality_win_bonus(team_name, self.final_npis)
            
            # Final NPI with QWB
            final_npi = (self.WIN_PERCENTAGE_WEIGHT * win_pct * 100) + (self.STRENGTH_OF_SCHEDULE_WEIGHT * sos) + qwb
            
            # Total games and record
            total_games = team['wins'] + team['losses'] + team['ties']
            
            team_result = {
                'team': team_name,
                'npi': final_npi,
                'wins': team['wins'],
                'losses': team['losses'],
                'ties': team['ties'],
                'win_percentage': win_pct,
                'strength_of_schedule': sos,
                'quality_win_bonus': qwb,
                'quality_wins_count': len(team['quality_wins']),
                'quality_wins': team['quality_wins'],
                'total_games': total_games,
                'tournament_eligible': team['wins'] >= self.MINIMUM_WINS
            }
            
            final_results.append(team_result)
        
        # Sort by NPI (highest first)
        final_results.sort(key=lambda x: x['npi'], reverse=True)
        
        # Add rankings
        for i, team_result in enumerate(final_results, 1):
            team_result['rank'] = i
        
        print(f"✅ NPI calculation complete! {len(final_results)} teams ranked")
        
        return final_results
    
    def get_team_summary(self, team_name):
        """Get detailed summary for a specific team"""
        if team_name not in self.teams:
            return None
            
        team = self.teams[team_name]
        
        return {
            'team': team_name,
            'record': f"{team['wins']}-{team['losses']}-{team['ties']}",
            'win_percentage': self.calculate_winning_percentage(team_name),
            'strength_of_schedule': self.calculate_strength_of_schedule(team_name, self.final_npis),
            'quality_win_bonus': self.calculate_quality_win_bonus(team_name, self.final_npis),
            'opponents': team['opponents'],
            'quality_wins': team['quality_wins'],
            'tournament_eligible': team['wins'] >= self.MINIMUM_WINS
        }
    
    def print_rankings(self, rankings, top_n=25):
        """Pretty print the rankings"""
        print(f"\n🏆 NCAA D3 WOMEN'S SOCCER NPI RANKINGS (Top {min(top_n, len(rankings))})")
        print("=" * 80)
        print(f"{'Rank':<4} {'Team':<25} {'NPI':<8} {'Record':<10} {'Win%':<6} {'SOS':<8} {'QWB':<6} {'Elig':<4}")
        print("-" * 80)
        
        for i, team in enumerate(rankings[:top_n], 1):
            eligible = "✓" if team['tournament_eligible'] else "✗"
            record = f"{team['wins']}-{team['losses']}-{team['ties']}"
            
            print(f"{i:<4} {team['team']:<25} {team['npi']:<8.3f} {record:<10} "
                  f"{team['win_percentage']:<6.3f} {team['strength_of_schedule']:<8.3f} "
                  f"{team['quality_win_bonus']:<6.2f} {eligible:<4}")

# Example usage and testing
if __name__ == "__main__":
    # Create calculator
    npi = OfficialSoccerNPI()
    
    # Add some test games
    print("🧪 Testing with sample games...")
    
    # Sample games - you would replace this with real data
    test_games = [
        ("Williams", "Middlebury", 2, 1),
        ("Williams", "Amherst", 1, 1),  # Tie game
        ("Middlebury", "Amherst", 3, 0),
        ("Williams", "Bowdoin", 2, 0),
        ("Middlebury", "Bowdoin", 1, 2),
        ("Amherst", "Bowdoin", 2, 1),
    ]
    
    for home, away, home_score, away_score in test_games:
        npi.add_game(home, away, home_score, away_score)
        print(f"   Added: {home} {home_score} - {away_score} {away}")
    
    # Calculate rankings
    rankings = npi.calculate_npi()
    
    # Display results
    npi.print_rankings(rankings)
    
    # Show detailed breakdown for top team
    if rankings:
        top_team = rankings[0]
        print(f"\n📊 Detailed breakdown for {top_team['team']}:")
        summary = npi.get_team_summary(top_team['team'])
        if summary:
            print(f"   Record: {summary['record']}")
            print(f"   Win%: {summary['win_percentage']:.3f}")
            print(f"   SOS: {summary['strength_of_schedule']:.3f}")
            print(f"   QWB: {summary['quality_win_bonus']:.2f}")
            print(f"   Tournament Eligible: {summary['tournament_eligible']}")
            if summary['quality_wins']:
                print(f"   Quality Wins:")
                for qw in summary['quality_wins']:
                    print(f"     vs {qw['opponent']} (NPI: {qw['opponent_npi']:.3f}) = +{qw['qwb_amount']:.2f}")
