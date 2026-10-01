import { request } from "./client";
import {
  issueSchema,
  commentSchema,
  activitySchema,
  type IssueFilters,
  type IssueInput,
  type IssueUpdate,
} from "../types/api";
export const issuesApi = {
  list: (projectId: number, params: IssueFilters = {}) =>
    request(`/projects/${projectId}/issues`, issueSchema.array(), { params }),
  get: (id: number) => request(`/issues/${id}`, issueSchema),
  create: (projectId: number, body: IssueInput) =>
    request(`/projects/${projectId}/issues`, issueSchema, {
      method: "POST",
      body,
    }),
  update: (id: number, body: IssueUpdate) =>
    request(`/issues/${id}`, issueSchema, { method: "PATCH", body }),
  comments: (id: number) =>
    request(`/issues/${id}/comments`, commentSchema.array()),
  addComment: (id: number, body: string) =>
    request(`/issues/${id}/comments`, commentSchema, {
      method: "POST",
      body: { body },
    }),
  activity: (id: number) =>
    request(`/issues/${id}/activity`, activitySchema.array()),
};
