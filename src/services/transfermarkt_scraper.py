"""
Transfermarkt Scraper Service

This module handles scraping team rosters from Transfermarkt.com.
Uses Playwright for browser automation (handles JavaScript rendering)
and BeautifulSoup for HTML parsing.

Transfermarkt URL structure:
    https://www.transfermarkt.com/{team-slug}/kader/verein/{team-id}
"""

import asyncio
import random
from typing import List, Optional
from dataclasses import dataclass

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from src.services.roster_sync import PlayerData


@dataclass
class ScraperConfig:
    """Configuration for the scraper."""
    headless: bool = True
    timeout_ms: int = 30000
    min_delay_ms: int = 1000
    max_delay_ms: int = 3000
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


class TransfermarktScraper:
    """
    Scraper for extracting team rosters from Transfermarkt.
    
    Transfermarkt has a consistent HTML structure across all team pages,
    allowing us to use the same selectors for any team.
    
    Usage:
        scraper = TransfermarktScraper()
        players = await scraper.get_squad(
            team_slug="fc-arsenal",
            team_id=11
        )
        for player in players:
            print(f"{player.player_name} - {player.position}")
    """
    
    # CSS selectors for Transfermarkt's squad table
    # These are consistent across all team pages
    SELECTORS = {
        # The main squad table
        "squad_table": "table.items",
        # Individual player rows (excluding header rows)
        "player_rows": "table.items > tbody > tr.odd, table.items > tbody > tr.even",
        # Player name within a row
        "player_name": "td.hauptlink a",
        # Position - in the inline table within the row
        "position": "table.inline-table tr:last-child td",
    }
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the scraper.
        
        Args:
            config: Optional scraper configuration
        """
        self.config = config or ScraperConfig()
    
    def _build_url(self, team_slug: str, team_id: int) -> str:
        """Build the Transfermarkt squad URL."""
        return f"https://www.transfermarkt.com/{team_slug}/kader/verein/{team_id}"
    
    async def _random_delay(self):
        """Add a random delay to avoid rate limiting."""
        delay = random.randint(self.config.min_delay_ms, self.config.max_delay_ms) / 1000
        await asyncio.sleep(delay)
    
    async def get_squad(
        self,
        team_slug: str,
        team_id: int
    ) -> List[PlayerData]:
        """
        Scrape the squad roster from Transfermarkt.
        
        Args:
            team_slug: Team's URL slug (e.g., "fc-arsenal")
            team_id: Team's Transfermarkt ID (e.g., 11)
            
        Returns:
            List of PlayerData with player names and positions
            
        Raises:
            Exception: If scraping fails
        """
        url = self._build_url(team_slug, team_id)
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=self.config.headless)
            
            try:
                # Create context with custom user agent
                context = await browser.new_context(
                    user_agent=self.config.user_agent,
                    viewport={"width": 1920, "height": 1080}
                )
                
                page = await context.new_page()
                
                # Add random delay before request
                await self._random_delay()
                
                # Navigate to the squad page
                print(f"🌐 Fetching: {url}")
                response = await page.goto(
                    url, 
                    wait_until="domcontentloaded",
                    timeout=self.config.timeout_ms
                )
                
                if not response or response.status != 200:
                    raise Exception(f"Failed to load page: HTTP {response.status if response else 'No response'}")
                
                # Wait for the squad table to load
                await page.wait_for_selector(
                    self.SELECTORS["squad_table"],
                    timeout=self.config.timeout_ms
                )
                
                # Get page content
                html = await page.content()
                
                # Parse the HTML
                players = self._parse_squad_html(html)
                
                print(f"✅ Found {len(players)} players")
                return players
                
            except PlaywrightTimeout:
                raise Exception(f"Timeout loading page: {url}")
            finally:
                await browser.close()
    
    def _parse_squad_html(self, html: str) -> List[PlayerData]:
        """
        Parse the squad HTML and extract player data.
        
        Args:
            html: Raw HTML content from the page
            
        Returns:
            List of PlayerData objects
        """
        soup = BeautifulSoup(html, "lxml")
        players = []
        
        # Find all player rows
        rows = soup.select(self.SELECTORS["player_rows"])
        
        for row in rows:
            try:
                # Extract player name
                name_elem = row.select_one(self.SELECTORS["player_name"])
                if not name_elem:
                    continue
                    
                player_name = name_elem.get_text(strip=True)
                
                # Extract position
                position = None
                position_elem = row.select_one(self.SELECTORS["position"])
                if position_elem:
                    position = position_elem.get_text(strip=True)
                
                # Skip if no valid name (log for debugging)
                if not player_name:
                    print(f"⚠️  Skipped row: could not extract player name")
                    continue
                
                players.append(PlayerData(
                    player_name=player_name,
                    position=position
                ))
                
            except Exception as e:
                # Log but continue with other players
                print(f"⚠️  Error parsing player row: {e}")
                continue
        
        return players
    
    async def get_squad_sync(
        self,
        team_slug: str,
        team_id: int
    ) -> List[PlayerData]:
        """
        Synchronous wrapper for get_squad.
        
        Use this when calling from synchronous code.
        
        Args:
            team_slug: Team's URL slug
            team_id: Team's Transfermarkt ID
            
        Returns:
            List of PlayerData
        """
        return await self.get_squad(team_slug, team_id)


def run_sync(coro):
    """Helper to run async code from sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def main():
    """
    Demo function to test the scraper.
    """
    print("=" * 60)
    print("Transfermarkt Scraper - Demo")
    print("=" * 60 + "\n")
    
    scraper = TransfermarktScraper()
    
    # Test with Arsenal
    test_teams = [
        ("fc-arsenal", 11, "Arsenal", "Premier League"),
        # Uncomment to test more teams:
        # ("manchester-united", 985, "Manchester United", "Premier League"),
        # ("fc-barcelona", 131, "Barcelona", "La Liga"),
    ]
    
    for slug, team_id, name, league in test_teams:
        print(f"\n🔄 Scraping {name} ({league})...")
        try:
            players = await scraper.get_squad(slug, team_id)
            
            print(f"\n📋 {name} Squad ({len(players)} players):")
            print("-" * 40)
            
            # Group by position for nicer output
            by_position = {}
            for p in players:
                pos = p.position or "Unknown"
                if pos not in by_position:
                    by_position[pos] = []
                by_position[pos].append(p.player_name)
            
            for pos, names in sorted(by_position.items()):
                print(f"\n  {pos}:")
                for name in names:
                    print(f"    - {name}")
                    
        except Exception as e:
            print(f"❌ Error scraping {name}: {e}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

