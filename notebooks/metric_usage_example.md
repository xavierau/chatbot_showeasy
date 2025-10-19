# Enhanced Metric Usage Guide

## What's New in the Enhanced Metric

The enhanced `conversation_quality_metric` provides comprehensive evaluation across 5 dimensions:

### 1. **Response Quality (25%)** - 25 points
- Response exists and is non-empty
- Adequate length (not too short/long)
- Multiple sentences
- Substance and detail

### 2. **Language Consistency (25%)** - 25 points
- **CRITICAL**: Matches question language (Chinese→Chinese, English→English)
- Language mismatch = automatic near-zero score
- Matches expected answer language

### 3. **Content Relevance (30%)** - 30 points
- **Event queries**: Mentions events/concerts
- **Membership queries**: Explains membership benefits
- **Ticket queries**: Addresses tickets/pricing/refunds
- Multi-intent detection
- Keyword matching for Chinese and English

### 4. **Response Formatting (10%)** - 10 points
- Includes URLs when discussing events
- Mentions membership benefits when relevant
- Professional structure

### 5. **Tool Usage Patterns (10%)** - 10 points
- Uses Thinking tool for complex queries
- Appropriate tool selection (requires trajectory access)

## Scoring Details

| Score Range | Interpretation |
|-------------|----------------|
| 0.90-1.00 | Excellent - All criteria met |
| 0.75-0.89 | Good - Minor issues |
| 0.60-0.74 | Acceptable - Some problems |
| 0.40-0.59 | Poor - Significant issues |
| 0.00-0.39 | Failed - Critical problems |

## Feedback Messages

The metric provides actionable feedback for GEPA optimization:

### Success Indicators (✓)
- `✓ All intents matched`
- `✓ Includes URLs for events`
- `✓ Promotes membership benefits`
- `✓ Used Thinking for complex query`

### Warnings (⚠️)
- `⚠️ Response too short (<20 chars)`
- `⚠️ Language mismatch: expected Chinese`
- `⚠️ Event query but response doesn't mention events`
- `⚠️ Could mention membership benefits`

### Critical Failures (❌)
- `❌ Empty response`
- `❌ CRITICAL: Language mismatch!`

## Usage in Notebook

### Option 1: Import the enhanced metric

```python
# Add to notebook cell after imports
sys.path.insert(0, str(Path.cwd()))
from enhanced_metric import conversation_quality_metric

# Use in optimization
bootstrap_optimizer = BootstrapFewShot(
    metric=conversation_quality_metric,
    ...
)
```

### Option 2: Copy into notebook

Replace the metric definition cell with the content from `enhanced_metric.py`

## Example Outputs

### Example 1: Perfect Response
```
Question: "Find rock concerts in LA"
Response: "I found 5 rock concerts in Los Angeles! Check out:
          [Concert 1](url), [Concert 2](url)...
          Premium members save 15% on tickets!"

Score: 0.95
Feedback: ✓ All intents matched | ✓ Includes URLs | ✓ Promotes membership
```

### Example 2: Language Mismatch (Critical)
```
Question: "找音樂會" (Chinese)
Response: "I found concerts in your area..."

Score: 0.15
Feedback: ❌ CRITICAL: Language mismatch! Question is Chinese, response is English
```

### Example 3: Incomplete Response
```
Question: "How much is membership and can I get refunds?"
Response: "Membership is $19.99/month"

Score: 0.62
Feedback: ⚠️ Partial intent match (1/2) | ⚠️ Didn't address refund question
```

## Advanced: LLM-as-Judge

For even more accurate evaluation, use the `llm_judge_metric`:

```python
# Configure judge LLM (use best model)
judge_lm = dspy.LM('gemini/gemini-2.5-pro')

# Use in optimization
gepa_optimizer = dspy.GEPA(
    metric=lambda ex, pred, trace=None: llm_judge_metric(ex, pred, judge_lm),
    ...
)
```

**Note**: LLM-as-judge is more accurate but:
- Much slower (extra LLM call per evaluation)
- More expensive
- Best for final validation, not training

## Customization

### Adjust Weights

Edit the point allocations in each function:

```python
# Make language consistency more important
def evaluate_language_consistency(...):
    # Change from 25 to 35 points
    if has_chinese_question == has_chinese_pred:
        score += 20  # was 15
    # ...
```

### Add Domain-Specific Rules

```python
# Add location detection
if 'location' in question_lower:
    if any(city in response_lower for city in ['los angeles', 'new york', 'san francisco']):
        score += 5
        feedback.append("✓ Mentions specific location")
```

### Integrate with Existing Metrics

```python
def combined_metric(example, prediction, trace=None):
    # Get scores from multiple metrics
    enhanced_score, feedback = conversation_quality_metric(example, prediction, trace)
    semantic_score = semantic_similarity(example.answer, prediction.answer)

    # Weighted combination
    final_score = 0.7 * enhanced_score + 0.3 * semantic_score

    return (final_score, feedback)
```
