import { useEffect, useState, useCallback } from "react";
import { User } from "@/types";
import { api, setAuthToken } from "@/lib/api";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setLoading(false);
        return;
      }
      
      setAuthToken(token);
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
    } catch (error) {
      console.error("Failed to fetch user", error);
      setUser(null);
      localStorage.removeItem("auth_token");
      setAuthToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token");
    setAuthToken(null);
    setUser(null);
  }, []);

  return { user, loading, logout, refetch: fetchUser };
}
