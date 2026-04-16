"""Snowflake query service.

Executes diagnostic and cost queries against Snowflake ACCOUNT_USAGE
and INFORMATION_SCHEMA views.  Every public method opens a fresh
connection, executes, and closes, keeping the connector pool-free and
safe for use inside both FastAPI routes and APScheduler jobs.

No credentials are logged.  OperationalError is caught at each method
boundary to allow the dashboard to degrade gracefully.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import snowflake.connector
import structlog

logger = structlog.get_logger(__name__)


class SnowflakeService:
    """Thin wrapper around the Snowflake Python connector for observability queries.

    Args:
        account: Snowflake account identifier (e.g. ``xy12345.us-east-1``).
        user: Service account username.
        password: Service account password (sourced from Secrets Manager in prod).
        database: Default database for INFORMATION_SCHEMA queries.
        warehouse: Warehouse used to execute queries.
        role: Role to assume after connecting.
    """

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        database: str,
        warehouse: str,
        role: str,
    ) -> None:
        self._conn_params: dict[str, str] = {
            "account": account,
            "user": user,
            "password": password,
            "database": database,
            "warehouse": warehouse,
            "role": role,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_connection(self) -> snowflake.connector.SnowflakeConnection:
        """Open and return a new Snowflake connection.

        Returns:
            An open SnowflakeConnection.

        Raises:
            snowflake.connector.errors.DatabaseError: On connection failure.
        """
        return snowflake.connector.connect(**self._conn_params)

    def _execute(
        self, query: str, params: tuple | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return all rows as dicts.

        Opens a dedicated connection, executes the query, fetches all rows,
        and closes the connection before returning.

        Args:
            query: SQL string. Use ``%s`` placeholders for parameterised queries.
            params: Optional tuple of bind values.

        Returns:
            List of row dicts.  Empty list if the result set is empty.

        Raises:
            snowflake.connector.errors.DatabaseError: On execution error.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor(snowflake.connector.DictCursor)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Public query methods
    # ------------------------------------------------------------------ #

    def get_slow_queries(
        self,
        min_duration_ms: int = 5000,
        hours: int = 24,
        limit: int = 50,
    ) -> list[dict]:
        """Return queries that exceeded the execution time threshold.

        Queries SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY which has ~45-minute
        propagation lag.  For near-real-time data use INFORMATION_SCHEMA
        QUERY_HISTORY table function instead.

        Args:
            min_duration_ms: Minimum execution time in milliseconds (default 5 s).
            hours: Lookback window in hours (default 24).
            limit: Maximum rows to return (default 50).

        Returns:
            List of query dicts, or empty list on error.
        """
        query = """
            SELECT
                QUERY_ID            AS query_id,
                LEFT(QUERY_TEXT, 500) AS query_text,
                WAREHOUSE_NAME      AS warehouse_name,
                EXECUTION_STATUS    AS execution_status,
                TOTAL_ELAPSED_TIME  AS total_elapsed_time,
                BYTES_SCANNED       AS bytes_scanned,
                CREDITS_USED_CLOUD_SERVICES AS credits_used_cloud_services,
                START_TIME          AS start_time,
                END_TIME            AS end_time,
                USER_NAME           AS user_name
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD('hour', %s, CURRENT_TIMESTAMP())
              AND TOTAL_ELAPSED_TIME >= %s
              AND EXECUTION_STATUS = 'SUCCESS'
            ORDER BY TOTAL_ELAPSED_TIME DESC
            LIMIT %s
        """
        try:
            return self._execute(query, (-hours, min_duration_ms, limit))
        except Exception as exc:
            logger.error("snowflake.get_slow_queries.failed", error=str(exc))
            return []

    def get_warehouse_costs(self, days: int = 30) -> list[dict]:
        """Return daily credit consumption grouped by warehouse.

        Args:
            days: Lookback window in days (default 30).

        Returns:
            List of dicts with keys: warehouse_name, usage_date, credits_used.
            Empty list on error.
        """
        query = """
            SELECT
                WAREHOUSE_NAME AS warehouse_name,
                DATE(START_TIME) AS usage_date,
                SUM(CREDITS_USED) AS credits_used
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
            WHERE START_TIME >= DATEADD('day', %s, CURRENT_TIMESTAMP())
            GROUP BY warehouse_name, usage_date
            ORDER BY usage_date DESC, credits_used DESC
        """
        try:
            return self._execute(query, (-days,))
        except Exception as exc:
            logger.error("snowflake.get_warehouse_costs.failed", error=str(exc))
            return []

    def get_table_freshness(
        self, database: str, schema: str, lookback_hours: int = 24
    ) -> list[dict]:
        """Detect tables that have not been updated within the lookback window.

        Args:
            database: Snowflake database name.
            schema: Schema to inspect.
            lookback_hours: Tables older than this are flagged as stale (default 24 h).

        Returns:
            List of dicts with table_name, last_altered, hours_since_update,
            is_stale.  Empty list on error.
        """
        query = f"""
            SELECT
                TABLE_NAME          AS table_name,
                LAST_ALTERED        AS last_altered,
                DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) AS hours_since_update,
                CASE
                    WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) > %s
                    THEN TRUE ELSE FALSE
                END AS is_stale
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY hours_since_update DESC
        """
        try:
            return self._execute(query, (lookback_hours, schema.upper()))
        except Exception as exc:
            logger.error("snowflake.get_table_freshness.failed", error=str(exc))
            return []

    def get_storage_usage(self) -> dict:
        """Return the most recent row from SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE.

        Returns:
            Dict with keys: usage_date, average_database_bytes,
            average_stage_bytes, average_failsafe_bytes.
            Empty dict on error.
        """
        query = """
            SELECT
                USAGE_DATE                  AS usage_date,
                AVERAGE_DATABASE_BYTES      AS average_database_bytes,
                AVERAGE_STAGE_BYTES         AS average_stage_bytes,
                AVERAGE_FAILSAFE_BYTES      AS average_failsafe_bytes
            FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
            ORDER BY USAGE_DATE DESC
            LIMIT 1
        """
        try:
            rows = self._execute(query)
            return rows[0] if rows else {}
        except Exception as exc:
            logger.error("snowflake.get_storage_usage.failed", error=str(exc))
            return {}

    def detect_cost_anomalies(self, days: int = 7) -> list[dict]:
        """Flag warehouses whose today's credit spend exceeds 2x the 7-day average.

        Args:
            days: Baseline window in days (default 7).

        Returns:
            List of anomaly dicts with keys: warehouse_name, today_credits,
            baseline_avg_credits, ratio, is_anomaly.
            Empty list on error.
        """
        query = """
            WITH daily AS (
                SELECT
                    WAREHOUSE_NAME                       AS warehouse_name,
                    DATE(START_TIME)                     AS usage_date,
                    SUM(CREDITS_USED)                    AS credits_used
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE START_TIME >= DATEADD('day', %s, CURRENT_TIMESTAMP())
                GROUP BY warehouse_name, usage_date
            ),
            today AS (
                SELECT warehouse_name, credits_used AS today_credits
                FROM daily
                WHERE usage_date = CURRENT_DATE()
            ),
            baseline AS (
                SELECT warehouse_name, AVG(credits_used) AS baseline_avg
                FROM daily
                WHERE usage_date < CURRENT_DATE()
                GROUP BY warehouse_name
            )
            SELECT
                t.warehouse_name,
                t.today_credits,
                b.baseline_avg               AS baseline_avg_credits,
                ROUND(t.today_credits / NULLIF(b.baseline_avg, 0), 2) AS ratio,
                CASE WHEN t.today_credits > 2 * b.baseline_avg THEN TRUE ELSE FALSE END
                    AS is_anomaly
            FROM today t
            JOIN baseline b ON t.warehouse_name = b.warehouse_name
            ORDER BY ratio DESC NULLS LAST
        """
        try:
            return self._execute(query, (-days,))
        except Exception as exc:
            logger.error("snowflake.detect_cost_anomalies.failed", error=str(exc))
            return []
