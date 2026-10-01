import { z } from "zod";
import { API_BASE_URL, ApiError, request } from "../api/client";
import { getToken, setToken } from "../auth/tokenStorage";
import { calls, reply } from "./server";

test("uses central base URL, JSON and Bearer token", async () => {
  setToken("private-token");
  reply("POST", "/test", { value: "ok" });
  expect(
    await request("/test", z.object({ value: z.string() }), {
      method: "POST",
      body: { name: "Test" },
    }),
  ).toEqual({ value: "ok" });
  expect(calls[0]).toMatchObject({
    baseURL: API_BASE_URL,
    authorization: "Bearer private-token",
    body: { name: "Test" },
  });
});
test("does not attach authorization without a token", async () => {
  reply("GET", "/test", "ok");
  await request("/test", z.string());
  expect(calls[0]?.authorization).toBeUndefined();
});
test("handles empty 204 response", async () => {
  reply("DELETE", "/test", "", 204);
  expect(
    await request("/test", z.undefined(), { method: "DELETE" }),
  ).toBeUndefined();
});
test.each([400, 403, 404])(
  "preserves status %s without logging out",
  async (status) => {
    setToken("private-token");
    reply("GET", "/test", { detail: "Not available" }, status);
    await expect(request("/test", z.string())).rejects.toMatchObject({
      status,
      detail: "Not available",
    });
    expect(getToken()).toBe("private-token");
  },
);
test("422 validation is readable", async () => {
  reply(
    "POST",
    "/test",
    { detail: [{ loc: ["body", "name"], msg: "Missing" }] },
    422,
  );
  await expect(
    request("/test", z.string(), { method: "POST" }),
  ).rejects.toMatchObject({
    status: 422,
    detail: "Please check the form values and try again.",
  });
});
test("never includes token or upstream internals in public errors", async () => {
  setToken("private-token");
  reply("GET", "/test", { detail: "Invalid private-token" }, 401);
  await expect(request("/test", z.string())).rejects.toMatchObject({
    status: 401,
    detail: "Invalid [redacted]",
  });
  expect(getToken()).toBeNull();
  reply("GET", "/test", { detail: "Traceback and secret" }, 500);
  await expect(request("/test", z.string())).rejects.toMatchObject({
    detail: "The service is unavailable. Please try again.",
  });
});
test("rejects malformed successful responses", async () => {
  reply("GET", "/test", { wrong: true });
  await expect(request("/test", z.string())).rejects.toBeInstanceOf(ApiError);
});
