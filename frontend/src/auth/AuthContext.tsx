import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "../api/auth";
import { clearToken, getToken, onTokenCleared, setToken } from "./tokenStorage";
import type { LoginInput, User } from "../types/api";
type AuthState = {
  user: User | null;
  loading: boolean;
  authenticated: boolean;
  login: (input: LoginInput) => Promise<void>;
  logout: () => void;
};
const AuthContext = createContext<AuthState | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const generation = useRef(0);
  const logout = useCallback(() => {
    generation.current++;
    clearToken();
    setUser(null);
    setLoading(false);
  }, []);
  useEffect(() => {
    const unsubscribe = onTokenCleared(() => {
      generation.current++;
      setUser(null);
      setLoading(false);
    });
    const current = ++generation.current;
    if (!getToken()) setLoading(false);
    else
      void authApi
        .me()
        .then((result) => {
          if (current === generation.current) setUser(result);
        })
        .catch(() => {
          if (current === generation.current) logout();
        })
        .finally(() => {
          if (current === generation.current) setLoading(false);
        });
    return () => {
      generation.current++;
      unsubscribe();
    };
  }, [logout]);
  async function login(input: LoginInput) {
    const current = ++generation.current;
    const result = await authApi.login(input);
    if (current !== generation.current) return;
    setToken(result.access_token);
    try {
      const account = await authApi.me();
      if (current === generation.current) setUser(account);
    } catch (error: unknown) {
      if (current === generation.current) logout();
      throw error;
    }
  }
  return (
    <AuthContext.Provider
      value={{ user, loading, authenticated: user !== null, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider is required");
  return context;
}
