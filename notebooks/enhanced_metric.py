"""
Enhanced Conversation Quality Metric for ConversationOrchestrator

This metric provides comprehensive evaluation across multiple dimensions:
1. Response Quality (existence, length, substance)
2. Language Consistency (multilingual support)
3. Content Relevance (intent matching, keyword analysis)
4. Tool Usage Patterns (via trajectory analysis)
5. Response Formatting (URLs, structure, actionability)
"""

import dspy
from typing import Tuple, Union, Optional


def conversation_quality_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    trace=None
) -> Union[float, Tuple[float, str]]:
    """
    Comprehensive metric for evaluating ConversationOrchestrator responses.

    Args:
        example: Ground truth example with question and expected answer
        prediction: Model prediction with answer field
        trace: Optional execution trace for tool usage analysis

    Returns:
        float: Score 0.0-1.0 (for BootstrapFewShot)
        Tuple[float, str]: Score + textual feedback (for GEPA reflection)
    """
    score = 0.0
    feedback = []
    max_score = 100  # Use points for easier tracking

    # Extract prediction response
    pred_response = prediction.answer if hasattr(prediction, 'answer') else str(prediction)
    expected_response = example.answer
    question = example.question

    # ========================================
    # 1. RESPONSE QUALITY (25 points)
    # ========================================
    quality_score = evaluate_response_quality(pred_response, expected_response, feedback)
    score += quality_score

    # ========================================
    # 2. LANGUAGE CONSISTENCY (25 points)
    # ========================================
    language_score = evaluate_language_consistency(question, pred_response, expected_response, feedback)
    score += language_score

    # ========================================
    # 3. CONTENT RELEVANCE (30 points)
    # ========================================
    relevance_score = evaluate_content_relevance(question, pred_response, expected_response, feedback)
    score += relevance_score

    # ========================================
    # 4. RESPONSE FORMATTING (10 points)
    # ========================================
    format_score = evaluate_response_format(pred_response, question, feedback)
    score += format_score

    # ========================================
    # 5. TOOL USAGE PATTERNS (10 points)
    # ========================================
    tool_score = evaluate_tool_usage(prediction, question, feedback, trace)
    score += tool_score

    # Convert to 0.0-1.0 scale
    final_score = score / max_score

    # Return with feedback for GEPA (helps reflection)
    if feedback:
        return (final_score, " | ".join(feedback))
    return final_score


def evaluate_response_quality(
    pred_response: str,
    expected_response: str,
    feedback: list
) -> float:
    """Evaluate response quality: existence, length, substance."""
    score = 0.0

    # 1. Response exists (5 points)
    if not pred_response or not pred_response.strip():
        feedback.append("❌ Empty response")
        return 0.0
    score += 5

    # 2. Minimum length (5 points) - should be substantial
    if len(pred_response.strip()) < 20:
        feedback.append("⚠️ Response too short (<20 chars)")
    elif len(pred_response.strip()) < 50:
        score += 2
        feedback.append("⚠️ Response short (<50 chars)")
    else:
        score += 5

    # 3. Reasonable length relative to expected (10 points)
    length_ratio = len(pred_response) / max(len(expected_response), 1)

    if length_ratio < 0.2:
        feedback.append(f"⚠️ Much shorter than expected ({length_ratio:.0%})")
        score += 2
    elif length_ratio < 0.5:
        score += 5
    elif length_ratio < 2.0:
        score += 10
    elif length_ratio < 3.0:
        score += 7
        feedback.append("⚠️ Longer than expected (may be verbose)")
    else:
        score += 4
        feedback.append("⚠️ Much longer than expected (likely verbose)")

    # 4. Contains multiple sentences (5 points)
    sentence_count = pred_response.count('.') + pred_response.count('!') + pred_response.count('?')
    if sentence_count >= 2:
        score += 5
    elif sentence_count == 1:
        score += 3
    else:
        feedback.append("⚠️ Single sentence response (may lack detail)")

    return score


def evaluate_language_consistency(
    question: str,
    pred_response: str,
    expected_response: str,
    feedback: list
) -> float:
    """Evaluate language matching between question and response."""
    score = 0.0

    # Detect languages
    has_chinese_question = any('\u4e00' <= c <= '\u9fff' for c in question)
    has_chinese_pred = any('\u4e00' <= c <= '\u9fff' for c in pred_response)
    has_chinese_expected = any('\u4e00' <= c <= '\u9fff' for c in expected_response)

    # 1. Matches question language (15 points) - CRITICAL
    if has_chinese_question == has_chinese_pred:
        score += 15
    else:
        lang_expected = "Chinese" if has_chinese_question else "English"
        lang_got = "Chinese" if has_chinese_pred else "English"
        feedback.append(f"❌ CRITICAL: Language mismatch! Question is {lang_expected}, response is {lang_got}")
        return 0.0  # This is a critical failure

    # 2. Matches expected language (10 points)
    if has_chinese_expected == has_chinese_pred:
        score += 10
    else:
        feedback.append("⚠️ Response language differs from expected answer")
        score += 5

    return score


def evaluate_content_relevance(
    question: str,
    pred_response: str,
    expected_response: str,
    feedback: list
) -> float:
    """Evaluate content relevance and intent matching."""
    score = 0.0

    question_lower = question.lower()
    response_lower = pred_response.lower()

    # Intent detection and keyword matching
    intent_matches = 0
    total_intents = 0

    # 1. Event/Concert queries (10 points)
    event_keywords = ['event', 'concert', 'show', 'performance', 'festival', 'gig']
    chinese_event_keywords = ['活動', '音樂會', '演唱會', '表演', '節目']

    if any(kw in question_lower for kw in event_keywords) or any(kw in question for kw in chinese_event_keywords):
        total_intents += 1
        if any(kw in response_lower for kw in event_keywords) or any(kw in pred_response for kw in chinese_event_keywords):
            score += 10
            intent_matches += 1
        else:
            feedback.append("⚠️ Event query but response doesn't mention events")

    # 2. Membership queries (10 points)
    membership_keywords = ['membership', 'member', 'premium', 'subscription', 'plan']
    chinese_membership_keywords = ['會員', '訂閱', '方案']

    if any(kw in question_lower for kw in membership_keywords) or any(kw in question for kw in chinese_membership_keywords):
        total_intents += 1
        if any(kw in response_lower for kw in membership_keywords) or any(kw in pred_response for kw in chinese_membership_keywords):
            score += 10
            intent_matches += 1
        else:
            feedback.append("⚠️ Membership query but response doesn't explain membership")

    # 3. Ticket queries (10 points)
    ticket_keywords = ['ticket', 'refund', 'purchase', 'buy', 'cancel', 'price', 'cost']
    chinese_ticket_keywords = ['票', '退款', '購買', '價格', '費用']

    if any(kw in question_lower for kw in ticket_keywords) or any(kw in question for kw in chinese_ticket_keywords):
        total_intents += 1
        if any(kw in response_lower for kw in ticket_keywords) or any(kw in pred_response for kw in chinese_ticket_keywords):
            score += 10
            intent_matches += 1
        else:
            feedback.append("⚠️ Ticket query but response doesn't address tickets")

    # If no specific intent detected, give base points for trying
    if total_intents == 0:
        if len(pred_response) > 30:
            score += 15  # At least trying to help
        else:
            score += 5
            feedback.append("⚠️ Generic query with minimal response")
    elif intent_matches == total_intents:
        feedback.append(f"✓ All intents matched ({intent_matches}/{total_intents})")
    elif intent_matches > 0:
        feedback.append(f"⚠️ Partial intent match ({intent_matches}/{total_intents})")

    return score


def evaluate_response_format(
    pred_response: str,
    question: str,
    feedback: list
) -> float:
    """Evaluate response formatting: URLs, structure, actionability."""
    score = 0.0

    # 1. Contains URLs when discussing events (5 points)
    has_url = 'http://' in pred_response or 'https://' in pred_response or '[' in pred_response and '](' in pred_response

    question_lower = question.lower()
    discusses_events = any(kw in question_lower for kw in ['event', 'concert', 'show', 'find', 'search'])

    if discusses_events and has_url:
        score += 5
        feedback.append("✓ Includes URLs for events")
    elif discusses_events and not has_url:
        feedback.append("⚠️ Event response should include URLs")
        score += 2
    else:
        score += 5  # Not event-related, doesn't need URLs

    # 2. Mentions membership benefits when relevant (5 points)
    mentions_benefits = any(word in pred_response.lower() for word in ['benefit', 'discount', 'premium', 'save', 'exclusive'])

    if discusses_events or 'ticket' in question_lower:
        if mentions_benefits:
            score += 5
            feedback.append("✓ Promotes membership benefits")
        else:
            score += 2
            feedback.append("⚠️ Could mention membership benefits")
    else:
        score += 5  # Not relevant to mention benefits

    return score


def evaluate_tool_usage(
    prediction: dspy.Prediction,
    question: str,
    feedback: list,
    trace=None
) -> float:
    """Evaluate tool usage patterns from trajectory."""
    score = 5  # Base score

    # Try to extract tool usage from prediction
    if hasattr(prediction, 'trajectory'):
        trajectory = prediction.trajectory

        # Check if Thinking tool was used for complex queries
        question_lower = question.lower()
        is_complex = ('and' in question_lower or '?' in question_lower.count('?') > 1 or
                     len(question.split()) > 10)

        if is_complex:
            if 'Thinking' in str(trajectory) or 'thinking' in str(trajectory):
                score += 5
                feedback.append("✓ Used Thinking for complex query")
            else:
                feedback.append("⚠️ Complex query could benefit from Thinking tool")

    else:
        # No trajectory info available
        score += 5  # Give benefit of doubt

    return score


# ========================================
# Alternative: LLM-as-Judge Metric
# ========================================

def llm_judge_metric(
    example: dspy.Example,
    prediction: dspy.Prediction,
    judge_lm=None
) -> Tuple[float, str]:
    """
    Use an LLM to judge response quality (more expensive but more accurate).

    This is an advanced metric that can be used instead of the rule-based one.
    """
    if judge_lm is None:
        # Fallback to rule-based
        return conversation_quality_metric(example, prediction)

    judge_prompt = f"""You are evaluating a customer service chatbot response.

Question: {example.question}
Expected Answer: {example.answer}
Actual Response: {prediction.answer if hasattr(prediction, 'answer') else str(prediction)}

Evaluate the actual response on these criteria (0-10 each):
1. Language Consistency: Does it match the question's language?
2. Content Relevance: Does it address the question appropriately?
3. Completeness: Does it provide sufficient information?
4. Tone: Is it professional and helpful?
5. Accuracy: Is the information correct?

Provide:
- Overall Score (0.0-1.0)
- Brief feedback explaining the score

Format:
Score: 0.85
Feedback: Response is relevant and helpful but could mention membership benefits.
"""

    try:
        result = judge_lm(judge_prompt)
        # Parse score and feedback from result
        # This is a simplified version - you'd need to parse the actual LLM output
        score = 0.8  # Placeholder
        feedback = "LLM judge evaluation"
        return (score, feedback)
    except Exception as e:
        # Fallback to rule-based
        return conversation_quality_metric(example, prediction)
