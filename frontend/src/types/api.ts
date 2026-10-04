import { z } from "zod";
export const issueTypes = ["bug", "feature", "task"] as const;
export const priorities = ["low", "medium", "high", "critical"] as const;
export const statuses = [
  "backlog",
  "todo",
  "in_progress",
  "in_review",
  "done",
  "cancelled",
] as const;
const timestamps = { created_at: z.string(), updated_at: z.string() };
export const userSchema = z.object({
  id: z.number(),
  first_name: z.string(),
  last_name: z.string(),
  email: z.string(),
  is_active: z.boolean(),
  ...timestamps,
});
export const tokenSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.literal("bearer"),
});
export const teamSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().nullable(),
  created_by_id: z.number(),
  ...timestamps,
});
export const teamMemberSchema = z.object({
  id: z.number(),
  team_id: z.number(),
  user_id: z.number(),
  role: z.enum(["owner", "admin", "member"]),
  joined_at: z.string(),
});
export const projectSchema = z.object({
  id: z.number(),
  team_id: z.number(),
  name: z.string(),
  key: z.string(),
  description: z.string().nullable(),
  created_by_id: z.number(),
  is_active: z.boolean(),
  ...timestamps,
});
export const projectMemberSchema = z.object({
  id: z.number(),
  project_id: z.number(),
  user_id: z.number(),
  role: z.enum(["manager", "member"]),
  joined_at: z.string(),
});
export const sprintSchema = z.object({
  id: z.number(),
  project_id: z.number(),
  name: z.string(),
  goal: z.string().nullable(),
  start_date: z.iso.date(),
  end_date: z.iso.date(),
  status: z.enum(["planned", "active", "completed", "cancelled"]),
  ...timestamps,
});
export const issueSchema = z.object({
  id: z.number(),
  project_id: z.number(),
  number: z.number(),
  issue_key: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  issue_type: z.enum(issueTypes),
  priority: z.enum(priorities),
  status: z.enum(statuses),
  reporter_id: z.number(),
  assignee_id: z.number().nullable(),
  sprint_id: z.number().nullable(),
  ...timestamps,
});
export const commentSchema = z.object({
  id: z.number(),
  issue_id: z.number(),
  author_id: z.number(),
  body: z.string(),
  ...timestamps,
});
export const activitySchema = z.object({
  id: z.number(),
  issue_id: z.number(),
  actor_id: z.number(),
  action: z.string(),
  field_name: z.string().nullable(),
  old_value: z.string().nullable(),
  new_value: z.string().nullable(),
  created_at: z.string(),
});
export type User = z.infer<typeof userSchema>;
export type Team = z.infer<typeof teamSchema>;
export type TeamMember = z.infer<typeof teamMemberSchema>;
export type Project = z.infer<typeof projectSchema>;
export type ProjectMember = z.infer<typeof projectMemberSchema>;
export type Sprint = z.infer<typeof sprintSchema>;
export type Issue = z.infer<typeof issueSchema>;
export type IssueComment = z.infer<typeof commentSchema>;
export type IssueActivity = z.infer<typeof activitySchema>;
export type LoginInput = { email: string; password: string };
export type RegisterInput = LoginInput & Pick<User, "first_name" | "last_name">;
export type TeamInput = Pick<Team, "name" | "description">;
export type ProjectInput = Pick<Project, "name" | "key" | "description">;
export type IssueInput = Pick<
  Issue,
  | "title"
  | "description"
  | "issue_type"
  | "priority"
  | "status"
  | "assignee_id"
  | "sprint_id"
>;
export type IssueUpdate = Partial<IssueInput>;
export type IssueFilters = Partial<
  Pick<Issue, "status" | "priority" | "issue_type"> & { sprint_id: number }
>;

export const aiAnalysisSchema = z.object({
  id: z.number().int().positive(),
  issue_id: z.number().int().positive(),
  requested_by_id: z.number().int().positive(),
  summary: z.string().trim().min(1).max(2000),
  suggested_type: issueSchema.shape.issue_type,
  suggested_priority: issueSchema.shape.priority,
  explanation: z.string().trim().min(1).max(1000),
  model_name: z.string().trim().min(1).max(200),
  created_at: z.iso.datetime({ offset: true, local: true }),
});
export type AIAnalysis = z.infer<typeof aiAnalysisSchema>;

export type SprintInput = Pick<
  Sprint,
  "name" | "goal" | "start_date" | "end_date"
>;
export type SprintUpdate = Partial<SprintInput & Pick<Sprint, "status">>;
