# Continuous Learning Guide for Time-Sensitive Data

## The Problem

User conversations contain time-specific information that becomes outdated:

```
December 2024: "Find Christmas concerts" → [Lists 5 concerts]
January 2025: Same query returns empty (no Christmas concerts)
```

**Traditional training breaks** because:
- Old examples reference past events
- Database state changes constantly
- Responses become incorrect over time

## The Solution: Canonicalization + Behavior Learning

### Core Principles

1. **Don't train on content, train on behavior**
2. **Canonicalize time-specific queries**
3. **Abstract entity references**
4. **Focus on tool usage patterns**

---

## Strategy 1: Data Canonicalization

### Transform Specific → General

| Original | Canonicalized |
|----------|---------------|
| "Find Taylor Swift concerts in December 2024" | "Find `<ARTIST_NAME>` concerts in `<MONTH>` `<YEAR>`" |
| "Show me events this weekend" | "Show me events `<RELATIVE_PERIOD>`" |
| "找12月的音樂會" | "找`<MONTH>`的音樂會" |

### Response Templates

Instead of exact responses, use templates:

```python
# Bad: Training on specific content
{
  "query": "Find rock concerts",
  "response": "Found 5 concerts: [Concert A](url1), [Concert B](url2)..."
}

# Good: Training on behavior pattern
{
  "query": "Find <GENRE> concerts",
  "expected_behavior": {
    "tools": ["Thinking", "SearchEvent"],
    "response_template": "Found <N> concerts: <EVENT_LIST_WITH_URLS>",
    "language": "same_as_query",
    "mentions_membership": true
  }
}
```

---

## Strategy 2: Behavior-Based Evaluation

### Metric Focuses on "How", not "What"

```python
def behavior_metric(example, prediction, trace=None):
    """Evaluate behavior, not exact content."""

    score = 0.0

    # 1. Correct tools used? (30%)
    expected_tools = example.expected_behavior['tools']
    actual_tools = extract_tools_from_trajectory(prediction)
    if set(expected_tools) == set(actual_tools):
        score += 0.3

    # 2. Language consistency? (30%)
    if matches_language(example.query, prediction.answer):
        score += 0.3

    # 3. Structure correct? (20%)
    if example.expected_behavior['mentions_membership']:
        if 'membership' in prediction.answer.lower():
            score += 0.2

    # 4. No hallucination? (20%)
    if validates_no_hallucination(prediction.answer):
        score += 0.2

    return score
```

### Key Checks

✅ **Good Checks** (time-agnostic):
- Did agent use SearchEvent for event queries?
- Did response match query language?
- Did response include URLs?
- Did response mention membership benefits?
- Did agent handle empty results gracefully?

❌ **Bad Checks** (time-specific):
- Does response contain "Taylor Swift"?
- Does response list exactly 5 events?
- Does response mention specific dates?

---

## Strategy 3: Mock Database for Training

### Use Deterministic Results During Optimization

```python
class MockSearchEvent:
    """Returns consistent results for training."""

    MOCK_RESULTS = {
        "rock concerts|Los Angeles": {
            "events": "Found 3 events: [Rock Fest](url1)..."
        },
        "jazz|New York": {
            "events": "Found 2 events: [Jazz Night](url1)..."
        }
    }

    def __call__(self, query, location=None, **kwargs):
        key = f"{query}|{location}"
        return self.MOCK_RESULTS.get(key, {"events": "No events found."})

# During optimization
with MockDatabase():
    optimized = optimizer.compile(orchestrator, trainset=trainset)

# In production
# Real database is used automatically
```

---

## Strategy 4: Continuous Curation Pipeline

### Weekly Process

```
┌─────────────────────────────────────┐
│ 1. COLLECT                          │
│    Production logs (last 7 days)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. CURATE                           │
│    • Canonicalize queries           │
│    • Abstract responses             │
│    • Extract behavior patterns      │
│    • Filter invalid examples        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. MERGE                            │
│    • Add to existing trainset       │
│    • Deduplicate                    │
│    • Balance intents                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. RETRAIN                          │
│    • BootstrapFewShot               │
│    • GEPA optimization              │
│    • Evaluate improvement           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. DEPLOY (if improvement > 2%)    │
│    • A/B test                       │
│    • Gradual rollout                │
│    • Monitor metrics                │
└─────────────────────────────────────┘
```

### Configuration

```json
{
  "collection": {
    "frequency": "weekly",
    "min_quality_score": 0.7,
    "sample_rate": 1.0
  },
  "curation": {
    "min_examples_for_retrain": 100,
    "max_example_age_days": 90
  },
  "retraining": {
    "min_improvement_threshold": 0.02,
    "validation_split": 0.2
  },
  "monitoring": {
    "drift_threshold": 0.05,
    "alert_on_degradation": true
  }
}
```

---

## Implementation Steps

### Phase 1: Setup (Week 1)

1. **Add logging to production**
   ```python
   # In your app
   @app.post("/chat")
   async def chat(message: str):
       response = orchestrator(message, [], "")

       # Log conversation
       logger.log_conversation({
           'user_query': message,
           'agent_response': response,
           'tool_calls': orchestrator.agent.last_tool_calls,
           'timestamp': datetime.now(),
           'quality_score': estimate_quality(response)
       })

       return response
   ```

2. **Setup curation scripts**
   - `scripts/curate_user_data.py`
   - `scripts/continuous_learning_pipeline.py`

3. **Create mock database**
   - Define common query patterns
   - Create deterministic responses

### Phase 2: Initial Curation (Week 2)

1. **Collect 2 weeks of production data**
2. **Run curation script**
   ```bash
   python scripts/curate_user_data.py \
     --input logs/production.csv \
     --output datasets/curated_user_data.json
   ```
3. **Review canonicalized examples**
4. **Adjust patterns if needed**

### Phase 3: First Retrain (Week 3)

1. **Merge curated data with synthetic data**
   ```python
   python scripts/continuous_learning_pipeline.py \
     --mode merge \
     --existing datasets/conversation_react_training.json \
     --new datasets/curated_user_data.json \
     --output datasets/merged_trainset.json
   ```

2. **Retrain with merged dataset**
   ```python
   # In notebook or script
   optimized = two_stage_optimization(
       trainset=merged_trainset,
       use_mock_db=True
   )
   ```

3. **Evaluate improvement**
4. **A/B test in production (10% traffic)**

### Phase 4: Automation (Week 4+)

1. **Schedule weekly pipeline**
   ```bash
   # Cron job
   0 2 * * 1 python scripts/continuous_learning_pipeline.py --mode weekly
   ```

2. **Setup monitoring**
   - Performance drift alerts
   - Data quality checks
   - Model version tracking

3. **Review monthly**
   - Check curation quality
   - Adjust thresholds
   - Update mock database

---

## Example: End-to-End Flow

### User Conversation (Production)
```
User: "Find Taylor Swift concerts in December 2024"
Agent: "I found 3 Taylor Swift concerts in December:
        [Concert 1](url1), [Concert 2](url2), [Concert 3](url3).
        Premium members save 15% on tickets!"
Tools: ['Thinking', 'SearchEvent']
Quality Score: 0.9
```

### After Curation
```json
{
  "canonical_query": "Find <ARTIST_NAME> concerts in <MONTH> <YEAR>",
  "expected_behavior": {
    "tools": ["Thinking", "SearchEvent"],
    "language": "en",
    "response_structure": {
      "has_urls": true,
      "mentions_membership": true,
      "event_count": "3"
    }
  },
  "response_template": "I found <N> <ARTIST_NAME> concerts in <MONTH>: <EVENT_LIST_WITH_URLS>. Premium members save on tickets!",
  "intent": "event_search",
  "is_valid": true
}
```

### Used in Training (January 2025)
```python
# Mock database returns consistent results
mock_search_results = {
  "<ARTIST_NAME> concerts": "Found 3 events: [Event A](url1), [Event B](url2)..."
}

# Metric evaluates behavior
metric_checks = {
  "used_correct_tools": True,  # ✓ Used Thinking + SearchEvent
  "language_correct": True,     # ✓ English query → English response
  "has_urls": True,            # ✓ Response includes URLs
  "mentions_membership": True   # ✓ Mentions Premium benefits
}

# Score: 0.95 (Excellent!)
```

---

## Monitoring & Maintenance

### Weekly Review

- **Curation Quality**: Are canonicalizations correct?
- **Data Balance**: Equal distribution across intents?
- **Performance Metrics**: Improvement over baseline?

### Monthly Review

- **Update Mock Database**: Add new query patterns
- **Adjust Thresholds**: Min quality score, drift threshold
- **Review Feedback**: Manual QA of sample responses

### Quarterly Review

- **Major Retrain**: Full optimization with all data
- **Architecture Updates**: New tools, improved signatures
- **Strategy Adjustment**: Based on 3 months of data

---

## Key Takeaways

1. ✅ **Canonicalize time-specific references** → Make training data evergreen
2. ✅ **Train on behavior, not content** → Focus on tool usage and patterns
3. ✅ **Use mock database for training** → Deterministic, reproducible results
4. ✅ **Continuous curation pipeline** → Keep learning from production
5. ✅ **Monitor drift** → Detect when model degrades
6. ✅ **Gradual deployment** → A/B test improvements before full rollout

This approach lets you continuously learn from real user data while avoiding the time-sensitivity trap! 🚀
