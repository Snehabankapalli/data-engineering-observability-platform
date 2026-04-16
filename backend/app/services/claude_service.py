"""Claude AI co-pilot service.

Wraps the Anthropic messages API to provide data-engineering-specific
analysis: slow query diagnosis, dbt test failure triage, schema.yml
test generation, and Snowflake cost spike investigation.

Every method returns a structured dict.  On API error it returns a dict
with an ``error`` key instead of raising, so callers can surface a
user-friendly message without crashing the request.
"""

from __future__ import annotations

import json

import anthropic
import structlog

logger = structlog.get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024

_SYSTEM_PROMPT = (
    "You are a senior data engineer with deep expertise in Snowflake, dbt, "
    "Apache Spark, and AWS data infrastructure. "
    "You give concise, actionable advice. "
    "When asked for SQL, produce optimised Snowflake SQL. "
    "When asked for YAML, produce valid dbt schema YAML. "
    "Always respond with valid JSON matching the schema specified in the user message."
)


class ClaudeService:
    """Anthropic Claude client for data engineering co-pilot features.

    Args:
        api_key: Anthropic API key sourced from AWS Secrets Manager or env var.
    """

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------ #
    # Internal helper
    # ------------------------------------------------------------------ #

    def _chat(self, user_message: str) -> str:
        """Send a single user message and return the assistant text.

        Args:
            user_message: The prompt to send to Claude.

        Returns:
            Raw text response from the model.

        Raises:
            anthropic.APIError: Propagated so callers can wrap it.
        """
        message = self._client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text

    def _safe_parse_json(self, raw: str, fallback: dict) -> dict:
        """Parse a JSON string, returning fallback on failure.

        Args:
            raw: Raw text that should contain JSON.
            fallback: Dict to return if JSON parsing fails.

        Returns:
            Parsed dict or the fallback.
        """
        try:
            # Claude sometimes wraps JSON in a markdown code fence; strip it.
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("claude.json_parse_failed", error=str(exc))
            return fallback

    # ------------------------------------------------------------------ #
    # Public analysis methods
    # ------------------------------------------------------------------ #

    async def analyze_slow_query(
        self,
        query_text: str,
        warehouse: str,
        duration_ms: int,
        bytes_scanned: int,
    ) -> dict:
        """Diagnose a slow Snowflake query and suggest optimisations.

        Args:
            query_text: The SQL that ran slowly (may be truncated).
            warehouse: Snowflake warehouse name where it executed.
            duration_ms: Measured execution time in milliseconds.
            bytes_scanned: Bytes scanned during execution.

        Returns:
            Dict with keys: analysis, suggestions (list[str]),
            priority (high/medium/low), estimated_improvement.
            On API error: {error: str}.
        """
        prompt = f"""Analyse this slow Snowflake query and return a JSON object.

Query (may be truncated):
{query_text}

Context:
- Warehouse: {warehouse}
- Duration: {duration_ms} ms
- Bytes scanned: {bytes_scanned:,}

Return ONLY valid JSON matching this exact schema:
{{
  "analysis": "<1-2 sentence root cause>",
  "suggestions": ["<actionable fix 1>", "<actionable fix 2>", ...],
  "priority": "high|medium|low",
  "estimated_improvement": "<e.g. 60% reduction in scan cost>"
}}"""
        try:
            raw = self._chat(prompt)
            fallback = {
                "analysis": "Unable to parse model response.",
                "suggestions": [],
                "priority": "medium",
                "estimated_improvement": "unknown",
            }
            return self._safe_parse_json(raw, fallback)
        except anthropic.APIError as exc:
            logger.error("claude.analyze_slow_query.failed", error=str(exc))
            return {"error": str(exc)}

    async def analyze_dbt_failure(
        self,
        test_name: str,
        model_name: str,
        error_message: str,
        sample_rows: list | None = None,
    ) -> dict:
        """Diagnose a dbt test failure and suggest a fix.

        Args:
            test_name: Name of the failing dbt test (e.g. not_null_orders_id).
            model_name: dbt model under test.
            error_message: Error or failure message from dbt run results.
            sample_rows: Optional list of failing row samples for context.

        Returns:
            Dict with keys: root_cause, fix_sql, prevention_steps (list[str]),
            severity (P1/P2/P3).
            On API error: {error: str}.
        """
        sample_section = ""
        if sample_rows:
            sample_section = f"\nSample failing rows (first 5):\n{json.dumps(sample_rows[:5], default=str)}"

        prompt = f"""A dbt test failed in production. Diagnose and suggest a fix. Return ONLY valid JSON.

Test name: {test_name}
Model: {model_name}
Error message: {error_message}{sample_section}

Return ONLY valid JSON matching this exact schema:
{{
  "root_cause": "<concise explanation>",
  "fix_sql": "<corrective SQL or dbt macro, or empty string if N/A>",
  "prevention_steps": ["<step 1>", "<step 2>", ...],
  "severity": "P1|P2|P3"
}}"""
        try:
            raw = self._chat(prompt)
            fallback = {
                "root_cause": "Unable to parse model response.",
                "fix_sql": "",
                "prevention_steps": [],
                "severity": "P2",
            }
            return self._safe_parse_json(raw, fallback)
        except anthropic.APIError as exc:
            logger.error("claude.analyze_dbt_failure.failed", error=str(exc))
            return {"error": str(exc)}

    async def generate_dbt_tests(
        self, model_name: str, columns: list[dict]
    ) -> str:
        """Generate a dbt schema.yml tests block for the given model columns.

        Args:
            model_name: dbt model name (used as the model entry name).
            columns: List of dicts with at minimum ``name`` and ``type`` keys.
                Additional keys like ``description`` are passed through.

        Returns:
            YAML string suitable for inclusion in a schema.yml file.
            On API error: empty string.
        """
        columns_json = json.dumps(columns, indent=2)
        prompt = f"""Generate a complete dbt schema.yml entry for the model '{model_name}'.

Columns:
{columns_json}

Rules:
- Use not_null for non-nullable columns based on their names (id, key, required fields).
- Use unique for id/key columns.
- Use accepted_values where enum values are implied by the column name.
- Use relationships where foreign key columns are present (suffix _id).
- Include a brief description for each column.

Return ONLY valid YAML, no markdown fences, no extra commentary."""
        try:
            return self._chat(prompt)
        except anthropic.APIError as exc:
            logger.error("claude.generate_dbt_tests.failed", error=str(exc))
            return ""

    async def analyze_cost_spike(
        self,
        warehouse: str,
        current_credits: float,
        baseline_credits: float,
        top_queries: list,
    ) -> dict:
        """Explain a Snowflake cost spike and identify culprit queries.

        Args:
            warehouse: Warehouse name exhibiting the spike.
            current_credits: Credits consumed today.
            baseline_credits: Average daily credits over the baseline period.
            top_queries: List of the most expensive queries run today
                (each dict should include query_text, duration_ms, bytes_scanned).

        Returns:
            Dict with keys: explanation, culprit_queries (list[str]),
            remediation_steps (list[str]), estimated_saving.
            On API error: {error: str}.
        """
        top_queries_json = json.dumps(top_queries[:5], default=str, indent=2)
        ratio = round(current_credits / max(baseline_credits, 0.001), 1)

        prompt = f"""A Snowflake warehouse has an abnormal cost spike. Explain why and suggest fixes.

Warehouse: {warehouse}
Today's credits: {current_credits:.2f}
7-day average: {baseline_credits:.2f}
Ratio: {ratio}x above baseline

Top expensive queries today (truncated):
{top_queries_json}

Return ONLY valid JSON matching this exact schema:
{{
  "explanation": "<root cause in plain English>",
  "culprit_queries": ["<description of query 1>", ...],
  "remediation_steps": ["<step 1>", "<step 2>", ...],
  "estimated_saving": "<e.g. 40% reduction if X is fixed>"
}}"""
        try:
            raw = self._chat(prompt)
            fallback = {
                "explanation": "Unable to parse model response.",
                "culprit_queries": [],
                "remediation_steps": [],
                "estimated_saving": "unknown",
            }
            return self._safe_parse_json(raw, fallback)
        except anthropic.APIError as exc:
            logger.error("claude.analyze_cost_spike.failed", error=str(exc))
            return {"error": str(exc)}
