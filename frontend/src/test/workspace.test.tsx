import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "./render";
import { calls, handlers, reply } from "./server";
import { comment, issue } from "./fixtures";

test("team list and project navigation", async () => {
  const user = userEvent.setup();
  renderApp();
  await user.click(await screen.findByRole("link", { name: "Platform team" }));
  await user.click(
    await screen.findByRole("link", { name: "Customer portal" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Customer portal" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("APP-1")).toBeInTheDocument();
});
test("empty team list", async () => {
  reply("GET", "/teams", []);
  renderApp();
  expect(
    await screen.findByText("A place for your next project"),
  ).toBeInTheDocument();
});
test("team API error", async () => {
  reply("GET", "/teams", { detail: "Server failed" }, 500);
  renderApp();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The service is unavailable",
  );
});
test("create team succeeds with mutable fields only", async () => {
  const user = userEvent.setup();
  renderApp();
  await user.click(
    await screen.findByRole("button", { name: "+ Create team" }),
  );
  await user.type(screen.getByLabelText("Name"), "Platform team");
  await user.click(screen.getByRole("button", { name: "Save team" }));
  expect(
    await screen.findByRole("heading", { name: "Platform team" }),
  ).toBeInTheDocument();
  expect(
    calls.find((call) => call.method === "POST" && call.path === "/teams")
      ?.body,
  ).toEqual({ name: "Platform team", description: null });
});
test("create team failure retains form and error", async () => {
  reply("POST", "/teams", { detail: "Cannot create team" }, 400);
  const user = userEvent.setup();
  renderApp();
  await user.click(
    await screen.findByRole("button", { name: "+ Create team" }),
  );
  await user.type(screen.getByLabelText("Name"), "Test");
  await user.click(screen.getByRole("button", { name: "Save team" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Cannot create team",
  );
});
test("owner can create project", async () => {
  const user = userEvent.setup();
  renderApp("/app/teams/1");
  await user.click(
    await screen.findByRole("button", { name: "+ Create project" }),
  );
  await user.type(screen.getByLabelText("Name"), "Customer portal");
  await user.type(screen.getByLabelText(/Project key/), "app");
  await user.click(screen.getByRole("button", { name: "Save project" }));
  expect(
    await screen.findByRole("heading", { name: "Customer portal" }),
  ).toBeInTheDocument();
  expect(
    calls.find(
      (call) => call.method === "POST" && call.path === "/teams/1/projects",
    )?.body,
  ).toEqual({ name: "Customer portal", key: "APP", description: null });
});
test("project creation error is visible", async () => {
  reply(
    "POST",
    "/teams/1/projects",
    { detail: "Project key already exists" },
    409,
  );
  const user = userEvent.setup();
  renderApp("/app/teams/1");
  await user.click(
    await screen.findByRole("button", { name: "+ Create project" }),
  );
  await user.type(screen.getByLabelText("Name"), "Duplicate");
  await user.type(screen.getByLabelText(/Project key/), "APP");
  await user.click(screen.getByRole("button", { name: "Save project" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Project key already exists",
  );
});
test("ordinary team members do not see project creation", async () => {
  reply("GET", "/teams/1/members", [
    { id: 1, team_id: 1, user_id: 1, role: "member", joined_at: "2026-10-01" },
  ]);
  renderApp("/app/teams/1");
  await screen.findByRole("heading", { name: "Platform team" });
  expect(
    screen.queryByRole("button", { name: "+ Create project" }),
  ).not.toBeInTheDocument();
});
test("issue list renders and filter sends backend query", async () => {
  const user = userEvent.setup();
  renderApp("/app/projects/1/issues");
  expect(await screen.findByText("APP-1")).toBeInTheDocument();
  expect(screen.getByText("Fix password reset")).toBeInTheDocument();
  expect(screen.getByText("High", { selector: ".badge" })).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Filter status"), "done");
  await waitFor(() =>
    expect(
      calls.filter((call) => call.path === "/projects/1/issues").at(-1)?.params,
    ).toEqual({ status: "done" }),
  );
});
test("filtered empty and API errors are visible", async () => {
  reply("GET", "/projects/1/issues", []);
  renderApp("/app/projects/1/issues?status=done");
  expect(await screen.findByText("No matching issues")).toBeInTheDocument();
});
test("create issue sends no immutable fields", async () => {
  const user = userEvent.setup();
  renderApp("/app/projects/1");
  await user.click(
    await screen.findByRole("button", { name: "+ Create issue" }),
  );
  await user.type(screen.getByLabelText("Title"), "Fix password reset");
  await screen.findByLabelText("Assignee");
  await user.click(screen.getByRole("button", { name: "Save issue" }));
  expect(
    await screen.findByRole("heading", { name: "Fix password reset" }),
  ).toBeInTheDocument();
  expect(
    calls.find(
      (call) => call.method === "POST" && call.path === "/projects/1/issues",
    )?.body,
  ).toEqual({
    title: "Fix password reset",
    description: null,
    issue_type: "task",
    priority: "medium",
    status: "backlog",
    assignee_id: null,
    sprint_id: null,
  });
});
test("detail shows issue, comments and read-only activity", async () => {
  renderApp("/app/issues/1");
  expect(
    await screen.findByRole("heading", { name: "Fix password reset" }),
  ).toBeInTheDocument();
  expect(
    await screen.findByText("I can reproduce this on the sign-in page."),
  ).toBeInTheDocument();
  expect(await screen.findByText("Created by User #1")).toBeInTheDocument();
  const section = screen
    .getByRole("heading", { name: "Activity" })
    .closest("section");
  if (!section) throw new Error("Missing activity section");
  expect(within(section).queryByRole("button")).not.toBeInTheDocument();
  expect(within(section).getByText(/Status/)).toBeInTheDocument();
});
test("edit issue sends only changed mutable fields", async () => {
  reply("PATCH", "/issues/1", { ...issue, title: "Updated title" });
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  await user.click(await screen.findByRole("button", { name: "Edit issue" }));
  const title = screen.getByLabelText("Title");
  await user.clear(title);
  await user.type(title, "Updated title");
  await screen.findByLabelText("Assignee");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    await screen.findByRole("heading", { name: "Updated title" }),
  ).toBeInTheDocument();
  expect(
    calls.find((call) => call.method === "PATCH" && call.path === "/issues/1")
      ?.body,
  ).toEqual({ title: "Updated title" });
});
test.each([
  ["create", "success"],
  ["edit", "success"],
  ["create", "failure"],
  ["edit", "failure"],
] as const)("issue %s locks draft until save %s", async (mode, outcome) => {
  const method = mode === "create" ? "POST" : "PATCH";
  const path = mode === "create" ? "/projects/1/issues" : "/issues/1";
  let complete: (value: { data: unknown; status: number }) => void = () => {
    throw new Error("Not started");
  };
  handlers.set(
    `${method} ${path}`,
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  const user = userEvent.setup();
  renderApp(mode === "create" ? "/app/projects/1" : "/app/issues/1");
  await user.click(await screen.findByRole("button", {
    name: mode === "create" ? "+ Create issue" : "Edit issue",
  }));
  await screen.findByLabelText("Assignee");
  const draft = {
    title: "Saved issue title",
    description: "Saved issue description",
    issue_type: "feature",
    priority: "low",
    status: "done",
    assignee_id: 2,
    sprint_id: 1,
  };
  const title = screen.getByLabelText("Title");
  const description = screen.getByLabelText("Description");
  await user.clear(title);
  await user.type(title, draft.title);
  await user.clear(description);
  await user.type(description, draft.description);
  const selections: [string, string, string][] = [
    ["Type", draft.issue_type, "task"],
    ["Priority", draft.priority, "high"],
    ["Status", draft.status, "backlog"],
    ["Assignee", String(draft.assignee_id), ""],
    ["Sprint", String(draft.sprint_id), ""],
  ];
  for (const [label, value] of selections) {
    await user.selectOptions(screen.getByLabelText(label), value);
  }
  await user.click(screen.getByRole("button", {
    name: mode === "create" ? "Save issue" : "Save changes",
  }));
  const fields = [title, description, ...selections.map(([label]) =>
    screen.getByLabelText(label))];
  for (const field of fields) expect(field).toBeDisabled();
  expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  await user.type(title, " lost edit");
  await user.type(description, " lost edit");
  for (const [label, , alternative] of selections) {
    await user.selectOptions(screen.getByLabelText(label), alternative);
  }
  const expectDraft = () => {
    expect(title).toHaveValue(draft.title);
    expect(description).toHaveValue(draft.description);
    for (const [label, value] of selections) {
      expect(screen.getByLabelText(label)).toHaveValue(value);
    }
  };
  expectDraft();
  expect(calls.filter((call) => call.method === method && call.path === path))
    .toHaveLength(1);
  const { sprint_id, ...changedDraft } = draft;
  expect(calls.find((call) => call.method === method && call.path === path)?.body)
    .toEqual(mode === "create" ? draft : changedDraft);
  if (outcome === "success") {
    const saved = { ...issue, ...draft };
    reply("GET", "/issues/1", saved);
    await act(async () => complete({ data: saved, status: 200 }));
    expect(await screen.findByRole("heading", { name: draft.title }))
      .toBeInTheDocument();
    expect(screen.getByText(draft.description)).toBeInTheDocument();
    expect(screen.getByText("Done", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit issue" })).toBeEnabled();
  } else {
    await act(async () => complete({
      data: { detail: "Issue save rejected" }, status: 400,
    }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Issue save rejected");
    expect(screen.getByRole("heading", {
      name: mode === "create" ? "Create issue" : "Edit issue",
    })).toBeInTheDocument();
    expectDraft();
    for (const field of fields) expect(field).toBeEnabled();
    expect(screen.getByRole("button", {
      name: mode === "create" ? "Save issue" : "Save changes",
    })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    await user.type(title, " revised");
    expect(title).toHaveValue(draft.title + " revised");
  }
});
test("comment submission locks input until success and submits only body", async () => {
  const returnedComment = { ...comment, id: 2, body: "New comment" };
  let complete: (value: { data: typeof comment }) => void = () => {
    throw new Error("Not started");
  };
  handlers.set(
    "POST /issues/1/comments",
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  await user.type(
    await screen.findByLabelText("Add a comment"),
    " New comment ",
  );
  await user.click(screen.getByRole("button", { name: "Post comment" }));
  const textarea = screen.getByLabelText("Add a comment");
  expect(textarea).toBeDisabled();
  expect(screen.getByRole("button", { name: "Posting…" })).toBeDisabled();
  await user.type(textarea, "Unsent edits");
  expect(textarea).toHaveValue(" New comment ");
  await act(async () => complete({ data: returnedComment }));
  expect(await screen.findByText("New comment")).toBeInTheDocument();
  expect(textarea).toHaveValue("");
  expect(textarea).toBeEnabled();
  await user.type(textarea, "Next draft");
  expect(textarea).toHaveValue("Next draft");
  expect(
    calls.find(
      (call) => call.method === "POST" && call.path.endsWith("/comments"),
    )?.body,
  ).toEqual({ body: "New comment" });
});
test("comment submission locks input until failure and retains text", async () => {
  let complete: (value: { data: { detail: string }; status: number }) => void =
    () => {
      throw new Error("Not started");
    };
  handlers.set(
    "POST /issues/1/comments",
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  await user.type(await screen.findByLabelText("Add a comment"), "Keep this");
  await user.click(screen.getByRole("button", { name: "Post comment" }));
  const textarea = screen.getByLabelText("Add a comment");
  expect(textarea).toBeDisabled();
  expect(screen.getByRole("button", { name: "Posting…" })).toBeDisabled();
  await user.type(textarea, "Unsent edits");
  expect(textarea).toHaveValue("Keep this");
  await act(async () =>
    complete({ data: { detail: "Comment rejected" }, status: 400 }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Comment rejected",
  );
  expect(textarea).toHaveValue("Keep this");
  expect(textarea).toBeEnabled();
  expect(screen.getByRole("button", { name: "Post comment" })).toBeEnabled();
  await user.type(textarea, " revised");
  expect(textarea).toHaveValue("Keep this revised");
});
test("issue unavailable state", async () => {
  reply("GET", "/issues/1", { detail: "Issue not found" }, 404);
  renderApp("/app/issues/1");
  expect(await screen.findByRole("alert")).toHaveTextContent("Issue not found");
});
