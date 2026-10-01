import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "./render";
import { calls, reply } from "./server";
import { issue } from "./fixtures";

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
test("comment submits only body", async () => {
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  await user.type(
    await screen.findByLabelText("Add a comment"),
    " New comment ",
  );
  await user.click(screen.getByRole("button", { name: "Post comment" }));
  expect(await screen.findByText("New comment")).toBeInTheDocument();
  expect(
    calls.find(
      (call) => call.method === "POST" && call.path.endsWith("/comments"),
    )?.body,
  ).toEqual({ body: "New comment" });
});
test("comment failure retains text", async () => {
  reply("POST", "/issues/1/comments", { detail: "Comment rejected" }, 400);
  const user = userEvent.setup();
  renderApp("/app/issues/1");
  await user.type(await screen.findByLabelText("Add a comment"), "Keep this");
  await user.click(screen.getByRole("button", { name: "Post comment" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Comment rejected",
  );
  expect(screen.getByLabelText("Add a comment")).toHaveValue("Keep this");
});
test("issue unavailable state", async () => {
  reply("GET", "/issues/1", { detail: "Issue not found" }, 404);
  renderApp("/app/issues/1");
  expect(await screen.findByRole("alert")).toHaveTextContent("Issue not found");
});
