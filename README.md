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
For local startup, set `DATABASE_URL` and `JWT_SECRET_KEY` in your environment or copy `.env.example`
to `.env` and replace its example credentials and secret. Use a unique random
JWT secret of at least 32 characters. `JWT_ALGORITHM` is `HS256` and
`ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 30 (must be positive). Environment variables override
`.env`. `APP_NAME`, `ENVIRONMENT`, and `API_V1_PREFIX` have development defaults.

With PostgreSQL available and configuration set, apply the migration explicitly:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

`GET /api/v1/health` returns `{"status":"ok"}` without opening a database
connection. Startup validates configuration but does not connect to PostgreSQL
or create tables. Alembic uses the application database URL and tracks schema
versions; `alembic history` shows the migration history. `users`, `teams`, and `team_members` are modeled.

Authentication accepts JSON at `POST /api/v1/auth/register` (first name, last name,
email, password) and `POST /api/v1/auth/login` (email, password). Registration
requires an 8–128 character password; passwords are stored as Argon2 hashes.
Login returns a Bearer JWT for `GET /api/v1/auth/me`. Responses never include
passwords or hashes. Duplicate registration returns 409; invalid credentials,
inactive accounts, and missing/invalid tokens return 401. There are no global
roles; team/project membership authorization belongs to later milestones.


Team endpoints under `/api/v1/teams` support creation/listing (`POST`/`GET`),
viewing/updating metadata (`GET`/`PATCH /{team_id}`), and member listing/adding
(`GET`/`POST /{team_id}/members`). Update roles or remove memberships with
`PATCH`/`DELETE /{team_id}/members/{user_id}`; removal returns 204.
Creation atomically makes the creator the sole owner. Owners manage admins and
members; admins manage ordinary members only. All members can read their team,
and owners/admins can update metadata. Outsiders receive 404 to hide team existence.
Adding by email requires an existing user. Assigning, removing, or demoting
the owner returns 400. Ownership transfer
and team deletion are not implemented in V1. Apply migration `0002` with the same
`alembic upgrade head` command.
