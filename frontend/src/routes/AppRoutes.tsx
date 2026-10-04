import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useParams,
  Link,
} from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Loading } from "../components/Feedback";
import { AppLayout } from "../layouts/AppLayout";
import { AuthPage } from "../pages/AuthPage";
import { TeamsPage } from "../pages/TeamsPage";
import { TeamPage } from "../pages/TeamPage";
import { ProjectPage } from "../pages/ProjectPage";
import { SprintPage } from "../pages/SprintPage";
import { IssuePage } from "../pages/IssuePage";
function Protected() {
  const auth = useAuth();
  return auth.loading ? (
    <Loading label="Restoring your session…" />
  ) : auth.authenticated ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace />
  );
}
function Guest() {
  const auth = useAuth();
  return auth.loading ? (
    <Loading label="Restoring your session…" />
  ) : auth.authenticated ? (
    <Navigate to="/app/teams" replace />
  ) : (
    <Outlet />
  );
}
function NotFound() {
  return (
    <div className="empty">
      <h1>Page not found</h1>
      <Link to="/app/teams">Return to your teams</Link>
    </div>
  );
}
function ResourcePage({
  kind,
}: {
  kind: "team" | "project" | "issue" | "sprint";
}) {
  const params = useParams();
  const value = params[`${kind}Id`];
  const id = Number(value);
  if (!value || !/^\d+$/.test(value) || !Number.isSafeInteger(id) || id < 1)
    return <NotFound />;
  if (kind === "team") return <TeamPage key={id} id={id} />;
  if (kind === "project") return <ProjectPage key={id} id={id} />;
  if (kind === "sprint") return <SprintPage key={id} id={id} />;
  return <IssuePage key={id} id={id} />;
}
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/teams" replace />} />
      <Route element={<Guest />}>
        <Route path="/login" element={<AuthPage key="login" />} />
        <Route
          path="/register"
          element={<AuthPage key="register" register />}
        />
      </Route>
      <Route element={<Protected />}>
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="teams" replace />} />
          <Route path="teams" element={<TeamsPage />} />
          <Route path="teams/:teamId" element={<ResourcePage kind="team" />} />
          <Route
            path="projects/:projectId"
            element={<ResourcePage kind="project" />}
          />
          <Route
            path="projects/:projectId/issues"
            element={<ResourcePage kind="project" />}
          />
          <Route
            path="issues/:issueId"
            element={<ResourcePage kind="issue" />}
          />
          <Route
            path="sprints/:sprintId"
            element={<ResourcePage kind="sprint" />}
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
