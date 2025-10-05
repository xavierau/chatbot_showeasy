import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
import glob


class InsightCache:
    """Manages multi-file cache for database insights with 5-minute TTL."""

    CACHE_DIR = "cache/db_insights"
    TTL_MINUTES = 5

    INSIGHT_TYPES = [
        "categories",
        "locations",
        "date_ranges",
        "popular_events",
        "statistics"
    ]

    def __init__(self):
        """Initialize cache directory."""
        Path(self.CACHE_DIR).mkdir(parents=True, exist_ok=True)

    def _get_cache_file_pattern(self, insight_type: str) -> str:
        """Get glob pattern for insight type."""
        return os.path.join(self.CACHE_DIR, f"{insight_type}_*.json")

    def _parse_timestamp_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract timestamp from cache filename."""
        try:
            # Extract timestamp from pattern: {type}_{timestamp}.json
            basename = os.path.basename(filename)
            timestamp_str = basename.split('_', 1)[1].replace('.json', '')
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, IndexError):
            return None

    def _is_cache_valid(self, filepath: str) -> bool:
        """Check if cache file is still valid (not older than TTL)."""
        timestamp = self._parse_timestamp_from_filename(filepath)
        if not timestamp:
            return False

        age = datetime.now() - timestamp
        return age < timedelta(minutes=self.TTL_MINUTES)

    def _cleanup_stale_files(self, insight_type: str):
        """Remove stale cache files for given insight type."""
        pattern = self._get_cache_file_pattern(insight_type)
        for filepath in glob.glob(pattern):
            if not self._is_cache_valid(filepath):
                try:
                    os.remove(filepath)
                    print(f"Removed stale cache: {filepath}")
                except OSError as e:
                    print(f"Error removing stale cache {filepath}: {e}")

    def get(self, insight_type: str) -> Optional[Dict]:
        """Get cached insight if valid, None otherwise."""
        if insight_type not in self.INSIGHT_TYPES:
            raise ValueError(f"Invalid insight type: {insight_type}")

        # Cleanup stale files first
        self._cleanup_stale_files(insight_type)

        # Find valid cache file
        pattern = self._get_cache_file_pattern(insight_type)
        cache_files = glob.glob(pattern)

        for filepath in cache_files:
            if self._is_cache_valid(filepath):
                try:
                    with open(filepath, 'r') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error reading cache {filepath}: {e}")
                    continue

        return None

    def _datetime_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def set(self, insight_type: str, data: Dict):
        """Store insight data with current timestamp."""
        if insight_type not in self.INSIGHT_TYPES:
            raise ValueError(f"Invalid insight type: {insight_type}")

        # Cleanup old files first
        self._cleanup_stale_files(insight_type)

        # Create new cache file with timestamp
        timestamp = datetime.now().isoformat()
        filename = f"{insight_type}_{timestamp}.json"
        filepath = os.path.join(self.CACHE_DIR, filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=self._datetime_serializer)
            print(f"Cached insight: {filepath}")
        except IOError as e:
            print(f"Error writing cache {filepath}: {e}")

    def get_all_insights(self) -> Dict[str, Dict]:
        """Get all valid cached insights."""
        insights = {}
        for insight_type in self.INSIGHT_TYPES:
            cached = self.get(insight_type)
            if cached:
                insights[insight_type] = cached
        return insights

    def clear_all(self):
        """Clear all cache files."""
        for insight_type in self.INSIGHT_TYPES:
            pattern = self._get_cache_file_pattern(insight_type)
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                    print(f"Removed cache: {filepath}")
                except OSError as e:
                    print(f"Error removing cache {filepath}: {e}")
