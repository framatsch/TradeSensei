/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * Zustand store for authentication state (token + current user).
 */

import { create } from "zustand";
import type { User } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: User | null;
  /** True once hydrate() has read from localStorage — prevents false redirects. */
  hydrated: boolean;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  hydrated: false,

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
      try {
        const token = localStorage.getItem("access_token");
        set({ token: token ?? null, hydrated: true });
      } catch (error) {
        console.warn("localStorage access denied:", error);
        set({ token: null, hydrated: true });
      }
    }
  },
}));
