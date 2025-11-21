"""
NewsAPI Article Retrieval Module

This module provides a class-based interface and utility functions 
to retrieve news articles from NewsAPI.
"""

import os
from typing import List, Dict, Optional
from newsapi import NewsApiClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class NewsAPIClient:
    """
    A wrapper class for NewsAPI that maintains an active client instance.
    
    This class provides a clean interface for retrieving news articles
    and can be used throughout an application without reinitializing
    the API client for each request.
    
    Usage:
        client = NewsAPIClient()
        articles = client.get_player_articles("Jaden Ivey", max_results=5)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the NewsAPI client.
        
        Args:
            api_key: Optional API key. If not provided, will look for 
                    NEWSAPI_KEY in environment variables.
                    
        Raises:
            ValueError: If no API key is found in arguments or environment
        """
        self.api_key = api_key or os.getenv('NEWSAPI_KEY')
        
        if not self.api_key:
            raise ValueError(
                "NEWSAPI_KEY not found. Please provide an api_key parameter "
                "or set NEWSAPI_KEY in your environment variables."
            )
        
        self._client = NewsApiClient(api_key=self.api_key)
    
    def get_articles_by_query(
        self,
        query: str,
        max_results: int = 5,
        language: str = 'en',
        sort_by: str = 'publishedAt'
    ) -> List[Dict]:
        """
        Retrieve news articles based on a search query.
        
        Args:
            query: Search query string (e.g., player name, team, topic)
            max_results: Maximum number of articles to return (default: 5)
            language: Language code for articles (default: 'en')
            sort_by: Sort order - 'publishedAt', 'relevancy', or 'popularity' 
                    (default: 'publishedAt')
                    
        Returns:
            List of article dictionaries containing title, description, url, 
            published date, source, and content
            
        Raises:
            Exception: If the API request fails
        """
        try:
            # Get articles using the everything endpoint for more flexibility
            response = self._client.get_everything(
                q=query,
                language=language,
                sort_by=sort_by,
                page_size=max_results
            )
            
            if response['status'] == 'ok':
                articles = response['articles']
                
                # Format articles for easier consumption
                formatted_articles = []
                for article in articles:
                    formatted_article = {
                        'title': article.get('title'),
                        'description': article.get('description'),
                        'url': article.get('url'),
                        'published_at': article.get('publishedAt'),
                        'source': article.get('source', {}).get('name'),
                        'author': article.get('author'),
                        'content': article.get('content')
                    }
                    formatted_articles.append(formatted_article)
                
                return formatted_articles
            else:
                raise Exception(f"API request failed with status: {response.get('status')}")
                
        except Exception as e:
            raise Exception(f"Error retrieving articles: {str(e)}")
    
    def get_player_articles(self, player_name: str, max_results: int = 5) -> List[Dict]:
        """
        Retrieve news articles about a specific player.
        
        This is a convenience method that wraps get_articles_by_query
        with player-specific defaults.
        
        Args:
            player_name: Name of the player to search for
            max_results: Maximum number of articles to return (default: 5)
            
        Returns:
            List of article dictionaries sorted by publish date (newest first)
        """
        return self.get_articles_by_query(
            query=player_name,
            max_results=max_results,
            sort_by='publishedAt'  # Newest first
        )
    
    def get_team_articles(self, team_name: str, max_results: int = 5) -> List[Dict]:
        """
        Retrieve news articles about a specific team.
        
        Args:
            team_name: Name of the team to search for
            max_results: Maximum number of articles to return (default: 5)
            
        Returns:
            List of article dictionaries sorted by publish date (newest first)
        """
        return self.get_articles_by_query(
            query=team_name,
            max_results=max_results,
            sort_by='publishedAt'
        )
    
    def search_articles(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = 'relevancy'
    ) -> List[Dict]:
        """
        Search for articles with custom sorting (defaults to relevancy).
        
        Args:
            query: Search query string
            max_results: Maximum number of articles to return (default: 10)
            sort_by: Sort order - 'publishedAt', 'relevancy', or 'popularity' 
                    (default: 'relevancy')
                    
        Returns:
            List of article dictionaries sorted by the specified criteria
        """
        return self.get_articles_by_query(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )


    def print_articles(self, articles: List[Dict]) -> None:
        """
        Pretty print a list of articles to console.
        
        Args:
            articles: List of article dictionaries to print
        """
        if not articles:
            print("No articles found.")
            return
        
        print(f"\n{'='*80}")
        print(f"Found {len(articles)} article(s)")
        print(f"{'='*80}\n")
        
        for idx, article in enumerate(articles, 1):
            print(f"Article {idx}:")
            print(f"  Title: {article['title']}")
            print(f"  Source: {article['source']}")
            print(f"  Published: {article['published_at']}")
            print(f"  URL: {article['url']}")
            if article['description']:
                print(f"  Description: {article['description'][:150]}...")
            print()


def main():
    """
    Main function demonstrating article retrieval for Jaden Ivey using the class-based API.
    """
    try:
        print("Initializing NewsAPI client...")
        
        # Initialize the client (will be reused for all requests)
        client = NewsAPIClient()
        
        print("Retrieving articles about Jaden Ivey...\n")
        
        # Get 5 most recent articles about Jaden Ivey
        articles = client.get_player_articles("Jaden Ivey", max_results=5)
        
        # Print the results
        client.print_articles(articles)
    
        
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nTo use this script, create a .env file with:")
        print("NEWSAPI_KEY=your_api_key_here")
        print("\nGet your free API key at: https://newsapi.org/")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

