import { request } from "./client";
import {
  sprintSchema,
  type SprintInput,
  type SprintUpdate,
} from "../types/api";
export const sprintsApi = {
  list: (projectId: number) =>
    request(`/projects/${projectId}/sprints`, sprintSchema.array()),
  get: (id: number) => request(`/sprints/${id}`, sprintSchema),
  create: (projectId: number, body: SprintInput) =>
    request(`/projects/${projectId}/sprints`, sprintSchema, {
      method: "POST",
      body,
    }),
  update: (id: number, body: SprintUpdate) =>
    request(`/sprints/${id}`, sprintSchema, { method: "PATCH", body }),
};
