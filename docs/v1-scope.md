# V1 Scope

## Product

AI-Powered Software Project Management Platform is a collaborative software
development workspace inspired by tools such as Jira and GitHub Issues.

The platform helps software teams organize projects, plan sprints, manage issues,
track work, collaborate through comments, and use AI to assist with issue triage.

## V1 Goals

V1 must support a complete workflow:

1. A user creates an account and signs in.
2. A user creates a team.
3. Team members can be invited or added.
4. A team creates software projects.
5. Project members create and manage issues.
6. Issues can represent bugs, features, or tasks.
7. Issues move through a defined workflow.
8. Issues can be assigned to project members.
9. Projects can organize issues into sprints.
10. Members can comment on issues.
11. Important issue changes are recorded in an activity history.
12. AI can analyze an issue and provide:
    - a concise summary
    - issue type classification
    - priority suggestion
    - explanation for the suggestion
13. Project dashboards summarize current project work.

## Issue Types

- bug
- feature
- task

## Issue Statuses

- backlog
- todo
- in_progress
- in_review
- done
- cancelled

## Issue Priorities

- low
- medium
- high
- critical

## V1 AI Features

AI features assist users but do not automatically overwrite user decisions.

The initial AI capabilities are:

- Issue summarization
- Issue type classification
- Priority suggestion with explanation

Users remain responsible for accepting or ignoring AI suggestions.

## Out of Scope for V1

The following are intentionally postponed:

- GitHub repository integration
- Duplicate issue detection
- Email notifications
- Real-time WebSocket collaboration
- File attachments
- Advanced analytics
- Time tracking
- Billing
- Organization-wide enterprise administration
- Mobile application
