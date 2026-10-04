import {
  act,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { renderApp } from "./render";
import { calls, handlers, reply } from "./server";
import { sprint, plannedSprint, completedSprint, issue } from "./fixtures";
import { getToken } from "../auth/tokenStorage";
import { sprintsApi } from "../api/sprints";

beforeEach(() => {
  vi.spyOn(console, "error");
  vi.spyOn(console, "warn");
});
afterEach(() => {
  expect(console.error).not.toHaveBeenCalled();
  expect(console.warn).not.toHaveBeenCalled();
});

test("project lists sprint names, statuses, goals and date-only values", async () => {
  reply("GET", "/projects/1/sprints", [sprint, plannedSprint, completedSprint]);
  const user = userEvent.setup();
  renderApp("/app/projects/1");
  const link = await screen.findByRole("link", { name: sprint.name });
  const card = link.closest("article");
  if (!card) throw new Error("Missing sprint");
  expect(within(card).getByText("Active")).toBeInTheDocument();
  expect(within(card).getByText("Improve sign-in")).toBeInTheDocument();
  expect(within(card).getByText("2026-10-01")).toHaveAttribute(
    "datetime",
    "2026-10-01",
  );
  expect(within(card).getByText("2026-10-14")).toBeInTheDocument();
  expect(screen.getByText("Planned")).toBeInTheDocument();
  expect(screen.getByText("Completed")).toBeInTheDocument();
  await user.click(link);
  expect(
    await screen.findByRole("heading", { name: sprint.name }),
  ).toBeInTheDocument();
});
test("empty sprints leave project issues available", async () => {
  reply("GET", "/projects/1/sprints", []);
  renderApp("/app/projects/1");
  expect(await screen.findByText("No sprints yet")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ Create sprint" })).toBeEnabled();
  expect(await screen.findByText(issue.title)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ Create issue" })).toBeEnabled();
});
async function fillSprint() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Sprint name"), " November planning ");
  await user.type(
    screen.getByLabelText("Goal"),
    " Plan recovery improvements ",
  );
  fireEvent.change(screen.getByLabelText("Start date"), {
    target: { value: "2026-11-01" },
  });
  fireEvent.change(screen.getByLabelText("End date"), {
    target: { value: "2026-11-14" },
  });
  return user;
}
test("create sends mutable fields only and updates list and filter", async () => {
  const user = userEvent.setup();
  renderApp("/app/projects/1");
  await user.click(
    await screen.findByRole("button", { name: "+ Create sprint" }),
  );
  await fillSprint();
  await user.click(screen.getByRole("button", { name: "Save sprint" }));
  expect(
    await screen.findByRole("link", { name: plannedSprint.name }),
  ).toBeInTheDocument();
  expect(calls.find((call) => call.method === "POST")?.body).toEqual({
    name: "November planning",
    goal: "Plan recovery improvements",
    start_date: "2026-11-01",
    end_date: "2026-11-14",
  });
  expect(calls.find((call) => call.method === "POST")?.path).toBe(
    "/projects/1/sprints",
  );
  expect(
    within(screen.getByLabelText("Filter sprint")).getByRole("option", {
      name: plannedSprint.name,
    }),
  ).toBeInTheDocument();
});
test.each([400, 403, 404, 409, 422, 503, 0])(
  "create failure %s preserves form and project",
  async (status) => {
    if (!status)
      handlers.set("POST /projects/1/sprints", () => {
        throw new AxiosError("Private error");
      });
    else
      reply(
        "POST",
        "/projects/1/sprints",
        { detail: "Creation denied" },
        status,
      );
    const user = userEvent.setup();
    renderApp("/app/projects/1");
    await user.click(
      await screen.findByRole("button", { name: "+ Create sprint" }),
    );
    await fillSprint();
    await user.click(screen.getByRole("button", { name: "Save sprint" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      !status
        ? "Unable to reach"
        : status === 422
          ? "Please check"
          : status >= 500
            ? "The service is unavailable"
            : "Creation denied",
    );
    expect(screen.getByLabelText("Sprint name")).toHaveValue(
      " November planning ",
    );
    expect(
      screen.queryByRole("link", { name: plannedSprint.name }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(issue.title)).toBeInTheDocument();
    expect(getToken()).toBe("test-token");
  },
);
test("date order validation prevents request, same-day dates accepted", async () => {
  const user = userEvent.setup();
  renderApp("/app/projects/1");
  await user.click(
    await screen.findByRole("button", { name: "+ Create sprint" }),
  );
  await fillSprint();
  fireEvent.change(screen.getByLabelText("End date"), {
    target: { value: "2026-10-31" },
  });
  await user.click(screen.getByRole("button", { name: "Save sprint" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "End date must be on or after start date",
  );
  expect(calls.some((call) => call.method === "POST")).toBe(false);
  fireEvent.change(screen.getByLabelText("End date"), {
    target: { value: "2026-11-01" },
  });
  await user.click(screen.getByRole("button", { name: "Save sprint" }));
  await screen.findByRole("link", { name: plannedSprint.name });
  expect(calls.find((call) => call.method === "POST")?.body).toMatchObject({
    start_date: "2026-11-01",
    end_date: "2026-11-01",
  });
});
test.each([
  {
    initial: plannedSprint,
    action: "Start sprint",
    status: "active",
    label: "Active",
  },
  {
    initial: plannedSprint,
    action: "Cancel sprint",
    status: "cancelled",
    label: "Cancelled",
  },
  {
    initial: sprint,
    action: "Complete sprint",
    status: "completed",
    label: "Completed",
  },
  {
    initial: sprint,
    action: "Cancel sprint",
    status: "cancelled",
    label: "Cancelled",
  },
])(
  "$action from $initial.status uses persisted PATCH without touching issues",
  async ({ initial, action, status, label }) => {
    reply("GET", "/sprints/1", { ...initial, id: 1 });
    reply("PATCH", "/sprints/1", { ...initial, id: 1, status });
    const user = userEvent.setup();
    renderApp("/app/sprints/1");
    await user.click(await screen.findByRole("button", { name: action }));
    expect(
      await screen.findByText(label, { selector: ".badge" }),
    ).toBeInTheDocument();
    expect(calls.filter((call) => call.method !== "GET")).toEqual([
      expect.objectContaining({
        method: "PATCH",
        path: "/sprints/1",
        body: { status },
      }),
    ]);
    expect(screen.getByText(issue.title)).toBeInTheDocument();
  },
);
test.each(["completed", "cancelled"])(
  "terminal %s offers metadata editing but no transitions",
  async (status) => {
    reply("GET", "/sprints/1", { ...sprint, status });
    renderApp("/app/sprints/1");
    expect(
      await screen.findByRole("button", { name: "Edit sprint" }),
    ).toBeEnabled();
    for (const name of ["Start sprint", "Complete sprint", "Cancel sprint"])
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
  },
);
test("failed transition preserves persisted status and permits manual retry", async () => {
  reply("PATCH", "/sprints/1", { detail: "Transition rejected" }, 400);
  const user = userEvent.setup();
  renderApp("/app/sprints/1");
  await user.click(
    await screen.findByRole("button", { name: "Complete sprint" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Transition rejected",
  );
  expect(
    screen.getByText("Active", { selector: ".badge" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Complete sprint" })).toBeEnabled();
});
test("pending transition prevents duplicate submissions", async () => {
  let finish: (value: { data: typeof sprint }) => void = () => {
    throw new Error("Not started");
  };
  handlers.set(
    "PATCH /sprints/1",
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const user = userEvent.setup();
  renderApp("/app/sprints/1");
  await user.dblClick(
    await screen.findByRole("button", { name: "Complete sprint" }),
  );
  expect(screen.getByRole("button", { name: "Cancel sprint" })).toBeDisabled();
  expect(screen.getByText("Updating sprint…")).toHaveAttribute(
    "role",
    "status",
  );
  await act(async () => finish({ data: { ...sprint, status: "completed" } }));
  expect(calls.filter((call) => call.method === "PATCH")).toHaveLength(1);
});
test("metadata edit sends only changed fields including nullable goal", async () => {
  reply("PATCH", "/sprints/1", {
    ...sprint,
    name: "Revised sprint",
    goal: null,
  });
  const user = userEvent.setup();
  renderApp("/app/sprints/1");
  await user.click(await screen.findByRole("button", { name: "Edit sprint" }));
  await user.clear(screen.getByLabelText("Sprint name"));
  await user.type(screen.getByLabelText("Sprint name"), "Revised sprint");
  await user.clear(screen.getByLabelText("Goal"));
  await user.click(screen.getByRole("button", { name: "Save sprint changes" }));
  expect(
    await screen.findByRole("heading", { name: "Revised sprint" }),
  ).toBeInTheDocument();
  expect(calls.find((call) => call.method === "PATCH")?.body).toEqual({
    name: "Revised sprint",
    goal: null,
  });
});
test("metadata rejection keeps form and persisted state", async () => {
  reply("PATCH", "/sprints/1", { detail: "Manager permissions required" }, 403);
  const user = userEvent.setup();
  renderApp("/app/sprints/1");
  await user.click(await screen.findByRole("button", { name: "Edit sprint" }));
  await user.type(screen.getByLabelText("Sprint name"), " revised");
  await user.click(screen.getByRole("button", { name: "Save sprint changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Manager permissions required",
  );
  expect(
    screen.getByRole("heading", { name: sprint.name }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Sprint name")).toHaveValue(
    sprint.name + " revised",
  );
});
test("sprint detail filters issues server-side, preserving other filters", async () => {
  renderApp(
    "/app/sprints/1?status=done&priority=high&issue_type=bug&sprint_id=999",
  );
  await screen.findByText(issue.title);
  expect(
    calls.find((call) => call.path === "/projects/1/issues")?.params,
  ).toEqual({
    sprint_id: 1,
    status: "done",
    priority: "high",
    issue_type: "bug",
  });
});
test("project sprint filter coexists with URL filters and clears without invalid params", async () => {
  const user = userEvent.setup();
  renderApp("/app/projects/1?status=done&priority=high&issue_type=bug");
  const select = await screen.findByLabelText("Filter sprint");
  await user.selectOptions(select, "1");
  await waitFor(() =>
    expect(
      calls.filter((call) => call.path === "/projects/1/issues").at(-1)?.params,
    ).toEqual({
      sprint_id: 1,
      status: "done",
      priority: "high",
      issue_type: "bug",
    }),
  );
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  await waitFor(() =>
    expect(
      calls.filter((call) => call.path === "/projects/1/issues").at(-1)?.params,
    ).toEqual({}),
  );
});
test("issue creation retains sprint assignment", async () => {
  const user = userEvent.setup();
  renderApp("/app/projects/1");
  await user.click(
    await screen.findByRole("button", { name: "+ Create issue" }),
  );
  await user.type(screen.getByLabelText("Title"), "Assigned issue");
  await user.selectOptions(await screen.findByLabelText("Sprint"), "1");
  await user.click(screen.getByRole("button", { name: "Save issue" }));
  await screen.findByRole("heading", { name: issue.title });
  expect(calls.find((call) => call.method === "POST")?.body).toMatchObject({
    sprint_id: 1,
  });
});
test.each(["2", ""])(
  "issue edit can change/clear sprint to %s",
  async (value) => {
    reply("GET", "/projects/1/sprints", [sprint, plannedSprint]);
    const user = userEvent.setup();
    renderApp("/app/issues/1");
    await user.click(await screen.findByRole("button", { name: "Edit issue" }));
    await user.selectOptions(await screen.findByLabelText("Sprint"), value);
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(calls.find((call) => call.method === "PATCH")?.body).toEqual({
        sprint_id: value ? 2 : null,
      }),
    );
  },
);
test("sprint 401 uses global logout", async () => {
  reply("GET", "/sprints/1", { detail: "Expired" }, 401);
  renderApp("/app/sprints/1");
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
test("list error stays local to sprint section", async () => {
  reply("GET", "/projects/1/sprints", {}, 503);
  renderApp("/app/projects/1");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The service is unavailable",
  );
  expect(await screen.findByText(issue.title)).toBeInTheDocument();
});
test("invalid sprint response is rejected by central Zod validation", async () => {
  reply("GET", "/sprints/1", { ...sprint, start_date: "not-a-date" });
  await expect(sprintsApi.get(1)).rejects.toThrow(
    "The service returned an unexpected response.",
  );
});
test("unchanged metadata does not send PATCH", async () => {
  const user = userEvent.setup();
  renderApp("/app/sprints/1");
  await user.click(await screen.findByRole("button", { name: "Edit sprint" }));
  await user.click(screen.getByRole("button", { name: "Save sprint changes" }));
  expect(screen.queryByLabelText("Sprint name")).not.toBeInTheDocument();
  expect(calls.some((call) => call.method === "PATCH")).toBe(false);
});
test("sprint deep link preserves backend filter", async () => {
  renderApp("/app/projects/1/issues?sprint_id=1&status=in_progress");
  await screen.findByText(issue.title);
  expect(screen.getByLabelText("Filter sprint")).toHaveValue("1");
  expect(
    calls.find((call) => call.path === "/projects/1/issues")?.params,
  ).toEqual({ sprint_id: 1, status: "in_progress" });
});
test("loading sprints does not block project issues", async () => {
  let finish: (value: { data: (typeof sprint)[] }) => void = () => {
    throw new Error("Not started");
  };
  handlers.set(
    "GET /projects/1/sprints",
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  renderApp("/app/projects/1");
  expect(await screen.findByText("Loading sprints…")).toHaveAttribute(
    "role",
    "status",
  );
  expect(await screen.findByText(issue.title)).toBeInTheDocument();
  await act(async () => finish({ data: [sprint] }));
  expect(
    await screen.findByRole("link", { name: sprint.name }),
  ).toBeInTheDocument();
});
test.each([403, 404])("sprint detail %s does not log out", async (status) => {
  reply("GET", "/sprints/1", { detail: "Sprint unavailable" }, status);
  renderApp("/app/sprints/1");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Sprint unavailable",
  );
  expect(getToken()).toBe("test-token");
});
