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

import { create } from "zustand";

const STORAGE_KEY = "desktopSidebarOpen";

function readFromStorage(): boolean {
  if (typeof window === "undefined") return true;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored !== null ? stored === "true" : true;
}

interface SidebarState {
  desktopSidebarOpen: boolean;
  toggle: () => void;
  setOpen: (open: boolean) => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  desktopSidebarOpen: readFromStorage(),
  toggle: () =>
    set((state) => {
      const next = !state.desktopSidebarOpen;
      window.localStorage.setItem(STORAGE_KEY, String(next));
      return { desktopSidebarOpen: next };
    }),
  setOpen: (open: boolean) => {
    window.localStorage.setItem(STORAGE_KEY, String(open));
    set({ desktopSidebarOpen: open });
  },
}));
