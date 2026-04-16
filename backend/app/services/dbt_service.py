"""dbt Cloud API client.

Wraps the dbt Cloud v2 REST API using an async httpx client.
All methods are safe to call concurrently and return empty collections
on any HTTP or network error rather than propagating exceptions, so
the dashboard degrades gracefully when dbt Cloud is unreachable.
"""

from __future__ import annotations

import structlog
import httpx

logger = structlog.get_logger(__name__)

_BASE_URL = "https://cloud.getdbt.com/api/v2"


class DbtCloudService:
    """Async client for the dbt Cloud v2 REST API.

    Args:
        api_token: dbt Cloud personal or service account token.
        account_id: Numeric dbt Cloud account identifier.
    """

    def __init__(self, api_token: str, account_id: int) -> None:
        self._account_id = account_id
        self._headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }
        self._base_url = _BASE_URL

    # ------------------------------------------------------------------ #
    # Public async methods
    # ------------------------------------------------------------------ #

    async def get_runs(
        self,
        limit: int = 20,
        status: str | None = None,
    ) -> list[dict]:
        """Fetch recent dbt Cloud job runs.

        Args:
            limit: Maximum number of runs to return (default 20).
            status: Optional filter; dbt statuses are 1=Queued,
                2=Starting, 3=Running, 10=Success, 20=Error, 30=Cancelled.

        Returns:
            List of run dicts from the dbt Cloud API, or empty list on error.
        """
        params: dict = {"limit": limit, "order_by": "-id"}
        if status is not None:
            params["status"] = status

        url = f"{self._base_url}/accounts/{self._account_id}/runs/"
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except httpx.HTTPError as exc:
            logger.error("dbt.get_runs.failed", error=str(exc), url=url)
            return []

    async def get_run_artifacts(self, run_id: int) -> dict:
        """List the artifact files produced by a completed run.

        Args:
            run_id: Numeric dbt Cloud run identifier.

        Returns:
            Dict with an ``artifacts`` key listing file paths, or empty dict.
        """
        url = f"{self._base_url}/accounts/{self._account_id}/runs/{run_id}/artifacts/"
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.error("dbt.get_run_artifacts.failed", run_id=run_id, error=str(exc))
            return {}

    async def get_jobs(self, limit: int = 50) -> list[dict]:
        """Fetch all dbt Cloud jobs for this account.

        Args:
            limit: Maximum number of jobs to return (default 50).

        Returns:
            List of job dicts, or empty list on error.
        """
        url = f"{self._base_url}/accounts/{self._account_id}/jobs/"
        params = {"limit": limit}
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json().get("data", [])
        except httpx.HTTPError as exc:
            logger.error("dbt.get_jobs.failed", error=str(exc))
            return []

    async def get_run_results(self, run_id: int) -> dict:
        """Fetch and return the run_results.json artifact for a completed run.

        Args:
            run_id: Numeric dbt Cloud run identifier.

        Returns:
            Parsed run_results.json as a dict, or empty dict on error.
        """
        url = (
            f"{self._base_url}/accounts/{self._account_id}"
            f"/runs/{run_id}/artifacts/run_results.json"
        )
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.error("dbt.get_run_results.failed", run_id=run_id, error=str(exc))
            return {}

    def parse_test_failures(self, run_results: dict) -> list[dict]:
        """Extract failed test records from a run_results.json payload.

        Args:
            run_results: Parsed run_results.json dict from ``get_run_results``.

        Returns:
            List of dicts, each with keys: model, test_name, severity, message.
            Empty list when there are no failures or the input is malformed.
        """
        failures: list[dict] = []
        results = run_results.get("results", [])

        for result in results:
            if result.get("status") not in ("fail", "error"):
                continue

            unique_id: str = result.get("unique_id", "")
            # unique_id format: test.project.test_name.model_name
            parts = unique_id.split(".")
            test_name = parts[2] if len(parts) > 2 else unique_id
            model_name = parts[3] if len(parts) > 3 else "unknown"

            failures.append(
                {
                    "model": model_name,
                    "test_name": test_name,
                    "severity": result.get("failures", 0),
                    "message": result.get("message", ""),
                    "status": result.get("status"),
                    "execution_time": result.get("execution_time"),
                }
            )

        logger.info("dbt.parse_test_failures", failure_count=len(failures))
        return failures
