import type {
  AIAnalysis,
  User,
  Team,
  Project,
  Issue,
  IssueComment,
  IssueActivity,
  ProjectMember,
  TeamMember,
  Sprint,
} from "../types/api";
const dates = {
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
};
export const user: User = {
  id: 1,
  first_name: "Sara",
  last_name: "Demo",
  email: "sara@example.com",
  is_active: true,
  ...dates,
};
export const team: Team = {
  id: 1,
  name: "Platform team",
  description: "Building thoughtful software.",
  created_by_id: 1,
  ...dates,
};
export const project: Project = {
  id: 1,
  team_id: 1,
  name: "Customer portal",
  key: "APP",
  description: "A better experience for customers.",
  created_by_id: 1,
  is_active: true,
  ...dates,
};
export const issue: Issue = {
  id: 1,
  project_id: 1,
  number: 1,
  issue_key: "APP-1",
  title: "Fix password reset",
  description: "The reset link expires too early.",
  issue_type: "bug",
  priority: "high",
  status: "in_progress",
  reporter_id: 1,
  assignee_id: 1,
  sprint_id: 1,
  ...dates,
};
export const comment: IssueComment = {
  id: 1,
  issue_id: 1,
  author_id: 1,
  body: "I can reproduce this on the sign-in page.",
  ...dates,
};
export const activities: IssueActivity[] = [
  {
    id: 1,
    issue_id: 1,
    actor_id: 1,
    action: "created",
    field_name: null,
    old_value: null,
    new_value: null,
    created_at: dates.created_at,
  },
  {
    id: 2,
    issue_id: 1,
    actor_id: 1,
    action: "field_changed",
    field_name: "status",
    old_value: "backlog",
    new_value: "in_progress",
    created_at: dates.created_at,
  },
];
export const teamMembers: TeamMember[] = [
  { id: 1, team_id: 1, user_id: 1, role: "owner", joined_at: dates.created_at },
];
export const projectMembers: ProjectMember[] = [
  {
    id: 1,
    project_id: 1,
    user_id: 1,
    role: "manager",
    joined_at: dates.created_at,
  },
  {
    id: 2,
    project_id: 1,
    user_id: 2,
    role: "member",
    joined_at: dates.created_at,
  },
];
export const sprint: Sprint = {
  id: 1,
  project_id: 1,
  name: "October iteration",
  goal: "Improve sign-in",
  start_date: "2026-10-01",
  end_date: "2026-10-14",
  status: "active",
  ...dates,
};

export const analysis: AIAnalysis = {
  id: 1,
  issue_id: 1,
  requested_by_id: 1,
  summary: "Password reset links expire before users can complete recovery.",
  suggested_type: "bug",
  suggested_priority: "critical",
  explanation: "Account recovery is blocked for affected users.",
  model_name: "test/triage-model",
  created_at: "2026-10-01T11:00:00Z",
};
export const newAnalysis: AIAnalysis = {
  ...analysis,
  id: 2,
  suggested_type: "feature",
  suggested_priority: "low",
  summary: "Consider improving the recovery link lifetime.",
  explanation: "An alternative recovery path remains available.",
  created_at: "2026-10-01T12:00:00Z",
};

export const plannedSprint: Sprint = {
  ...sprint,
  id: 2,
  name: "November planning",
  goal: "Plan recovery improvements",
  status: "planned",
  start_date: "2026-11-01",
  end_date: "2026-11-14",
};
export const completedSprint: Sprint = {
  ...sprint,
  id: 3,
  name: "September delivery",
  status: "completed",
};
