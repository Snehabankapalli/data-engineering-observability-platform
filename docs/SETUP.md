# Setup Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+
- Snowflake account (for Snowflake monitoring)
- dbt Cloud account (for dbt monitoring)
- Anthropic API key (for AI co-pilot)

## Quick Start (Docker)

```bash
git clone https://github.com/Snehabankapalli/data-engineering-observability-platform
cd data-engineering-observability-platform

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# Start all services
docker-compose up -d

# Open dashboard
open http://localhost:3000
# API docs
open http://localhost:8000/docs
```

## Local Development

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Start backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Fill in credentials
uvicorn app.main:app --reload --port 8000

# 3. Start frontend (new terminal)
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

## Configuration

### Required (for full functionality)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Claude API key from console.anthropic.com |
| `DBT_CLOUD_API_TOKEN` | dbt Cloud service token (Settings → API) |
| `DBT_CLOUD_ACCOUNT_ID` | dbt Cloud account ID (URL: cloud.getdbt.com/accounts/{ID}) |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |

### Optional

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for alerts |
| `SECRET_KEY` | JWT secret (default: change-me-in-production) |
| `DEBUG` | Enable debug mode (default: False) |

## Snowflake Permissions

The monitoring user needs:

```sql
-- Create monitoring role and user
CREATE ROLE MONITOR_ROLE;
CREATE USER monitor_user PASSWORD='...' DEFAULT_ROLE=MONITOR_ROLE;
GRANT ROLE MONITOR_ROLE TO USER monitor_user;

-- Grant required permissions
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE MONITOR_ROLE;
GRANT USAGE ON WAREHOUSE MONITOR_WH TO ROLE MONITOR_ROLE;
GRANT MONITOR ON WAREHOUSE MONITOR_WH TO ROLE MONITOR_ROLE;
```

## Verify Installation

```bash
curl http://localhost:8000/health
# {"status":"healthy","timestamp":"...","version":"1.0.0"}

curl http://localhost:8000/api/dashboard/overview
# {"total_pipelines":0,"healthy_pipelines":0,...}
```
