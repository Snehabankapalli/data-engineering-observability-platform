# Contributing

## Setup

```bash
git clone https://github.com/Snehabankapalli/data-engineering-observability-platform
cd data-engineering-observability-platform

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your credentials

# Frontend
cd ../frontend
npm install

# Start all services
docker-compose up -d postgres
uvicorn app.main:app --reload  # backend
npm run dev                    # frontend (new terminal)
```

## Workflow

1. `git checkout -b feature/your-feature`
2. Make changes + write tests
3. Run quality checks
4. `git commit -m 'feat: add your feature'`
5. Open a PR

## Quality Standards

```bash
# Backend
black app/ && isort app/
flake8 app/ --max-line-length=100
pytest tests/ -v --cov=app --cov-fail-under=80

# Frontend
npm run build  # must pass
```

## Commit Format

`feat|fix|docs|test|refactor|perf|chore: description`

## Environment Setup

Never commit real credentials. Use `.env` locally (gitignored). For CI, use GitHub Secrets.

Required secrets for full functionality:
- `ANTHROPIC_API_KEY` — Claude API key
- `DBT_CLOUD_API_TOKEN` — dbt Cloud service token
- `SNOWFLAKE_*` — Snowflake connection params

Questions? Open an issue on GitHub.
