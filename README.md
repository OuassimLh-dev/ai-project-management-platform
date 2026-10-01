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
versions; `alembic history` shows the migration history. Users, teams, projects,
their memberships, and project-scoped sprints are modeled.

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


Projects belong to one team. Create/list them at
`POST`/`GET /api/v1/teams/{team_id}/projects`; view/update them at
`GET`/`PATCH /api/v1/projects/{project_id}`. Membership endpoints are
`GET`/`POST /api/v1/projects/{project_id}/members` and
`PATCH`/`DELETE /api/v1/projects/{project_id}/members/{user_id}` (DELETE returns 204).
Creation requires a team owner/admin and atomically makes the creator a project
manager. Project keys are required, normalized to uppercase, unique per team,
and contain 1–20 alphanumeric characters starting with a letter. The documented
`is_active` field defaults true; it is metadata, not an access-control switch.
Team owners/admins have administrative access to every project in their team.
Other team members see only assigned projects: project managers manage metadata
and membership; project members have read access. Adding a member by `user_id`
requires existing team membership. Remove project memberships before removing a
user from the team. Multiple managers are allowed, but removing/demoting the last
manager returns 400. Project deletion is not implemented. Apply migration `0003`
with `alembic upgrade head`.


Sprints belong to projects: `POST`/`GET /api/v1/projects/{project_id}/sprints`
create/list them; `GET`/`PATCH /api/v1/sprints/{sprint_id}` retrieve/update them.
Project managers and parent-team owners/admins can create/update; authorized
project readers can read/list. Project `is_active` remains metadata and does not
change these permissions. New sprints start `planned`; transitions are
`planned → active/cancelled` and `active → completed/cancelled`. Terminal statuses
cannot reopen; metadata remains editable. Names may repeat, goals are optional,
and required dates permit same-day sprints. Dates never change status automatically.
No sprint deletion is implemented. Apply migration `0004` with `alembic upgrade head`.


Issues belong to projects. All authorized project readers can create and edit
issues. Types are `bug`, `feature`, and `task`; priorities are `low`, `medium`
(default), `high`, and `critical`. Status defaults to `backlog`; `todo`,
`in_progress`, `in_review`, `done`, and `cancelled` are also supported, with free
transitions in V1. Project-local immutable numbers start at 1; `issue_key` derives
from the current project key and number (for example `API-17`). The authenticated
creator is the reporter (`created_by_id` in storage, `reporter_id` in responses).
Optional assignees must be explicit ProjectMembers; optional sprints must belong
to the same project. Both may be cleared with null.

Use `POST`/`GET /api/v1/projects/{project_id}/issues` and
`GET`/`PATCH /api/v1/issues/{issue_id}`. Lists sort by number and support exact
`status`, `priority`, `issue_type`, `assignee_id`, and `sprint_id` filters.
Apply migration `0005` with `alembic upgrade head`. Issue deletion is not implemented.


Issue comments: `POST`/`GET /api/v1/issues/{issue_id}/comments` allow authorized
issue users to create/list comments. Only the author with current issue access
may `PATCH`/`DELETE /api/v1/issues/{issue_id}/comments/{comment_id}`.
`GET /api/v1/issues/{issue_id}/activity` returns append-only history: one creation
event and one entry per changed issue field, committed atomically with the issue.
No-op updates add nothing; comment actions remain separate from field history.
Apply migration `0006` with `alembic upgrade head`.
