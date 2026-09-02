import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, AUTH_EXPIRED_EVENT, clearToken, getRefreshToken, getToken, setSession } from "./api";
import { clearCatalogs } from "./offline";

interface AuthState {
  user: any | null;
  loading: boolean;
  login: (email: string, password: string, totp?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({} as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const onExpired = () => {
      clearCatalogs().catch(() => {});
      setUser(null);
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  useEffect(() => {
    (async () => {
      if (getToken() || getRefreshToken()) {
        try {
          setUser(await api.me());
        } catch {
          clearToken();
        }
      }
      setLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string, totp?: string) => {
    const res = await api.login(email, password, totp);
    setSession(res.access_token, res.refresh_token);
    setUser(await api.me());
  };

  const logout = () => {
    clearToken();
    clearCatalogs().catch(() => {});
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
