"""
Player name matching utilities.

Handles the complexity of matching player names between different
data sources which may have:
- Different accent handling (Gyökeres vs Gyokeres)
- Nickname variations (Gabriel Magalhães vs Gabriel)
- Name order differences (First Last vs Last, First)
- Abbreviations (William Saliba vs W. Saliba)
"""

import unicodedata
import re
from typing import Optional
from functools import lru_cache


class PlayerMatcher:
    """
    Fuzzy player name matcher with configurable similarity threshold.
    
    Uses multiple strategies to match player names:
    1. Exact match (case-insensitive)
    2. Normalized match (accent-insensitive)
    3. Levenshtein distance (typo tolerance)
    4. Partial match (surname matching)
    
    Usage:
        matcher = PlayerMatcher(threshold=0.85)
        matcher.is_match("Viktor Gyökeres", "Viktor Gyokeres")  # True
        matcher.is_match("Gabriel", "Gabriel Magalhães")  # True
    """
    
    def __init__(self, threshold: float = 0.80):
        """
        Initialize the matcher.
        
        Args:
            threshold: Minimum similarity score (0-1) for fuzzy matches
        """
        self.threshold = threshold
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def normalize(name: str) -> str:
        """
        Normalize a player name for comparison.
        
        Removes accents, converts to lowercase, strips extra whitespace.
        
        Args:
            name: Player name to normalize
            
        Returns:
            str: Normalized name
        """
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove accents using Unicode normalization
        # NFD decomposes characters, then we filter out combining marks
        normalized = unicodedata.normalize("NFD", name)
        normalized = "".join(
            char for char in normalized 
            if unicodedata.category(char) != "Mn"
        )
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        # Remove common punctuation that might differ
        normalized = re.sub(r"['\-\.]", "", normalized)
        
        return normalized
    
    @staticmethod
    def extract_surname(name: str) -> str:
        """
        Extract likely surname from a player name.
        
        Assumes Western naming convention (last word is surname).
        
        Args:
            name: Full player name
            
        Returns:
            str: Extracted surname
        """
        normalized = PlayerMatcher.normalize(name)
        parts = normalized.split()
        return parts[-1] if parts else ""
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            int: Edit distance
        """
        if len(s1) < len(s2):
            return PlayerMatcher.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def similarity_score(self, name1: str, name2: str) -> float:
        """
        Calculate similarity score between two names.
        
        Uses normalized Levenshtein distance.
        
        Args:
            name1: First player name
            name2: Second player name
            
        Returns:
            float: Similarity score (0-1, higher is more similar)
        """
        n1 = self.normalize(name1)
        n2 = self.normalize(name2)
        
        if not n1 or not n2:
            return 0.0
        
        if n1 == n2:
            return 1.0
        
        distance = self.levenshtein_distance(n1, n2)
        max_len = max(len(n1), len(n2))
        
        return 1.0 - (distance / max_len)
    
    def is_match(self, name1: str, name2: str) -> bool:
        """
        Determine if two player names refer to the same player.
        
        Uses multiple strategies:
        1. Exact normalized match
        2. Full similarity score above threshold
        3. Partial name matching (one name is substring of other)
        4. Surname matching with first initial
        
        Args:
            name1: First player name (e.g., from projections)
            name2: Second player name (e.g., from alerts)
            
        Returns:
            bool: True if names likely refer to same player
        """
        n1 = self.normalize(name1)
        n2 = self.normalize(name2)
        
        # Strategy 1: Exact normalized match
        if n1 == n2:
            return True
        
        # Strategy 2: One name is a subset of the other
        # Handles "Gabriel" matching "Gabriel Magalhães"
        if n1 in n2 or n2 in n1:
            # But make sure it's a significant match (not just "a" in "Gabriel")
            shorter = n1 if len(n1) < len(n2) else n2
            if len(shorter) >= 5:  # Minimum substring length
                return True
        
        # Strategy 3: Surname match with similar structure
        surname1 = self.extract_surname(name1)
        surname2 = self.extract_surname(name2)
        
        if surname1 == surname2 and len(surname1) >= 4:
            # Same surname - check if first parts are compatible
            # E.g., "W. Saliba" matches "William Saliba"
            parts1 = n1.split()
            parts2 = n2.split()
            
            # If one is just surname, it's a match
            if len(parts1) == 1 or len(parts2) == 1:
                return True
            
            # Check if first characters match (handles "W." vs "William")
            if parts1[0][0] == parts2[0][0]:
                return True
        
        # Strategy 4: Full fuzzy matching
        score = self.similarity_score(name1, name2)
        if score >= self.threshold:
            return True
        
        return False
    
    def find_best_match(
        self,
        target_name: str,
        candidates: list[str]
    ) -> Optional[tuple[str, float]]:
        """
        Find the best matching name from a list of candidates.
        
        Args:
            target_name: Name to match
            candidates: List of potential matches
            
        Returns:
            tuple[str, float] or None: Best match and score, or None if no match
        """
        if not candidates:
            return None
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            if self.is_match(target_name, candidate):
                score = self.similarity_score(target_name, candidate)
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        if best_match and best_score >= self.threshold:
            return (best_match, best_score)
        
        return None

