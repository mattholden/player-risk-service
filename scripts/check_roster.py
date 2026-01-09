"""
Quick script to check a team's roster from the database.

Usage:
    python -m scripts.check_roster "Manchester United" "Premier League"
    python -m scripts.check_roster "Arsenal" "Premier League"
    
Or use the make command:
    make check-roster TEAM="Manchester United" LEAGUE="Premier League"
"""

import sys
import json
from dotenv import load_dotenv

load_dotenv()


def check_roster(team_name: str, league: str):
    """Check roster for a team from the database."""
    from src.tools import ActiveRosterTool
    
    print("\n" + "=" * 60)
    print(f"🔍 ROSTER CHECK: {team_name}")
    print(f"   League: {league}")
    print("=" * 60)
    
    tool = ActiveRosterTool()
    result_json = tool.execute(team=team_name, league=league)
    
    try:
        result = json.loads(result_json)
        
        if result.get('roster_not_found'):
            print(f"\n❌ Roster not found!")
            print(f"   Message: {result.get('message', 'Unknown error')}")
            if result.get('suggested_sources'):
                print(f"\n   Suggested sources:")
                for source in result['suggested_sources']:
                    print(f"      - {source}")
            return
        
        players = result.get('players', [])
        print(f"\n✅ Found {len(players)} players:\n")
        
        # Group by position
        by_position = {}
        for player in players:
            pos = player.get('position', 'Unknown')
            if pos not in by_position:
                by_position[pos] = []
            by_position[pos].append(player)
        
        # Print by position
        position_order = ['Goalkeeper', 'Defence', 'Midfield', 'Attack', 'Unknown']
        for pos in position_order:
            if pos in by_position:
                print(f"📍 {pos}:")
                for p in by_position[pos]:
                    age = p.get('age', '?')
                    nationality = p.get('nationality', '?')
                    print(f"   • {p['name']} ({age}, {nationality})")
                print()
        
    except json.JSONDecodeError:
        print(f"\n❌ Failed to parse result: {result_json[:200]}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nExamples:")
        print('  python -m scripts.check_roster "Manchester United" "Premier League"')
        print('  python -m scripts.check_roster "AFC Bournemouth" "Premier League"')
        print('  python -m scripts.check_roster "Arsenal" "Premier League"')
        return
    
    team_name = sys.argv[1]
    league = sys.argv[2]
    
    check_roster(team_name, league)


if __name__ == "__main__":
    main()

