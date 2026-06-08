import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { TokenRes, UserProfile } from "@/lib/api/v2";

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  setToken: (token: string | null) => void;
  setUser: (user: UserProfile | null) => void;
  setAuth: (res: TokenRes) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isLoading: false,
      error: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setAuth: (res) => {
        localStorage.setItem("cran_v2_auth_token", res.access_token);
        set({ token: res.access_token, user: res.user, error: null });
      },
      clearAuth: () => {
        localStorage.removeItem("cran_v2_auth_token");
        set({ token: null, user: null, error: null });
      },
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
    }),
    {
      name: "cran-auth-store",
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);
