import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp } from "./render";
import { getToken, setToken } from "../auth/tokenStorage";
import { calls, reply } from "./server";

test("login renders and protects application routes", async () => {
  renderApp("/app/issues/1", false);
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Fix password reset" }),
  ).not.toBeInTheDocument();
});
test("successful login stores token, loads account and enters app", async () => {
  const user = userEvent.setup();
  renderApp("/login", false);
  await user.type(await screen.findByLabelText("Email"), "sara@example.com");
  await user.type(screen.getByLabelText("Password"), "password123");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(
    await screen.findByRole("heading", { name: "Your teams" }),
  ).toBeInTheDocument();
  expect(getToken()).toBe("test-token");
  expect(calls.find((call) => call.path === "/auth/login")?.body).toEqual({
    email: "sara@example.com",
    password: "password123",
  });
});
test("login failure displays an error", async () => {
  reply(
    "POST",
    "/auth/login",
    { detail: "Could not validate credentials" },
    401,
  );
  const user = userEvent.setup();
  renderApp("/login", false);
  await user.type(await screen.findByLabelText("Email"), "sara@example.com");
  await user.type(screen.getByLabelText("Password"), "wrong");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not validate credentials",
  );
  expect(getToken()).toBeNull();
});
test("stored token restores session and logout clears it", async () => {
  const user = userEvent.setup();
  renderApp();
  expect(
    await screen.findByRole("heading", { name: "Your teams" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Sara Demo")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Log out" }));
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
test("expired stored token clears session", async () => {
  reply("GET", "/auth/me", { detail: "Expired" }, 401);
  renderApp();
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
test("401 from protected API transitions to login", async () => {
  reply("GET", "/teams", { detail: "Expired" }, 401);
  renderApp();
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
  expect(getToken()).toBeNull();
});
test("registration sends exact fields and leads to login", async () => {
  const user = userEvent.setup();
  renderApp("/register", false);
  await user.type(await screen.findByLabelText("First name"), "Sara");
  await user.type(screen.getByLabelText("Last name"), "Demo");
  await user.type(screen.getByLabelText("Email"), "sara@example.com");
  await user.type(screen.getByLabelText("Password"), "password123");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByText("Your account is ready.")).toBeInTheDocument();
  expect(calls.find((call) => call.path === "/auth/register")?.body).toEqual({
    first_name: "Sara",
    last_name: "Demo",
    email: "sara@example.com",
    password: "password123",
  });
  expect(getToken()).toBeNull();
});
test("authenticated users visiting login enter the workspace", async () => {
  setToken("test-token");
  renderApp("/login");
  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: "Your teams" }),
    ).toBeInTheDocument(),
  );
});
