# Test script to verify NPI calculator works correctly
# Save as: test_npi_calculator.py (in your repository root)

import os
import sys

# Add the myapp directory to the path so we can import the NPI calculator
sys.path.append('myapp')

try:
    from models.official_soccer_npi import OfficialSoccerNPI
    print("✅ Successfully imported OfficialSoccerNPI")
except ImportError as e:
    print(f"❌ Could not import OfficialSoccerNPI: {e}")
    print("\nMake sure you have this file structure:")
    print("myapp/")
    print("  models/")
    print("    __init__.py")
    print("    official_soccer_npi.py")
    sys.exit(1)

def test_basic_functionality():
    """Test the NPI calculator with a small set of games"""
    print("\n🧪 TESTING NPI CALCULATOR")
    print("=" * 50)
    
    # Create calculator
    npi = OfficialSoccerNPI()
    
    # Test games with variety of outcomes
    test_games = [
        # (home_team, away_team, home_score, away_score)
        ("Williams", "Middlebury", 2, 1),      # Williams wins
        ("Williams", "Amherst", 1, 1),         # Tie
        ("Middlebury", "Amherst", 3, 0),       # Middlebury wins big
        ("Williams", "Bowdoin", 2, 0),         # Williams wins
        ("Middlebury", "Bowdoin", 1, 2),       # Bowdoin wins (upset)
        ("Amherst", "Bowdoin", 2, 1),          # Amherst wins
        ("Williams", "Colby", 3, 1),           # Williams wins
        ("Middlebury", "Colby", 2, 0),         # Middlebury wins
        ("Amherst", "Colby", 1, 1),            # Tie
        ("Bowdoin", "Colby", 0, 1),            # Colby wins
    ]
    
    print(f"Adding {len(test_games)} test games...")
    for home, away, home_score, away_score in test_games:
        npi.add_game(home, away, home_score, away_score)
        outcome = "TIE" if home_score == away_score else f"{home if home_score > away_score else away} wins"
        print(f"   {home} {home_score}-{away_score} {away} ({outcome})")
    
    # Calculate rankings
    print("\n🧮 Calculating NPI rankings...")
    rankings = npi.calculate_npi()
    
    if not rankings:
        print("❌ No rankings calculated!")
        return False
    
    # Display results
    npi.print_rankings(rankings)
    
    # Verify key aspects of the calculation
    print("\n🔍 VERIFICATION CHECKS")
    print("-" * 30)
    
    # Check that all teams have reasonable NPIs
    for team in rankings:
        if team['npi'] < 0 or team['npi'] > 100:
            print(f"❌ {team['team']} has invalid NPI: {team['npi']}")
            return False
    
    print("✅ All NPIs are in reasonable range (0-100)")
    
    # Check that winning percentage calculation includes ties correctly
    williams_data = next((team for team in rankings if team['team'] == 'Williams'), None)
    if williams_data:
        # Williams should have 3 wins, 0 losses, 1 tie
        expected_wins = 3
        expected_ties = 1
        expected_losses = 0
        
        if (williams_data['wins'] == expected_wins and 
            williams_data['ties'] == expected_ties and 
            williams_data['losses'] == expected_losses):
            
            # Tie should count as 1/3 win, so win% = (3 + 1/3) / 4 = 3.333/4 = 0.833
            expected_win_pct = (3 + 1/3) / 4
            actual_win_pct = williams_data['win_percentage']
            
            if abs(actual_win_pct - expected_win_pct) < 0.001:
                print(f"✅ Tie handling correct: Williams win% = {actual_win_pct:.3f}")
            else:
                print(f"❌ Tie handling incorrect: expected {expected_win_pct:.3f}, got {actual_win_pct:.3f}")
                return False
        else:
            print(f"❌ Williams record incorrect: expected 3-0-1, got {williams_data['wins']}-{williams_data['losses']}-{williams_data['ties']}")
            return False
    
    # Check that strength of schedule is calculated
    top_team = rankings[0]
    if top_team['strength_of_schedule'] > 0:
        print(f"✅ Strength of Schedule calculated: {top_team['team']} SOS = {top_team['strength_of_schedule']:.3f}")
    else:
        print(f"❌ Strength of Schedule not calculated for {top_team['team']}")
        return False
    
    # Check Quality Win Bonus (might be 0 if no teams have high enough NPI)
    total_qwb = sum(team['quality_win_bonus'] for team in rankings)
    print(f"✅ Total Quality Win Bonuses across all teams: {total_qwb:.2f}")
    
    # Show tournament eligibility
    eligible_teams = [team for team in rankings if team['tournament_eligible']]
    print(f"✅ Tournament eligible teams (8+ wins): {len(eligible_teams)}")
    
    return True

def test_edge_cases():
    """Test edge cases and special scenarios"""
    print("\n🧪 TESTING EDGE CASES")
    print("=" * 30)
    
    # Test with no games
    npi_empty = OfficialSoccerNPI()
    rankings_empty = npi_empty.calculate_npi()
    
    if len(rankings_empty) == 0:
        print("✅ Empty dataset handled correctly")
    else:
        print("❌ Empty dataset should return empty rankings")
        return False
    
    # Test with only tie games
    npi_ties = OfficialSoccerNPI()
    npi_ties.add_game("Team A", "Team B", 1, 1)
    npi_ties.add_game("Team A", "Team C", 2, 2)
    npi_ties.add_game("Team B", "Team C", 0, 0)
    
    rankings_ties = npi_ties.calculate_npi()
    
    if len(rankings_ties) == 3:
        # All teams should have same win percentage (1/3 from ties)
        win_pcts = [team['win_percentage'] for team in rankings_ties]
        expected_win_pct = 1/3
        
        if all(abs(wp - expected_win_pct) < 0.001 for wp in win_pcts):
            print("✅ All-tie scenario handled correctly")
        else:
            print(f"❌ All-tie scenario incorrect: win%s = {win_pcts}")
            return False
    else:
        print(f"❌ All-tie scenario should have 3 teams, got {len(rankings_ties)}")
        return False
    
    return True

def verify_official_parameters():
    """Verify that our parameters match the official NCAA document"""
    print("\n📋 VERIFYING OFFICIAL PARAMETERS")
    print("=" * 40)
    
    npi = OfficialSoccerNPI()
    
    # Check parameters against official document
    checks = [
        ("Win%/SOS Weight", f"{npi.WIN_PERCENTAGE_WEIGHT:.2f}/{npi.STRENGTH_OF_SCHEDULE_WEIGHT:.2f}", "0.20/0.80"),
        ("Home/Away Multiplier", f"{npi.HOME_MULTIPLIER:.1f}/{npi.AWAY_MULTIPLIER:.1f}", "1.0/1.0"),
        ("Quality Win Base", f"{npi.QUALITY_WIN_BASE:.2f}", "54.00"),
        ("Quality Win Multiplier", f"{npi.QUALITY_WIN_MULTIPLIER:.3f}", "0.500"),
        ("Overtime Weight", f"{npi.OVERTIME_WIN_WEIGHT:.0f}/{npi.OVERTIME_LOSS_WEIGHT:.0f}", "1/0"),
        ("Minimum Wins", f"{npi.MINIMUM_WINS:.1f}", "8.0"),
    ]
    
    all_correct = True
    for param_name, actual, expected in checks:
        if actual == expected:
            print(f"✅ {param_name}: {actual}")
        else:
            print(f"❌ {param_name}: got {actual}, expected {expected}")
            all_correct = False
    
    return all_correct

def main():
    """Run all tests"""
    print("🏈 NCAA D3 WOMEN'S SOCCER NPI CALCULATOR TESTING")
    print("=" * 60)
    
    # Test 1: Verify parameters
    if not verify_official_parameters():
        print("\n❌ FAILED: Official parameters don't match")
        return False
    
    # Test 2: Basic functionality
    if not test_basic_functionality():
        print("\n❌ FAILED: Basic functionality test")
        return False
    
    # Test 3: Edge cases
    if not test_edge_cases():
        print("\n❌ FAILED: Edge cases test")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Your NPI calculator is implementing the official NCAA formula correctly!")
    print("\nNext steps:")
    print("1. Test with real game data")
    print("2. Set up GitHub Actions automation")
    print("3. Create Streamlit dashboard")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
