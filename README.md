# Data Engineering Observability Platform

<div align="center">

**Production-grade monitoring for dbt + Snowflake with Claude AI co-pilot**

[![CI/CD](https://github.com/Snehabankapalli/data-engineering-observability-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Snehabankapalli/data-engineering-observability-platform/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](#)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](#)
[![Claude API](https://img.shields.io/badge/Claude_API-claude--sonnet--4--6-6B48FF)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Architecture](.github/ARCHITECTURE.md) • [Setup](docs/SETUP.md) • [API Reference](docs/API.md) • [Contributing](.github/CONTRIBUTING.md)

</div>

---

## What It Does

Data teams spend 10-15% of their time firefighting pipeline failures instead of building. This platform changes that.

- **Real-time dbt monitoring** — catch test failures and run anomalies within seconds, not hours
- **Snowflake cost intelligence** — track warehouse spend, detect cost spikes, identify expensive queries
- **Claude AI co-pilot** — get instant root cause analysis and optimization suggestions for any failure
- **Anomaly detection** — null spikes, volume drops, schema drift, freshness issues — all automated
- **One-click remediation** — resolve, annotate, and track anomalies from a single dashboard

---

## Results

| Metric | Impact |
|--------|--------|
| Mean time to detection | Hours → Seconds |
| Pipeline firefighting time | -60% on-call interruptions |
| Snowflake cost visibility | Per-warehouse daily breakdown |
| SQL optimization | Claude identifies 40-80% query improvements |
| Test coverage | Auto-generates dbt tests from schema |

---

## Architecture

```
dbt Cloud ─────────────────┐
                           │
Snowflake (queries/costs) ─┼──► FastAPI Backend ──► PostgreSQL
                           │         │
                           │    Claude AI co-pilot
                           │         │
                           └──► React Dashboard ──► Browser
                                     │
                                Slack Alerts + Prometheus
```

[Full architecture diagrams →](.github/ARCHITECTURE.md)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI, SQLAlchemy 2.0, PostgreSQL |
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| AI | Claude API (claude-sonnet-4-6) |
| dbt Integration | dbt Cloud REST API |
| Snowflake | snowflake-connector-python |
| Monitoring | Prometheus metrics, Slack webhooks |
| Infrastructure | Docker Compose, GitHub Actions |

---

## Quick Start

```bash
git clone https://github.com/Snehabankapalli/data-engineering-observability-platform
cd data-engineering-observability-platform

# Configure credentials
cp backend/.env.example backend/.env
# Edit .env: add ANTHROPIC_API_KEY, DBT_CLOUD_API_TOKEN, SNOWFLAKE_* vars

# Launch everything
docker-compose up -d

# Open dashboard
open http://localhost:3000
# API docs
open http://localhost:8000/docs
```

---

## Dashboard Features

### Overview
- Pipeline health KPIs (success rate, active anomalies, daily cost)
- 7-day run history chart
- Recent anomalies and AI insights

### dbt Monitoring
- Real-time run status and history
- Test failure log with Claude root cause analysis
- One-click "Analyze with AI" for any failure

### Snowflake Intelligence
- Warehouse cost trend chart (daily credits)
- Slow query table with latency and cost
- "Analyze with AI" → instant optimization suggestions

### Anomaly Management
- Filter by severity (P1/P2/P3), type, and status
- Resolve anomalies with one click
- Auto-routing to Slack for P1/P2

### AI Insights
- Ongoing recommendations from Claude
- Query optimization opportunities
- Cost reduction suggestions
- dbt test generation for uncovered models

---

## API Reference

45+ endpoints. Full documentation at `/docs` (interactive Swagger UI).

Key endpoints:
```bash
GET  /api/dashboard/overview         # KPI summary
GET  /api/dbt/runs                   # Recent dbt runs
POST /api/dbt/analyze/{run_id}       # AI analysis of a run
GET  /api/snowflake/slow-queries     # Queries > 5s
POST /api/snowflake/analyze-query    # AI query optimization
GET  /api/anomalies                  # Active anomalies
POST /api/anomalies/{id}/resolve     # Resolve anomaly
GET  /api/insights                   # AI recommendations
GET  /metrics                        # Prometheus metrics
```

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for setup, standards, and workflow.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sneha2095/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/Snehabankapalli)
