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

## IssueComment

Represents discussion on an issue.

Core fields:

- id
- issue_id
- author_id
- body
- created_at
- updated_at

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
