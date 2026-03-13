/**
 * Zustand store for authentication state (token + current user).
 */

import { create } from "zustand";
import type { User } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: User | null;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,

  setToken: (token: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", token);
    }
    set({ token });
  },

  setUser: (user: User) => {
    set({ user });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
    }
    set({ token: null, user: null });
  },

  hydrate: () => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        set({ token });
      }
    }
  },
}));
