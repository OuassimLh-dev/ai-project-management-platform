# Data Model

## User

Represents an authenticated platform user.

Core fields:

- id
- first_name
- last_name
- email
- hashed_password
- is_active
- created_at
- updated_at

## Team

Represents a collaborative workspace.

Core fields:

- id
- name
- description
- created_by_id
- created_at
- updated_at

## TeamMember

Associates users with teams.

Core fields:

- id
- team_id
- user_id
- role
- joined_at

Initial team roles:

- owner
- admin
- member

A user may belong to multiple teams.

## Project

Represents a software project owned by a team.

Core fields:

- id
- team_id
- name
- key
- description
- created_by_id
- is_active
- created_at
- updated_at

The project key is a short unique identifier within a team, for example:

- CAMPUS
- MOBILE
- API

Issue identifiers can later be displayed as PROJECT_KEY-number.

## ProjectMember

Associates users with individual projects.

Core fields:

- id
- project_id
- user_id
- role
- joined_at

Initial project roles:

- manager
- member

## Sprint

Represents a project iteration.

Core fields:

- id
- project_id
- name
- goal
- start_date
- end_date
- status
- created_at
- updated_at

Initial sprint statuses:

- planned
- active
- completed
- cancelled

V1 details: names are trimmed, nonblank, at most 150 characters, and need not be
unique. Goal is optional (up to 5000 characters); both dates are required and
end_date must be on or after start_date. No creator field is defined for sprints.
New sprints start planned. Allowed transitions are planned -> active/cancelled
and active -> completed/cancelled. Completed and cancelled are terminal; setting
the existing status again is a no-op. Metadata remains editable in any status.
Dates never automatically change status.

## Issue

Represents work tracked within a project.

Core fields:

- id
- project_id
- number
- sprint_id
- created_by_id
- assignee_id
- title
- description
- issue_type
- status
- priority
- created_at
- updated_at

Issue types:

- bug
- feature
- task

Issue statuses:

- backlog
- todo
- in_progress
- in_review
- done
- cancelled

Issue priorities:

- low
- medium
- high
- critical

An issue may exist without a sprint or assignee.

V1 details: `created_by_id` is the authenticated creator/reporter, exposed as
`reporter_id` in the API (one stored foreign key, not two identities). Clients
cannot set either creator field. Titles are trimmed, nonblank, and at most 200
characters; optional descriptions are trimmed and limited to 10000 characters.
Type is required; priority defaults to medium and status to backlog. Authorized
project users can change freely between all valid issue statuses.

Numbers start at 1 within each project, are immutable, and are allocated under
parent project locks using max(number) + 1. There is no issue deletion; numbers
are not reused. The derived API `issue_key` uses the current Project.key and the
stable number, so changing a project key changes its displayed issue keys.
Keys are project/team context identifiers, not globally unique lookup keys.
Assignees must be explicit project members; sprints must belong to the same
project. Either reference can be cleared with null. Sprint status does not
change issue status. Project readers (including ordinary project members) may
create and edit issues. Project activity remains metadata.

## IssueComment

Represents discussion on an issue.

Core fields:

- id
- issue_id
- author_id
- body
- created_at
- updated_at

V1 comments use trimmed, nonblank `body` text, limited to 10000 characters.
Authorized issue users can create/list comments. Only the author, while still
having issue access, may edit/delete their comment; managers have no moderation
override. Comments are ordered by ID. Author identity survives membership removal.
Comment actions are separate from issue field activity.

## IssueActivity

Provides an audit-style history for meaningful issue changes.

Core fields:

- id
- issue_id
- actor_id
- action
- field_name
- old_value
- new_value
- created_at

Examples:

- issue created
- status changed
- priority changed
- assignee changed
- sprint changed

V1 stores history in `issue_activity`, read-only through the API. Creation adds
one `created` event with null field/old/new values. Updates add `field_changed`
rows for actual changes to title, description, issue_type, priority, status,
assignee_id, and sprint_id. Enums use lowercase values, IDs use decimal strings,
and null remains SQL/API null. No-op updates and reads add nothing. Issue and
history writes commit atomically; history is ordered by created_at then ID.
Historical actor identity survives membership removal. Existing issues receive
no fabricated backfill events when migration 0006 is applied.

## AIAnalysis

Stores AI-generated assistance for an issue.

Core fields:

- id
- issue_id
- requested_by_id
- summary
- suggested_type
- suggested_priority
- explanation
- model_name
- created_at

AI analysis is advisory.

It must not silently modify the issue type or priority.

V1 stores immutable history in `ai_analyses`, using exactly these fields.
`suggested_type` and `suggested_priority` reuse Issue enums. Summary is trimmed,
nonblank, at most 2000 characters; explanation is trimmed, nonblank, at most 1000.
`model_name` records the configured provider/model (for example `openai/<model>`),
at most 200 characters. Only title/description are sent for analysis; comments,
activity, and user details are excluded. Each valid successful execution creates
one row. No Issue field or IssueActivity is changed. No analysis update/delete
API exists. Access follows the Issue; historic requesters remain linked to Users.
Network calls run without an open database transaction; access is checked again
before persistence. No input version tracking is provided in V1.

## Relationships

User
  -> TeamMember
  -> ProjectMember
  -> created issues
  -> assigned issues
  -> comments
  -> activities
  -> AI analysis requests

Team
  -> TeamMembers
  -> Projects

Project
  -> ProjectMembers
  -> Sprints
  -> Issues

Sprint
  -> Issues

Issue
  -> Comments
  -> Activity history
  -> AI analyses
