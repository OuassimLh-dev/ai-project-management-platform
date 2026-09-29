# Architecture

## Overview

The application uses a conventional full-stack architecture with a REST API,
relational database, React frontend, and isolated AI integration layer.

## Backend

Technology:

- Python
- FastAPI
- SQLAlchemy 2.x
- Pydantic
- PostgreSQL

Backend responsibilities:

- authentication
- authorization
- teams and memberships
- projects and memberships
- sprint management
- issue workflows
- comments
- activity history
- dashboard aggregation
- AI orchestration

The backend should follow a layered structure:

app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  ai/

API routers handle HTTP concerns.

Services contain business logic.

SQLAlchemy models manage persistence.

Pydantic schemas define API input and output contracts.

The AI package isolates external model-provider dependencies from normal
application business logic.

## Frontend

Technology:

- React
- TypeScript
- Vite
- React Router
- Axios

Frontend responsibilities:

- authentication UI
- team selection
- project navigation
- issue board and issue details
- sprint management
- comments and activity history
- dashboard views
- AI analysis controls and results

The frontend should communicate only with the FastAPI API.

## Database

PostgreSQL is the production database.

Schema changes must be versioned through migrations.

The relational model should enforce important uniqueness and integrity
constraints rather than relying only on frontend validation.

## Authentication

Authentication uses email/password login with securely hashed passwords.

The API issues JWT access tokens.

Authorization is enforced by the backend based on team and project membership,
not merely by hiding frontend controls.

## AI Architecture

AI providers must be accessed through an application-owned service abstraction.

Business code should not depend directly on one LLM vendor.

Conceptually:

Issue -> AI Analysis Service -> AI Provider -> Structured Analysis Result

AI responses should be validated before being returned to the user or stored.

AI suggestions are advisory and never silently overwrite user-selected values.

## Testing Strategy

The project will use multiple layers of automated testing:

- pytest unit/service/API tests
- PostgreSQL integration coverage where appropriate
- frontend type checking and production builds
- Playwright browser end-to-end tests
- Docker integration verification

## Infrastructure

Local development and integration testing will use Docker Compose.

GitHub Actions will verify:

- backend tests
- frontend checks
- Docker build/integration
- end-to-end tests

Production deployment will be added after the core V1 workflow is stable.
