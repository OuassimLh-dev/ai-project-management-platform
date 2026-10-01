import { request } from "./client";
import {
  projectSchema,
  projectMemberSchema,
  sprintSchema,
  type ProjectInput,
} from "../types/api";
export const projectsApi = {
  list: (teamId: number) =>
    request(`/teams/${teamId}/projects`, projectSchema.array()),
  get: (id: number) => request(`/projects/${id}`, projectSchema),
  create: (teamId: number, body: ProjectInput) =>
    request(`/teams/${teamId}/projects`, projectSchema, {
      method: "POST",
      body,
    }),
  members: (id: number) =>
    request(`/projects/${id}/members`, projectMemberSchema.array()),
  sprints: (id: number) =>
    request(`/projects/${id}/sprints`, sprintSchema.array()),
};
