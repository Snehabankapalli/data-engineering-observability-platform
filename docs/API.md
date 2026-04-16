# API Reference

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

## Authentication

Currently no auth for local development. Production deployments should add JWT middleware.

## Endpoints

### Health

```
GET /health
→ {"status":"healthy","timestamp":"...","version":"1.0.0"}
```

### Dashboard

```
GET /api/dashboard/overview
→ {
    "total_pipelines": int,
    "healthy_pipelines": int,
    "failed_today": int,
    "anomalies_active": int,
    "avg_success_rate_pct": float,
    "total_cost_today_usd": float
  }
```

### dbt Cloud

```
GET /api/dbt/runs?limit=20&status=success|failed|running
GET /api/dbt/failures
POST /api/dbt/analyze/{run_id}
→ {"root_cause":"...","fix_sql":"...","prevention_steps":["..."]}
```

### Snowflake

```
GET /api/snowflake/slow-queries?hours=24&min_duration_ms=5000
GET /api/snowflake/costs?days=30
GET /api/snowflake/freshness
POST /api/snowflake/analyze-query
  Body: {"query_text":"...","warehouse":"PIPELINE_WH","duration_ms":45000,"bytes_scanned":1073741824}
→ {"analysis":"...","suggestions":["..."],"priority":"high","estimated_improvement":"60% faster"}
```

### Anomalies

```
GET /api/anomalies?days=7&severity=P1&resolved=false
POST /api/anomalies/{id}/resolve
```

### AI Insights

```
GET /api/insights
→ [{"id":"...","title":"...","priority":"high","recommendation":"...","estimated_impact":"..."}]
```

### Metrics (Prometheus)

```
GET /metrics
→ Prometheus text format
```
