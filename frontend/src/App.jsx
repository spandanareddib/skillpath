import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import AuthPage from "./AuthPage";
import Dashboard from "./Dashboard";

const TOKEN_KEY = "skillpath_token";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [notice, setNotice] = useState("");

  const logout = useCallback((message = "") => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setNotice(message);
  }, []);

  function login(newToken) {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setNotice("");
  }

  // Whenever we hold a token, confirm it is still valid and learn who the user is.
  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    api
      .me(token)
      .then((u) => !cancelled && setUser(u))
      .catch((err) => !cancelled && logout(err.status === 401 ? "Your session expired. Please log in again." : err.message));
    return () => {
      cancelled = true;
    };
  }, [token, logout]);

  if (!token) return <AuthPage onLogin={login} notice={notice} />;
  if (!user) return <p className="center">Loading...</p>;
  return <Dashboard token={token} user={user} onLogout={logout} />;
}
