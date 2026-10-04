import { AxiosError, AxiosHeaders, type AxiosAdapter } from "axios";
import { transport } from "../api/client";
import {
  analysis,
  newAnalysis,
  activities,
  comment,
  issue,
  project,
  projectMembers,
  sprint,
  team,
  teamMembers,
  user,
} from "./fixtures";
export type Call = {
  method: string;
  path: string;
  body: unknown;
  params: unknown;
  authorization: unknown;
  baseURL: string | undefined;
};
type Reply = { status?: number; data: unknown };
export const calls: Call[] = [];
export const handlers = new Map<
  string,
  (call: Call) => Reply | Promise<Reply>
>();
export function reply(
  method: string,
  path: string,
  data: unknown,
  status = 200,
) {
  handlers.set(`${method} ${path}`, () => ({ data, status }));
}
const adapter: AxiosAdapter = async (config) => {
  const body: unknown =
    typeof config.data === "string" ? JSON.parse(config.data) : config.data;
  const call: Call = {
    method: config.method?.toUpperCase() ?? "GET",
    path: config.url ?? "",
    body,
    params: config.params,
    authorization: config.headers.get("Authorization"),
    baseURL: config.baseURL,
  };
  calls.push(call);
  const handler = handlers.get(`${call.method} ${call.path}`);
  if (!handler)
    throw new Error(`No mock response for ${call.method} ${call.path}`);
  const result = await handler(call);
  const response = {
    data: result.data,
    status: result.status ?? 200,
    statusText: "Test response",
    headers: new AxiosHeaders(),
    config,
  };
  if (response.status >= 400)
    throw new AxiosError(
      "Private upstream error",
      "ERR_BAD_RESPONSE",
      config,
      undefined,
      response,
    );
  return response;
};
export function resetServer() {
  calls.length = 0;
  handlers.clear();
  transport.defaults.adapter = adapter;
  reply("POST", "/auth/login", {
    access_token: "test-token",
    token_type: "bearer",
  });
  reply("POST", "/auth/register", user, 201);
  reply("GET", "/auth/me", user);
  reply("GET", "/teams", [team]);
  reply("GET", "/teams/1", team);
  reply("GET", "/teams/1/members", teamMembers);
  reply("POST", "/teams", team, 201);
  reply("GET", "/teams/1/projects", [project]);
  reply("POST", "/teams/1/projects", project, 201);
  reply("GET", "/projects/1", project);
  reply("GET", "/projects/1/members", projectMembers);
  reply("GET", "/projects/1/sprints", [sprint]);
  reply("GET", "/projects/1/issues", [issue]);
  reply("POST", "/projects/1/issues", issue, 201);
  reply("GET", "/issues/1", issue);
  reply("PATCH", "/issues/1", issue);
  reply("GET", "/issues/1/comments", [comment]);
  reply(
    "POST",
    "/issues/1/comments",
    { ...comment, id: 2, body: "New comment" },
    201,
  );
  reply("GET", "/issues/1/activity", activities);
  reply("GET", "/issues/1/ai/analyses", [analysis]);
  reply("POST", "/issues/1/ai/analyze", newAnalysis, 201);
}
