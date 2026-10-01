import { request } from "./client";
import { teamSchema, teamMemberSchema, type TeamInput } from "../types/api";
export const teamsApi = {
  list: () => request("/teams", teamSchema.array()),
  get: (id: number) => request(`/teams/${id}`, teamSchema),
  members: (id: number) =>
    request(`/teams/${id}/members`, teamMemberSchema.array()),
  create: (body: TeamInput) =>
    request("/teams", teamSchema, { method: "POST", body }),
};
