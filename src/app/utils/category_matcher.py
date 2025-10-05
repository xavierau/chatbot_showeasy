from difflib import SequenceMatcher
from typing import Optional, List, Dict


class CategoryMatcher:
    """Fuzzy matcher to map user queries to actual database categories."""

    SIMILARITY_THRESHOLD = 0.6  # 60% similarity threshold

    # Common synonyms for category matching
    CATEGORY_SYNONYMS = {
        'exhibition': ['show', 'exhibit', 'display', 'gallery'],
        'concert': ['show', 'performance', 'gig'],
        'workshop': ['class', 'training', 'session'],
        'conference': ['summit', 'meeting', 'convention']
    }

    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings (case-insensitive)."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    @staticmethod
    def _generate_variations(category_name: str) -> List[str]:
        """Generate common variations of a category name for better matching."""
        variations = [category_name.lower()]

        # Add singular/plural variations
        if category_name.endswith('s'):
            variations.append(category_name[:-1].lower())
        else:
            variations.append(f"{category_name}s".lower())

        # Add variations without common words
        for word in ['the', 'a', 'an']:
            if category_name.lower().startswith(word + ' '):
                variations.append(category_name[len(word) + 1:].lower())

        return variations

    @classmethod
    def _check_synonym_match(cls, query: str, category_name: str) -> float:
        """Check if query contains synonyms of words in category name."""
        query_lower = query.lower()
        category_lower = category_name.lower()
        query_words = set(query_lower.split())
        category_words = set(category_lower.split())

        # Check each word in category against synonyms
        for key_word, synonyms in cls.CATEGORY_SYNONYMS.items():
            if key_word in category_lower:
                # Check if any synonym appears in query
                for synonym in synonyms:
                    if synonym in query_words:
                        # Also check if there's additional context match
                        # (at least one other word from category should be in query)
                        common_words = query_words & category_words
                        if common_words or len(query_words) == 1:
                            return 0.75  # Synonym match boost

        return 0.0

    @classmethod
    def find_best_match(
        cls,
        query: str,
        categories: List[Dict[str, any]]
    ) -> Optional[str]:
        """
        Find the best matching category for a user query using fuzzy matching.

        Args:
            query: User's search query (e.g., "musical concert")
            categories: List of category dicts with 'category_name' key

        Returns:
            Best matching category name if similarity >= threshold, None otherwise
        """
        if not query or not categories:
            return None

        best_match = None
        highest_similarity = 0.0

        for category in categories:
            category_name = category.get('category_name', '')
            if not category_name:
                continue

            # Check direct similarity
            similarity = cls._calculate_similarity(query, category_name)

            # Also check against variations
            variations = cls._generate_variations(category_name)
            for variation in variations:
                var_similarity = cls._calculate_similarity(query, variation)
                similarity = max(similarity, var_similarity)

            # Check if query is a substring of category (or vice versa)
            if query.lower() in category_name.lower() or category_name.lower() in query.lower():
                similarity = max(similarity, 0.7)  # Boost substring matches

            # Check synonym matches (e.g., "art show" -> "Art Exhibitions")
            synonym_similarity = cls._check_synonym_match(query, category_name)
            similarity = max(similarity, synonym_similarity)

            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = category_name

        # Return match only if it meets threshold
        if highest_similarity >= cls.SIMILARITY_THRESHOLD:
            return best_match

        return None

    @classmethod
    def enrich_query_with_category(
        cls,
        query: str,
        categories: List[Dict[str, any]]
    ) -> str:
        """
        Enrich user query by appending matched category if found.

        Args:
            query: Original user query
            categories: Available categories from database

        Returns:
            Enriched query or original query if no match
        """
        matched_category = cls.find_best_match(query, categories)

        if matched_category and matched_category.lower() not in query.lower():
            return f"{query} (category: {matched_category})"

        return query
