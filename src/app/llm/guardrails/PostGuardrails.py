import dspy
import os
import re
from typing import Dict
from ..signatures.GuardrailSignatures import OutputGuardrailSignature


class OutputGuardrailViolation(Exception):
    """Exception raised when output violates guardrail policies."""

    def __init__(self, violation_type: str, sanitized_response: str, improvement: str):
        self.violation_type = violation_type
        self.sanitized_response = sanitized_response
        self.improvement = improvement
        super().__init__(f"Output guardrail violation: {violation_type}")


class PostGuardrails(dspy.Module):
    """Post-processing guardrails to validate agent output before delivery.

    Ensures all responses:
    - Do not mention competitors
    - Do not leak system internals (SQL, prompts, schemas)
    - Maintain price integrity (no unauthorized discounts)
    - Follow brand voice and compliance policies
    - Are professional and helpful
    """

    def __init__(self):
        super().__init__()
        self.validator = dspy.Predict(OutputGuardrailSignature)

        # Load configuration
        self.auto_sanitize = os.getenv("GUARDRAIL_AUTO_SANITIZE", "true").lower() == "true"
        self.log_violations = os.getenv("GUARDRAIL_LOG_VIOLATIONS", "true").lower() == "true"

        # Competitor blocklist
        self.competitors = [
            "eventbrite",
            "ticketmaster",
            "stubhub",
            "seatgeek",
            "vivid seats",
            "ticketek",
            "axs.com",
            "ticketfly",
        ]

        # System leakage patterns
        self.leakage_patterns = [
            r"SELECT\s+.*\s+FROM",  # SQL queries
            r"```sql",  # SQL code blocks
            r"database schema",
            r"system prompt",
            r"instructions:",
            r"api[_\s]?key",
            r"token:",
            r"password:",
            r"secret:",
            r"mysql",
            r"connection string",
        ]

    def _quick_sanitization_check(self, response: str) -> tuple[bool, str]:
        """Fast pattern-based checks before LLM validation.

        Returns:
            (has_violation, sanitized_response)
        """
        sanitized = response
        has_violation = False
        response_lower = response.lower()

        # Check for competitor mentions
        for competitor in self.competitors:
            if competitor in response_lower:
                has_violation = True
                # Remove competitor mentions (case-insensitive)
                pattern = re.compile(re.escape(competitor), re.IGNORECASE)
                sanitized = pattern.sub("[external platform]", sanitized)

        # Check for system leakage patterns
        for pattern in self.leakage_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                has_violation = True
                # If SQL detected, remove code blocks
                sanitized = re.sub(r"```sql.*?```", "[query details]", sanitized, flags=re.DOTALL | re.IGNORECASE)
                sanitized = re.sub(r"SELECT.*?FROM.*?(?=\.|;|\n|$)", "[database query]", sanitized, flags=re.IGNORECASE)

        return has_violation, sanitized

    def forward(
        self,
        agent_response: str,
        user_query: str,
        response_intent: str
    ) -> Dict[str, any]:
        """Validate agent output through guardrails.

        Args:
            agent_response: The agent's proposed response
            user_query: The original user query for context
            response_intent: The intent being addressed (e.g., 'SEARCH_EVENT')

        Returns:
            Dict with keys:
                - is_safe: bool
                - response: str (sanitized if needed, original if safe)
                - violation_type: str (if unsafe)
                - improvement: str (internal note if unsafe)

        Raises:
            OutputGuardrailViolation: If auto_sanitize is disabled and output is unsafe
        """
        # Layer 1: Quick pattern-based sanitization
        quick_violation, quick_sanitized = self._quick_sanitization_check(agent_response)

        if quick_violation:
            if self.log_violations:
                print(f"[PostGuardrail] Quick check detected violation in response")

            if not self.auto_sanitize:
                raise OutputGuardrailViolation(
                    violation_type="pattern_violation",
                    sanitized_response=quick_sanitized,
                    improvement="Response contained blocked patterns (competitor/leakage)"
                )

            # Continue with sanitized version for LLM validation
            agent_response = quick_sanitized

        # Layer 2: LLM-based validation for nuanced compliance
        validation = self.validator(
            agent_response=agent_response,
            user_query=user_query,
            response_intent=response_intent
        )

        if not validation.is_safe:
            if self.log_violations:
                print(f"[PostGuardrail] LLM validation failed: {validation.violation_type}")
                print(f"[PostGuardrail] Improvement: {validation.improvement_suggestion}")

            if not self.auto_sanitize:
                raise OutputGuardrailViolation(
                    violation_type=validation.violation_type,
                    sanitized_response=validation.sanitized_response,
                    improvement=validation.improvement_suggestion
                )

            return {
                "is_safe": False,
                "response": validation.sanitized_response,
                "violation_type": validation.violation_type,
                "improvement": validation.improvement_suggestion
            }

        # Output passed all guardrails
        return {
            "is_safe": True,
            "response": validation.sanitized_response,  # Use sanitized even if safe (might have minor improvements)
            "violation_type": "",
            "improvement": ""
        }
