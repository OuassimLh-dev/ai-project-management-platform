import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api/auth";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorMessage } from "../components/Feedback";
export function AuthPage({ register = false }: { register?: boolean }) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [registered, setRegistered] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    setError(null);
    setPending(true);
    try {
      if (register) {
        await authApi.register({
          email,
          password,
          first_name: String(form.get("first_name") ?? "").trim(),
          last_name: String(form.get("last_name") ?? "").trim(),
        });
        setRegistered(true);
      } else {
        await login({ email, password });
        navigate("/app/teams", { replace: true });
      }
    } catch (reason: unknown) {
      setError(errorMessage(reason));
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="auth-page">
      <aside className="auth-story">
        <Link className="brand" to="/">
          ▦ <span>Project Workspace</span>
        </Link>
        <div>
          <p className="eyebrow">FROM IDEA TO DELIVERY</p>
          <h1>
            Good work starts
            <br />
            with a clear plan.
          </h1>
          <p>
            Bring your team, projects, and conversations into one focused
            workspace.
          </p>
        </div>
        <p className="muted">AI-Powered Software Project Management Platform</p>
      </aside>
      <main className="auth-main">
        <div className="auth-card">
          <p className="eyebrow">YOUR WORKSPACE</p>
          <h2>{register ? "Create your account" : "Welcome back"}</h2>
          <p>
            {register
              ? "Start organizing work with your team."
              : "Sign in to pick up where you left off."}
          </p>
          {registered ? (
            <div role="status">
              <p>Your account is ready.</p>
              <Link className="button" to="/login">
                Continue to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={submit} className="stack">
              {register && (
                <div className="form-grid">
                  <label>
                    First name
                    <input
                      name="first_name"
                      required
                      maxLength={100}
                      autoComplete="given-name"
                      pattern=".*\S.*"
                    />
                  </label>
                  <label>
                    Last name
                    <input
                      name="last_name"
                      required
                      maxLength={100}
                      autoComplete="family-name"
                      pattern=".*\S.*"
                    />
                  </label>
                </div>
              )}
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  required
                  maxLength={254}
                  autoComplete="email"
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  required
                  minLength={register ? 8 : 1}
                  maxLength={128}
                  autoComplete={register ? "new-password" : "current-password"}
                />
              </label>
              {register && <small>Use at least 8 characters.</small>}
              <ErrorMessage message={error} />
              <button disabled={pending}>
                {pending
                  ? "Please wait…"
                  : register
                    ? "Create account"
                    : "Sign in"}
              </button>
            </form>
          )}
          <p className="auth-switch">
            {register ? "Already have an account?" : "New to the workspace?"}{" "}
            <Link to={register ? "/login" : "/register"}>
              {register ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
