import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { aiApi } from "../api/ai";
import { getToken } from "../auth/tokenStorage";
import { renderApp } from "./render";
import { calls, handlers, reply } from "./server";
import { analysis, newAnalysis, issue } from "./fixtures";

test("AI client uses exact endpoints without POST body or query", async () => {
  expect(await aiApi.history(1)).toEqual([analysis]);
  expect(await aiApi.analyze(1)).toEqual(newAnalysis);
  expect(
    calls.map(({ method, path, body, params }) => ({
      method,
      path,
      body,
      params,
    })),
  ).toEqual([
    {
      method: "GET",
      path: "/issues/1/ai/analyses",
      body: undefined,
      params: undefined,
    },
    {
      method: "POST",
      path: "/issues/1/ai/analyze",
      body: undefined,
      params: undefined,
    },
  ]);
});
test.each(["GET", "POST"])(
  "malformed %s response is safely rejected",
  async (method) => {
    reply(
      method,
      method === "GET" ? "/issues/1/ai/analyses" : "/issues/1/ai/analyze",
      method === "GET"
        ? [{ ...analysis, suggested_type: "unknown" }]
        : { ...newAnalysis, summary: null },
    );
    await expect(
      method === "GET" ? aiApi.history(1) : aiApi.analyze(1),
    ).rejects.toThrow("The service returned an unexpected response.");
  },
);
test("renders history content and metadata", async () => {
  renderApp("/app/issues/1");
  const card = await screen.findByRole("article", { name: "Latest analysis" });
  for (const text of [
    analysis.summary,
    analysis.explanation,
    "Bug",
    "Critical",
  ])
    expect(within(card).getByText(text)).toBeInTheDocument();
  expect(card).toHaveTextContent("User #1");
  expect(card).toHaveTextContent(analysis.model_name);
  expect(card.querySelector("time")).toHaveAttribute(
    "datetime",
    analysis.created_at,
  );
});
test("single-flight analysis preserves issue, activity, edit defaults and immutable history", async () => {
  let complete: (value: { data: typeof newAnalysis }) => void = () => {
    throw new Error("Not started");
  };
  handlers.set(
    "POST /issues/1/ai/analyze",
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  await screen.findByText(analysis.summary);
  await screen.findByText("Created by User #1");
  const activity = screen
    .getByRole("heading", { name: "Activity" })
    .closest("section")?.textContent;
  await user.dblClick(screen.getByRole("button", { name: "Analyze issue" }));
  expect(screen.getByRole("button", { name: "Analyzing…" })).toBeDisabled();
  expect(screen.getByText("Analyzing issue…")).toHaveAttribute(
    "role",
    "status",
  );
  await act(async () => complete({ data: newAnalysis }));
  expect(await screen.findByText(newAnalysis.summary)).toBeInTheDocument();
  expect(screen.getAllByRole("article")).toHaveLength(2);
  const latest = screen.getByRole("article", { name: "Latest analysis" });
  expect(within(latest).getByText("Feature")).toBeInTheDocument();
  expect(within(latest).getByText("Low")).toBeInTheDocument();
  expect(screen.getByText(analysis.summary)).toBeInTheDocument();
  expect(screen.getByText(/AI suggestions are advisory/)).toBeInTheDocument();
  const heading = screen.getByRole("heading", {
    name: issue.title,
  }).parentElement;
  if (!heading) throw new Error("Missing heading");
  for (const text of ["Bug", "High", "In progress"])
    expect(within(heading).getByText(text)).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Activity" }).closest("section")
      ?.textContent,
  ).toBe(activity);
  expect(calls.filter((call) => call.method !== "GET")).toEqual([
    expect.objectContaining({
      method: "POST",
      path: "/issues/1/ai/analyze",
      body: undefined,
    }),
  ]);
  expect(calls.filter((call) => call.path.endsWith("/activity"))).toHaveLength(
    1,
  );
  expect(calls.filter((call) => call.path.endsWith("/analyses"))).toHaveLength(
    1,
  );
  await user.click(screen.getByRole("button", { name: "Edit issue" }));
  expect(screen.getByLabelText("Type")).toHaveValue(issue.issue_type);
  expect(screen.getByLabelText("Priority")).toHaveValue(issue.priority);
  expect(screen.getByLabelText("Status")).toHaveValue(issue.status);
  expect(screen.getByLabelText("Title")).toHaveValue(issue.title);
  expect(screen.getByLabelText("Description")).toHaveValue(issue.description);
  expect(await screen.findByLabelText("Assignee")).toHaveValue(
    String(issue.assignee_id),
  );
  expect(screen.getByLabelText("Sprint")).toHaveValue(String(issue.sprint_id));
});
test.each([403, 404, 502, 503, 0])(
  "failure %s preserves workspace and supports manual retry",
  async (status) => {
    if (!status)
      handlers.set("POST /issues/1/ai/analyze", () => {
        throw new AxiosError("private-network-detail");
      });
    else
      reply(
        "POST",
        "/issues/1/ai/analyze",
        {
          detail:
            status >= 500 ? "private-provider-detail" : "Issue unavailable",
        },
        status,
      );
    const user = userEvent.setup();
    renderApp("/app/issues/1");
    await screen.findByText(analysis.summary);
    await user.click(screen.getByRole("button", { name: "Analyze issue" }));
    const error = await screen.findByRole("alert");
    expect(error).toHaveTextContent(
      !status
        ? "Unable to reach the service"
        : status >= 500
          ? "The service is unavailable"
          : "Issue unavailable",
    );
    expect(error).not.toHaveTextContent("private");
    expect(screen.getByText(analysis.summary)).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      screen.getByRole("heading", { name: issue.title }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Add a comment")).toBeEnabled();
    expect(screen.getByRole("button", { name: "Edit issue" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Analyze issue" })).toBeEnabled();
    expect(getToken()).toBe("test-token");
    expect(calls.some((call) => call.method === "PATCH")).toBe(false);
    reply("POST", "/issues/1/ai/analyze", newAnalysis, 201);
    await user.click(screen.getByRole("button", { name: "Analyze issue" }));
    expect(await screen.findByText(newAnalysis.summary)).toBeInTheDocument();
  },
);
test.each(["GET", "POST"])("AI %s 401 uses global logout", async (method) => {
  reply(
    method,
    method === "GET" ? "/issues/1/ai/analyses" : "/issues/1/ai/analyze",
    { detail: "Expired token" },
    401,
  );
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  if (method === "POST")
    await user.click(
      await screen.findByRole("button", { name: "Analyze issue" }),
    );
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
test("empty history is not an error", async () => {
  reply("GET", "/issues/1/ai/analyses", []);
  renderApp("/app/issues/1");
  expect(await screen.findByText("No AI analyses yet")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze issue" })).toBeEnabled();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
test("multiple records use newest-first order with ID tie-break", async () => {
  reply("GET", "/issues/1/ai/analyses", [
    analysis,
    { ...newAnalysis, created_at: analysis.created_at },
  ]);
  renderApp("/app/issues/1");
  await screen.findByText(newAnalysis.summary);
  const cards = screen.getAllByRole("article");
  expect(cards[0]).toHaveTextContent(newAnalysis.summary);
  expect(cards[1]).toHaveTextContent(analysis.summary);
});
test("late history cannot overwrite or duplicate new analysis", async () => {
  let complete: (value: { data: (typeof analysis)[] }) => void = () => {
    throw new Error("Not started");
  };
  handlers.set(
    "GET /issues/1/ai/analyses",
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  expect(
    await screen.findByText("Loading analysis history…"),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Analyze issue" }));
  await screen.findByText(newAnalysis.summary);
  await act(async () => complete({ data: [analysis, newAnalysis] }));
  expect(screen.getAllByRole("article")).toHaveLength(2);
  expect(screen.getAllByText(newAnalysis.summary)).toHaveLength(1);
});
test("history error stays local and can be retried", async () => {
  reply("GET", "/issues/1/ai/analyses", {}, 503);
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The service is unavailable",
  );
  expect(
    screen.getByRole("heading", { name: issue.title }),
  ).toBeInTheDocument();
  reply("GET", "/issues/1/ai/analyses", [analysis]);
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText(analysis.summary)).toBeInTheDocument();
});
