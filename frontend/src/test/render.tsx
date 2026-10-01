import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { setToken } from "../auth/tokenStorage";
import { AppRoutes } from "../routes/AppRoutes";
export function renderApp(path = "/app/teams", authenticated = true) {
  if (authenticated) setToken("test-token");
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}
