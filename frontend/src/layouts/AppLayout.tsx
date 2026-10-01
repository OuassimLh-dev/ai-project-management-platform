import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
export function AppLayout() {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <NavLink to="/app/teams" className="brand">
          ▦{" "}
          <span>
            Project
            <br />
            Workspace
          </span>
        </NavLink>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          <NavLink to="/app/teams">
            ▧ <span>Teams & projects</span>
          </NavLink>
        </nav>
        <p className="sidebar-note">
          A shared place
          <br />
          for work that matters.
        </p>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>Team workspace</span>
          <div className="account">
            <span>
              <strong>
                {user?.first_name} {user?.last_name}
              </strong>
              <small>{user?.email}</small>
            </span>
            <button className="secondary" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
        <main id="main" className="main-content">
          <Outlet />
        </main>
        <footer>
          Project Workspace <span>Plan. Collaborate. Deliver.</span>
        </footer>
      </div>
    </div>
  );
}
