# AI-Powered Software Project Management Platform

A full-stack software project management platform for teams to organize projects,
sprints, issues, collaboration, and AI-assisted issue triage.

## Planned Core Capabilities

- Team and project workspaces
- Role-based memberships
- Bugs, features, and tasks
- Issue assignment and workflow tracking
- Sprint planning
- Comments and activity history
- Project dashboards
- AI issue summarization
- AI issue classification
- AI priority suggestions with explanations

## Planned Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- React
- TypeScript
- Docker
- pytest
- Playwright
- GitHub Actions

See `docs/v1-scope.md`, `docs/data-model.md`, and `docs/architecture.md` for the
initial system design.

## Backend Development

Requires Python 3.13+; PostgreSQL is the runtime database.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

Tests use isolated configuration and SQLite in memory; no PostgreSQL is needed.
For local startup, set `DATABASE_URL` in your environment or copy `.env.example`
to `.env` and replace its example credentials. Environment variables override
`.env`. `APP_NAME`, `ENVIRONMENT`, and `API_V1_PREFIX` have development defaults.

```bash
uvicorn app.main:app --reload
```

`GET /api/v1/health` returns `{"status":"ok"}` without opening a database
connection. Startup validates configuration but does not connect to PostgreSQL
or create tables. Domain models and versioned migrations will follow later.
