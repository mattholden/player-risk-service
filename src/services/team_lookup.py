"""
Team Lookup Service - Searches Transfermarkt to find team identifiers.

This service:
1. Searches Transfermarkt for a team by name
2. Extracts the transfermarkt_id and transfermarkt_slug from search results
3. Optionally saves the team to the database

Usage:
    # As a script
    python -m src.services.team_lookup "Manchester City" "Premier League"
    
    # Programmatically
    from src.services.team_lookup import TeamLookupService
    
    service = TeamLookupService()
    result = await service.lookup_team("Manchester City", "Premier League", "England")
    if result:
        print(f"Found: {result}")
        # Optionally save to database
        team = await service.add_team_to_database(result)
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Optional, List
from urllib.parse import quote

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from database import session_scope
from database.models.team import Team


@dataclass
class TeamLookupResult:
    """Result from a Transfermarkt team lookup."""
    team_name: str
    league: str
    country: str
    transfermarkt_id: int
    transfermarkt_slug: str
    transfermarkt_url: str
    
    def __repr__(self):
        return f"TeamLookupResult(name='{self.team_name}', league='{self.league}', tm_id={self.transfermarkt_id})"


class TeamLookupService:
    """
    Service to look up team information from Transfermarkt.
    
    Searches Transfermarkt and extracts the team's ID and slug
    needed for roster scraping.
    """
    
    SEARCH_URL = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
    
    # Common league name mappings to help match results
    LEAGUE_MAPPINGS = {
        "premier league": ["premier league", "england"],
        "la liga": ["laliga", "la liga", "spain", "primera división"],
        "bundesliga": ["bundesliga", "germany", "1.bundesliga"],
        "serie a": ["serie a", "italy"],
        "ligue 1": ["ligue 1", "france"],
        "eredivisie": ["eredivisie", "netherlands"],
        "primeira liga": ["primeira liga", "portugal", "liga portugal"],
        "scottish premiership": ["scottish premiership", "scotland"],
        "championship": ["championship", "england"],
        "mls": ["mls", "major league soccer", "usa"],
    }
    
    # Country mappings
    COUNTRY_MAPPINGS = {
        "premier league": "England",
        "championship": "England",
        "la liga": "Spain",
        "bundesliga": "Germany",
        "serie a": "Italy",
        "ligue 1": "France",
        "eredivisie": "Netherlands",
        "primeira liga": "Portugal",
        "scottish premiership": "Scotland",
        "mls": "USA",
    }
    
    async def lookup_team(
        self, 
        team_name: str, 
        league: str,
        country: Optional[str] = None,
        headless: bool = True
    ) -> Optional[TeamLookupResult]:
        """
        Search Transfermarkt for a team and extract its identifiers.
        
        Args:
            team_name: Name of the team to search for
            league: League the team plays in (helps filter results)
            country: Country (optional, will be inferred from league if not provided)
            headless: Run browser in headless mode
            
        Returns:
            TeamLookupResult if found, None otherwise
        """
        # Infer country from league if not provided
        if not country:
            country = self.COUNTRY_MAPPINGS.get(league.lower(), "")
        
        print(f"\n🔍 Searching Transfermarkt for: {team_name}")
        print(f"   League: {league}")
        print(f"   Country: {country or 'Unknown'}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # Build search URL
                search_query = quote(team_name)
                url = f"{self.SEARCH_URL}?query={search_query}"
                
                print(f"   URL: {url}")
                
                # Navigate to search results
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for dynamic content
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find team results - they're in a table with class "items"
                # The search results page has multiple sections (players, clubs, etc.)
                # We want the "Clubs" section
                
                results = await self._parse_search_results(soup, team_name, league)
                
                if not results:
                    print(f"   ❌ No matching teams found")
                    return None
                
                # Return the best match
                best_match = results[0]
                print(f"   ✅ Found: {best_match.team_name}")
                print(f"      ID: {best_match.transfermarkt_id}")
                print(f"      Slug: {best_match.transfermarkt_slug}")
                print(f"      URL: {best_match.transfermarkt_url}")
                
                return best_match
                
            except Exception as e:
                print(f"   ❌ Error during search: {e}")
                import traceback
                traceback.print_exc()
                return None
                
            finally:
                await browser.close()
    
    async def _parse_search_results(
        self, 
        soup: BeautifulSoup, 
        team_name: str,
        league: str
    ) -> List[TeamLookupResult]:
        """Parse Transfermarkt search results to find matching teams."""
        results = []
        
        # Find the clubs section - look for header "Clubs" or similar
        # The structure is: <div class="box"><h2>Clubs</h2>...</div>
        
        # Find all result rows - team links typically have this structure:
        # <a href="/fc-arsenal/startseite/verein/11">Arsenal FC</a>
        
        # Look for links that match the team URL pattern
        team_links = soup.find_all('a', href=re.compile(r'/[^/]+/startseite/verein/\d+'))
        
        seen_ids = set()  # Avoid duplicates
        
        for link in team_links:
            href = link.get('href', '')
            
            # Parse the URL: /fc-arsenal/startseite/verein/11
            match = re.match(r'/([^/]+)/startseite/verein/(\d+)', href)
            if not match:
                continue
                
            slug = match.group(1)
            team_id = int(match.group(2))
            
            # Skip duplicates
            if team_id in seen_ids:
                continue
            seen_ids.add(team_id)
            
            # Get team name from link text
            found_name = link.get_text(strip=True)
            if not found_name:
                continue
            
            # Try to find the league/country info nearby
            # Usually in the same row or parent element
            parent_row = link.find_parent('tr') or link.find_parent('div')
            league_info = ""
            country_info = ""
            
            if parent_row:
                # Look for league/country text
                row_text = parent_row.get_text(" ", strip=True).lower()
                league_info = row_text
            
            # Check if this matches our search criteria
            name_match = self._fuzzy_match(team_name.lower(), found_name.lower())
            league_match = self._check_league_match(league, league_info)
            
            if name_match:
                # Infer country from league
                country = self.COUNTRY_MAPPINGS.get(league.lower(), "")
                
                result = TeamLookupResult(
                    team_name=found_name,
                    league=league,
                    country=country,
                    transfermarkt_id=team_id,
                    transfermarkt_slug=slug,
                    transfermarkt_url=f"https://www.transfermarkt.com{href}"
                )
                
                # Prioritize results that also match the league
                if league_match:
                    results.insert(0, result)
                else:
                    results.append(result)
        
        return results
    
    def _fuzzy_match(self, search: str, found: str) -> bool:
        """Check if the found name matches the search term."""
        # Simple matching - check if search terms are in found name
        search_words = search.lower().split()
        found_lower = found.lower()
        
        # All search words should be in the found name
        matches = sum(1 for word in search_words if word in found_lower)
        return matches >= len(search_words) * 0.5  # At least 50% of words match
    
    def _check_league_match(self, target_league: str, found_text: str) -> bool:
        """Check if the found text contains league indicators."""
        target_lower = target_league.lower()
        found_lower = found_text.lower()
        
        # Get possible league identifiers
        identifiers = self.LEAGUE_MAPPINGS.get(target_lower, [target_lower])
        
        return any(ident in found_lower for ident in identifiers)
    
    def add_team_to_database(self, result: TeamLookupResult) -> Optional[Team]:
        """
        Add a looked-up team to the database.
        
        Args:
            result: TeamLookupResult from lookup_team()
            
        Returns:
            Team object if added successfully, None if team already exists
        """
        with session_scope() as session:
            # Check if team already exists
            existing = session.query(Team).filter(
                Team.transfermarkt_id == result.transfermarkt_id
            ).first()
            
            if existing:
                print(f"   ⚠️  Team already exists in database: {existing.team_name}")
                return existing
            
            # Also check by name + league
            existing_by_name = session.query(Team).filter(
                Team.team_name == result.team_name,
                Team.league == result.league
            ).first()
            
            if existing_by_name:
                # Update with Transfermarkt info if missing
                if not existing_by_name.transfermarkt_id:
                    existing_by_name.transfermarkt_id = result.transfermarkt_id
                    existing_by_name.transfermarkt_slug = result.transfermarkt_slug
                    print(f"   ✅ Updated existing team with Transfermarkt data")
                    return existing_by_name
                else:
                    print(f"   ⚠️  Team already exists: {existing_by_name.team_name}")
                    return existing_by_name
            
            # Create new team
            team = Team(
                team_name=result.team_name,
                league=result.league,
                country=result.country,
                transfermarkt_id=result.transfermarkt_id,
                transfermarkt_slug=result.transfermarkt_slug,
                is_active=True
            )
            session.add(team)
            print(f"   ✅ Added team to database: {team.team_name}")
            
            return team
    
    async def lookup_and_add(
        self, 
        team_name: str, 
        league: str,
        country: Optional[str] = None,
        headless: bool = True
    ) -> Optional[Team]:
        """
        Convenience method to lookup a team and add it to the database.
        
        Args:
            team_name: Name of the team
            league: League name
            country: Country (optional)
            headless: Run browser headless
            
        Returns:
            Team object if successful, None otherwise
        """
        result = await self.lookup_team(team_name, league, country, headless)
        
        if result:
            return self.add_team_to_database(result)
        
        return None


async def main():
    """CLI entry point for team lookup."""
    import sys
    
    print("=" * 60)
    print("🔍 Team Lookup Service")
    print("=" * 60)
    
    # Parse arguments
    if len(sys.argv) < 3:
        print("\nUsage: python -m src.services.team_lookup <team_name> <league> [--save]")
        print("\nExamples:")
        print('  python -m src.services.team_lookup "Manchester City" "Premier League"')
        print('  python -m src.services.team_lookup "Barcelona" "La Liga" --save')
        print('  python -m src.services.team_lookup "Bayern Munich" "Bundesliga" --save')
        print("\nSupported leagues:")
        print("  - Premier League, Championship (England)")
        print("  - La Liga (Spain)")
        print("  - Bundesliga (Germany)")
        print("  - Serie A (Italy)")
        print("  - Ligue 1 (France)")
        print("  - Eredivisie (Netherlands)")
        print("  - MLS (USA)")
        return
    
    team_name = sys.argv[1]
    league = sys.argv[2]
    save_to_db = "--save" in sys.argv
    
    service = TeamLookupService()
    
    if save_to_db:
        print(f"\n📥 Looking up and saving: {team_name} ({league})")
        team = await service.lookup_and_add(team_name, league)
        if team:
            print(f"\n✅ Team ready for roster scraping!")
            print(f"   Run: make test-roster-update")
    else:
        print(f"\n🔍 Looking up: {team_name} ({league})")
        result = await service.lookup_team(team_name, league)
        if result:
            print(f"\n📋 To add this team to the database, run:")
            print(f'   python -m src.services.team_lookup "{team_name}" "{league}" --save')


if __name__ == "__main__":
    asyncio.run(main())

