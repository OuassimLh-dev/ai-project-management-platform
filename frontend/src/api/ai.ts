import { request } from "./client";
import { aiAnalysisSchema } from "../types/api";

export const aiApi = {
  history: (issueId: number) =>
    request(`/issues/${issueId}/ai/analyses`, aiAnalysisSchema.array()),
  analyze: (issueId: number) =>
    request(`/issues/${issueId}/ai/analyze`, aiAnalysisSchema, {
      method: "POST",
      // Allow the backend's maximum 120-second provider timeout to finish.
      timeout: 150000,
    }),
};
