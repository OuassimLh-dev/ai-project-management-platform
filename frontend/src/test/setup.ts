import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { resetServer } from "./server";
beforeEach(() => {
  sessionStorage.clear();
  resetServer();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
