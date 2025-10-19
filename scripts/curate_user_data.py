"""
User Data Curation Pipeline for Time-Sensitive Conversational AI

This script processes real user conversations and transforms them into
reusable training data by:
1. Canonicalizing time-specific queries
2. Abstracting specific event details
3. Preserving behavioral patterns
4. Removing outdated information
"""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd


class UserDataCurator:
    """Curates user conversation data for training."""

    # Time expressions to canonicalize
    TIME_PATTERNS = {
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b': 'MONTH',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b': 'DAY_OF_WEEK',
        r'\b(2024|2025|2026|2027)\b': 'YEAR',
        r'\b(christmas|new year|thanksgiving|easter|halloween)\b': 'HOLIDAY',
        r'\b(tomorrow|today|yesterday)\b': 'RELATIVE_DATE',
        r'\b(this|next|last) (week|weekend|month|year)\b': 'RELATIVE_PERIOD',
        r'\b\d{1,2}/\d{1,2}/\d{4}\b': 'SPECIFIC_DATE',
    }

    # Specific entities to abstract
    ENTITY_PATTERNS = {
        r'\b(taylor swift|beyonce|coldplay|bts|drake)\b': 'ARTIST_NAME',
        r'\b(staples center|madison square garden|wembley)\b': 'VENUE_NAME',
        r'\$\d+(\.\d{2})?': 'PRICE',
    }

    def __init__(self):
        self.canonical_patterns = []
        self.behavior_patterns = []

    def curate_conversation(
        self,
        user_query: str,
        agent_response: str,
        tool_calls: List[str],
        metadata: Dict
    ) -> Dict:
        """
        Transform a single conversation into reusable training data.

        Args:
            user_query: Original user input
            agent_response: Original agent response
            tool_calls: List of tools called (e.g., ['Thinking', 'SearchEvent'])
            metadata: Additional info (timestamp, page_context, etc.)

        Returns:
            Curated training example
        """
        # 1. Canonicalize the query
        canonical_query = self._canonicalize_query(user_query)

        # 2. Abstract the response
        canonical_response = self._abstract_response(
            agent_response,
            user_query,
            tool_calls
        )

        # 3. Extract behavioral patterns
        behavior = self._extract_behavior_pattern(
            user_query,
            agent_response,
            tool_calls
        )

        # 4. Determine if example is still valid
        is_valid, reason = self._validate_example(
            user_query,
            agent_response,
            metadata
        )

        return {
            'original_query': user_query,
            'canonical_query': canonical_query,
            'original_response': agent_response,
            'canonical_response': canonical_response,
            'tool_calls': tool_calls,
            'behavior_pattern': behavior,
            'is_valid': is_valid,
            'validity_reason': reason,
            'metadata': metadata,
            'curated_at': datetime.now().isoformat()
        }

    def _canonicalize_query(self, query: str) -> str:
        """
        Transform specific query into canonical pattern.

        Example:
            "Find Taylor Swift concerts in December 2024"
            → "Find ARTIST_NAME concerts in MONTH YEAR"
        """
        canonical = query.lower()

        # Replace time expressions
        for pattern, replacement in self.TIME_PATTERNS.items():
            canonical = re.sub(pattern, f'<{replacement}>', canonical, flags=re.IGNORECASE)

        # Replace specific entities
        for pattern, replacement in self.ENTITY_PATTERNS.items():
            canonical = re.sub(pattern, f'<{replacement}>', canonical, flags=re.IGNORECASE)

        return canonical

    def _abstract_response(
        self,
        response: str,
        query: str,
        tool_calls: List[str]
    ) -> str:
        """
        Abstract response to remove time-specific details.

        Strategy:
        - If SearchEvent was called: Replace with template
        - Preserve response structure and tone
        - Keep tool usage patterns
        """
        if 'SearchEvent' in tool_calls or 'search_event' in str(tool_calls):
            # Response likely contains specific events
            # Replace with template showing expected behavior

            template = self._generate_response_template(query, response)
            return template

        # For non-search responses (membership, tickets, etc.)
        # These are usually time-agnostic, so keep as-is
        return response

    def _generate_response_template(self, query: str, response: str) -> str:
        """
        Generate response template for event search results.

        Template captures:
        - Acknowledgment of query
        - Tool usage pattern
        - Response structure (URLs, membership mention)
        - Tone and language
        """
        # Detect language
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in query)

        # Count number of events in response
        url_count = response.count('http') + response.count('[')

        # Check if mentions membership
        mentions_membership = any(word in response.lower()
                                 for word in ['membership', 'premium', 'member', '會員'])

        if has_chinese:
            template = f"""我找到了<EVENT_COUNT>場符合條件的活動：

<EVENT_LIST_WITH_URLS>

{'Premium會員可享折扣優惠！' if mentions_membership else ''}"""
        else:
            template = f"""I found <EVENT_COUNT> events matching your criteria:

<EVENT_LIST_WITH_URLS>

{'Premium members save on ticket fees!' if mentions_membership else ''}"""

        return template.strip()

    def _extract_behavior_pattern(
        self,
        query: str,
        response: str,
        tool_calls: List[str]
    ) -> Dict:
        """
        Extract behavioral patterns from conversation.

        These patterns are time-agnostic and capture:
        - Intent detection
        - Tool selection logic
        - Response structure
        """
        pattern = {
            'query_type': self._classify_query_type(query),
            'tools_used': tool_calls,
            'response_characteristics': {
                'has_urls': bool(re.search(r'https?://', response) or '[' in response),
                'has_membership_mention': any(word in response.lower()
                                             for word in ['membership', 'premium', '會員']),
                'language': 'zh' if any('\u4e00' <= c <= '\u9fff' for c in response) else 'en',
                'length_category': 'short' if len(response) < 100 else 'medium' if len(response) < 300 else 'long'
            }
        }

        return pattern

    def _classify_query_type(self, query: str) -> str:
        """Classify query into high-level intent."""
        query_lower = query.lower()

        if any(word in query_lower for word in ['event', 'concert', 'show', '活動', '音樂會']):
            return 'event_search'
        elif any(word in query_lower for word in ['membership', 'member', 'premium', '會員']):
            return 'membership_inquiry'
        elif any(word in query_lower for word in ['ticket', 'refund', 'cancel', '票', '退款']):
            return 'ticket_inquiry'
        elif any(word in query_lower for word in ['help', 'how', 'what', '怎麼', '如何']):
            return 'general_help'
        else:
            return 'other'

    def _validate_example(
        self,
        query: str,
        response: str,
        metadata: Dict
    ) -> Tuple[bool, str]:
        """
        Determine if example is still valid for training.

        Invalid cases:
        - Very old (>6 months)
        - Contains errors or hallucinations
        - Policy/pricing changed since then
        """
        # Check age
        if 'timestamp' in metadata:
            timestamp = datetime.fromisoformat(metadata['timestamp'])
            age = datetime.now() - timestamp

            if age > timedelta(days=180):
                return False, "Example too old (>6 months)"

        # Check for errors
        if 'error' in response.lower() or '錯誤' in response:
            return False, "Contains error message"

        # Check for hallucination indicators
        if 'found' in response.lower() and not ('http' in response or '[' in response):
            return False, "Possible hallucination (claims results without URLs)"

        return True, "Valid"

    def process_user_logs(
        self,
        log_file: str,
        output_file: str,
        min_quality_score: float = 0.7
    ):
        """
        Process a batch of user conversation logs.

        Args:
            log_file: Path to conversation logs (CSV or JSON)
            output_file: Path to save curated data
            min_quality_score: Minimum quality threshold
        """
        # Load logs
        if log_file.endswith('.csv'):
            df = pd.read_csv(log_file)
        else:
            with open(log_file) as f:
                data = json.load(f)
                df = pd.DataFrame(data)

        curated_examples = []

        for _, row in df.iterrows():
            # Skip low-quality conversations
            if 'quality_score' in row and row['quality_score'] < min_quality_score:
                continue

            # Curate
            curated = self.curate_conversation(
                user_query=row['user_query'],
                agent_response=row['agent_response'],
                tool_calls=json.loads(row['tool_calls']) if isinstance(row['tool_calls'], str) else row['tool_calls'],
                metadata={
                    'timestamp': row.get('timestamp'),
                    'page_context': row.get('page_context'),
                    'user_id': row.get('user_id'),
                    'session_id': row.get('session_id')
                }
            )

            # Only keep valid examples
            if curated['is_valid']:
                curated_examples.append(curated)

        # Save curated data
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(curated_examples, f, indent=2, ensure_ascii=False)

        print(f"✓ Curated {len(curated_examples)} examples from {len(df)} logs")
        print(f"  Saved to: {output_file}")

        return curated_examples


class BehaviorOnlyTrainingSet:
    """
    Creates training examples that focus on BEHAVIOR, not content.

    Instead of checking exact responses, checks:
    - Did agent use correct tools?
    - Did agent respond in correct language?
    - Did agent handle empty results gracefully?
    """

    @staticmethod
    def create_from_curated_data(curated_data: List[Dict]) -> List[Dict]:
        """
        Convert curated data into behavior-focused training examples.
        """
        training_examples = []

        for item in curated_data:
            example = {
                'user_input': item['canonical_query'],
                'expected_behavior': {
                    'tools_called': item['tool_calls'],
                    'language': item['behavior_pattern']['response_characteristics']['language'],
                    'includes_urls': item['behavior_pattern']['response_characteristics']['has_urls'],
                    'mentions_membership': item['behavior_pattern']['response_characteristics']['has_membership_mention']
                },
                'response_template': item['canonical_response'],
                'intent_category': item['behavior_pattern']['query_type']
            }

            training_examples.append(example)

        return training_examples


# Example usage
if __name__ == "__main__":
    curator = UserDataCurator()

    # Example: Curate a single conversation
    example = curator.curate_conversation(
        user_query="Find Taylor Swift concerts in December 2024",
        agent_response="I found 3 Taylor Swift concerts in December: [Concert 1](url1), [Concert 2](url2). Premium members save 15%!",
        tool_calls=['Thinking', 'SearchEvent'],
        metadata={
            'timestamp': '2024-12-01T10:00:00',
            'page_context': 'homepage'
        }
    )

    print(json.dumps(example, indent=2, ensure_ascii=False))

    # Process batch of logs
    # curator.process_user_logs(
    #     log_file='logs/user_conversations.csv',
    #     output_file='datasets/curated_user_data.json',
    #     min_quality_score=0.7
    # )
