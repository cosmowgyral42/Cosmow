import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { supabase } from "../../lib/supabase.js";
import { apiRequest } from "../../lib/apiClient.js";
import * as authService from "./authService.js";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      setAuthError("Supabase is not configured. Check frontend/.env.");
      return undefined;
    }

    let active = true;

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (!active || event === "TOKEN_REFRESHED") return;

      setSession(nextSession);

      if (!nextSession) {
        setUser(null);
        setAuthError("");
        setLoading(false);
      }
    });

    supabase.auth.getSession()
      .then(({ data, error }) => {
        if (!active) return;

        if (error) {
          setAuthError("Unable to restore your session. Please sign in again.");
          setSession(null);
          setUser(null);
          setLoading(false);
          return;
        }

        setSession(data.session);

        if (!data.session) {
          setLoading(false);
        }
      })
      .catch(() => {
        if (!active) return;

        setAuthError("Unable to restore your session. Please sign in again.");
        setSession(null);
        setUser(null);
        setLoading(false);
      });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    let active = true;

    if (!session) {
      setUser(null);
      setLoading(false);
      return undefined;
    }

    setUser(null);
    setAuthError("");
    setLoading(true);

    apiRequest("auth/me")
      .then((profile) => {
        if (active) setUser(profile);
      })
      .catch((error) => {
        if (active) {
          setUser(null);
          setAuthError(
            error.message || "Could not verify your account with the backend."
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [session]);

  const register = useCallback(
    (email, password) => authService.signUp(email, password),
    []
  );

  const login = useCallback(
    (email, password) => authService.signIn(email, password),
    []
  );

  const logout = useCallback(
    () => authService.signOut(),
    []
  );

  const value = useMemo(
    () => ({
      session,
      user,
      loading,
      authError,
      isAuthenticated: Boolean(session && user),
      register,
      login,
      logout,
    }),
    [session, user, loading, authError, register, login, logout]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
