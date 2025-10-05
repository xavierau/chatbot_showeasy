import sys
import os
import unittest

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.utils.category_matcher import CategoryMatcher


class TestCategoryMatcher(unittest.TestCase):
    """Test cases for semantic category matching."""

    def setUp(self):
        """Set up test data."""
        self.categories = [
            {"category_name": "Tech Conferences", "event_count": 4},
            {"category_name": "Art Exhibitions", "event_count": 3},
            {"category_name": "Workshops", "event_count": 2},
            {"category_name": "Music Concerts", "event_count": 1}
        ]

    def test_exact_match(self):
        """Test exact category name matching."""
        result = CategoryMatcher.find_best_match("Tech Conferences", self.categories)
        self.assertEqual(result, "Tech Conferences")

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        result = CategoryMatcher.find_best_match("tech conferences", self.categories)
        self.assertEqual(result, "Tech Conferences")

    def test_singular_to_plural_match(self):
        """Test matching singular form to plural category."""
        result = CategoryMatcher.find_best_match("workshop", self.categories)
        self.assertEqual(result, "Workshops")

    def test_partial_match(self):
        """Test partial/substring matching."""
        result = CategoryMatcher.find_best_match("concert", self.categories)
        self.assertEqual(result, "Music Concerts")

    def test_semantic_match_musical_concert(self):
        """Test the main use case: 'musical concert' -> 'Music Concerts'."""
        result = CategoryMatcher.find_best_match("musical concert", self.categories)
        self.assertEqual(result, "Music Concerts")

    def test_semantic_match_art_show(self):
        """Test 'art show' -> 'Art Exhibitions'."""
        result = CategoryMatcher.find_best_match("art show", self.categories)
        self.assertEqual(result, "Art Exhibitions")

    def test_semantic_match_tech_conference(self):
        """Test 'tech conference' (singular) -> 'Tech Conferences'."""
        result = CategoryMatcher.find_best_match("tech conference", self.categories)
        self.assertEqual(result, "Tech Conferences")

    def test_no_match_below_threshold(self):
        """Test that completely unrelated queries return None."""
        result = CategoryMatcher.find_best_match("cooking class", self.categories)
        self.assertIsNone(result)

    def test_empty_query(self):
        """Test handling of empty query."""
        result = CategoryMatcher.find_best_match("", self.categories)
        self.assertIsNone(result)

    def test_empty_categories(self):
        """Test handling of empty categories list."""
        result = CategoryMatcher.find_best_match("music", [])
        self.assertIsNone(result)

    def test_enrich_query_with_match(self):
        """Test query enrichment when category is matched."""
        enriched = CategoryMatcher.enrich_query_with_category(
            "musical concert", self.categories
        )
        self.assertIn("Music Concerts", enriched)
        self.assertIn("musical concert", enriched)

    def test_enrich_query_no_match(self):
        """Test query enrichment when no category matches."""
        enriched = CategoryMatcher.enrich_query_with_category(
            "cooking class", self.categories
        )
        self.assertEqual(enriched, "cooking class")

    def test_enrich_query_already_contains_category(self):
        """Test that enrichment doesn't duplicate if category already in query."""
        enriched = CategoryMatcher.enrich_query_with_category(
            "Music Concerts near me", self.categories
        )
        # Should not duplicate "Music Concerts"
        self.assertEqual(enriched.count("Music Concerts"), 1)


if __name__ == "__main__":
    unittest.main()
